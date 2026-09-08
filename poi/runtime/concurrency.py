"""POI 동시성 — 스레드 기반 고수준 API (v1.12).

파이썬 표준 라이브러리(threading·queue)만 쓴다. 새 VM·이벤트 루프 없음.

    use 없이 바로:  task
      task.run(fn, *args)        -> 핸들 (바로 시작)
      task.wait(handle)          -> 결과 (오류는 그대로 다시 던짐)
      task.all([fn1, fn2, ...])  -> 결과 리스트 (전부 병렬, 전부 대기)
      task.all(fn, 목록)          -> 각 항목에 fn 적용, 병렬
      task.race([fn1, fn2])      -> 가장 먼저 끝난 결과
      task.map(fn, 목록, workers=8) -> 순서 유지 결과 (동시 개수 제한)
      task.sleep(초)
      task.every(초, fn)          -> 타이머 (.stop())
      task.after(초, fn)          -> 타이머
      task.channel(크기=0)        -> 채널 (.send / .recv / .close, for 문 순회)
      task.lock()                -> 잠금 (.run(fn) 또는 .acquire()/.release())
      task.cpu_count()

문장 문법도 있다:
      background { ... }          -> task.run 으로 백그라운드 실행
      every 1 second { ... }      -> 1초마다 반복 (프로그램이 사는 동안)
"""
from __future__ import annotations

import os as _os
import queue as _queue
import threading as _threading
import time as _time
from types import SimpleNamespace

from ..errors import POIError
from .boxes import Box


def _fail(msg, code="P320", hint=None):
    return POIError(msg, code, hint=hint)


class Task:
    """task.run 의 결과 핸들."""

    __slots__ = ("_thread", "_result", "_error", "_done", "name")
    _seq = 0

    def __init__(self, fn, args, kwargs):
        Task._seq += 1
        self.name = f"task-{Task._seq}"
        self._result = None
        self._error = None
        self._done = _threading.Event()
        self._thread = _threading.Thread(
            target=self._run, args=(fn, args, kwargs), name=self.name, daemon=True)
        self._thread.start()

    def _run(self, fn, args, kwargs):
        try:
            self._result = fn(*args, **kwargs)
        except BaseException as e:  # noqa: BLE001  (다시 던져 준다)
            self._error = e
        finally:
            self._done.set()

    def wait(self, timeout=None):
        if not self._done.wait(timeout):
            raise _fail("작업이 제한 시간 안에 끝나지 않았습니다.", "P321")
        if self._error is not None:
            if isinstance(self._error, POIError):
                raise self._error
            raise _fail(f"백그라운드 작업에서 오류: {self._error}", "P322")
        return self._result

    @property
    def done(self):
        return self._done.is_set()

    def __repr__(self):
        st = "완료" if self.done else "실행 중"
        return f"<task {self.name} {st}>"


class Channel:
    """스레드 사이로 값을 주고받는 큐. for 문으로 순회하면 close 까지 받는다."""

    __slots__ = ("_q", "_closed")

    def __init__(self, maxsize=0):
        self._q = _queue.Queue(maxsize=int(maxsize) if maxsize else 0)
        self._closed = False

    def send(self, value):
        if self._closed:
            raise _fail("닫힌 채널에는 보낼 수 없습니다.", "P323")
        self._q.put(value)
        return True

    def recv(self, timeout=None):
        try:
            item = self._q.get(timeout=timeout)
        except _queue.Empty:
            raise _fail("채널에서 받을 값이 제한 시간 안에 오지 않았습니다.", "P324")
        if item is _CLOSE:
            self._q.put(_CLOSE)  # 다음 소비자도 끝을 보게
            raise StopIteration
        return item

    def try_recv(self, default=None):
        try:
            item = self._q.get_nowait()
        except _queue.Empty:
            return default
        if item is _CLOSE:
            self._q.put(_CLOSE)
            return default
        return item

    def close(self):
        if not self._closed:
            self._closed = True
            self._q.put(_CLOSE)
        return True

    def take_all(self):
        out = []
        while True:
            try:
                out.append(self.recv())
            except StopIteration:
                break
        return out

    def __iter__(self):
        return self

    def __next__(self):
        return self.recv()

    def __repr__(self):
        return f"<channel {'닫힘' if self._closed else '열림'} 대기 {self._q.qsize()}>"


_CLOSE = object()


class Timer:
    """every / after 로 만든 반복·지연 타이머. .stop() 으로 멈춘다."""

    __slots__ = ("_stop", "_thread", "kind")

    def __init__(self, seconds, fn, repeat):
        self.kind = "every" if repeat else "after"
        self._stop = _threading.Event()
        self._thread = _threading.Thread(
            target=self._loop, args=(float(seconds), fn, repeat),
            name="poi-timer", daemon=True)
        self._thread.start()

    def _loop(self, seconds, fn, repeat):
        while not self._stop.wait(seconds):
            try:
                fn()
            except BaseException:  # noqa: BLE001  (타이머는 계속 돈다)
                import traceback
                traceback.print_exc()
            if not repeat:
                return

    def stop(self):
        self._stop.set()
        return True

    @property
    def running(self):
        return not self._stop.is_set() and self._thread.is_alive()

    def __repr__(self):
        return f"<timer {self.kind} {'동작' if self.running else '멈춤'}>"


class Lock:
    __slots__ = ("_lock",)

    def __init__(self):
        self._lock = _threading.RLock()

    def acquire(self, timeout=-1):
        return self._lock.acquire(timeout=timeout)

    def release(self):
        try:
            self._lock.release()
        except RuntimeError:
            pass
        return True

    def run(self, fn):
        with self._lock:
            return fn()

    def __repr__(self):
        return "<lock>"


# ── 자유 함수 ────────────────────────────────────────────────────────────

def _run(fn, *args, **kwargs):
    if not callable(fn):
        raise _fail("task.run(fn) — 함수를 넘겨 주세요.", "P325")
    return Task(fn, args, kwargs)


def _wait(handle, timeout=None):
    if isinstance(handle, Task):
        return handle.wait(timeout)
    if isinstance(handle, (list, tuple)):
        return [_wait(h, timeout) for h in handle]
    return handle


def _all(fn_or_list, iterable=None):
    if iterable is None:
        tasks = [_run(f) for f in fn_or_list]
        return [t.wait() for t in tasks]
    tasks = [_run(fn_or_list, x) for x in iterable]
    return [t.wait() for t in tasks]


def _race(fns):
    ch = Channel()
    done = _threading.Event()

    def wrap(f):
        def _g():
            try:
                r = f()
            except BaseException as e:  # noqa: BLE001
                r = e
            if not done.is_set():
                done.set()
                ch.send(r)
        return _g

    for f in fns:
        Task(wrap(f), (), {})
    r = ch.recv()
    if isinstance(r, BaseException):
        if isinstance(r, POIError):
            raise r
        raise _fail(f"race 작업에서 오류: {r}", "P322")
    return r


def _map(fn, iterable, workers=8):
    items = list(iterable)
    out = [None] * len(items)
    sem = _threading.Semaphore(max(1, int(workers)))
    threads = []

    def work(i, x):
        with sem:
            out[i] = fn(x)

    for i, x in enumerate(items):
        t = _threading.Thread(target=work, args=(i, x), daemon=True)
        t.start()
        threads.append(t)
    for t in threads:
        t.join()
    return out


def _every(seconds, fn):
    return Timer(seconds, fn, repeat=True)


def _after(seconds, fn):
    return Timer(seconds, fn, repeat=False)


def _sleep(seconds):
    _time.sleep(max(0.0, float(seconds)))
    return True


task = SimpleNamespace(
    run=_run,
    wait=_wait,
    gather=_wait,
    all=_all,
    race=_race,
    map=_map,
    sleep=_sleep,
    every=_every,
    after=_after,
    channel=lambda maxsize=0: Channel(maxsize),
    queue=lambda maxsize=0: Channel(maxsize),
    lock=lambda: Lock(),
    cpu_count=lambda: _os.cpu_count() or 1,
    now=_time.perf_counter,
)

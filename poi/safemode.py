"""안전 모드 (v1.2).

`poi run --safe` 와 플레이그라운드 서버가 쓴다. 모르는 사람의 코드를
받아서 실행해도 서버가 안 터지게 하는 게 목적이다.

막는 것:
  · python { ... } 원문 블록          (임의 파이썬 실행)
  · use py:...  /  use pyfile "..."    (임의 라이브러리 로드)
  · use file  /  use web  및 file.*/web.* (파일·네트워크 접근)
  · 위험한 파이썬 내장 (open, __import__, eval, exec, compile, input …)
  · 무한 루프 → 벽시계 시간 제한
  · 출력 폭탄 → 출력 바이트 제한
"""
from __future__ import annotations

import _thread
import builtins as _builtins
import contextlib
import sys
import threading

from .errors import POIError

_SAFE_NAMES = {
    "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
    "callable", "chr", "complex", "dict", "divmod", "enumerate", "filter",
    "float", "format", "frozenset", "hash", "hex", "int", "isinstance",
    "issubclass", "iter", "len", "list", "map", "max", "min", "next", "object",
    "oct", "ord", "pow", "print", "range", "repr", "reversed", "round", "set",
    "slice", "sorted", "str", "sum", "tuple", "type", "zip", "True", "False",
    "None", "NotImplemented", "Ellipsis",
    # 예외 계열 (try/catch 가 잡을 수 있게)
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "ZeroDivisionError", "AttributeError", "RuntimeError", "StopIteration",
    "ArithmeticError", "LookupError", "OverflowError", "NameError",
}

_FORBIDDEN_STD = {"file", "web", "gui", "ui", "env", "shell",
                  # v1.7 — 파일/환경/네트워크에 닿는 것
                  "dotenv", "system", "compress",
                  "압축", "시스템",
                  # v1.10/1.11 — 외부 LLM · GUI
                  "ai", "uikit", "유아이", "지유아이",
                  # v1.12 — 네트워크 · 백그라운드 스레드
                  "http", "net", "task",
                  "요청", "망", "네트워크", "작업", "동시성"}


def safe_builtins() -> dict:
    d = {}
    for name in _SAFE_NAMES:
        if hasattr(_builtins, name):
            d[name] = getattr(_builtins, name)
    return d


def _denied(what: str):
    def _f(*_a, **_kw):
        raise POIError(f"안전 모드에서는 {what} 을(를) 쓸 수 없습니다.", "P210",
                       hint="플레이그라운드가 아닌 곳에서 실행하면 됩니다.")
    return _f


class _Denied:
    def __init__(self, what):
        self._what = what

    def __getattr__(self, _n):
        raise POIError(f"안전 모드에서는 {self._what} 을(를) 쓸 수 없습니다.", "P210")


def harden_globals(g: dict) -> dict:
    """make_globals() 결과를 안전 모드용으로 조인다."""
    g["__builtins__"] = safe_builtins()
    g["file"] = _Denied("파일")
    g["web"] = _Denied("네트워크")
    g["shell"] = _Denied("셸/외부 명령")
    g["env"] = _Denied("환경변수")
    g["ai"] = _Denied("AI(외부 LLM) 호출")
    g["http"] = _Denied("네트워크 요청")
    g["net"] = _Denied("네트워크")
    g["task"] = _Denied("백그라운드 작업")
    g["system"] = _Denied("시스템 정보")
    g["dotenv"] = _Denied(".env 읽기")
    g["compress"] = _Denied("압축")
    g["pause"] = lambda *_a, **_kw: None          # 서버에선 멈출 수 없음
    g["poi_import_pyfile"] = _denied("다른 파일 불러오기")
    g["poi_import_module"] = _denied("다른 파일 불러오기")
    g["poi_import_pkg"] = _denied("패키지 모듈 불러오기")
    g["poi_std"] = _guard_std(g.get("poi_std"))
    g["database"] = _denied("데이터베이스 열기")
    return g


def _guard_std(orig):
    def _f(name):
        if name in _FORBIDDEN_STD:
            raise POIError(f"안전 모드에서는 '{name}' 모듈을 쓸 수 없습니다.", "P210")
        return orig(name) if orig else None
    return _f


# ── AST 검사 (컴파일 단계에서 거절) ───────────────────────────────────

def assert_safe(program) -> None:
    for node in _walk(program):
        k = getattr(node, "kind", None)
        if k in ("Server", "WebApp"):
            raise POIError("안전 모드에서는 server / webapp (포트 열기) 를 쓸 수 없습니다.",
                           "P211", getattr(node, "line", None))
        if k in ("Background", "Every"):
            raise POIError(
                "안전 모드에서는 background / every (백그라운드 스레드) 를 쓸 수 없습니다.",
                "P211", getattr(node, "line", None))
        if k == "PyBlock":
            raise POIError("안전 모드에서는 python { ... } 블록을 쓸 수 없습니다.",
                           "P211", getattr(node, "line", None),
                           hint="POI 문법과 표준 모듈(math·time·json)만 쓰세요.")
        if k == "Use":
            uk = getattr(node, "use_kind", "")
            if uk in ("py", "pyfile", "poimod", "pkgmod"):
                raise POIError("안전 모드에서는 다른 파일·라이브러리를 불러올 수 없습니다.",
                               "P211", getattr(node, "line", None))
            if uk == "std" and getattr(node, "target", "") in _FORBIDDEN_STD:
                raise POIError(
                    f"안전 모드에서는 '{node.target}' 모듈을 쓸 수 없습니다.",
                    "P211", getattr(node, "line", None))


def _walk(node):
    yield node
    for v in vars(node).values() if hasattr(node, "__dict__") else []:
        if hasattr(v, "kind"):
            yield from _walk(v)
        elif isinstance(v, (list, tuple)):
            for it in v:
                if hasattr(it, "kind"):
                    yield from _walk(it)
                elif isinstance(it, (list, tuple)):
                    for it2 in it:
                        if hasattr(it2, "kind"):
                            yield from _walk(it2)


# ── 실행 제한 (시간·출력) ────────────────────────────────────────────

class _CappedWriter:
    def __init__(self, real, limit: int):
        self._real = real
        self._limit = limit
        self._n = 0

    def write(self, s):
        self._n += len(s)
        if self._n > self._limit:
            raise POIError("출력이 너무 많습니다 (안전 모드 한도 초과).", "P212",
                           hint="print/show 를 줄이거나 반복을 줄이세요.")
        return self._real.write(s)

    def flush(self):
        self._real.flush()

    def __getattr__(self, n):
        return getattr(self._real, n)


@contextlib.contextmanager
def limits(time_limit: float = 5.0, output_limit: int = 64_000):
    old_out, old_err = sys.stdout, sys.stderr
    old_rec = sys.getrecursionlimit()
    sys.stdout = _CappedWriter(old_out, output_limit)
    sys.stderr = _CappedWriter(old_err, output_limit)
    sys.setrecursionlimit(min(old_rec, 800))

    timed_out = {"v": False}

    def _kill():
        timed_out["v"] = True
        _thread.interrupt_main()

    timer = threading.Timer(time_limit, _kill)
    timer.daemon = True
    timer.start()
    try:
        yield timed_out
    finally:
        timer.cancel()
        sys.stdout, sys.stderr = old_out, old_err
        sys.setrecursionlimit(old_rec)

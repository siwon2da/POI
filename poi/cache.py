"""컴파일 캐시 (v1.13) — 안 바뀐 `.poi` 는 렉싱·파싱·트랜스파일·compile 을 건너뛴다.

키 = SHA-256( POI 버전 + trace 여부 + 소스 ).  저장 위치:
  `POI_CACHE_DIR` 환경변수  또는  `~/.poi/cache/`

  <키>.json  →  { py, linemap, cn, v }
  <키>.code  →  marshal.dumps(code object)   (compile 까지 건너뜀)

끄기:  `POI_NO_CACHE=1`  또는  `poi run --no-cache`.
안전 모드(--safe)에서는 assert_safe 를 매번 해야 하므로 캐시를 쓰지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import marshal
import os
import sys
import time

from . import __version__

_MAX_ENTRIES = 800
_PRUNE_TO = 500


def enabled() -> bool:
    return os.environ.get("POI_NO_CACHE", "") not in ("1", "true", "yes")


def _dir() -> str:
    d = os.environ.get("POI_CACHE_DIR") or os.path.join(
        os.path.expanduser("~"), ".poi", "cache")
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def _key(src: str, trace: bool) -> str:
    h = hashlib.sha256()
    h.update(__version__.encode("utf-8"))
    h.update(b"\x00trace" if trace else b"\x00plain")
    h.update(b"\x00")
    h.update(src.encode("utf-8", "surrogatepass"))
    return h.hexdigest()


def load(src: str, trace: bool = False):
    """(py_src, linemap, compiled_name) 또는 None."""
    if not enabled():
        return None
    p = os.path.join(_dir(), _key(src, trace) + ".json")
    try:
        with open(p, encoding="utf-8") as f:
            d = json.load(f)
        if d.get("v") != __version__:
            return None
        os.utime(p, None)  # LRU 갱신
        lm = {int(k): v for k, v in d["linemap"].items()}
        return d["py"], lm, d["cn"]
    except (OSError, ValueError, KeyError):
        return None


def save(src: str, trace: bool, py_src: str, linemap: dict, cn: str) -> None:
    if not enabled():
        return
    d = _dir()
    key = _key(src, trace)
    tmp = os.path.join(d, key + ".json.tmp%d" % os.getpid())
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"py": py_src, "linemap": linemap, "cn": cn,
                       "v": __version__}, f, ensure_ascii=False)
        os.replace(tmp, os.path.join(d, key + ".json"))
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        return
    _maybe_prune(d)


def load_code(src: str, trace: bool = False):
    """marshal 로 저장한 code object 또는 None (compile 까지 건너뜀)."""
    if not enabled():
        return None
    p = os.path.join(_dir(), _key(src, trace) + ".code")
    try:
        with open(p, "rb") as f:
            tag = f.read(len(__version__) + 1)
            if tag != (__version__ + "\n").encode("utf-8"):
                return None
            code = marshal.loads(f.read())
        os.utime(p, None)
        return code
    except (OSError, ValueError, EOFError, TypeError):
        return None


def save_code(src: str, trace: bool, code) -> None:
    if not enabled():
        return
    d = _dir()
    key = _key(src, trace)
    tmp = os.path.join(d, key + ".code.tmp%d" % os.getpid())
    try:
        with open(tmp, "wb") as f:
            f.write((__version__ + "\n").encode("utf-8"))
            f.write(marshal.dumps(code))
        os.replace(tmp, os.path.join(d, key + ".code"))
    except (OSError, ValueError):
        try:
            os.unlink(tmp)
        except OSError:
            pass


def _maybe_prune(d: str) -> None:
    try:
        names = [n for n in os.listdir(d) if n.endswith((".json", ".code"))]
        if len(names) <= _MAX_ENTRIES:
            return
        paths = sorted(
            (os.path.join(d, n) for n in names),
            key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0)
        for p in paths[:len(paths) - _PRUNE_TO]:
            try:
                os.unlink(p)
            except OSError:
                pass
    except OSError:
        pass


def clear() -> int:
    d = _dir()
    n = 0
    try:
        for name in os.listdir(d):
            if name.endswith((".json", ".code")) or ".json.tmp" in name \
                    or ".code.tmp" in name:
                try:
                    os.unlink(os.path.join(d, name))
                    n += 1
                except OSError:
                    pass
    except OSError:
        pass
    return n


def info() -> dict:
    d = _dir()
    files = 0
    size = 0
    try:
        for name in os.listdir(d):
            if name.endswith((".json", ".code")):
                files += 1
                try:
                    size += os.path.getsize(os.path.join(d, name))
                except OSError:
                    pass
    except OSError:
        pass
    return {"dir": d, "entries": files, "bytes": size,
            "enabled": enabled(), "version": __version__}


def cmd_cache(args: list[str]) -> int:
    sub = args[0] if args else "info"
    if sub == "clear":
        n = clear()
        print(f"캐시 {n}개 파일을 지웠어요.  ({_dir()})")
        return 0
    d = info()
    mb = d["bytes"] / 1e6
    state = "켜짐" if d["enabled"] else "꺼짐 (POI_NO_CACHE)"
    print(f"POI 컴파일 캐시  —  {state}")
    print(f"  위치 : {d['dir']}")
    print(f"  항목 : {d['entries']}개  ·  {mb:.1f} MB")
    print(f"  버전 : {d['version']}")
    print("  비우기:  poi cache clear")
    return 0

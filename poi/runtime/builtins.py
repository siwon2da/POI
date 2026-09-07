"""POI 기본 함수 (import 없이 항상 쓸 수 있는 것들)."""
from __future__ import annotations

import importlib.util
import json as _json

from ..errors import POIError
from .boxes import Box, boxify


def _disp(v):
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, (dict, list)):
        try:
            return _json.dumps(v, ensure_ascii=False, indent=2, default=str)
        except TypeError:
            return str(v)
    return str(v)


def poi_show(*args):
    print(" ".join(_disp(a) for a in args))


def poi_fmt(v):
    """문자열 보간 `"{x}"` 안에서 값을 한 줄로 (true/false/null)."""
    if v is True:
        return "true"
    if v is False:
        return "false"
    if v is None:
        return "null"
    if isinstance(v, (dict, list)):
        try:
            return _json.dumps(v, ensure_ascii=False, default=str)
        except TypeError:
            return str(v)
    return str(v)


def poi_ask(prompt=""):
    try:
        return input(_disp(prompt))
    except EOFError:
        return ""


def number(x):
    if isinstance(x, bool):
        return 1 if x else 0
    if isinstance(x, (int, float)):
        return x
    s = str(x).strip()
    try:
        if s.lower() in ("true", "false"):
            return 1 if s.lower() == "true" else 0
        if "." in s or "e" in s.lower():
            return float(s)
        return int(s)
    except ValueError:
        raise POIError(f"숫자로 바꿀 수 없습니다: {x!r}", "P110",
                       hint="숫자만 들어있는 문자열인지 확인하세요. 예: number(\"12\")")


def text(x):
    return _disp(x)


def boolean(x):
    if isinstance(x, str):
        return x.strip().lower() not in ("", "false", "0", "null", "no")
    return bool(x)


# -- 점 접근 (문자열/리스트 편의 기능 + 친절한 오류) ---------------------

_STR_EXTRA = {
    "length": lambda s: len(s),
    "is_empty": lambda s: len(s) == 0,
    "contains": lambda s: (lambda sub: sub in s),
    "starts_with": lambda s: (lambda p: s.startswith(p)),
    "ends_with": lambda s: (lambda p: s.endswith(p)),
    "trim": lambda s: (lambda: s.strip()),
    "reverse": lambda s: (lambda: s[::-1]),
    "upper": lambda s: (lambda: s.upper()),
    "lower": lambda s: (lambda: s.lower()),
    "words": lambda s: (lambda: s.split()),
}

_LIST_EXTRA = {
    "length": lambda xs: len(xs),
    "is_empty": lambda xs: len(xs) == 0,
    "first": lambda xs: (xs[0] if xs else None),
    "last": lambda xs: (xs[-1] if xs else None),
    "add": lambda xs: xs.append,
    "remove": lambda xs: (lambda v: xs.remove(v) if v in xs else None),
    "contains": lambda xs: (lambda v: v in xs),
    "reverse": lambda xs: (lambda: list(reversed(xs))),
    "sort": lambda xs: (lambda: sorted(xs)),
    "join": lambda xs: (lambda sep=", ": sep.join(str(x) for x in xs)),
}


def poi_getattr(obj, name):
    # POI 편의 기능을 먼저 본다 (list.sort 처럼 파이썬 기본이
    # 제자리 정렬 + None 반환이라 헷갈리는 경우를 막는다).
    if isinstance(obj, str) and name in _STR_EXTRA:
        return _STR_EXTRA[name](obj)
    if isinstance(obj, (list, tuple)) and name in _LIST_EXTRA:
        return _LIST_EXTRA[name](obj)
    try:
        return getattr(obj, name)
    except AttributeError:
        pass
    if isinstance(obj, dict):
        if name in obj:
            return boxify(obj[name])
        if name == "length":
            return len(obj)
        if name == "keys":
            return lambda: list(obj.keys())
        if name == "values":
            return lambda: list(obj.values())
        if name == "has":
            return lambda k: k in obj
    tname = type(obj).__name__
    raise POIError(f"'{tname}' 값에는 '{name}' 기능이 없습니다.", "P120",
                   hint="이름을 잘못 썼거나, 그 자료형이 지원하지 않는 기능입니다.")


def poi_getattr_safe(obj, name):
    """`obj?.name` - obj 가 null 이거나 그런 항목이 없으면 null."""
    if obj is None:
        return None
    try:
        return poi_getattr(obj, name)
    except (AttributeError, KeyError, POIError):
        return None


def poi_setattr(obj, name, value):
    if isinstance(obj, dict):
        obj[name] = value
        return
    setattr(obj, name, value)


def poi_coalesce(get_left, get_right):
    v = get_left()
    return v if v is not None else get_right()


def poi_error_value(err):
    """catch 로 잡힌 값을 사람이 읽기 좋게."""
    if isinstance(err, POIError):
        return err.message
    return f"{type(err).__name__}: {err}"


def poi_make_error(value):
    """raise <값>  →  예외로."""
    if isinstance(value, BaseException):
        return value
    return POIError(str(value), "P300")


def poi_assert(cond, src=""):
    if not cond:
        raise POIError(f"확인(assert) 실패: {src}".rstrip(": "), "P301",
                       hint="이 조건이 참이어야 하는데 거짓입니다.")


# --- 테스트 레지스트리 (poi test) ------------------------------------

_POI_TESTS: list = []


def poi_register_test(name, fn):
    _POI_TESTS.append((name, fn))


def poi_run_tests() -> int:
    if not _POI_TESTS:
        print("테스트가 없습니다. test \"이름\" { ... assert ... } 로 만드세요.")
        return 0
    ok = bad = 0
    for name, fn in _POI_TESTS:
        try:
            fn()
            print(f"  ✓ {name}")
            ok += 1
        except POIError as e:
            print(f"  ✗ {name}\n      {e.message}")
            bad += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ✗ {name}\n      {type(e).__name__}: {e}")
            bad += 1
    print(f"\n테스트 {ok + bad}개 중  통과 {ok} · 실패 {bad}")
    return 1 if bad else 0


def poi_import_module(path):
    """use \"./다른파일.poi\"  →  그 파일의 함수·변수를 담은 객체."""
    import os
    import sys as _sys
    from ..interpreter import compile_source

    frame = _sys._getframe(1)
    base = frame.f_globals.get("__poi_dir__") or os.getcwd()
    full = os.path.normpath(os.path.join(base, path))
    if not os.path.isfile(full):
        raise POIError(f"POI 모듈을 찾을 수 없습니다: {path}", "P302",
                       hint=f"찾은 경로: {full}")
    with open(full, encoding="utf-8") as f:
        src = f.read()
    py, linemap, cname = compile_source(src, os.path.basename(full))

    from . import make_globals
    g2 = make_globals()
    base_keys = set(g2)
    g2["__name__"] = "__poi_module__"
    g2["__poi_file__"] = full
    g2["__poi_dir__"] = os.path.dirname(full)
    g2["__poi_source__"] = src
    g2["__poi_linemap__"] = linemap
    exec(compile(py, cname, "exec"), g2)  # noqa: S102
    return Box({k: v for k, v in g2.items()
                if k not in base_keys and not k.startswith("__")})


def poi_import_pyfile(path):
    spec = importlib.util.spec_from_file_location("_poi_pyfile", path)
    if spec is None or spec.loader is None:
        raise POIError(f"파이썬 파일을 불러올 수 없습니다: {path}", "P130")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


_STD_CACHE: dict = {}


def poi_std(name):
    if name in _STD_CACHE:
        return _STD_CACHE[name]
    from . import stdmods
    mapping = {
        "file": stdmods.file,
        "json": stdmods.json,
        "web": stdmods.web,
        "math": stdmods.math,
        "time": stdmods.time,
        "regex": stdmods.regex,
        "csv": stdmods.csv,
        "datetime": stdmods.datetime,
        "random": stdmods.random,
        "stats": stdmods.stats,
        "env": stdmods.env,
        "shell": stdmods.shell,
    }
    if name in ("ui", "gui"):
        from . import gui as _guimod
        mapping["ui"] = _guimod
        mapping["gui"] = _guimod
    if name not in mapping:
        raise POIError(f"'{name}' 표준 모듈은 없습니다.", "P021")
    _STD_CACHE[name] = mapping[name]
    return mapping[name]


__all__ = [
    "Box", "boxify", "poi_show", "poi_fmt", "poi_ask", "number", "text", "boolean",
    "poi_getattr", "poi_getattr_safe", "poi_setattr", "poi_coalesce",
    "poi_error_value", "poi_import_pyfile", "poi_std",
]

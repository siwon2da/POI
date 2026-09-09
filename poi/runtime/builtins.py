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


def poi_print(*args, sep=" ", end="\n", file=None, flush=False):
    """파이썬 print 와 호환 — POI 에서 print(...) 를 그대로 써도 된다."""
    import sys as _s
    out = (file or _s.stdout)
    out.write(str(sep).join(_disp(a) for a in args) + str(end))
    if flush:
        try:
            out.flush()
        except Exception:
            pass


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


_ASK_HOOK = {"fn": None}


def poi_set_ask(fn):
    """입력을 받을 방법을 갈아끼운다 (POI IDLE 은 대화상자로). fn(prompt) -> str."""
    _ASK_HOOK["fn"] = fn


def poi_ask(prompt=""):
    hook = _ASK_HOOK["fn"]
    if hook is not None:
        try:
            v = hook(_disp(prompt))
            return "" if v is None else str(v)
        except Exception:  # noqa: BLE001
            return ""
    try:
        return input(_disp(prompt))
    except (EOFError, RuntimeError, OSError, AttributeError):
        # 콘솔 없는 환경(윈도우 GUI 실행 등) — "lost sys.stdin" 방지
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


class PoiErrorValue(str):
    """catch 로 잡힌 오류 — 문자열처럼도(메시지) 쓰이고 .type / .message 도 있다."""
    def __new__(cls, message, etype="Error"):
        s = super().__new__(cls, message)
        s.message = message
        s.type = etype
        return s


class _PoiRaise(Exception):
    def __init__(self, message, etype="Error"):
        super().__init__(message)
        self.poi_message = message
        self.poi_type = etype


def poi_error_value(err):
    """catch 로 잡힌 값을 사람이 읽기 좋게 (+ .type / .message)."""
    if isinstance(err, _PoiRaise):
        return PoiErrorValue(err.poi_message, err.poi_type)
    if isinstance(err, POIError):
        return PoiErrorValue(err.message, "POIError")
    return PoiErrorValue(f"{type(err).__name__}: {err}", type(err).__name__)


def poi_error_is(err, typename) -> bool:
    if isinstance(err, _PoiRaise):
        return err.poi_type == typename or typename in ("Error", "Exception")
    return type(err).__name__ == typename or typename in ("Error", "Exception")


def poi_error(message, etype="Error"):
    """raise Error("...") / raise ValueError("...") 용 오류 값 생성기."""
    return _PoiRaise(str(message), str(etype))


# raise Error(...) · raise ValueError(...) 등에서 바로 쓰는 이름들
_ERROR_MAKERS = {
    name: (lambda _n: (lambda msg="": poi_error(msg, _n)))(name)
    for name in ("Error", "ValueError", "TypeError", "NameError", "KeyError",
                 "IndexError", "RuntimeError", "FileError", "ValidationError",
                 "AuthError", "NotFoundError", "PermissionError", "TimeoutError")
}


def poi_make_error(value):
    """raise <값>  →  예외로."""
    if isinstance(value, BaseException):
        return value
    if isinstance(value, PoiErrorValue):
        return _PoiRaise(value.message, value.type)
    return _PoiRaise(str(value), "Error")


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
    exports = g2.get("__poi_exports__")
    if exports:  # export 를 하나라도 쓴 파일 → 명시된 것만 공개
        return Box({k: g2[k] for k in exports if k in g2})
    return Box({k: v for k, v in g2.items()
                if k not in base_keys and not k.startswith("__")})


def poi_range(a, b, inclusive=True):
    """1..10 (양끝 포함) / 1..<10 (끝 미포함)  →  리스트.
    b < a 이면 빈 리스트 (역방향은 reverse_of(1..10) 로)."""
    a, b = int(a), int(b)
    stop = (b + 1) if inclusive else b
    return list(range(a, max(a, stop)))


def _load_poi_file(full):
    import os
    from ..interpreter import compile_source
    from . import make_globals
    with open(full, encoding="utf-8") as f:
        src = f.read()
    py, linemap, cname = compile_source(src, os.path.basename(full))
    g2 = make_globals()
    base_keys = set(g2)
    g2["__name__"] = "__poi_module__"
    g2["__poi_file__"] = full
    g2["__poi_dir__"] = os.path.dirname(full)
    g2["__poi_source__"] = src
    g2["__poi_linemap__"] = linemap
    exec(compile(py, cname, "exec"), g2)  # noqa: S102
    exports = g2.get("__poi_exports__")
    if exports:
        return Box({k: g2[k] for k in exports if k in g2})
    return Box({k: v for k, v in g2.items()
                if k not in base_keys and not k.startswith("__")})


def poi_import_pkg(name):
    """use pkg:name  →  poi_modules / ~/.poi/modules / POI_PATH 에서 모듈을 찾아 로드.

    확장성의 핵심 — 재사용 가능한 POI/파이썬 모듈을 폴더로 배포해서 쓴다.
    폴더면 main.poi / __init__.poi / <name>.poi 를, 아니면 <name>.poi / <name>.py 를 찾는다.
    """
    import os
    import sys as _sys
    frame = _sys._getframe(1)
    here = frame.f_globals.get("__poi_dir__") or os.getcwd()
    bases = [os.path.join(here, "poi_modules"),
             os.path.join(os.path.expanduser("~"), ".poi", "modules")]
    bases += [p for p in os.environ.get("POI_PATH", "").split(os.pathsep) if p]
    tried = []
    for base in bases:
        d = os.path.join(base, name)
        cands = [os.path.join(d, "main.poi"), os.path.join(d, "__init__.poi"),
                 os.path.join(d, name + ".poi"),
                 os.path.join(base, name + ".poi"),
                 os.path.join(base, name + ".py"), os.path.join(d, name + ".py")]
        for c in cands:
            tried.append(c)
            if os.path.isfile(c):
                return poi_import_pyfile(c) if c.endswith(".py") \
                    else _load_poi_file(c)
    raise POIError(f"패키지 모듈을 찾을 수 없습니다: {name}", "P303",
                   hint="찾은 곳:\n  " + "\n  ".join(tried[:6]) +
                        "\n poi_modules/ 폴더에 두거나 POI_PATH 를 설정하세요.")


# pip 이름이 import 이름과 다른 흔한 것들
_PIP_NAME = {
    "cv2": "opencv-python", "PIL": "Pillow", "sklearn": "scikit-learn",
    "yaml": "PyYAML", "bs4": "beautifulsoup4", "serial": "pyserial",
    "dotenv": "python-dotenv", "OpenSSL": "pyOpenSSL", "Crypto": "pycryptodome",
    "jwt": "PyJWT", "dateutil": "python-dateutil", "win32api": "pywin32",
    "win32con": "pywin32", "win32gui": "pywin32", "docx": "python-docx",
    "pptx": "python-pptx", "fitz": "PyMuPDF", "psycopg2": "psycopg2-binary",
}
_ENSURED_PYMOD: set = set()


def _pymod_installed(root: str) -> bool:
    try:
        return importlib.util.find_spec(root) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def poi_ensure_pymod(root: str):
    """`use py:이름` 이 부를 파이썬 모듈이 없으면 물어보고 설치한다.

    - 이미 있으면 아무것도 안 함 (거의 모든 경우 — 오버헤드 없음).
    - exe 로 묶인 상태(sys.frozen): 빌드 때 자동 포함되므로 없으면 그냥 오류.
    - POI_AUTO_PIP=1  : 묻지 않고 바로 설치
    - POI_AUTO_PIP=0  : 묻지 않고 바로 오류
    - 그 밖에 터미널이면 y/n 로 물어본다.
    """
    import os
    import sys as _sys
    if not root or root in _ENSURED_PYMOD:
        return
    if _pymod_installed(root):
        _ENSURED_PYMOD.add(root)
        return

    pkg = _PIP_NAME.get(root, root)
    frozen = getattr(_sys, "frozen", False)
    mode = os.environ.get("POI_AUTO_PIP", "").strip().lower()

    if frozen:
        raise POIError(
            f"'{root}' 파이썬 라이브러리가 이 실행파일에 없습니다.", "P131",
            hint=f"이 exe 를 다시 빌드할 때 자동 포함됩니다:  poi build <파일>.poi\n"
                 f"(임시로는 옆에 '{root}' 를 설치한 파이썬을 두세요.)")

    want = mode in ("1", "y", "yes", "true", "on")
    if not want and mode not in ("0", "n", "no", "false", "off"):
        try:
            if _sys.stdin and _sys.stdin.isatty():
                ans = input(f"필요한 라이브러리 '{pkg}' 가 없습니다. 지금 설치할까요? [Y/n] ")
                want = ans.strip().lower() in ("", "y", "yes", "ㅇ")
        except (EOFError, OSError):
            want = False

    if not want:
        raise POIError(
            f"'{root}' 파이썬 라이브러리가 없습니다.", "P131",
            hint=f"설치:  pip install {pkg}\n"
                 f"또는 묻지 않고 자동 설치하려면  POI_AUTO_PIP=1")

    import subprocess
    print(f"⏳  pip install {pkg} …")
    rc = subprocess.run([_sys.executable, "-m", "pip", "install", pkg]).returncode
    importlib.invalidate_caches()
    if rc != 0 or not _pymod_installed(root):
        raise POIError(
            f"'{pkg}' 설치에 실패했습니다.", "P131",
            hint=f"직접 해보세요:  {_sys.executable} -m pip install {pkg}")
    _ENSURED_PYMOD.add(root)
    print(f"✓  {pkg} 준비 완료")


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
    from . import stdlib2
    mapping.update(stdlib2.MODULES)
    mapping.update(stdlib2.KO_MODULES)
    if name not in mapping:
        raise POIError(f"'{name}' 표준 모듈은 없습니다.", "P021")
    _STD_CACHE[name] = mapping[name]
    return mapping[name]


__all__ = [
    "Box", "boxify", "poi_show", "poi_print", "poi_fmt", "poi_ask", "number", "text", "boolean",
    "poi_getattr", "poi_getattr_safe", "poi_setattr", "poi_coalesce",
    "poi_error_value", "poi_import_pyfile", "poi_std",
]

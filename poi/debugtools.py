"""POI 디버깅 도구 (v1.1).

세 갈래:

1. inspect(x)           — 값의 타입·구조·길이·미리보기를 예쁘게 출력 (x 를 그대로 반환)
2. pause() / watch(x)   — 그 자리에서 멈춰 지역 변수를 보고, 식을 쳐보고, 계속
3. --trace              — 문장이 실행될 때마다 줄번호와 소스를 찍는다 (transpiler 협조)
   --explain            — 오류가 나면 그 프레임의 지역 변수까지 사후 분석

런타임 전역에는 inspect / pause / watch / _poi_trace / _poi_pause 로 올라간다.
"""
from __future__ import annotations

import sys

_C = {
    "dim": "\033[2m", "red": "\033[31m", "grn": "\033[32m", "yel": "\033[33m",
    "blu": "\033[34m", "cyn": "\033[36m", "b": "\033[1m", "x": "\033[0m",
}


def _use_color(stream) -> bool:
    try:
        return stream.isatty() and sys.platform != "emscripten"
    except Exception:
        return False


def _paint(s: str, c: str, stream) -> str:
    return f"{_C[c]}{s}{_C['x']}" if _use_color(stream) else s


# ── inspect ────────────────────────────────────────────────────────────

def _short(v, maxlen=60) -> str:
    r = repr(v)
    return r if len(r) <= maxlen else r[: maxlen - 1] + "…"


def _describe(v) -> tuple[str, str]:
    """(타입이름, 크기설명)"""
    t = type(v).__name__
    if v is True or v is False:
        return "bool(true/false)", ""
    if v is None:
        return "null", ""
    if isinstance(v, str):
        return "Text", f"{len(v)}글자"
    if isinstance(v, bool):
        return "bool", ""
    if isinstance(v, int):
        return "Int", ""
    if isinstance(v, float):
        return "Float", ""
    if isinstance(v, (list, tuple)):
        return ("List" if isinstance(v, list) else "묶음"), f"{len(v)}개"
    if isinstance(v, dict):
        return "객체", f"{len(v)}개 항목"
    if callable(v):
        return "함수", getattr(v, "__name__", "")
    return t, ""


def inspect_value(v, label=None, _depth=0, _stream=None):
    """값을 예쁘게 출력하고 그대로 돌려준다. `x = inspect(x)` 로 체이닝 가능."""
    out = _stream or sys.stdout
    pad = "  " * _depth
    tname, size = _describe(v)
    head = _paint(tname, "cyn", out)
    if size:
        head += _paint(f"  {size}", "dim", out)
    prefix = f"{pad}{_paint(str(label) + ' =', 'b', out)} " if label else pad
    print(f"{prefix}{head}", file=out)

    if isinstance(v, dict):
        for k, val in list(v.items())[:20]:
            kt, ksize = _describe(val)
            line = f"{pad}  {_paint('.' + str(k), 'yel', out)}: {_paint(kt, 'dim', out)}"
            if not isinstance(val, (dict, list)):
                line += f" = {_short(val, 48)}"
            elif ksize:
                line += f" ({ksize})"
            print(line, file=out)
        if len(v) > 20:
            print(f"{pad}  {_paint(f'… 그리고 {len(v) - 20}개 더', 'dim', out)}", file=out)
    elif isinstance(v, (list, tuple)):
        for i, val in enumerate(v[:15]):
            kt, _ = _describe(val)
            print(f"{pad}  {_paint(f'[{i}]', 'yel', out)} {_paint(kt, 'dim', out)}"
                  f"  {_short(val, 48)}", file=out)
        if len(v) > 15:
            print(f"{pad}  {_paint(f'… 그리고 {len(v) - 15}개 더', 'dim', out)}", file=out)
    elif isinstance(v, str) and "\n" in v:
        for ln in v.splitlines()[:8]:
            print(f"{pad}  {_paint('│', 'dim', out)} {ln}", file=out)
    elif not isinstance(v, (int, float, bool)) and v is not None and not callable(v):
        attrs = [a for a in dir(v) if not a.startswith("_")][:12]
        if attrs:
            print(f"{pad}  {_paint('속성: ' + ', '.join(attrs), 'dim', out)}", file=out)
    return v


# ── trace (transpiler 가 문장 앞에 심는다) ─────────────────────────────

class _TraceState:
    on = False
    show_vars = False
    primed = False
    _last_locals: dict = {}


# 런타임이 전역에 심어두는 이름들 — 변수 변화에서 제외
_RUNTIME_NAMES = {
    "file", "json", "web", "math", "time", "gui", "ui", "app",
    "pp청춘", "test", "poi_argv", "Box", "boxify",
}


def poi_set_trace(on: bool, show_vars: bool = False):
    _TraceState.on = on
    _TraceState.show_vars = show_vars
    _TraceState.primed = False
    _TraceState._last_locals = {}


def _interesting(k: str, val) -> bool:
    if k.startswith("_") or k in _RUNTIME_NAMES:
        return False
    if callable(val):
        return False
    if type(val).__name__ in ("module", "SimpleNamespace"):
        return False
    return True


def _poi_trace(line: int, src: str, _frame_locals=None):
    if not _TraceState.on:
        return
    out = sys.stderr
    bar = _paint("╎", "dim", out)
    ln = _paint(f"{line:>4}", "blu", out)
    print(f"{bar} {ln} {_paint('│', 'dim', out)} {src.strip()}", file=out)
    if not _TraceState.show_vars or _frame_locals is None:
        return
    snapshot = {k: v for k, v in _frame_locals.items() if _interesting(k, v)}
    if not _TraceState.primed:
        _TraceState.primed = True
        _TraceState._last_locals = snapshot
        return
    changed = {k: v for k, v in snapshot.items()
               if k not in _TraceState._last_locals or _TraceState._last_locals[k] is not v}
    _TraceState._last_locals = snapshot
    for k, val in list(changed.items())[:6]:
        print(f"{bar}      {_paint('→ ' + k, 'grn', out)} = {_short(val, 50)}", file=out)


# ── pause / watch ─────────────────────────────────────────────────────

def _poi_pause(line: int, src: str, frame_locals: dict, frame_globals: dict,
               label=None):
    out = sys.stderr
    print("", file=out)
    tag = f" {label}" if label else ""
    print(_paint(f"⏸  일시정지{tag}  (줄 {line})", "yel", out), file=out)
    print(f"{_paint('│', 'dim', out)} {src.strip()}", file=out)
    user_vars = {k: v for k, v in frame_locals.items()
                 if not k.startswith("_") and not callable(v)}
    if user_vars:
        names = ", ".join(user_vars)
        print(f"{_paint('│', 'dim', out)} 지역 변수: {_paint(names, 'cyn', out)}", file=out)
    print(_paint("│ 식을 입력하면 계산해 봅니다.  vars=전체보기  c/Enter=계속  q=중단",
                 "dim", out), file=out)
    scope = dict(frame_globals)
    scope.update(frame_locals)
    while True:
        try:
            expr = input(_paint("(pause) ", "yel", out)).strip()
        except EOFError:
            break
        if expr in ("", "c", "continue"):
            break
        if expr in ("q", "quit", "abort"):
            raise KeyboardInterrupt("pause 에서 중단")
        if expr in ("vars", "v", "ls"):
            for k, v in user_vars.items():
                inspect_value(v, k, _stream=out)
            continue
        try:
            print("  " + _short(eval(expr, scope), 200), file=out)  # noqa: S307
        except Exception as e:  # noqa: BLE001
            print(_paint(f"  ! {type(e).__name__}: {e}", "red", out), file=out)


def poi_pause(label=None):
    """POI 코드에서 `pause()` — 그 자리에서 멈춘다."""
    f = sys._getframe(1)
    line = _map_line(f)
    src = _src_line(f, line)
    _poi_pause(line, src, f.f_locals, f.f_globals, label)


def poi_watch(value, label=None):
    """`watch(x)` — x 를 inspect 하고 그대로 반환 (흐름 안 끊음)."""
    f = sys._getframe(1)
    line = _map_line(f)
    lbl = label or f"watch (줄 {line})"
    return inspect_value(value, lbl, _stream=sys.stderr)


def _map_line(frame) -> int:
    lm = frame.f_globals.get("__poi_linemap__") or {}
    return lm.get(frame.f_lineno, frame.f_lineno)


def _src_line(frame, poi_line: int) -> str:
    src = frame.f_globals.get("__poi_source__") or ""
    lines = src.splitlines()
    return lines[poi_line - 1] if 0 < poi_line <= len(lines) else ""


# ── post-mortem (--explain) ──────────────────────────────────────────

def explain_exception(exc: BaseException, source: str, linemap: dict,
                      compiled_name: str) -> str:
    import traceback
    out = sys.stderr
    frames = [(fr, ln) for fr, ln in traceback.walk_tb(getattr(exc, "__traceback__", None))
              if fr.f_code.co_filename == compiled_name]
    if not frames:
        return ""
    fr, py_ln = frames[-1]
    poi_ln = linemap.get(py_ln)
    lines = ["", _paint("── 자세히 (--explain) ──", "b", out)]
    if poi_ln:
        src_lines = source.splitlines()
        lo, hi = max(1, poi_ln - 2), min(len(src_lines), poi_ln + 2)
        for n in range(lo, hi + 1):
            mark = _paint(">", "red", out) if n == poi_ln else " "
            lines.append(f"  {mark} {n:>3} │ {src_lines[n - 1]}")
    user = {k: v for k, v in fr.f_locals.items() if _interesting(k, v)}
    if user:
        lines.append(_paint("  그때 값들:", "dim", out))
        for k, v in list(user.items())[:10]:
            tname, _ = _describe(v)
            lines.append(f"    {_paint(k, 'cyn', out)}: {tname} = {_short(v, 60)}")
    return "\n".join(lines)

"""사람 친화적인 오류.

파이썬 예외를 그대로 보여주지 않고, POI 소스 줄과 함께
한국어 설명 + 해결 힌트를 붙여서 보여준다.
"""
from __future__ import annotations

import re
import traceback


class POIError(Exception):
    def __init__(self, message: str, code: str = "P000", line: int | None = None,
                 col: int | None = None, hint: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.line = line
        self.col = col
        self.hint = hint

    def render(self, source: str | None = None) -> str:
        out = []
        out.append(f"POI Error {self.code}")
        out.append("")
        out.append(f"  {self.message}")
        if source and self.line:
            out.append("")
            out.append(_source_frame(source, self.line, self.col))
        if self.hint:
            out.append("")
            out.append("해결:")
            for ln in self.hint.splitlines():
                out.append(f"  {ln}")
        return "\n".join(out)


def _source_frame(source: str, line: int, col: int | None, context: int = 1) -> str:
    lines = source.splitlines()
    if not lines:
        return ""
    lo = max(1, line - context)
    hi = min(len(lines), line + context)
    width = len(str(hi))
    buf = []
    for n in range(lo, hi + 1):
        text = lines[n - 1]
        marker = ">" if n == line else " "
        buf.append(f"  {marker} {str(n).rjust(width)} | {text}")
        if n == line and col:
            pad = " " * (2 + 2 + width + 3 + max(0, col - 1))
            buf.append(pad + "^")
    return "\n".join(buf)


# --- 파이썬 예외 -> POI 오류 번역 -----------------------------------------

def translate_exception(exc: BaseException, source: str, linemap: dict,
                        compiled_name: str) -> POIError:
    poi_line = _find_poi_line(exc, linemap, compiled_name)
    name = type(exc).__name__
    msg = str(exc)

    # raise Error("...") / raise ValueError("...") 로 던진 것
    if hasattr(exc, "poi_message"):
        et = getattr(exc, "poi_type", "Error")
        head = f"[{et}] " if et not in ("Error", "") else ""
        return POIError(head + str(getattr(exc, "poi_message", msg)), "P300",
                        poi_line,
                        hint=f"try {{ ... }} catch {et} as e {{ ... }} 로 잡을 수 있어요.")

    if isinstance(exc, ZeroDivisionError):
        return POIError("0 으로는 나눌 수 없습니다.", "P101", poi_line,
                        hint="나누는 값이 0 이 아닌지 먼저 확인하세요.")

    if isinstance(exc, NameError):
        m = re.search(r"name '([^']+)'", msg)
        who = m.group(1) if m else "값"
        return POIError(f"'{who}' 을(를) 아직 모릅니다. 정의된 적이 없어요.", "P102",
                        poi_line,
                        hint=f"오타가 없는지, '{who} = ...' 로 먼저 값을 넣었는지 확인하세요.")

    if isinstance(exc, TypeError) and (
        "unsupported operand" in msg
        or "can only concatenate" in msg
        or ("not supported between" in msg)
        or ("must be str" in msg)
    ):
        return POIError("숫자와 문자를 함께 계산할 수 없습니다.", "P103", poi_line,
                        hint="number(...) 로 문자열을 숫자로 바꾸거나,\n"
                             "text(...) 로 숫자를 문자열로 바꿔서 맞추세요.")

    if isinstance(exc, FileNotFoundError):
        target = getattr(exc, "filename", None) or msg
        return POIError(f"파일을 찾을 수 없습니다: {target}", "P104", poi_line,
                        hint="파일 이름과 경로가 맞는지, 파일이 실제로 있는지 확인하세요.")

    if isinstance(exc, KeyError):
        return POIError(f"항목 {msg} 이(가) 없습니다.", "P105", poi_line,
                        hint="키 이름이 맞는지, 그 항목이 실제로 들어있는지 확인하세요.")

    if isinstance(exc, IndexError):
        return POIError("목록 범위를 벗어났습니다.", "P106", poi_line,
                        hint="목록의 길이는 list.length 로 확인할 수 있어요.")

    if isinstance(exc, AttributeError):
        m = re.search(r"attribute '([^']+)'", msg)
        who = m.group(1) if m else "그 기능"
        return POIError(f"'{who}' 이라는 기능(속성)이 없습니다.", "P107", poi_line,
                        hint="이름을 잘못 썼거나, 그 자료형이 지원하지 않는 기능일 수 있어요.")

    if isinstance(exc, RecursionError):
        return POIError("함수가 자기 자신을 너무 깊게 불렀습니다.", "P108", poi_line,
                        hint="끝나는 조건(return)이 있는지 확인하세요.")

    return POIError(f"{name}: {msg}", "P199", poi_line)


def _find_poi_line(exc, linemap: dict, compiled_name: str) -> int | None:
    tb = getattr(exc, "__traceback__", None)
    best = None
    for frame, lineno in traceback.walk_tb(tb):
        if frame.f_code.co_filename == compiled_name:
            best = lineno
    if best is None:
        return None
    if best in linemap:
        return linemap[best]
    # 가장 가까운 아래쪽 매핑을 찾는다.
    for py_ln in sorted(linemap):
        if py_ln >= best:
            return linemap[py_ln]
    return linemap[max(linemap)] if linemap else None

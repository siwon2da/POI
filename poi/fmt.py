"""poi fmt — POI 소스 정리 (v1.8, 기본형).

하는 일 (안전한 것만):
  · 탭 → 스페이스 4칸
  · 줄 끝 공백 제거
  · 블록 깊이에 맞춰 4칸 단위로 다시 들여쓰기
    (중괄호 { }, 콜론 헤더, if/fn/for/repeat/while/try/else/match/server/webapp,
     end 로 닫기 — 다섯 스타일 모두 인식)
  · 연속 빈 줄 1줄로, 파일 끝 개행 1개
  · `python { ... }` 원문 블록은 손대지 않음

정리 후 파서로 다시 확인해서, 깨지면 원본을 그대로 둔다.
전면 재작성(콜론/ end → 중괄호 통일)은 로드맵 v1.9 (CST 필요).
"""
from __future__ import annotations

import os
import re

_INDENT = "    "
_HEADER = re.compile(
    r"^(if|else if|else|for|repeat|while|fn|try|catch|match|when|"
    r"server|webapp|page|state|action|app|window|test)\b")
_DEDENT_START = re.compile(r"^\s*[)}\]]")


def _strip_code(line: str) -> str:
    """문자열·주석을 뺀 코드만 (괄호 세기용). 완벽하진 않아도 실용적으로 충분."""
    out, i, n = [], 0, len(line)
    while i < n:
        c = line[i]
        if c == "#":
            break
        if c == "/" and line[i:i + 2] == "//":
            break
        if c == '"':
            i += 1
            while i < n and line[i] != '"':
                i += 2 if line[i] == "\\" else 1
            i += 1
            continue
        out.append(c)
        i += 1
    return "".join(out)


def hygiene_only(src: str) -> str:
    """탭→4칸, 줄 끝 공백 제거, 연속 빈 줄 축소, 파일 끝 개행 1개. (재들여쓰기 없음)"""
    src = src.replace("\t", _INDENT)
    out, blank = [], 0
    for raw in src.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            blank += 1
            if blank <= 1:
                out.append("")
        else:
            blank = 0
            out.append(line)
    return "\n".join(out).rstrip("\n") + "\n"


def format_source(src: str, reindent: bool = True) -> str:
    if not reindent:
        return hygiene_only(src)
    src = src.replace("\t", _INDENT)
    lines = src.split("\n")
    out: list[str] = []
    depth = 0
    blank = 0
    in_py = 0            # python { } 원문 블록 안이면 > 0

    for raw in lines:
        line = raw.rstrip()
        code = _strip_code(line)
        stripped = line.strip()

        # python { ... } 원문 블록은 그대로 둔다 (중괄호 균형으로 끝을 찾음)
        if in_py:
            out.append(line)
            in_py += code.count("{") - code.count("}")
            continue
        if re.match(r"^(python|파이썬)\s*\{", stripped):
            out.append(_INDENT * depth + stripped)
            in_py = code.count("{") - code.count("}")
            continue

        if not stripped:
            blank += 1
            if blank <= 1:
                out.append("")
            continue
        blank = 0

        opens = code.count("{") + code.count("[") + code.count("(")
        closes = code.count("}") + code.count("]") + code.count(")")
        net = opens - closes

        this_depth = depth
        if _DEDENT_START.match(line) or stripped in ("end", "}", "});", "})"):
            this_depth = max(0, depth - 1)

        out.append(_INDENT * this_depth + stripped)

        # 다음 줄 깊이
        if stripped in ("end",):
            depth = max(0, depth - 1)
        else:
            depth = max(0, depth + net)
            # 콜론 헤더 한 줄 블록은 다음 줄에 영향 없음 (한 문장이므로)
            if net == 0 and _HEADER.match(stripped) and stripped.endswith(":"):
                depth += 1
            # end 스타일 헤더(중괄호·콜론 없음)는 end 로 닫히므로 여기선 안 올림
            #  → 들여쓰기 스타일은 사용자가 이미 들여썼다고 보고 net 만 반영

    text = "\n".join(out).rstrip("\n") + "\n"
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text


def fmt_file(path: str, write: bool = True) -> tuple[bool, str]:
    """(변경됨?, 메시지)."""
    with open(path, encoding="utf-8", newline="") as f:
        original = f.read().replace("\r\n", "\n")

    from .interpreter import compile_source
    base = os.path.basename(path)

    def ok(text: str) -> bool:
        try:
            compile_source(text, base)
            return True
        except Exception:  # noqa: BLE001
            return False

    # 1) 중괄호 깊이 재들여쓰기까지 시도 → 깨지면 2) 공백 정리만
    full = format_source(original, reindent=True)
    if ok(full):
        formatted, mode = full, "정리함"
    else:
        formatted, mode = hygiene_only(original), "정리함(공백만)"
        if not ok(formatted):
            return False, f"건너뜀: {path}"

    if formatted == original:
        return False, f"이미 정리됨: {path}"
    if write:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(formatted)
    return True, f"{mode}: {path}"

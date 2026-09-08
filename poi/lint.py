"""poi lint — 가벼운 정적 점검 (v1.8).

지금 잡는 것 (오탐 최소):
  POI-W101  선언한 뒤 한 번도 안 쓴 변수
  POI-W102  같은 스코프에서 이미 있는 이름을 const 로 다시 선언
  POI-W103  return 뒤에 도달할 수 없는 코드

경고만 낸다 (exit 0). `--strict` 면 경고가 있을 때 exit 1.
"""
from __future__ import annotations

import os
import re

from .errors import POIError

_INTERP = re.compile(r"\{([^{}]+)\}")
_IDENT = re.compile(r"[^\W\d]\w*", re.UNICODE)


class Warn:
    def __init__(self, code, msg, line, hint=None):
        self.code, self.msg, self.line, self.hint = code, msg, line, hint


_IGNORE = {"_", "params", "query", "body", "headers", "method", "e", "err",
           "error", "self", "it", "i", "j", "k", "x", "_i"}


def _names_used(node, acc):
    """식/문장에서 '읽는' 이름을 모은다."""
    k = getattr(node, "kind", None)
    if k is None:
        return
    if k == "Name":
        acc.add(node.id)
    if k == "Str" and isinstance(getattr(node, "value", None), str):
        for frag in _INTERP.findall(node.value):        # 보간 "{나이}" 안의 이름도 사용
            for m in _IDENT.findall(frag):
                acc.add(m)
    for key, v in vars(node).items():
        if key in ("kind", "line"):
            continue
        if key == "target":        # 대입 왼쪽은 '사용' 아님
            t = v
            if getattr(t, "kind", "") in ("Member", "Index"):
                _names_used(getattr(t, "obj", None), acc)
            continue
        if hasattr(v, "kind"):
            _names_used(v, acc)
        elif isinstance(v, (list, tuple)):
            for it in v:
                if hasattr(it, "kind"):
                    _names_used(it, acc)
                elif isinstance(it, (list, tuple)):
                    for it2 in it:
                        if hasattr(it2, "kind"):
                            _names_used(it2, acc)


def _walk_block(body, warns, assigned, used):
    seen_return = False
    for s in body or []:
        k = getattr(s, "kind", None)
        if seen_return and k not in ("FnDecl",):
            warns.append(Warn("POI-W103", "return 뒤라서 실행되지 않는 줄입니다.",
                              getattr(s, "line", 0)))
            seen_return = False  # 한 번만
        if k == "Assign" and getattr(s.target, "kind", "") == "Name":
            nm = s.target.id
            if getattr(s, "is_const", False) and nm in assigned:
                warns.append(Warn("POI-W102",
                                  f"'{nm}' 를 const 로 다시 선언했습니다.", s.line))
            assigned.setdefault(nm, s.line)
            _names_used(s.value, used)
        elif k == "Return":
            if s.value is not None:
                _names_used(s.value, used)
            seen_return = True
        elif k == "FnDecl":
            for p in s.params:
                if p[1] is not None:
                    _names_used(p[1], used)
            inner_assigned, inner_used = {}, set()
            bodylist = s.body if not s.is_expr_body else []
            _walk_block(bodylist, warns, inner_assigned, inner_used)
            if s.is_expr_body:
                _names_used(s.body, inner_used)
            for nm, ln in inner_assigned.items():
                if nm not in inner_used and nm not in _IGNORE \
                        and not nm.startswith("_"):
                    warns.append(Warn("POI-W101",
                                      f"'{nm}' 를 넣었지만 한 번도 쓰지 않았습니다.",
                                      ln))
        else:
            _names_used(s, used)
            for key, v in vars(s).items():
                if isinstance(v, list) and v and hasattr(v[0], "kind"):
                    _walk_block(v, warns, assigned, used)
                elif isinstance(v, list):
                    for it in v:
                        if isinstance(it, (list, tuple)) and it \
                                and hasattr(it[-1], "kind"):
                            _walk_block(it, warns, assigned, used)


def lint_source(src: str, filename: str) -> list[Warn]:
    from .lexer import Lexer
    from .parser import Parser
    warns: list[Warn] = []
    try:
        toks = Lexer(src, filename).tokenize()
        program = Parser(toks, src, filename).parse()
    except POIError:
        return warns  # 문법 오류는 poi check 의 몫
    assigned, used = {}, set()
    _walk_block(program.body, warns, assigned, used)
    for nm, ln in assigned.items():
        if nm not in used and nm not in _IGNORE and not nm.startswith("_"):
            warns.append(Warn("POI-W101",
                              f"'{nm}' 를 넣었지만 한 번도 쓰지 않았습니다.", ln))
    warns.sort(key=lambda w: w.line)
    return warns


def lint_file(path: str, strict: bool = False) -> int:
    with open(path, encoding="utf-8") as f:
        src = f.read()
    warns = lint_source(src, os.path.basename(path))
    if not warns:
        print(f"깨끗함: {path}")
        return 0
    lines = src.splitlines()
    for w in warns:
        print(f"\n{w.code}  {path}:{w.line}")
        print(f"  {w.msg}")
        if 0 < w.line <= len(lines):
            print(f"  {w.line} | {lines[w.line - 1].strip()}")
    print(f"\n경고 {len(warns)}개.")
    return 1 if strict else 0

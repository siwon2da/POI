"""POI 렉서.

핵심 트릭: 줄바꿈(NEWLINE)을 문장 구분자로 쓰되, 괄호 ( [ 안이나
연속 연산자 뒤, 그리고 다음 줄이 `.` / `|>` 로 이어질 때는 삼킨다.
중괄호 { } 는 줄바꿈을 삼키지 않는다 (블록/객체 안에서 줄이 의미를 가짐).
"""
from __future__ import annotations

import re

from .errors import POIError
from .tokens import KOREAN_ALIASES, MULTI_OPS, RESERVED, SINGLE_OPS, Token

_NAME = re.compile(r"[^\W\d][\w]*", re.UNICODE)
_NUMBER = re.compile(r"\d+(?:\.\d+)?")
_DIM = re.compile(r"\d+x\d+")

_CONT_OP_VALUES = {
    "+", "-", "*", "/", "%", "=", "==", "!=", "<", ">", "<=", ">=",
    "=>", "->", "|>", "&&", "||", ",", ".", "?.", "??", "(", "[", "{", ":",
}
_CONT_KEYWORDS = {"and", "or", "not", "is", "between"}


class Lexer:
    def __init__(self, source: str, filename: str = "<poi>"):
        self.src = source.lstrip("﻿")  # BOM(들) 제거
        self.filename = filename
        self.i = 0
        self.n = len(source)
        self.line = 1
        self.col = 1
        self.paren_depth = 0
        self.tokens: list[Token] = []

    # -- helpers ---------------------------------------------------------
    def _add(self, type_: str, value, line=None, col=None):
        self.tokens.append(Token(type_, value, line or self.line, col or self.col))

    def _advance(self, k=1):
        for _ in range(k):
            if self.i < self.n:
                if self.src[self.i] == "\n":
                    self.line += 1
                    self.col = 1
                else:
                    self.col += 1
                self.i += 1

    def _last(self):
        return self.tokens[-1] if self.tokens else None

    def _emit_newline_here(self) -> bool:
        if self.paren_depth > 0:
            return False
        last = self._last()
        if last is None or last.type == "NEWLINE":
            return False
        if last.type == "OP" and last.value in _CONT_OP_VALUES:
            return False
        if last.type == "KEYWORD" and last.value in _CONT_KEYWORDS:
            return False
        # 다음 줄이 . 또는 |> 로 이어지면 삼킨다
        j = self.i
        while j < self.n and self.src[j] in " \t\r\n":
            j += 1
        if j < self.n:
            if self.src[j] == "." or self.src[j:j + 2] == "|>":
                return False
        return True

    # -- main ----------------------------------------------------------
    def tokenize(self) -> list[Token]:
        while self.i < self.n:
            c = self.src[self.i]

            if c == "\n":
                if self._emit_newline_here():
                    self._add("NEWLINE", "\n")
                self._advance()
                continue

            if c in " \t\r":
                self._advance()
                continue

            # 주석
            if c == "#" or (c == "/" and self.src[self.i:self.i + 2] == "//"):
                while self.i < self.n and self.src[self.i] != "\n":
                    self._advance()
                continue
            if c == "/" and self.src[self.i:self.i + 2] == "/*":
                self._advance(2)
                while self.i < self.n and self.src[self.i:self.i + 2] != "*/":
                    self._advance()
                self._advance(2)
                continue

            # 문자열
            if c == '"':
                self._read_string()
                continue

            # 500x300 같은 크기 리터럴
            m = _DIM.match(self.src, self.i)
            if m and not _followed_by_wordchar(self.src, m.end()):
                self._add("DIM", m.group(0))
                self._advance(len(m.group(0)))
                continue

            # 숫자
            m = _NUMBER.match(self.src, self.i)
            if m:
                raw = m.group(0)
                val = float(raw) if "." in raw else int(raw)
                self._add("NUMBER", val)
                self._advance(len(raw))
                continue

            # 이름 / 키워드
            m = _NAME.match(self.src, self.i)
            if m:
                word = m.group(0)
                kw = KOREAN_ALIASES.get(word, word)  # 한국어 별칭 → 영문 키워드
                # python { ... } 원문 블록 (파이썬 별칭 포함)
                if kw == "python" and _next_nonspace_is_brace(self.src, m.end()):
                    self._read_pyblock(m.end())
                    continue
                if kw in RESERVED:
                    self._add("KEYWORD", kw)
                else:
                    self._add("IDENT", word)
                self._advance(len(word))
                continue

            # 연산자
            hit = None
            for op in MULTI_OPS:
                if self.src.startswith(op, self.i):
                    hit = op
                    break
            if hit:
                self._add("OP", hit)
                self._advance(len(hit))
                continue

            if c in SINGLE_OPS:
                if c in "([":
                    self.paren_depth += 1
                elif c in ")]":
                    self.paren_depth = max(0, self.paren_depth - 1)
                self._add("OP", c)
                self._advance()
                continue

            raise POIError(f"알 수 없는 글자예요: {c!r}", "P001", self.line, self.col,
                           hint="따옴표를 빠뜨렸거나 특수문자를 잘못 쓴 건 아닌지 보세요.")

        if self._last() is not None and self._last().type != "NEWLINE":
            self._add("NEWLINE", "\n")
        self._add("EOF", None)
        return self.tokens

    def _read_string(self):
        start_line, start_col = self.line, self.col
        triple = self.src.startswith('"""', self.i)
        q = '"""' if triple else '"'
        self._advance(len(q))
        buf = []
        while self.i < self.n:
            if self.src.startswith(q, self.i):
                self._advance(len(q))
                self._add("STRING", "".join(buf), start_line, start_col)
                return
            ch = self.src[self.i]
            if ch == "\\" and self.i + 1 < self.n:
                buf.append(ch)
                buf.append(self.src[self.i + 1])
                self._advance(2)
                continue
            if ch == "\n" and not triple:
                raise POIError("문자열이 한 줄에서 닫히지 않았습니다.", "P002",
                               start_line, start_col,
                               hint='끝에 닫는 따옴표 " 를 넣거나 """ 여러 줄 문자열을 쓰세요.')
            buf.append(ch)
            self._advance()
        raise POIError("문자열이 닫히지 않았습니다.", "P002", start_line, start_col,
                       hint='닫는 따옴표를 넣어주세요.')

    def _read_pyblock(self, after_word_idx: int):
        start_line = self.line
        j = after_word_idx
        while j < self.n and self.src[j] in " \t\r\n":
            j += 1
        # j 는 '{'
        depth = 0
        k = j
        while k < self.n:
            ch = self.src[k]
            if ch in ('"', "'"):
                quote = ch
                trip = self.src[k:k + 3] == quote * 3
                qlen = 3 if trip else 1
                k += qlen
                while k < self.n and not self.src.startswith(quote * qlen, k):
                    if self.src[k] == "\\":
                        k += 2
                    else:
                        k += 1
                k += qlen
                continue
            if ch == "#":
                while k < self.n and self.src[k] != "\n":
                    k += 1
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    raw = self.src[j + 1:k]
                    # 렉서 위치를 원문 블록 끝 다음으로 옮긴다
                    consumed = self.src[self.i:k + 1]
                    self.line += consumed.count("\n")
                    self.i = k + 1
                    self.col = 1
                    self._add("PYBLOCK", raw, start_line)
                    return
            k += 1
        raise POIError("python { ... } 블록이 닫히지 않았습니다.", "P003", start_line)


def _followed_by_wordchar(src: str, idx: int) -> bool:
    return idx < len(src) and (src[idx].isalnum() or src[idx] == "_")


def _next_nonspace_is_brace(src: str, idx: int) -> bool:
    j = idx
    while j < len(src) and src[j] in " \t\r\n":
        j += 1
    return j < len(src) and src[j] == "{"

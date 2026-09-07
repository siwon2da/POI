"""토큰 정의."""
from __future__ import annotations


class Token:
    __slots__ = ("type", "value", "line", "col")

    def __init__(self, type_: str, value, line: int, col: int):
        self.type = type_
        self.value = value
        self.line = line
        self.col = col

    def __repr__(self):
        return f"Token({self.type}, {self.value!r}, L{self.line}:{self.col})"


# 변수명으로 쓸 수 없는 진짜 예약어. GUI 단어(app/window/button 등)는
# 문맥으로만 인식하므로 여기에 넣지 않는다.
RESERVED = {
    "if", "else", "for", "in", "fn", "return", "const",
    "show", "ask", "use", "python", "try", "catch",
    "true", "false", "null",
    "is", "between", "and", "or", "not",
    "repeat", "as", "end", "raise", "test", "assert",
}

# 여러 글자 연산자 (긴 것부터 매칭)
MULTI_OPS = ["?.", "??", "==", "!=", "<=", ">=", "=>", "->", "|>", "&&", "||"]
SINGLE_OPS = set("+-*/%<>=(){}[],.:;!")

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
    "match", "when",
}

# 한국어 키워드 별칭 — 영문 키워드와 완전 호환, 한 파일에서 섞어 써도 됨.
KOREAN_ALIASES = {
    "보여주기": "show", "출력": "show", "보이기": "show", "출력하기": "show",
    "찍기": "show", "말하기": "show",
    "물어보기": "ask", "묻기": "ask", "입력받기": "ask",
    "만약": "if", "만일": "if", "가령": "if",
    "아니면": "else", "그밖에": "else", "아니라면": "else", "그외": "else",
    "반복": "repeat", "되풀이": "repeat", "반복하기": "repeat",
    "순회": "for", "각각": "for", "모든": "for",
    "함수": "fn", "기능": "fn", "정의": "fn",
    "돌려주기": "return", "반환": "return", "결과": "return", "내보내기": "return",
    "참": "true", "거짓": "false", "없음": "null", "널": "null",
    "그리고": "and", "또한": "and", "이고": "and",
    "또는": "or", "혹은": "or",
    "아님": "not", "부정": "not",
    "시도": "try", "예외처리": "try", "해보기": "try",
    "잡기": "catch", "예외잡기": "catch", "붙잡기": "catch",
    "끝": "end", "마침": "end",
    "상수": "const", "불변": "const", "고정": "const",
    "사용": "use", "가져오기": "use", "불러오기": "use",
    "던지기": "raise", "발생": "raise", "오류내기": "raise",
    "분기": "match", "고르기": "match",
    "경우": "when", "케이스": "when",
    "검사": "test", "확인": "assert", "단언": "assert",
    "안에": "in",
    "사이": "between", "범위": "between",
    "마다": "as", "로": "as", "으로": "as",
    "파이썬": "python",
}

# 여러 글자 연산자 (긴 것부터 매칭)
MULTI_OPS = ["?.", "??", "==", "!=", "<=", ">=", "=>", "->", "|>", "&&", "||"]
SINGLE_OPS = set("+-*/%<>=(){}[],.:;!")

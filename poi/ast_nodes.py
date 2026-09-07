"""아주 가벼운 AST 노드.

노드마다 클래스를 만들지 않고 하나의 Node 로 통일한다.
`kind` 문자열로 종류를 구분하고 나머지는 자유 속성.
"""
from __future__ import annotations


class Node:
    def __init__(self, kind: str, line: int = 0, **fields):
        self.kind = kind
        self.line = line
        for k, v in fields.items():
            setattr(self, k, v)

    def __repr__(self):
        extra = {k: v for k, v in self.__dict__.items() if k not in ("kind", "line")}
        return f"<{self.kind} {extra}>"

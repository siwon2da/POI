"""점 접근이 되는 딕셔너리."""
from __future__ import annotations


class Box(dict):
    """user.name 처럼 점으로 접근되는 dict. JSON 직렬화도 그대로 됨."""

    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)

    def __dir__(self):
        return list(self.keys()) + list(super().__dir__())


def boxify(value):
    """중첩 dict/list 를 Box 로 재귀 변환."""
    if isinstance(value, Box):
        return value
    if isinstance(value, dict):
        return Box({k: boxify(v) for k, v in value.items()})
    if isinstance(value, list):
        return [boxify(v) for v in value]
    if isinstance(value, tuple):
        return [boxify(v) for v in value]
    return value

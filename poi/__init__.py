"""POI - Power Of Imagination.

우리가 만든 언어. 자체 문법 · 타입 · 오류 · GUI 모델을 가지며, 실행만
세계에서 가장 검증된 런타임(CPython) 위에서 한다. 그래서 새 언어인데도
numpy/pandas/torch 같은 파이썬 라이브러리를 첫날부터 그대로 쓸 수 있다.

내부 동작: 소스 -> Lexer -> Parser -> POI AST -> POI 컴파일러(파이썬으로 낮춤)
-> compile() -> exec(). 오류는 내부 줄번호를 POI 줄번호로 되돌려 사람 말로 보여준다.
"""

__version__ = "1.10.0"
POI_SPEC_VERSION = "1.10"

from .interpreter import run_source, run_file  # noqa: E402,F401

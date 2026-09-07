"""POI Language - Python Powered, Human First.

POI 코드는 렉서/파서를 거쳐 POI AST 가 되고, 그 AST 를 파이썬 소스로
트랜스파일한 뒤 CPython 에서 바로 실행한다. 그래서 numpy/pandas/requests
같은 파이썬 라이브러리를 그대로 쓸 수 있다.
"""

__version__ = "0.1.0"
POI_SPEC_VERSION = "0.1"

from .interpreter import run_source, run_file  # noqa: E402,F401

"""소스 -> 실행 글루."""
from __future__ import annotations

import sys

from .errors import POIError, translate_exception
from .lexer import Lexer
from .parser import Parser
from .transpiler import Transpiler


def compile_source(src: str, filename: str = "main.poi"):
    """POI 소스를 (파이썬소스, linemap, compiled_name) 으로."""
    compiled_name = f"<poi {filename}>"
    tokens = Lexer(src, filename).tokenize()
    ast = Parser(tokens, src, filename).parse()
    py_src, linemap = Transpiler(compiled_name).generate(ast)
    return py_src, linemap, compiled_name


def run_source(src: str, filename: str = "main.poi", *, emit_python: bool = False,
               argv: list[str] | None = None) -> int:
    from .runtime import make_globals

    try:
        py_src, linemap, compiled_name = compile_source(src, filename)
    except POIError as e:
        print(e.render(src), file=sys.stderr)
        return 1

    if emit_python:
        print(py_src)
        return 0

    g = make_globals()
    g["__name__"] = "__main__"
    g["__poi_file__"] = filename
    g["poi_argv"] = argv or []

    try:
        code = compile(py_src, compiled_name, "exec")
        exec(code, g)
    except POIError as e:
        print(e.render(src), file=sys.stderr)
        return 1
    except SystemExit as e:
        return int(e.code or 0)
    except KeyboardInterrupt:
        print("\n중단했습니다.", file=sys.stderr)
        return 130
    except SyntaxError as e:
        # 트랜스파일 결과가 잘못됐거나 python{} 블록이 잘못된 경우
        pe = POIError(f"파이썬 변환 결과에 문법 오류가 있습니다: {e.msg}", "P098",
                      linemap.get(e.lineno or 0))
        print(pe.render(src), file=sys.stderr)
        return 1
    except BaseException as e:  # noqa: BLE001
        pe = translate_exception(e, src, linemap, compiled_name)
        print(pe.render(src), file=sys.stderr)
        return 1
    return 0


def run_file(path: str, *, emit_python: bool = False,
             argv: list[str] | None = None) -> int:
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    import os
    return run_source(src, os.path.basename(path), emit_python=emit_python, argv=argv)

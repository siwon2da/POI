"""소스 -> 실행 글루."""
from __future__ import annotations

import sys

from .errors import POIError, translate_exception
from .lexer import Lexer
from .parser import Parser
from .transpiler import Transpiler


def compile_source(src: str, filename: str = "main.poi", *, trace: bool = False):
    """POI 소스를 (파이썬소스, linemap, compiled_name) 으로."""
    compiled_name = f"<poi {filename}>"
    tokens = Lexer(src, filename).tokenize()
    ast = Parser(tokens, src, filename).parse()
    py_src, linemap = Transpiler(compiled_name, source=src, trace=trace).generate(ast)
    return py_src, linemap, compiled_name


def run_source(src: str, filename: str = "main.poi", *, emit_python: bool = False,
               argv: list[str] | None = None, trace: bool = False,
               trace_vars: bool = False, explain: bool = False) -> int:
    from .runtime import make_globals

    trace_on = trace or trace_vars
    try:
        py_src, linemap, compiled_name = compile_source(src, filename, trace=trace_on)
    except POIError as e:
        print(e.render(src), file=sys.stderr)
        return 1

    if emit_python:
        print(py_src)
        return 0

    g = make_globals()
    g["__name__"] = "__main__"
    g["__poi_file__"] = filename
    g["__poi_source__"] = src
    g["__poi_linemap__"] = linemap
    g["poi_argv"] = argv or []

    if trace_on:
        from .debugtools import poi_set_trace
        poi_set_trace(True, trace_vars)

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
        pe = POIError(f"파이썬 변환 결과에 문법 오류가 있습니다: {e.msg}", "P098",
                      linemap.get(e.lineno or 0))
        print(pe.render(src), file=sys.stderr)
        return 1
    except BaseException as e:  # noqa: BLE001
        pe = translate_exception(e, src, linemap, compiled_name)
        print(pe.render(src), file=sys.stderr)
        if explain:
            try:
                from .debugtools import explain_exception
                extra = explain_exception(e, src, linemap, compiled_name)
                if extra:
                    print(extra, file=sys.stderr)
            except Exception:
                pass
        return 1
    finally:
        if trace_on:
            from .debugtools import poi_set_trace
            poi_set_trace(False, False)
    return 0


def run_file(path: str, *, emit_python: bool = False, argv: list[str] | None = None,
             trace: bool = False, trace_vars: bool = False,
             explain: bool = False) -> int:
    import os
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    return run_source(src, os.path.basename(path), emit_python=emit_python, argv=argv,
                      trace=trace, trace_vars=trace_vars, explain=explain)

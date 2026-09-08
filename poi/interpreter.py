"""소스 -> 실행 글루."""
from __future__ import annotations

import sys

from .errors import POIError, translate_exception
from .lexer import Lexer
from .parser import Parser
from .transpiler import Transpiler


def compile_source(src: str, filename: str = "main.poi", *, trace: bool = False,
                   safe: bool = False):
    """POI 소스를 (파이썬소스, linemap, compiled_name) 으로."""
    compiled_name = f"<poi {filename}>"
    tokens = Lexer(src, filename).tokenize()
    ast = Parser(tokens, src, filename).parse()
    if safe:
        from .safemode import assert_safe
        assert_safe(ast)
    py_src, linemap = Transpiler(compiled_name, source=src, trace=trace).generate(ast)
    return py_src, linemap, compiled_name


def run_source(src: str, filename: str = "main.poi", *, emit_python: bool = False,
               argv: list[str] | None = None, trace: bool = False,
               trace_vars: bool = False, explain: bool = False,
               safe: bool = False, time_limit: float = 5.0,
               output_limit: int = 64_000, run_tests: bool = False,
               base_dir: str | None = None, web_port: int = 8080) -> int:
    from .runtime import make_globals
    from .runtime import webserver as _ws
    _ws.reset()

    trace_on = trace or trace_vars
    try:
        py_src, linemap, compiled_name = compile_source(
            src, filename, trace=trace_on, safe=safe)
    except POIError as e:
        print(e.render(src), file=sys.stderr)
        return 1

    if emit_python:
        print(py_src)
        return 0

    import os as _os
    g = make_globals()
    g["__name__"] = "__main__"
    g["__poi_file__"] = filename
    g["__poi_dir__"] = base_dir or _os.getcwd()
    g["__poi_source__"] = src
    g["__poi_linemap__"] = linemap
    g["poi_argv"] = argv or []

    if safe:
        from .safemode import harden_globals
        harden_globals(g)
    if trace_on:
        from .debugtools import poi_set_trace
        poi_set_trace(True, trace_vars)

    import contextlib
    limit_ctx = contextlib.nullcontext({"v": False})
    if safe:
        from .safemode import limits
        limit_ctx = limits(time_limit, output_limit)

    try:
        code = compile(py_src, compiled_name, "exec")
        with limit_ctx as _to:
            try:
                exec(code, g)
                if run_tests:
                    print("\n테스트 실행:")
                    return g["poi_run_tests"]()
                if g.get("__poi_has_web__") and not safe \
                        and not __import__("os").environ.get("POI_NO_SERVE"):
                    return _ws.run_all(web_port)
            except KeyboardInterrupt:
                if isinstance(_to, dict) and _to.get("v"):
                    print(f"\n시간이 초과됐습니다 ({time_limit:g}초). 무한 루프가 아닌지 보세요.",
                          file=sys.stderr)
                    return 1
                raise
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
             explain: bool = False, safe: bool = False,
             time_limit: float = 5.0, run_tests: bool = False,
             web_port: int = 8080) -> int:
    import os
    with open(path, "r", encoding="utf-8") as f:
        src = f.read()
    return run_source(src, os.path.basename(path), emit_python=emit_python, argv=argv,
                      trace=trace, trace_vars=trace_vars, explain=explain,
                      safe=safe, time_limit=time_limit, run_tests=run_tests,
                      base_dir=os.path.dirname(os.path.abspath(path)), web_port=web_port)

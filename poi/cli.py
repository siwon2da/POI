"""POI 명령줄 도구."""
from __future__ import annotations

import os
import sys

from . import __version__
from .errors import POIError
from .interpreter import compile_source, run_file, run_source

HELP = """\
POI v{ver}  -  Power Of Imagination

사용법:
  poi run [파일.poi]                   POI 파일 실행 (기본: src/main.poi 또는 main.poi)
       --emit-python                  변환된 중간 표현만 출력
       --trace                        문장마다 줄번호·소스를 찍으며 실행
       --vars                         --trace + 변수 변화까지
       --explain                      오류가 나면 그때의 지역 변수까지 사후 분석
       --debug                        위 세 개를 한 번에
       --safe [--time N]              샌드박스로 실행 (python{}·use py·파일·네트워크 차단, 시간 제한)
  poi debug <파일.poi>                 = poi run --debug
  poi serve [폴더] [--port 8900]       플레이그라운드 서버 (정적 서빙 + 안전 실행 /run)
  poi new <이름>                       새 프로젝트 폴더 만들기
  poi check <파일.poi>                 문법만 검사 (실행 안 함)
  poi repl                            대화형 셸
  poi update                          새 버전 확인 / 올리기
  poi version                        버전 출력
  poi help                          이 도움말

코드 안에서 쓰는 디버깅 함수:
  inspect(x)   값의 타입·구조·길이를 예쁘게 출력 (x 를 그대로 반환)
  watch(x)     inspect 하고 그대로 반환 — 흐름을 안 끊음
  pause()      그 자리에서 멈춰 지역 변수 보기 / 식 계산 / 계속

환경변수:
  POI_NO_UPDATE_CHECK=1               새 버전 자동 확인 끄기

예:
  poi run examples/hello.poi
  poi new my-app && cd my-app && poi run
"""

_TEMPLATE_MAIN = '''\
# __NAME__ - POI 앱

show "안녕하세요, __NAME__ 입니다!"

who = ask "이름이 뭐예요? "

if who.length >= 2 {
    show "반가워요 {who}님"
} else {
    show "이름이 좀 짧네요"
}
'''

_TEMPLATE_TOML = '''\
[project]
name = "__NAME__"
version = "0.1.0"

[poi]
version = "0.1"

[dependencies]
# poi add <이름> 으로 추가됩니다
'''


def _find_default_entry() -> str | None:
    for cand in ("src/main.poi", "main.poi", "app.poi"):
        if os.path.exists(cand):
            return cand
    return None


def _maybe_update_notice():
    if os.environ.get("POI_NO_UPDATE_CHECK"):
        return
    try:
        from .update import notice_line
        line = notice_line()
        if line:
            print(line, file=sys.stderr)
    except Exception:
        pass


_RUN_FLAGS = {"--emit-python", "--trace", "--vars", "--explain", "--debug", "--safe"}


def _run(args: list[str], *, force_debug: bool = False) -> int:
    time_limit = 5.0
    kept = []
    it = iter(args)
    for a in it:
        if a == "--time":
            try:
                time_limit = float(next(it))
            except (StopIteration, ValueError):
                pass
        elif a.startswith("--time="):
            try:
                time_limit = float(a.split("=", 1)[1])
            except ValueError:
                pass
        else:
            kept.append(a)
    flags = {a for a in kept if a in _RUN_FLAGS}
    rest = [a for a in kept if a not in _RUN_FLAGS]
    emit = "--emit-python" in flags
    trace = "--trace" in flags or "--debug" in flags or force_debug
    trace_vars = "--vars" in flags or "--debug" in flags or force_debug
    explain = "--explain" in flags or "--debug" in flags or force_debug
    safe = "--safe" in flags

    path = rest[0] if rest else _find_default_entry()
    if not path:
        print("실행할 .poi 파일을 못 찾았어요. `poi run 파일.poi` 처럼 지정하세요.",
              file=sys.stderr)
        return 1
    if not os.path.exists(path):
        print(f"파일이 없습니다: {path}", file=sys.stderr)
        return 1
    rc = run_file(path, emit_python=emit, argv=rest[1:],
                  trace=trace, trace_vars=trace_vars, explain=explain,
                  safe=safe, time_limit=time_limit)
    if not emit and not safe:
        _maybe_update_notice()
    return rc


def cmd_run(args: list[str]) -> int:
    return _run(args)


def cmd_debug(args: list[str]) -> int:
    """poi debug <파일> — 추적 + 변수 변화 + 오류 시 사후 분석까지 한 번에."""
    return _run(args, force_debug=True)


def cmd_test(args: list[str]) -> int:
    """poi test [파일] — 파일 안의 test 블록을 실행하고 통과/실패 요약."""
    path = next((a for a in args if not a.startswith("-")), None) or _find_default_entry()
    if not path or not os.path.exists(path):
        print("테스트할 .poi 파일을 지정하세요: poi test 파일.poi", file=sys.stderr)
        return 1
    return run_file(path, run_tests=True)


def cmd_update(args: list[str]) -> int:
    from .update import run_update
    return run_update()


def cmd_exercises(args: list[str]) -> int:
    from .exrun import main as ex_main
    return ex_main(args)


def cmd_serve(args: list[str]) -> int:
    from .playground import serve
    port = 8900
    root = "."
    it = iter(args)
    for a in it:
        if a in ("--port", "-p"):
            try:
                port = int(next(it))
            except (StopIteration, ValueError):
                pass
        elif a.startswith("--port="):
            port = int(a.split("=", 1)[1])
        elif not a.startswith("-"):
            root = a
    if root == ".":
        for cand in ("site/hagora", "site", "."):
            if os.path.isdir(cand):
                root = cand
                break
    return serve(root, port)


def cmd_new(args: list[str]) -> int:
    if not args:
        print("프로젝트 이름을 알려주세요: poi new <이름>", file=sys.stderr)
        return 1
    root = os.path.abspath(args[0])
    name = os.path.basename(root.rstrip("/\\")) or "poi-app"
    if os.path.exists(root):
        print(f"이미 있는 폴더입니다: {root}", file=sys.stderr)
        return 1
    for sub in ("", "src", "assets", "tests"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    with open(os.path.join(root, "src", "main.poi"), "w", encoding="utf-8") as f:
        f.write(_TEMPLATE_MAIN.replace("__NAME__", name))
    with open(os.path.join(root, "poi.toml"), "w", encoding="utf-8") as f:
        f.write(_TEMPLATE_TOML.replace("__NAME__", name))
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(f"# {name}\n\n```bash\npoi run\n```\n")
    print(f"만들었어요: {root}")
    print("다음:")
    print(f"  cd {name}")
    print("  poi run")
    return 0


def cmd_check(args: list[str]) -> int:
    if not args:
        print("검사할 파일을 알려주세요: poi check <파일.poi>", file=sys.stderr)
        return 1
    path = args[0]
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print(f"파일을 열 수 없습니다: {e}", file=sys.stderr)
        return 1
    try:
        compile_source(src, os.path.basename(path))
    except POIError as e:
        print(e.render(src), file=sys.stderr)
        return 1
    print(f"문법 OK: {path}")
    return 0


def cmd_fmt(args: list[str]) -> int:
    print("poi fmt 는 아직 준비 중이에요 (로드맵 v0.9). 지금은 `poi check` 를 쓰세요.")
    return 0


def cmd_build(args: list[str]) -> int:
    from .build import build
    return build(args)


def cmd_repl(_args: list[str]) -> int:
    from .runtime import make_globals
    from . import banner
    banner.show()
    g = make_globals()
    g["__name__"] = "__main__"
    print(f"POI {__version__} REPL - 나가려면 exit 또는 Ctrl+C")
    buf = ""
    while True:
        try:
            prompt = "... " if buf else "poi> "
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not buf and line.strip() in ("exit", "quit"):
            return 0
        buf += line + "\n"
        if line.strip().endswith("{") or _unbalanced(buf):
            continue
        code = buf
        buf = ""
        try:
            py_src, linemap, cname = compile_source(code, "<repl>")
            exec(compile(py_src, cname, "exec"), g)
        except POIError as e:
            print(e.render(code), file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            from .errors import translate_exception
            print(translate_exception(e, code, {}, "<repl>").render(code),
                  file=sys.stderr)


def _unbalanced(text: str) -> bool:
    depth = 0
    in_str = False
    esc = False
    for ch in text:
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
    return depth > 0


def cmd_install(args: list[str]) -> int:
    from .winsetup import install
    return install(args)


def cmd_uninstall(args: list[str]) -> int:
    from .winsetup import uninstall
    return uninstall(args)


def main(argv: list[str] | None = None) -> int:
    for _s in (sys.stdout, sys.stderr):
        try:
            _s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] in ("__install__", "install"):
        return cmd_install(argv[1:])
    if argv and argv[0] in ("__uninstall__", "uninstall"):
        return cmd_uninstall(argv[1:])
    if "--no-banner" in argv:
        os.environ["POI_NO_BANNER"] = "1"
        argv = [a for a in argv if a != "--no-banner"]
    if not argv or argv[0] in ("help", "-h", "--help"):
        from . import banner
        banner.show()
        print(HELP.format(ver=__version__))
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd in ("version", "-v", "--version"):
        print(f"POI {__version__}")
        _maybe_update_notice()
        return 0
    table = {
        "run": cmd_run, "new": cmd_new, "check": cmd_check,
        "repl": cmd_repl, "fmt": cmd_fmt, "build": cmd_build,
        "update": cmd_update, "upgrade": cmd_update, "debug": cmd_debug,
        "serve": cmd_serve, "playground": cmd_serve, "exercises": cmd_exercises,
        "ex": cmd_exercises, "test": cmd_test, "build": cmd_build,
    }
    if cmd in table:
        return table[cmd](rest)
    # `poi foo.poi` 처럼 바로 파일을 주면 run 으로
    if cmd.endswith(".poi") and os.path.exists(cmd):
        return cmd_run([cmd, *rest])
    print(f"모르는 명령입니다: {cmd}\n`poi help` 를 보세요.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

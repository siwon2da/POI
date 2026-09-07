"""POI 명령줄 도구."""
from __future__ import annotations

import os
import sys

from . import __version__
from .errors import POIError
from .interpreter import compile_source, run_file, run_source

HELP = """\
POI v{ver}  -  Python Powered, Human First

사용법:
  poi run [파일.poi] [--emit-python]   POI 파일 실행 (기본: src/main.poi 또는 main.poi)
  poi new <이름>                       새 프로젝트 폴더 만들기
  poi check <파일.poi>                 문법만 검사 (실행 안 함)
  poi repl                            대화형 셸
  poi version                        버전 출력
  poi help                          이 도움말

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


def cmd_run(args: list[str]) -> int:
    emit = "--emit-python" in args
    args = [a for a in args if a != "--emit-python"]
    path = args[0] if args else _find_default_entry()
    if not path:
        print("실행할 .poi 파일을 못 찾았어요. `poi run 파일.poi` 처럼 지정하세요.",
              file=sys.stderr)
        return 1
    if not os.path.exists(path):
        print(f"파일이 없습니다: {path}", file=sys.stderr)
        return 1
    return run_file(path, emit_python=emit, argv=args[1:])


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
    print("poi build (단일 실행파일) 는 로드맵 v0.8 입니다.\n"
          "지금 배포하려면: python -m poi run <파일> 또는 pip install -e . 후 poi 명령 사용.")
    return 0


def cmd_repl(_args: list[str]) -> int:
    from .runtime import make_globals
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


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] in ("help", "-h", "--help"):
        print(HELP.format(ver=__version__))
        return 0
    cmd, rest = argv[0], argv[1:]
    if cmd in ("version", "-v", "--version"):
        print(f"POI {__version__}")
        return 0
    table = {
        "run": cmd_run, "new": cmd_new, "check": cmd_check,
        "repl": cmd_repl, "fmt": cmd_fmt, "build": cmd_build,
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

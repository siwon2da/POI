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
       --safe [--time N]              샌드박스로 실행 (python 블록·use py·파일·네트워크 차단, 시간 제한)
       --types                       선택적 정적 타입 검사도 함께
  poi debug <파일.poi>                 = poi run --debug
  poi test [파일.poi]                  파일 안의 test 블록 실행
  poi build <파일.poi> [-o 이름]        단일 실행파일(.exe) 로 빌드
  poi idle [파일.poi]                  POI IDLE — POI 로 만든 코드 편집기
  poi photo [사진]                     POI 로 만든 사진 편집기 (Pillow 필요)
  poi add / remove / install          프로젝트 파이썬 의존성 (.venv + poi.toml + poi.lock)
       install --frozen               poi.lock 그대로 설치 (재현용)
  poi cache [clear]                   컴파일 캐시 상태 / 비우기 (~/.poi/cache)
  poi run 파일 --serve --host 0.0.0.0 --port 80 [--prod]   운영 서버로 노출
  poi wsgi <앱.poi> [-o wsgi.py]      gunicorn/waitress 용 WSGI 진입점 생성
  poi doctor                          실행 환경 진단 (파이썬·tkinter·캐시·하온 …)
  poi new <이름> [--web|--api|--cli]   템플릿으로 프로젝트 생성
  poi fmt [파일 | .] [--check]         소스 정리 (탭·공백·들여쓰기)
  poi lint [파일 | .] [--strict]       안 쓴 변수 등 가벼운 점검
  poi serve [폴더] [--port 8900]       플레이그라운드 서버 (정적 서빙 + 안전 실행 /run)
  poi new <이름>                       새 프로젝트 폴더 만들기
  poi check <파일.poi | .> [--types]    문법·타입만 검사 (실행 안 함)
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


_RUN_FLAGS = {"--emit-python", "--trace", "--vars", "--explain", "--debug",
              "--safe", "--types", "--no-cache"}


def _run(args: list[str], *, force_debug: bool = False) -> int:
    time_limit = 5.0
    web_port = 8080
    web_host = "127.0.0.1"
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
        elif a in ("--port", "-p"):
            try:
                web_port = int(next(it))
            except (StopIteration, ValueError):
                pass
        elif a.startswith("--port="):
            try:
                web_port = int(a.split("=", 1)[1])
            except ValueError:
                pass
        elif a == "--host":
            web_host = next(it, "127.0.0.1")
        elif a.startswith("--host="):
            web_host = a.split("=", 1)[1]
        elif a == "--prod":
            os.environ["POI_ENV"] = "production"
        else:
            kept.append(a)
    flags = {a for a in kept if a in _RUN_FLAGS}
    rest = [a for a in kept if a not in _RUN_FLAGS]
    emit = "--emit-python" in flags
    trace = "--trace" in flags or "--debug" in flags or force_debug
    trace_vars = "--vars" in flags or "--debug" in flags or force_debug
    explain = "--explain" in flags or "--debug" in flags or force_debug
    safe = "--safe" in flags
    want_types = "--types" in flags
    if "--no-cache" in flags:
        os.environ["POI_NO_CACHE"] = "1"

    path = rest[0] if rest else _find_default_entry()
    if not path:
        print("실행할 .poi 파일을 못 찾았어요. `poi run 파일.poi` 처럼 지정하세요.",
              file=sys.stderr)
        return 1
    if not os.path.exists(path):
        print(f"파일이 없습니다: {path}", file=sys.stderr)
        return 1
    if not safe:
        try:
            from .pkg import activate as _pkg_activate
            _pkg_activate(os.path.dirname(os.path.abspath(path)) or ".")
            _pkg_activate(".")
        except Exception:
            pass
    if want_types:
        _typecheck_file(path, block=False)
    rc = run_file(path, emit_python=emit, argv=rest[1:],
                  trace=trace, trace_vars=trace_vars, explain=explain,
                  safe=safe, time_limit=time_limit, web_port=web_port,
                  web_host=web_host)
    if not emit and not safe:
        _maybe_update_notice()
    return rc


def _typecheck_file(path: str, block: bool) -> int:
    """block=True 면 오류 있을 때 exit 1. False 면 경고만 찍고 0."""
    from .interpreter import compile_source  # 파서까지만 필요
    from .lexer import Lexer
    from .parser import Parser
    from . import typecheck as tc
    try:
        with open(path, "r", encoding="utf-8") as f:
            src = f.read()
    except OSError as e:
        print(f"파일을 열 수 없습니다: {e}", file=sys.stderr)
        return 1
    try:
        ast = Parser(Lexer(src, os.path.basename(path)).tokenize(), src).parse()
    except Exception as e:  # noqa: BLE001
        from .errors import POIError
        if isinstance(e, POIError):
            print(e.render(src), file=sys.stderr)
        return 1
    findings = tc.check(ast)
    if not findings:
        if block:
            print(f"타입 문제 없음: {path}")
        return 0
    print(tc.render(findings, src), file=sys.stderr)
    errs = [f for f in findings if f.level == "error"]
    return 1 if (block and errs) else 0


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


_TPL_WEB = '''\
# __NAME__ — POI 웹 앱.   실행:  poi run   ·   프로덕션:  poi wsgi src/main.poi
# 공유 상태는 Box 에 담는다 (함수·라우트는 전역을 재대입 못 함)
S = { 글: [{ id: 1, title: "첫 글", body: "POI 로 만든 웹앱입니다." }] }

server {
    get "/" {
        render("home.html", { title: "__NAME__", 글: S.글 })
    }
    get "/api/posts" { respond.json(S.글) }
    post "/api/posts" {
        새 = { id: S.글.length + 1, title: body.title ?? "제목없음", body: body.body ?? "" }
        S.글 = S.글 + [새]
        respond.json(새, 201)
    }
}
'''

_TPL_WEB_HOME = '''\
<!doctype html><meta charset=utf-8><title>{{ title }}</title>
<style>body{font:16px/1.6 system-ui;max-width:640px;margin:40px auto;padding:0 20px}
h1{letter-spacing:-.02em} .post{border:1px solid #ddd;border-radius:12px;padding:14px 16px;margin:10px 0}</style>
<h1>{{ title }}</h1>
{% for p in 글 %}
  <div class=post><b>{{ p.title }}</b><p>{{ p.body }}</p></div>
{% endfor %}
<p><code>GET /api/posts</code> · <code>POST /api/posts</code></p>
'''

_TPL_API = '''\
# __NAME__ — POI JSON API.   실행:  poi run   ·   프로덕션:  poi wsgi src/main.poi
S = { 할일: [] }

server {
    get "/health" { respond.json({ ok: true }) }
    get "/todos"  { respond.json(S.할일) }
    post "/todos" {
        t = { id: S.할일.length + 1, text: body.text ?? "", done: false }
        S.할일 = S.할일 + [t]
        respond.json(t, 201)
    }
}
'''

_TPL_CLI = '''\
# __NAME__ — POI CLI.   실행:  poi run -- 인자들
인자 = poi_argv

if 인자.length == 0 {
    show "사용법: __NAME__ <이름>"
} else {
    show "안녕하세요, {인자.first}님!"
}
'''


def cmd_new(args: list[str]) -> int:
    kinds = {"--web": ("web", _TPL_WEB), "--api": ("api", _TPL_API),
             "--cli": ("cli", _TPL_CLI)}
    kind = next((kinds[a] for a in args if a in kinds), None)
    names = [a for a in args if not a.startswith("-")]
    if not names:
        print("프로젝트 이름을 알려주세요: poi new <이름> [--web|--api|--cli]",
              file=sys.stderr)
        return 1
    root = os.path.abspath(names[0])
    name = os.path.basename(root.rstrip("/\\")) or "poi-app"
    if os.path.exists(root):
        print(f"이미 있는 폴더입니다: {root}", file=sys.stderr)
        return 1
    for sub in ("", "src", "assets", "tests"):
        os.makedirs(os.path.join(root, sub), exist_ok=True)
    main_tpl = kind[1] if kind else _TEMPLATE_MAIN
    with open(os.path.join(root, "src", "main.poi"), "w", encoding="utf-8") as f:
        f.write(main_tpl.replace("__NAME__", name))
    if kind and kind[0] == "web":
        os.makedirs(os.path.join(root, "views"), exist_ok=True)
        with open(os.path.join(root, "views", "home.html"), "w", encoding="utf-8") as f:
            f.write(_TPL_WEB_HOME.replace("__NAME__", name))
    with open(os.path.join(root, "poi.toml"), "w", encoding="utf-8") as f:
        f.write(_TEMPLATE_TOML.replace("__NAME__", name))
    with open(os.path.join(root, "README.md"), "w", encoding="utf-8") as f:
        f.write(f"# {name}\n\n```bash\npoi run\n```\n")
    print(f"만들었어요: {root}   ({kind[0] if kind else '기본'} 템플릿)")
    print("다음:")
    print(f"  cd {name}")
    print("  poi run")
    return 0


def cmd_doctor(_args: list[str]) -> int:
    import shutil
    import platform
    ok = "  \033[32mOK\033[0m  " if sys.stdout.isatty() else "  OK  "
    no = "  \033[31m--\033[0m  " if sys.stdout.isatty() else "  --  "
    rows = []
    rows.append((sys.version_info >= (3, 9),
                 f"파이썬 {platform.python_version()}  (3.9+ 필요)"))
    try:
        import tkinter  # noqa: F401
        rows.append((True, "tkinter  (GUI · IDLE)"))
    except Exception:
        rows.append((False, "tkinter 없음 — GUI/IDLE 안 됨"))
    try:
        import PIL  # noqa: F401
        rows.append((True, "Pillow  (poi photo)"))
    except Exception:
        rows.append((False, "Pillow 없음 — poi photo 는 'poi add pillow'"))
    from . import cache as _cache
    ci = _cache.info()
    rows.append((os.access(os.path.dirname(ci["dir"]) or ".", os.W_OK),
                 f"컴파일 캐시  {ci['dir']}  ({ci['entries']}개)"))
    for tool in ("git", "gunicorn", "waitress-serve"):
        rows.append((shutil.which(tool) is not None,
                     f"{tool}  {'있음' if shutil.which(tool) else '(선택)'}"))
    try:
        from .apps import haon as _h
        d = _h.detect()
        rows.append((d.get("mode") not in (None, "none"),
                     f"하온 백엔드: {d.get('mode')}"))
    except Exception:
        rows.append((False, "하온 감지 실패"))
    print(f"\n  POI {__version__}  진단\n")
    bad = 0
    for good, label in rows:
        print((ok if good else no) + label)
        if not good and "필요" in label:
            bad += 1
    print()
    return 1 if bad else 0


_WSGI_SHIM = '''\
"""자동 생성 — POI 앱을 WSGI 로 노출.
  gunicorn  wsgi:application  -w 4 -b 0.0.0.0:8000
  waitress-serve  --port=8000  wsgi:application
"""
from poi.runtime.wsgi import load
application = load(r"__APP__")
'''


def cmd_wsgi(args: list[str]) -> int:
    rest = [a for a in args if not a.startswith("-")]
    if not rest:
        print("사용법: poi wsgi <앱.poi> [-o wsgi.py]", file=sys.stderr)
        return 1
    app = os.path.abspath(rest[0])
    if not os.path.isfile(app):
        print(f"파일이 없습니다: {app}", file=sys.stderr)
        return 1
    out = "wsgi.py"
    if "-o" in args:
        i = args.index("-o")
        if i + 1 < len(args):
            out = args[i + 1]
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(_WSGI_SHIM.replace("__APP__", app))
    mod = os.path.splitext(os.path.basename(out))[0]
    print(f"만들었어요: {out}\n")
    print("프로덕션 서버로 (하나 골라서):")
    print(f"  pip install gunicorn   &&   gunicorn {mod}:application -w 4 -b 0.0.0.0:8000")
    print(f"  pip install waitress   &&   waitress-serve --port=8000 {mod}:application")
    print(f"  pip install uvicorn    &&   uvicorn --interface wsgi {mod}:application --port 8000")
    print("\n환경변수: POI_ENV=production (오류 상세 숨김) · /healthz 는 자동 제공")
    return 0


def cmd_check(args: list[str]) -> int:
    want_types = "--types" in args
    rest = [a for a in args if not a.startswith("-")]
    if not rest:
        print("검사할 파일을 알려주세요: poi check [--types] <파일.poi | .>",
              file=sys.stderr)
        return 1
    targets = []
    for t in rest:
        targets += _poi_files(t)
    if not targets:
        print("검사할 .poi 파일이 없어요.", file=sys.stderr)
        return 1
    rc = 0
    for path in targets:
        try:
            with open(path, "r", encoding="utf-8") as f:
                src = f.read()
        except OSError as e:
            print(f"파일을 열 수 없습니다: {e}", file=sys.stderr)
            rc = 1
            continue
        try:
            compile_source(src, os.path.basename(path))
        except POIError as e:
            print(e.render(src), file=sys.stderr)
            rc = 1
            continue
        if want_types:
            rc |= _typecheck_file(path, block=True)
        else:
            print(f"문법 OK: {path}")
    if not want_types and rc == 0:
        print("(타입도 보려면 --types)")
    return rc


def _poi_files(target: str) -> list[str]:
    """'.' 또는 폴더 → 그 안의 .poi 전부. 파일이면 그 하나."""
    if os.path.isfile(target):
        return [target]
    root = "." if target == "." else target
    found = []
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in
                   ("__pycache__", ".git", "node_modules", "dist", "build")]
        for name in sorted(files):
            if name.endswith(".poi"):
                found.append(os.path.join(base, name))
    return found


def cmd_fmt(args: list[str]) -> int:
    from .fmt import fmt_file
    check_only = "--check" in args
    rest = [a for a in args if not a.startswith("-")] or ["."]
    targets = []
    for t in rest:
        targets += _poi_files(t)
    if not targets:
        print("정리할 .poi 파일이 없어요.", file=sys.stderr)
        return 1
    changed = 0
    for p in targets:
        did, msg = fmt_file(p, write=not check_only)
        if did:
            changed += 1
            print(msg)
        elif "건너뜀" in msg:
            print(msg)
    if check_only:
        print(f"\n정리 필요: {changed}개" if changed else "\n전부 정리돼 있어요.")
        return 1 if changed else 0
    print(f"\n{changed}개 정리함." if changed else "\n바꿀 게 없었어요.")
    return 0


def cmd_lint(args: list[str]) -> int:
    from .lint import lint_file
    strict = "--strict" in args
    rest = [a for a in args if not a.startswith("-")] or ["."]
    targets = []
    for t in rest:
        targets += _poi_files(t)
    if not targets:
        print("검사할 .poi 파일이 없어요.", file=sys.stderr)
        return 1
    rc = 0
    for p in targets:
        rc |= lint_file(p, strict=strict)
    return rc


def cmd_build(args: list[str]) -> int:
    if "--site" in args:
        return _build_site([a for a in args if a != "--site"])
    from .build import build
    return build(args)


def _build_site(args: list[str]) -> int:
    """poi build --site 앱.poi [-o dist]  —  GET 라우트를 정적 HTML 로 굽는다."""
    import shutil
    rest = [a for a in args if not a.startswith("-")]
    if not rest:
        print("poi build --site <앱.poi> [-o 폴더]", file=sys.stderr)
        return 1
    app = os.path.abspath(rest[0])
    out = "dist"
    if "-o" in args:
        i = args.index("-o")
        if i + 1 < len(args):
            out = args[i + 1]
    from .interpreter import compile_source
    from .runtime import make_globals
    from .runtime import webserver as ws
    ws.reset()
    src = open(app, encoding="utf-8").read()
    py, lm, cn = compile_source(src, os.path.basename(app))
    g = make_globals()
    g["__name__"] = "__main__"
    g["__poi_dir__"] = os.path.dirname(app)
    os.environ["POI_NO_SERVE"] = "1"
    exec(compile(py, cn, "exec"), g)  # noqa: S102
    compiled, static_dirs, _actions, _title = ws._routes_now()
    os.makedirs(out, exist_ok=True)
    n = 0
    for m, rx, fn in compiled:
        pat = rx.pattern
        if m != "GET" or "?P<" in pat or ".*" in pat:
            continue
        path = pat[1:].rstrip("/?$").replace("\\", "") or "/"
        try:
            result = fn(_ns_box(), _ns_box(), _ns_box(),
                        _ns_box(), "GET")
        except Exception as e:  # noqa: BLE001
            print(f"  건너뜀 {path}: {e}", file=sys.stderr)
            continue
        st, data, ct, _ex = ws._coerce(result)
        if st != 200 or b"html" not in ct.encode():
            if "json" not in ct:
                continue
        rel = "index.html" if path in ("/", "") else path.strip("/") + "/index.html"
        dst = os.path.join(out, rel)
        os.makedirs(os.path.dirname(dst) or out, exist_ok=True)
        with open(dst, "wb") as f:
            f.write(data)
        n += 1
        print(f"  {path:24} → {rel}")
    for d in static_dirs:
        if os.path.isdir(d):
            shutil.copytree(d, os.path.join(out, os.path.basename(d)),
                            dirs_exist_ok=True)
    print(f"\n정적 사이트 {n}쪽 → {out}/   (아무 데나 올리면 됩니다)")
    return 0


def _ns_box():
    from .runtime.boxes import Box
    return Box()


def _app_path(name: str) -> str:
    return os.path.join(os.path.dirname(__file__), "apps", name + ".poi")


def cmd_idle(args: list[str]) -> int:
    """poi idle [파일.poi] — POI 로 작성한 코드 편집기 (POI IDLE)."""
    path = _app_path("idle")
    if not os.path.isfile(path):
        print("POI IDLE 을 찾을 수 없습니다.", file=sys.stderr)
        return 1
    target = next((a for a in args if not a.startswith("-")), None)
    if target:
        os.environ["POI_IDLE_OPEN"] = os.path.abspath(target)
    os.environ["POI_NO_SERVE"] = "1"
    return run_file(path)


def cmd_photo(args: list[str]) -> int:
    """poi photo [사진] — POI 로 작성한 사진 편집기."""
    path = _app_path("photo")
    if not os.path.isfile(path):
        print("POI 사진 편집기를 찾을 수 없습니다.", file=sys.stderr)
        return 1
    target = next((a for a in args if not a.startswith("-")), None)
    if target and os.path.isfile(target):
        os.environ["POI_PHOTO_OPEN"] = os.path.abspath(target)
    os.environ["POI_NO_SERVE"] = "1"
    return run_file(path)


_REPL_HELP = """\
POI REPL 도움말
  show <값>              값 출력          예:  show "안녕"   /   show 2 + 3
  이름 = <값>            변수                예:  나이 = 16
  fn 함수(a, b) ...      함수 정의 (여러 줄은 자동으로 이어집니다)
  for x in [1,2,3] ...   반복 / repeat 5 as i ...
  use math              표준 모듈 (crypto·path·jwt·url·datetime …)
  show test             ✦
  exit / 나가기          REPL 종료        (Ctrl+C 도 됩니다)
자세히:  poi help    ·    책:  https://hagora.kr/poi/book/
"""


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
        if not buf and line.strip() in ("exit", "quit", "나가기"):
            return 0
        if not buf and line.strip() in ("help", "?", "도움말", "도움"):
            print(_REPL_HELP)
            continue
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
        print(HELP.replace("{ver}", __version__))
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
        "ex": cmd_exercises, "test": cmd_test, "idle": cmd_idle,
        "lint": cmd_lint, "photo": cmd_photo,
        "add": lambda a: __import__("poi.pkg", fromlist=["cmd_add"]).cmd_add(a),
        "remove": lambda a: __import__("poi.pkg", fromlist=["cmd_remove"]).cmd_remove(a),
        "rm": lambda a: __import__("poi.pkg", fromlist=["cmd_remove"]).cmd_remove(a),
        "install": lambda a: __import__("poi.pkg", fromlist=["cmd_install"]).cmd_install(a),
        "cache": lambda a: __import__("poi.cache", fromlist=["cmd_cache"]).cmd_cache(a),
        "doctor": cmd_doctor, "wsgi": cmd_wsgi,
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

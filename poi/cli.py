"""POI 명령줄 도구."""
from __future__ import annotations

import os
import subprocess
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
       --safe [--time N]              샌드박스로 실행 (파일·네트워크·외부 실행 차단, 시간 제한)
       --types                       선택적 정적 타입 검사도 함께
  poi debug <파일.poi>                 = poi run --debug
  poi test [파일.poi]                  파일 안의 test 블록 실행
  poi build <파일.poi> [-o 이름]        단일 실행파일(.exe) 로 빌드
  poi idle [파일.poi]                  POI IDLE — POI 로 만든 코드 편집기
  poi photo [사진]                     POI 로 만든 사진 편집기 (Pillow 필요)
  poi add / remove / install          프로젝트 의존성 (.venv + poi.toml + poi.lock)
       install --frozen               poi.lock 그대로 설치 (재현용)
  poi cache [clear]                   컴파일 캐시 상태 / 비우기 (~/.poi/cache)
  poi run 파일 --host 0.0.0.0 --port 80 [--prod]   운영 서버로 노출
  poi wsgi <앱.poi> [-o wsgi.py]      gunicorn/waitress 용 WSGI 진입점 생성
  poi doctor                          실행 환경 진단
  poi init                            대화형으로 프로젝트 만들기 (콘솔/웹/API/GUI/게임/데이터)
  poi new <이름> [--web|--api|--cli]   템플릿으로 프로젝트 생성
  poi search <말>                     패키지 레지스트리 검색      poi add <이름>  설치
  poi publish                         현재 프로젝트를 패키지로 묶기
  poi migrate <파일|.> [--write]      v2.0 스타일로 정리 (콜론/파이썬 습관 → 중괄호/POI)
  poi haon login | status | agent <폴더> "<할 일>"    하온: ChatGPT 연결 · 에이전트
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


def _project_meta() -> dict:
    """poi.toml 의 [project] 를 읽는다 (아주 최소)."""
    p = "poi.toml"
    out, section = {}, None
    if not os.path.isfile(p):
        return out
    try:
        for line in open(p, encoding="utf-8"):
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                section = s[1:-1]
                continue
            if section == "project" and "=" in s and not s.startswith("#"):
                k, _, v = s.partition("=")
                out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        pass
    return out


def _find_default_entry() -> str | None:
    meta = _project_meta()
    if meta.get("entry") and os.path.exists(meta["entry"]):
        return meta["entry"]
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


def _eco(name):
    return getattr(__import__("poi.ecosystem", fromlist=[name]), name)


def _deploy_config() -> dict:
    """배포 설정을 로컬에서만 읽는다 (poi.toml [deploy] → ~/.poi/deploy.json).
    비밀번호·키는 절대 명령행 인자로 받지 않는다."""
    cfg = {}
    p = "poi.toml"
    if os.path.isfile(p):
        section = None
        for line in open(p, encoding="utf-8"):
            s = line.strip()
            if s.startswith("[") and s.endswith("]"):
                section = s[1:-1]
                continue
            if section == "deploy" and "=" in s and not s.startswith("#"):
                k, _, v = s.partition("=")
                cfg[k.strip()] = v.strip().strip('"').strip("'")
    home = os.path.join(os.path.expanduser("~"), ".poi", "deploy.json")
    if os.path.isfile(home):
        try:
            import json
            cfg = {**json.load(open(home, encoding="utf-8")), **cfg}
        except Exception:
            pass
    return cfg


def _haon_deploy(args: list[str]) -> int:
    """poi haon deploy [--git] [--dry] — 로컬 설정의 서버로 프로젝트를 올린다."""
    cfg = _deploy_config()
    host, user = cfg.get("host"), cfg.get("user", "root")
    remote = cfg.get("path")
    do_git = "--git" in args or str(cfg.get("git", "")).lower() in ("1", "true", "yes")
    dry = "--dry" in args or "--dry-run" in args
    if not host or not remote:
        print("배포 설정이 없어요. poi.toml 에 넣거나 ~/.poi/deploy.json 을 만드세요:\n"
              '  [deploy]\n  host = "example.com"\n  user = "deploy"\n'
              '  path = "/var/www/app"\n  key = "~/.ssh/id_ed25519"   # 또는 생략하면 실행 시 비번 물음\n'
              "  git = true", file=sys.stderr)
        return 1
    try:
        import paramiko
    except ImportError:
        print("SSH 배포에는 paramiko 가 필요해요:  poi add paramiko", file=sys.stderr)
        return 1

    import fnmatch
    import getpass
    import posixpath
    ignore = ["*.pyc", "__pycache__", ".git", ".venv", "node_modules", "dist",
              ".poi", "*.log"] + [g.strip() for g in
                                  (open(".gitignore", encoding="utf-8").read().splitlines()
                                   if os.path.isfile(".gitignore") else [])
                                  if g.strip() and not g.startswith("#")]

    def skip(rel):
        return any(fnmatch.fnmatch(rel, g) or fnmatch.fnmatch(os.path.basename(rel), g)
                   or g.rstrip("/") in rel.split("/") for g in ignore)

    files = []
    for base, dirs, fs in os.walk("."):
        dirs[:] = [d for d in dirs if not skip(os.path.relpath(os.path.join(base, d), "."))]
        for f in fs:
            rel = os.path.relpath(os.path.join(base, f), ".").replace("\\", "/")
            if not skip(rel):
                files.append(rel)
    print(f"대상: {user}@{host}:{remote}   ·   파일 {len(files)}개"
          + ("   (드라이런)" if dry else ""))
    if dry:
        for rel in files[:40]:
            print("  " + rel)
        if len(files) > 40:
            print(f"  … 외 {len(files) - 40}개")
        return 0

    cli = paramiko.SSHClient()
    cli.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    key_path = os.path.expanduser(cfg["key"]) if cfg.get("key") else None
    try:
        if key_path and os.path.isfile(key_path):
            cli.connect(host, port=int(cfg.get("port", 22)), username=user,
                        key_filename=key_path, timeout=25)
        else:
            pw = os.environ.get("POI_DEPLOY_PASSWORD") or getpass.getpass(
                f"{user}@{host} 비밀번호: ")
            cli.connect(host, port=int(cfg.get("port", 22)), username=user,
                        password=pw, timeout=25, look_for_keys=False, allow_agent=False)
    except Exception as e:  # noqa: BLE001
        print(f"접속 실패: {e}", file=sys.stderr)
        return 1
    sftp = cli.open_sftp()
    made = set()

    def mkdirs(rp):
        parts = rp.split("/")
        cur = ""
        for p in parts[:-1]:
            cur = posixpath.join(cur, p) if cur else p
            full = posixpath.join(remote, cur)
            if full not in made:
                cli.exec_command(f'mkdir -p "{full}"')
                made.add(full)

    n = 0
    for rel in files:
        rp = posixpath.join(remote, rel)
        mkdirs(rel)
        try:
            sftp.put(rel, rp)
            n += 1
        except Exception as e:  # noqa: BLE001
            print(f"  실패 {rel}: {e}", file=sys.stderr)
    sftp.close()
    cli.close()
    print(f"올림: {n}/{len(files)}개")
    if do_git:
        import time as _t
        for c in (["git", "add", "-A"],
                  ["git", "commit", "-m", "deploy: " + _t.strftime("%Y-%m-%d %H:%M")],
                  ["git", "push"]):
            r = subprocess.run(c)
            if c[1] == "commit" and r.returncode != 0:
                print("(커밋할 변경 없음 — push 만 시도)")
        print("git push 완료")
    return 0


def _cmd_add(args: list[str]) -> int:
    """poi add <이름> — 레지스트리에 있으면 POI 모듈, 없으면 pip 패키지."""
    names = [a for a in args if not a.startswith("-")]
    from . import ecosystem as eco
    handled = []
    for n in list(names):
        try:
            if eco.registry_add(n):
                handled.append(n)
        except Exception:
            pass
    leftover = [a for a in args if a not in handled]
    if [a for a in leftover if not a.startswith("-")]:
        from .pkg import cmd_add
        return cmd_add(leftover)
    return 0 if handled else 1


def cmd_haon(args: list[str]) -> int:
    """poi haon login | logout | status | agent <폴더> "<할 일>" | fix <파일>"""
    sub = args[0] if args else "status"
    rest = args[1:]
    from .apps import haon as h
    if sub == "login":
        try:
            from .apps import haon_gpt as cg
        except Exception as e:  # noqa: BLE001
            print(f"불가: {e}", file=sys.stderr)
            return 1
        return 0 if cg.login(print) else 1
    if sub == "logout":
        from .apps import haon_gpt as cg
        cg.logout()
        print("ChatGPT 로그아웃 했어요.")
        return 0
    if sub in ("status", "whoami"):
        try:
            from .apps import haon_gpt as cg
            st = cg.status()
            info = cg.detect()
        except Exception:
            st, info = {"logged_in": False}, h.detect()
        print(f"하온 백엔드:  {info.get('mode')}")
        if st.get("logged_in"):
            print(f"ChatGPT:      로그인됨 ({st.get('email') or '계정'})"
                  + ("  · 만료 — poi haon login" if st.get("expired") else ""))
        else:
            print("ChatGPT:      로그아웃  (poi haon login 으로 연결)")
        print(f"Groq:         {'있음' if info.get('groq') else '없음 (GROQ_API_KEY)'}")
        print(f"로컬 LLM:      {', '.join(info.get('models') or []) or '없음 (poi 로 ollama 설치)'}")
        return 0
    if sub == "prompt":
        print(h._POI_RULES)
        return 0
    if sub in ("agent", "do"):
        pos = [a for a in rest if not a.startswith("-")]
        folder, task = ".", ""
        # 인자가 2개 이상이면 첫 번째를 폴더로 (없으면 만든다)
        if len(pos) >= 2 and not pos[0].endswith(".poi") and " " not in pos[0]:
            folder, task = pos[0], " ".join(pos[1:])
        else:
            task = " ".join(pos)
        if not task:
            print('poi haon agent <폴더> "<만들 것>"', file=sys.stderr)
            return 1
        from .apps import haon_gpt as cg
        r = cg.agent(task, folder, print)
        print()
        print("결과:", "성공 — " + r.get("message", "") if r.get("ok")
              else "미완 — " + r.get("message", ""))
        if r.get("files"):
            print("파일:", ", ".join(r["files"]))
        return 0 if r.get("ok") else 1
    if sub == "deploy":
        return _haon_deploy(rest)
    if sub == "fix":
        if not rest:
            print("poi haon fix <파일.poi>", file=sys.stderr)
            return 1
        src = open(rest[0], encoding="utf-8").read()
        new, log = h.autofix(src)
        print("\n".join(log) or "고칠 게 없었어요.")
        if new != src and ("--write" in rest or "-w" in rest):
            open(rest[0], "w", encoding="utf-8", newline="\n").write(new)
            print("고쳐서 저장했어요.")
        return 0
    print(f"모르는 하온 명령: {sub}\n  login / logout / status / agent / fix / prompt",
          file=sys.stderr)
    return 1


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
  이름 = <값>            변수 (마지막 식은 자동으로 값이 찍힙니다)
  show <값>              값 출력          예:  show 2 + 3
  fn 함수(a, b) ...      함수 정의 (여러 줄은 자동으로 이어집니다)
  use math              표준 모듈 (crypto·path·jwt·url·datetime …)
  :type <식>            식의 타입          :type "안녕"  →  Text
  :vars                 지금까지의 변수
  :clear               화면 지우기        :reset  변수 전부 비우기
  :help                이 도움말          exit / 나가기  종료
자세히:  poi help    ·    책:  https://hagora.kr/poi/book/
"""


def _repl_kind(v):
    import numbers as _n
    if v is True or v is False:
        return "Bool"
    if v is None:
        return "Null"
    if isinstance(v, bool):
        return "Bool"
    if isinstance(v, int):
        return "Int"
    if isinstance(v, float):
        return "Float"
    if isinstance(v, str):
        return "Text"
    if isinstance(v, dict):
        return "Map"
    if isinstance(v, (list, tuple)):
        return "List"
    if callable(v):
        return "Fn"
    return type(v).__name__


_REPL_STMT = __import__("re").compile(
    r"^\s*(show|ask|use|python|if|else|elif|for|while|repeat|fn|def|return|const|"
    r"try|catch|match|when|raise|assert|test|break|continue|export|import|pass|"
    r"server|webapp|app|background|every|game)\b")


def _repl_block_open(text: str) -> bool:
    """마지막 비어있지 않은 줄이 블록 여는 키워드인데 { 도 : 도 없으면 계속 입력받는다."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if not lines:
        return False
    last = lines[-1].rstrip()
    if last.endswith(("{", ":", "\\", ",", "(", "[", "+", "-", "=>", "|>")):
        return True
    m = __import__("re").match(
        r"\s*(if|else if|elif|for|while|repeat|fn|def|try|catch|match|when)\b", last)
    return bool(m) and not last.endswith("}")


def cmd_repl(_args: list[str]) -> int:
    from .runtime import make_globals
    from . import banner
    banner.show()
    g = make_globals()
    g["__name__"] = "__main__"
    _repl_base = set(g)
    print(f"POI {__version__} REPL   ·   :help  도움말   ·   exit  종료")
    buf = ""
    while True:
        try:
            prompt = "... " if buf else "poi> "
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        s = line.strip()
        if not buf and s in ("exit", "quit", "나가기"):
            return 0
        if not buf and s in ("help", "?", "도움말", "도움", ":help", ":h"):
            print(_REPL_HELP)
            continue
        if not buf and s in (":clear", ":cls"):
            os.system("cls" if os.name == "nt" else "clear")
            continue
        if not buf and s in (":reset",):
            from .runtime import make_globals as _mg
            g.clear()
            g.update(_mg())
            g["__name__"] = "__main__"
            print("변수를 전부 비웠어요.")
            continue
        if not buf and s == ":vars":
            base = set(_repl_base)
            names = [k for k in g
                     if k not in base and not k.startswith("_") and k != "__name__"]
            if not names:
                print("(아직 변수 없음)")
            for k in sorted(names):
                v = g[k]
                try:
                    from .runtime.builtins import poi_fmt as _pf
                    disp = _pf(v)
                except Exception:
                    disp = repr(v)
                print(f"  {k} : {_repl_kind(v)} = {disp}")
            continue
        if not buf and s.startswith(":type "):
            expr = s[6:].strip()
            try:
                py_src, _lm, cn = compile_source(expr, "<repl>")
                val = eval(compile(py_src.strip() or "None", cn, "eval"), g)  # noqa: S307
                print(f"  {_repl_kind(val)}")
            except Exception:
                try:
                    exec(compile(f"__t = ({expr})", "<repl>", "exec"), g)
                    print(f"  {_repl_kind(g.get('__t'))}")
                except Exception as e:  # noqa: BLE001
                    print(f"  ? ({e})")
            continue
        buf += line + "\n"
        if buf.strip() and line.strip() == "":
            pass  # 빈 줄 → 여러 줄 입력 끝
        elif line.strip().endswith(("{", ":")) or _unbalanced(buf) \
                or _repl_block_open(buf):
            continue
        code = buf
        buf = ""
        try:
            py_src, linemap, cname = compile_source(code, "<repl>")
            _co = compile(py_src, cname, "exec")
            exec(_co, g)
            # 마지막 줄이 순수 식이면 값도 찍는다
            _last = code.strip().splitlines()[-1] if code.strip() else ""
            if _last and not _REPL_STMT.match(_last) and "=" not in _last.split("#")[0]:
                try:
                    val = eval(compile(_last, cname, "eval"), g)  # noqa: S307
                    if val is not None:
                        from .runtime.builtins import poi_fmt as _pf
                        print(_pf(val))
                except Exception:
                    pass
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
        "add": _cmd_add,
        "remove": lambda a: __import__("poi.pkg", fromlist=["cmd_remove"]).cmd_remove(a),
        "rm": lambda a: __import__("poi.pkg", fromlist=["cmd_remove"]).cmd_remove(a),
        "install": lambda a: __import__("poi.pkg", fromlist=["cmd_install"]).cmd_install(a),
        "cache": lambda a: __import__("poi.cache", fromlist=["cmd_cache"]).cmd_cache(a),
        "doctor": cmd_doctor, "wsgi": cmd_wsgi,
        "init": lambda a: _eco("cmd_init")(a),
        "search": lambda a: _eco("cmd_search")(a),
        "publish": lambda a: _eco("cmd_publish")(a),
        "migrate": lambda a: _eco("cmd_migrate")(a),
        "haon": cmd_haon,
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

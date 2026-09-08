"""poi build — POI 프로그램을 단일 실행파일로 (v1.3).

    poi build app.poi [-o 이름] [--console]

PyInstaller 로 묶는다. 파이썬이 없는 컴퓨터에서도 돈다.
한계: use pyfile / use "./x.poi" 로 부르는 파일은 자동 포함되지 않는다
      (필요하면 만든 exe 옆에 같이 두거나 --add-data 로).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile


def _have_pyinstaller() -> bool:
    try:
        import PyInstaller  # noqa: F401
        return True
    except Exception:
        return False


def build(args: list[str]) -> int:
    from .interpreter import compile_source

    src_path = None
    out_name = None
    console = False
    obfuscate = False
    lock_pw = None
    ask_pw = False
    it = iter(args)
    for a in it:
        if a in ("-o", "--out", "--name"):
            out_name = next(it, None)
        elif a in ("--console", "-c"):
            console = True
        elif a in ("--obfuscate", "--obf"):
            obfuscate = True
        elif a == "--lock":
            lock_pw = next(it, "") or ""
        elif a.startswith("--lock="):
            lock_pw = a.split("=", 1)[1]
        elif a == "--ask-password":
            ask_pw = True
        elif a == "--app":
            name = next(it, None)
            if name:
                src_path = os.path.join(os.path.dirname(__file__), "apps",
                                        name + ".poi")
                out_name = out_name or ("poi-" + name)
        elif not a.startswith("-"):
            src_path = a

    if not src_path or not os.path.isfile(src_path):
        print("빌드할 .poi 파일을 지정하세요:  poi build app.poi\n"
              "               또는:  poi build --app idle", file=sys.stderr)
        return 1
    if not _have_pyinstaller():
        print("PyInstaller 가 필요합니다:  python -m pip install pyinstaller")
        print("(설치 후 다시 poi build)")
        return 1

    with open(src_path, encoding="utf-8") as f:
        poi_src = f.read()
    try:
        py_src, _lm, _cn = compile_source(poi_src, os.path.basename(src_path))
    except Exception as e:  # noqa: BLE001
        from .errors import POIError
        if isinstance(e, POIError):
            print(e.render(poi_src), file=sys.stderr)
        else:
            print(f"컴파일 실패: {e}", file=sys.stderr)
        return 1

    name = out_name or os.path.splitext(os.path.basename(src_path))[0]
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    work = tempfile.mkdtemp(prefix="poi_build_")
    boot = os.path.join(work, "_poi_app.py")

    if lock_pw is not None:
        # 비밀번호 잠금 — 코드 객체를 암호화, 로더만 exe 에
        from .protect import make_locked_entry
        if not lock_pw and not ask_pw:
            try:
                import getpass
                lock_pw = getpass.getpass("exe 비밀번호: ")
            except Exception:
                lock_pw = input("exe 비밀번호: ")
        code_obj = compile(py_src, "<poi app>", "exec")
        entry = make_locked_entry(code_obj, lock_pw or "poi", embed=not ask_pw)
        with open(boot, "w", encoding="utf-8") as f:
            f.write("import os, sys\n"
                    "from poi.runtime import make_globals\n"
                    "sys.modules.setdefault('__poi_g__', None)\n"
                    + entry.replace('g = {"__name__": "__main__"}',
                                    "g = make_globals(); g['__name__']='__main__';"
                                    " g['__poi_dir__']=os.getcwd();"
                                    " g['poi_argv']=sys.argv[1:]"))
        print("🔒 비밀번호 잠금" + (" (실행 시 물어봄)" if ask_pw else " (내장)"))
    else:
        if obfuscate:
            from .protect import obfuscate_py
            py_src = obfuscate_py(py_src)
            print("🌫  난독화 적용")
        with open(boot, "w", encoding="utf-8") as f:
            f.write(
                "import os, sys\n"
                "from poi.runtime import make_globals\n"
                "PY_SRC = " + repr(py_src) + "\n"
                "g = make_globals()\n"
                "g['__name__'] = '__main__'\n"
                "g['__poi_dir__'] = os.getcwd()\n"
                "g['__poi_file__'] = " + repr(os.path.basename(src_path)) + "\n"
                "g['__poi_source__'] = ''\n"
                "g['__poi_linemap__'] = {}\n"
                "g['poi_argv'] = sys.argv[1:]\n"
                "exec(compile(PY_SRC, '<poi app>', 'exec'), g)\n"
            )

    out_dist = os.path.join(os.getcwd(), "dist")
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile",
           "--name", name, "--collect-all", "poi", "--collect-data", "poi",
           "--distpath", out_dist,
           "--workpath", os.path.join(work, "b"),
           "--specpath", work,
           "--console" if console else "--noconsole", boot]
    if "tkinter" in py_src:      # GUI 앱 — tkinter 하위 모듈까지 챙긴다
        cmd[3:3] = ["--collect-submodules", "tkinter"]
    if "PIL" in py_src or "Pillow" in py_src:
        cmd[3:3] = ["--collect-all", "PIL"]
    ico = os.path.join(repo, "installer", "poi.ico")
    if os.path.isfile(ico):
        cmd[3:3] = ["--icon", ico]

    print(f"빌드 중: {name}  (PyInstaller)  — 처음엔 1~2분 걸립니다")
    rc = subprocess.run(cmd, cwd=work,
                        env={**os.environ, "PYTHONPATH": repo}).returncode
    shutil.rmtree(work, ignore_errors=True)

    exe = os.path.join(os.getcwd(), "dist", name + (".exe" if os.name == "nt" else ""))
    if rc == 0 and os.path.exists(exe):
        print(f"\n완성:  {exe}  ({os.path.getsize(exe) / 1e6:.1f} MB)")
        return 0
    print("빌드 실패.", file=sys.stderr)
    return 1

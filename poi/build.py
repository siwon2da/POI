"""poi build — POI 프로그램을 단일 실행파일로.

    poi build app.poi [-o 이름] [--console]

설치본에서는 POI 전용 패키저를 사용한다. 소스 환경에서는 PyInstaller를
개발용 대체 경로로 사용한다. 완성 파일은 파이썬이 없는 컴퓨터에서도 돈다.
한계: use pyfile / use "./x.poi" 로 부르는 파일은 자동 포함되지 않는다
      (필요하면 만든 exe 옆에 같이 두거나 --add-data 로).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile


def _write_version_file(work: str, name: str, meta: dict) -> str:
    """Windows 버전 리소스 파일 (--version-file 용)."""
    ver = (meta.get("version") or "1.0.0").strip()
    nums = [int(x) for x in (ver.split(".") + ["0", "0", "0", "0"])[:4]
            if x.isdigit()][:4] or [1, 0, 0, 0]
    while len(nums) < 4:
        nums.append(0)
    author = (meta.get("author") or "").replace('"', "'")
    product = (meta.get("product") or name).replace('"', "'")
    txt = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tuple(nums)}, prodvers={tuple(nums)},
    mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', '{author}'),
      StringStruct('FileDescription', '{product}'),
      StringStruct('FileVersion', '{ver}'),
      StringStruct('ProductName', '{product}'),
      StringStruct('ProductVersion', '{ver}'),
      StringStruct('OriginalFilename', '{name}.exe'),
    ])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ],
)
"""
    p = os.path.join(work, "version_info.txt")
    with open(p, "w", encoding="utf-8") as f:
        f.write(txt)
    return p


_STDLIB_ROOTS = set(getattr(__import__("sys"), "stdlib_module_names", ()))


def _third_party_imports(py_src: str) -> list[str]:
    """트랜스파일된 파이썬에서 외부(3rd-party) import 루트 이름을 뽑는다.

    `use py:numpy as np` → `import numpy as np` 로 낮춰지므로 여기서 다 보인다.
    표준 라이브러리와 poi 자신은 뺀다 → 남는 건 exe 에 통째로 담아야 하는 것들.
    """
    import ast
    roots: set[str] = set()
    try:
        tree = ast.parse(py_src)
    except SyntaxError:
        return []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                roots.add(a.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.level == 0 and node.module:
                roots.add(node.module.split(".")[0])
    drop = _STDLIB_ROOTS | {"poi", "_poi_app", "__future__"}
    return sorted(r for r in roots if r and r not in drop and not r.startswith("_"))


def _module_present(root: str) -> bool:
    import importlib.util
    try:
        return importlib.util.find_spec(root) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def _have_pyinstaller() -> bool:
    try:
        import PyInstaller  # noqa: F401
        return True
    except Exception:
        return False


def _native_build(src_path: str, name: str, py_src: str, console: bool,
                  obfuscate: bool, lock_pw: str | None, ask_pw: bool,
                  meta: dict, deps: list[str], linemap: dict) -> int:
    """설치본 자체를 스텁으로 쓰는 POI 전용 패키징 경로."""
    from . import __version__
    from .packager import PackageError, package_executable

    if name.lower().endswith(".exe"):
        name = name[:-4]
    reserved = {"CON", "PRN", "AUX", "NUL",
                *(f"COM{i}" for i in range(1, 10)),
                *(f"LPT{i}" for i in range(1, 10))}
    if (not name or os.path.basename(name) != name
            or any(ch in name for ch in '<>:"/\\|?*')
            or any(ord(ch) < 32 for ch in name)
            or name.rstrip(" .").split(".", 1)[0].upper() in reserved
            or name != name.rstrip(" .")):
        print("출력 이름에는 폴더 경로나 Windows 금지 문자를 쓸 수 없습니다.",
              file=sys.stderr)
        return 1

    missing = [mod for mod in deps if not _module_present(mod)]
    if missing:
        print("전용 패키저가 앱의 외부 라이브러리를 찾지 못했습니다: "
              + ", ".join(missing), file=sys.stderr)
        print("POI 설치본에 포함된 라이브러리만 단일 EXE에 사용할 수 있습니다.",
              file=sys.stderr)
        return 1

    try:
        mode = "compiled"
        if lock_pw is not None:
            from .protect import make_locked_entry
            if not lock_pw and not ask_pw:
                import getpass
                lock_pw = getpass.getpass("exe 비밀번호: ")
            inner = compile(py_src, "<poi app>", "exec", optimize=2)
            entry = make_locked_entry(inner, lock_pw or "poi", embed=not ask_pw)
            entry = (
                "import os, sys\nfrom poi.runtime import make_globals\n"
                + entry.replace(
                    'g = {"__name__": "__main__"}',
                    "g = make_globals(); g['__name__']='__main__';"
                    " g['__poi_dir__']=os.path.dirname(sys.executable);"
                    " g['poi_argv']=sys.argv[1:]"))
            code = compile(entry, "<poi locked app>", "exec", optimize=2)
            mode = "locked-prompt" if ask_pw else "locked-embedded"
            if ask_pw and not console:
                console = True
                print("비밀번호 입력을 위해 콘솔 실행파일로 만듭니다.")
        elif obfuscate:
            from .protect import obfuscate_py
            code = compile(obfuscate_py(py_src), "<poi app>", "exec", optimize=2)
            mode = "obfuscated"
        else:
            code = compile(py_src, "<poi app>", "exec", optimize=2)

        install_dir = os.path.dirname(os.path.abspath(sys.executable))
        stub = sys.executable if console else os.path.join(install_dir, "poi-idle.exe")
        if not os.path.isfile(stub):
            stub = sys.executable
            console = True
            print("GUI 스텁이 없어 콘솔 실행파일로 만듭니다.")
        out_dir = os.path.join(os.getcwd(), "dist")
        output = os.path.join(out_dir, name + ".exe")
        info = package_executable(stub, output, code, {
            "engine_version": __version__,
            "name": meta.get("product") or name,
            "source_file": os.path.basename(src_path),
            "mode": mode,
            "console": console,
            "author": meta.get("author") or "",
            "app_version": meta.get("version") or "1.0.0",
            "linemap": linemap,
        })
    except (OSError, ValueError, PackageError) as exc:
        print(f"POI 전용 패키징 실패: {exc}", file=sys.stderr)
        return 1

    print("POI 전용 패키저: 외부 Python/PyInstaller 불필요")
    if meta.get("icon"):
        print("참고: 전용 패키저는 스텁 아이콘을 유지합니다. "
              "아이콘 교체는 소스/PyInstaller 빌드에서 지원합니다.")
    print(f"보호: {mode} · SHA-256 무결성 검사 · 원자적 출력")
    print(f"완성:  {output}  ({info['size'] / 1e6:.1f} MB)")
    print(f"SHA-256: {info['file_sha256']}")
    return 0


def build(args: list[str]) -> int:
    from .interpreter import compile_source

    src_path = None
    out_name = None
    console = False
    obfuscate = False
    lock_pw = None
    ask_pw = False
    meta = {}   # author / product / version / icon
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
        elif a in ("--author", "--product", "--file-version", "--icon"):
            meta[a.lstrip("-").replace("file-version", "version")] = next(it, "")
        elif a.startswith(("--author=", "--product=", "--file-version=", "--icon=")):
            k, v = a[2:].split("=", 1)
            meta[k.replace("file-version", "version")] = v
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
    if not getattr(sys, "frozen", False) and not _have_pyinstaller():
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
    # 이 앱이 부르는 외부 파이썬 라이브러리 — 난독화 전에 뽑아 통째로 담는다
    deps = _third_party_imports(py_src)

    if getattr(sys, "frozen", False):
        return _native_build(src_path, name, py_src, console, obfuscate,
                             lock_pw, ask_pw, meta, deps, _lm)

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
    if "tkinter" in py_src or "tkinter" in poi_src:   # GUI 앱 — 하위 모듈까지
        cmd[3:3] = ["--collect-submodules", "tkinter"]

    # use py:<라이브러리> 로 부른 것들 — 전부 --collect-all 로 통째 포함
    for mod in deps:
        if mod == "tkinter":
            continue
        cmd[3:3] = ["--collect-all", mod]
    if deps:
        print("포함할 라이브러리: " + ", ".join(deps))
        missing = [m for m in deps if not _module_present(m)]
        if missing:
            print("⚠️  아직 설치 안 된 것: " + ", ".join(missing)
                  + "  →  pip install " + " ".join(missing))
    ico = meta.get("icon") or os.path.join(repo, "installer", "poi.ico")
    if ico and os.path.isfile(ico):
        cmd[3:3] = ["--icon", ico]

    if os.name == "nt" and (meta.get("author") or meta.get("product") or meta.get("version")):
        vf = _write_version_file(work, name, meta)
        cmd[3:3] = ["--version-file", vf]
        print(f"메타데이터: 제품={meta.get('product') or name} · 작자={meta.get('author') or '-'}"
              f" · 버전={meta.get('version') or '1.0.0'}")

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

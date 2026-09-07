"""poi.exe + poi-setup-<버전>.exe 빌드 (PyInstaller).

    python installer/build_exe.py

결과: dist/exe/poi.exe , dist/exe/poi-setup-<버전>.exe
"""
from __future__ import annotations

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def _ver() -> str:
    ns: dict = {}
    with open(os.path.join(ROOT, "poi", "__init__.py"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                exec(line, ns)  # noqa: S102
                return ns["__version__"]
    return "0.0.0"


def _pyi(args: list[str]):
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--onefile", *args,
                    "--distpath", os.path.join(ROOT, "dist", "exe"),
                    "--workpath", os.path.join(ROOT, "build", "pyi")],
                   check=True, cwd=ROOT, env={**os.environ, "PYTHONPATH": ROOT})


def main() -> int:
    ver = _ver()
    ico = os.path.join(HERE, "poi.ico")
    poi_exe = os.path.join(ROOT, "dist", "exe", "poi.exe")

    print(f"[1/2] poi.exe  (POI {ver})")
    _pyi(["--console", "--name", "poi", "--collect-submodules", "poi",
          "--paths", ROOT] + (["--icon", ico] if os.path.exists(ico) else []) +
         [os.path.join(HERE, "poi_entry.py")])

    print(f"[2/2] poi-setup-{ver}.exe")
    _pyi(["--noconsole", "--name", f"poi-setup-{ver}"] +
         (["--icon", ico] if os.path.exists(ico) else []) +
         ["--add-binary", f"{poi_exe}{os.pathsep}.",
          "--add-data", f"{os.path.join(ROOT, 'examples')}{os.pathsep}examples",
          "--add-data", f"{os.path.join(ROOT, 'README.md')}{os.pathsep}.",
          "--add-data", f"{os.path.join(ROOT, 'LICENSE')}{os.pathsep}."] +
         (["--add-data", f"{ico}{os.pathsep}."] if os.path.exists(ico) else []) +
         [os.path.join(HERE, "wizard.py")])

    print("\n완료:")
    for f in ("poi.exe", f"poi-setup-{ver}.exe"):
        p = os.path.join(ROOT, "dist", "exe", f)
        if os.path.exists(p):
            print(f"  {p}  ({os.path.getsize(p) / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

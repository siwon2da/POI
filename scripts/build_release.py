"""배포용 zip 만들기.

    python scripts/build_release.py

dist/poi-<버전>.zip 을 만든다. 파이썬만 있으면 압축 풀고
    python -m poi run <파일>
로 바로 실행 가능 (외부 의존성 없음).
"""
from __future__ import annotations

import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _version() -> str:
    ns: dict = {}
    with open(os.path.join(ROOT, "poi", "__init__.py"), encoding="utf-8") as f:
        for line in f:
            if line.startswith("__version__"):
                exec(line, ns)  # noqa: S102
                return ns["__version__"]
    return "0.0.0"


INCLUDE_DIRS = ["poi", "examples", "docs", "tests", "installer", "exercises",
                "editors"]
INCLUDE_FILES = ["README.md", "LICENSE", "pyproject.toml", "run.py", "poi.cmd",
                 "VERSION", "CHANGELOG.md", ".gitignore", ".gitattributes"]
SKIP = {"__pycache__", ".pyc", ".pyo"}


def _keep(path: str) -> bool:
    return not any(s in path for s in SKIP)


def main() -> int:
    version = _version()
    out_dir = os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    zip_path = os.path.join(out_dir, f"poi-{version}.zip")
    prefix = f"poi-{version}/"

    n = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for f in INCLUDE_FILES:
            p = os.path.join(ROOT, f)
            if os.path.exists(p):
                z.write(p, prefix + f)
                n += 1
        for d in INCLUDE_DIRS:
            for base, _dirs, files in os.walk(os.path.join(ROOT, d)):
                if not _keep(base):
                    continue
                for name in files:
                    full = os.path.join(base, name)
                    if not _keep(full):
                        continue
                    rel = os.path.relpath(full, ROOT).replace("\\", "/")
                    z.write(full, prefix + rel)
                    n += 1

    size_kb = os.path.getsize(zip_path) / 1024
    print(f"만들었습니다: {zip_path}")
    print(f"  파일 {n}개, {size_kb:.1f} KB")
    print("\n사용법:")
    print(f"  1) 압축 풀기 → poi-{version}/")
    print("  2) python -m poi run examples/basics.poi")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

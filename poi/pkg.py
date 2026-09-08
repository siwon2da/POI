"""poi add / remove / install — 프로젝트 전용 파이썬 의존성 (v1.11).

    poi add numpy pillow          # .venv 에 설치하고 poi.toml 에 기록
    poi remove numpy
    poi install                   # poi.toml [dependencies] 전부 설치

`.venv` 가 있으면 `poi run` 이 자동으로 그 site-packages 를 sys.path 앞에 넣는다.
그래서 `use py:numpy` 가 프로젝트 venv 의 numpy 를 쓴다.
"""
from __future__ import annotations

import os
import subprocess
import sys

VENV = os.environ.get("POI_VENV", ".venv")


def _venv_python(root: str = ".") -> str:
    d = os.path.join(root, VENV)
    for c in (os.path.join(d, "Scripts", "python.exe"),
              os.path.join(d, "bin", "python")):
        if os.path.isfile(c):
            return c
    return ""


def venv_site_packages(root: str = ".") -> str | None:
    d = os.path.join(root, VENV)
    for c in (os.path.join(d, "Lib", "site-packages"),):
        if os.path.isdir(c):
            return c
    lib = os.path.join(d, "lib")
    if os.path.isdir(lib):
        for name in os.listdir(lib):
            sp = os.path.join(lib, name, "site-packages")
            if os.path.isdir(sp):
                return sp
    return None


def activate(root: str = ".") -> bool:
    """`.venv` 가 있으면 그 site-packages 를 import 경로 앞에 붙인다."""
    sp = venv_site_packages(root)
    if sp and sp not in sys.path:
        sys.path.insert(0, sp)
        return True
    return False


def _ensure_venv(root: str) -> str:
    py = _venv_python(root)
    if py:
        return py
    print(f".venv 만드는 중  ({os.path.join(root, VENV)})")
    subprocess.run([sys.executable, "-m", "venv", os.path.join(root, VENV)],
                   check=True)
    return _venv_python(root)


# ── poi.toml [dependencies] 편집 (아주 최소) ─────────────────────────

def _toml_path(root: str) -> str:
    return os.path.join(root, "poi.toml")


def _read_deps(root: str) -> dict:
    p = _toml_path(root)
    deps, section = {}, None
    if not os.path.isfile(p):
        return deps
    for line in open(p, encoding="utf-8"):
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            section = s[1:-1]
            continue
        if section == "dependencies" and "=" in s and not s.startswith("#"):
            k, _, v = s.partition("=")
            deps[k.strip()] = v.strip().strip('"').strip("'")
    return deps


def _write_deps(root: str, deps: dict) -> None:
    p = _toml_path(root)
    lines = open(p, encoding="utf-8").read().splitlines() if os.path.isfile(p) else []
    out, i, done = [], 0, False
    while i < len(lines):
        s = lines[i].strip()
        if s == "[dependencies]":
            out.append("[dependencies]")
            for k, v in sorted(deps.items()):
                out.append(f'{k} = "{v}"')
            done = True
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("["):
                i += 1
            continue
        out.append(lines[i])
        i += 1
    if not done:
        if out and out[-1].strip():
            out.append("")
        out.append("[dependencies]")
        for k, v in sorted(deps.items()):
            out.append(f'{k} = "{v}"')
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out).rstrip("\n") + "\n")


def _pip(root: str, args: list[str]) -> int:
    py = _ensure_venv(root)
    if not py:
        print("파이썬 venv 를 만들지 못했어요.", file=sys.stderr)
        return 1
    return subprocess.run([py, "-m", "pip", *args]).returncode


def _norm(name: str) -> str:
    return name[3:] if name.startswith("py:") else name


def cmd_add(args: list[str]) -> int:
    root = "."
    names = [_norm(a) for a in args if not a.startswith("-")]
    if not names:
        print("설치할 패키지를 알려주세요:  poi add numpy pillow", file=sys.stderr)
        return 1
    rc = _pip(root, ["install", *names])
    if rc != 0:
        return rc
    deps = _read_deps(root)
    for n in names:
        base = n.split("==")[0].split(">")[0].split("<")[0].strip()
        deps[base] = ("==" + n.split("==")[1]) if "==" in n else "*"
    _write_deps(root, deps)
    print(f"\n추가함: {', '.join(names)}   (poi.toml + {VENV})")
    return 0


def cmd_remove(args: list[str]) -> int:
    root = "."
    names = [_norm(a) for a in args if not a.startswith("-")]
    if not names:
        print("제거할 패키지를 알려주세요:  poi remove numpy", file=sys.stderr)
        return 1
    _pip(root, ["uninstall", "-y", *names])
    deps = _read_deps(root)
    for n in names:
        deps.pop(n.split("==")[0], None)
    _write_deps(root, deps)
    print(f"제거함: {', '.join(names)}")
    return 0


def cmd_install(_args: list[str]) -> int:
    root = "."
    deps = _read_deps(root)
    if not deps:
        print("poi.toml 에 [dependencies] 가 없어요.  poi add <이름> 으로 추가하세요.")
        return 0
    spec = [k + (v if v != "*" else "") for k, v in deps.items()]
    print("설치:", ", ".join(spec))
    return _pip(root, ["install", *spec])

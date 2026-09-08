"""POI 생태계 — poi init · poi search / publish · poi migrate (1.9.9).

레지스트리는 정적 인덱스(JSON) 하나로 시작한다:
  https://hagora.kr/poi/registry/index.json
  { "packages": { "<이름>": { "version": "1.0.0", "summary": "...",
                              "url": "<github zip 또는 tar.gz>", "author": "..." } } }
`poi add <이름>` 은 이 인덱스를 보고 없으면 pip 로 폴백한다.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import urllib.request
import zipfile

from . import __version__

INDEX_URL = os.environ.get(
    "POI_REGISTRY", "https://hagora.kr/poi/registry/index.json")
_UA = {"User-Agent": f"POI/{__version__}"}


# ── 레지스트리 ─────────────────────────────────────────────────────────

def fetch_index() -> dict:
    try:
        req = urllib.request.Request(INDEX_URL, headers=_UA)
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode("utf-8")).get("packages", {})
    except Exception as e:  # noqa: BLE001
        print(f"레지스트리를 못 읽었어요: {e}", file=sys.stderr)
        return {}


def cmd_search(args: list[str]) -> int:
    q = " ".join(a for a in args if not a.startswith("-")).strip().lower()
    pkgs = fetch_index()
    if not pkgs:
        return 1
    hits = [(n, m) for n, m in sorted(pkgs.items())
            if not q or q in n.lower() or q in str(m.get("summary", "")).lower()]
    if not hits:
        print(f"'{q}' 에 맞는 패키지가 없어요.")
        return 0
    for n, m in hits:
        print(f"  {n:18} {m.get('version','?'):8} {m.get('summary','')}")
    print(f"\n설치:  poi add {hits[0][0]}")
    return 0


def registry_add(name: str, root: str = ".") -> bool:
    """인덱스에 있으면 poi_modules/<name>/ 로 받아 온다. 성공하면 True."""
    pkgs = fetch_index()
    meta = pkgs.get(name)
    if not meta:
        return False
    url = meta.get("url", "")
    dest = os.path.join(root, "poi_modules", name)
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    print(f"  받는 중: {name} {meta.get('version','')}  ({url})")
    try:
        req = urllib.request.Request(url, headers=_UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
    except Exception as e:  # noqa: BLE001
        print(f"  내려받기 실패: {e}", file=sys.stderr)
        return False
    import shutil
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    os.makedirs(dest, exist_ok=True)
    if data[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            names = z.namelist()
            root_prefix = os.path.commonprefix([n for n in names if "/" in n]) \
                if any("/" in n for n in names) else ""
            for n in names:
                if n.endswith("/"):
                    continue
                rel = n[len(root_prefix):] if root_prefix and n.startswith(root_prefix) else n
                if not rel:
                    continue
                tgt = os.path.join(dest, rel)
                os.makedirs(os.path.dirname(tgt) or dest, exist_ok=True)
                with open(tgt, "wb") as f:
                    f.write(z.read(n))
    elif b"\x1f\x8b" == data[:2] or url.endswith((".tar.gz", ".tgz")):
        import tarfile
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as t:
            t.extractall(dest, filter="data")
    else:
        with open(os.path.join(dest, name + ".poi"), "wb") as f:
            f.write(data)
    _record_pkg(root, name, meta.get("version", "*"))
    print(f"  설치됨:  poi_modules/{name}/   →  use pkg:{name}")
    return True


def _record_pkg(root: str, name: str, version: str) -> None:
    p = os.path.join(root, "poi.toml")
    lines = open(p, encoding="utf-8").read().splitlines() if os.path.isfile(p) else []
    out, i, done = [], 0, False
    while i < len(lines):
        if lines[i].strip() == "[poi-packages]":
            out.append(lines[i])
            i += 1
            body = {}
            while i < len(lines) and not lines[i].strip().startswith("["):
                s = lines[i].strip()
                if "=" in s and not s.startswith("#"):
                    k, _, v = s.partition("=")
                    body[k.strip()] = v.strip().strip('"')
                i += 1
            body[name] = version
            for k, v in sorted(body.items()):
                out.append(f'{k} = "{v}"')
            done = True
            continue
        out.append(lines[i])
        i += 1
    if not done:
        if out and out[-1].strip():
            out.append("")
        out.append("[poi-packages]")
        out.append(f'{name} = "{version}"')
    with open(p, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out).rstrip("\n") + "\n")


def cmd_publish(args: list[str]) -> int:
    root = "."
    name = os.path.basename(os.path.abspath(root))
    meta_p = os.path.join(root, "poi.toml")
    ver = "0.1.0"
    if os.path.isfile(meta_p):
        for line in open(meta_p, encoding="utf-8"):
            m = re.match(r'\s*name\s*=\s*"([^"]+)"', line)
            if m:
                name = m.group(1)
            m = re.match(r'\s*version\s*=\s*"([^"]+)"', line)
            if m:
                ver = m.group(1)
    os.makedirs("dist", exist_ok=True)
    out = os.path.join("dist", f"{name}-{ver}.zip")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for base, _dirs, files in os.walk(root):
            if any(seg in base for seg in (".git", ".venv", "dist", "__pycache__",
                                           "node_modules")):
                continue
            for fn in files:
                if fn.endswith((".pyc",)):
                    continue
                fp = os.path.join(base, fn)
                z.write(fp, os.path.relpath(fp, root))
    print(f"패키지 묶음: {out}\n")
    print("공개하려면 레지스트리 인덱스에 항목을 추가하세요 "
          "(PR: github.com/siwon2da/POI → site/hagora/registry/index.json):")
    print(json.dumps({name: {"version": ver, "summary": "...",
                             "url": f"https://.../{name}-{ver}.zip",
                             "author": "you"}}, ensure_ascii=False, indent=2))
    return 0


# ── poi init — 대화형 생성 ───────────────────────────────────────────

_KINDS = [
    ("콘솔 프로그램", "cli"),
    ("웹사이트", "web"),
    ("REST API", "api"),
    ("GUI 앱", "gui"),
    ("게임 (2D)", "game"),
    ("데이터 분석", "data"),
    ("빈 프로젝트", "empty"),
]

_INIT_TPL = {
    "gui": '# __NAME__ — GUI 앱\nwin = uikit.window("__NAME__", 640, 420)\n'
           'uikit.label(uikit.row(win), "안녕하세요")\n'
           'uikit.button(uikit.row(win), "확인", () => uikit.toast(win, "눌림", "ok"), true)\n'
           'uikit.run(win)\n',
    "game": '# __NAME__ — 2D 게임\nwin = game.window("__NAME__", 800, 500)\n'
            'p = game.sprite(win, { x: 100, y: 250, w: 40, h: 40, color: "#5b9dff" })\n'
            'game.on_key(win, "Left",  () => p.move(-8, 0))\n'
            'game.on_key(win, "Right", () => p.move(8, 0))\n'
            'game.on_key(win, "Up",    () => p.move(0, -8))\n'
            'game.on_key(win, "Down",  () => p.move(0, 8))\n'
            'game.run(win)\n',
    "data": '# __NAME__ — 데이터 분석\n수치 = [12, 7, 22, 19, 5, 31, 14]\n'
            'show "평균 {stats.mean(수치)} · 중앙값 {stats.median(수치)} · 최대 {stats.max(수치)}"\n'
            'show 수치 |> filter(n => n > 10) |> sort_desc\n',
    "empty": '# __NAME__\nshow "안녕하세요, __NAME__ 입니다!"\n',
}


def cmd_init(args: list[str]) -> int:
    from .cli import cmd_new
    here = os.getcwd()
    name = os.path.basename(here) or "poi-app"
    print("어떤 프로젝트를 만들까요?\n")
    for i, (label, _k) in enumerate(_KINDS, 1):
        print(f"  {i}. {label}")
    try:
        sel = input("\n번호 (기본 1): ").strip() or "1"
        idx = max(1, min(len(_KINDS), int(sel))) - 1
    except (ValueError, EOFError, KeyboardInterrupt):
        idx = 0
    label, kind = _KINDS[idx]
    print(f"\n✓ {label}")

    os.makedirs("src", exist_ok=True)
    os.makedirs("tests", exist_ok=True)
    main = os.path.join("src", "main.poi")
    if kind in ("web", "api"):
        # cmd_new 의 웹/api 템플릿 재사용 (현재 폴더에 풀어놓기)
        tmp = os.path.join(here, "__poi_init_tmp__")
        cmd_new([tmp, "--" + kind])
        import shutil
        for rel in ("src/main.poi", "views/home.html"):
            s = os.path.join(tmp, rel)
            if os.path.isfile(s):
                d = os.path.join(here, rel)
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy(s, d)
        shutil.rmtree(tmp, ignore_errors=True)
    elif kind == "cli":
        with open(main, "w", encoding="utf-8") as f:
            f.write(f'# {name} — 콘솔 프로그램\n이름 = ask "이름이 뭐예요? "\n'
                    f'show "반가워요 {{이름}}님"\n')
    else:
        with open(main, "w", encoding="utf-8") as f:
            f.write(_INIT_TPL.get(kind, _INIT_TPL["empty"]).replace("__NAME__", name))

    with open("poi.toml", "w", encoding="utf-8", newline="\n") as f:
        f.write(f'[project]\nname = "{name}"\nversion = "0.1.0"\n'
                f'entry = "src/main.poi"\ntype = "{kind}"\n\n[dependencies]\n')
    with open("README.md", "w", encoding="utf-8") as f:
        f.write(f"# {name}\n\n```bash\npoi run\n```\n")
    print("✓ 프로젝트 생성 (src/main.poi · poi.toml · README.md)")
    print("✓ 예제 코드 생성\n")
    print("  poi run   으로 시작하세요.")
    return 0


# ── poi migrate — v2.0 스타일로 정리 (1차: 안전한 것만) ──────────────

def _migrate_text(src: str):
    """콜론 한 줄 블록·파이썬 습관을 중괄호/POI 로. (line 단위, 보수적)"""
    out, changes = [], []
    for i, line in enumerate(src.splitlines(), 1):
        orig = line
        # def/func/function/fun → fn   (이미 동작하지만 정규화)
        line = re.sub(r"^(\s*)(?:def|func|function|fun)(\s+\w)", r"\1fn\2", line)
        # elif → else if
        line = re.sub(r"^(\s*)elif\b", r"\1else if", line)
        # True/False/None → true/false/null (문자열 밖에서만, 대충)
        if '"' not in line:
            line = re.sub(r"\bTrue\b", "true", line)
            line = re.sub(r"\bFalse\b", "false", line)
            line = re.sub(r"\bNone\b", "null", line)
        # `if 조건:` 한 줄 (뒤에 문장 있음) → `if 조건 { 문장 }`
        m = re.match(r"^(\s*)(if|else if|for .+? in .+?|while .+?|repeat .+?"
                     r"|fn \w+\(.*?\)|else)\s*:\s*(\S.*)$", line)
        if m and not m.group(3).startswith("#"):
            line = f"{m.group(1)}{m.group(2)} {{ {m.group(3).rstrip()} }}"
        if line != orig:
            changes.append((i, orig.strip(), line.strip()))
        out.append(line)
    return "\n".join(out) + ("\n" if src.endswith("\n") else ""), changes


def cmd_migrate(args: list[str]) -> int:
    write = "--write" in args or "-w" in args
    files = [a for a in args if not a.startswith("-") and a != "2"]
    if not files:
        print("poi migrate <파일.poi | .> [--write] [--to 2]", file=sys.stderr)
        return 1
    targets = []
    for t in files:
        if os.path.isdir(t):
            for base, _d, fs in os.walk(t):
                targets += [os.path.join(base, f) for f in fs if f.endswith(".poi")]
        elif t.endswith(".poi"):
            targets.append(t)
    total = 0
    for p in targets:
        src = open(p, encoding="utf-8").read()
        new, ch = _migrate_text(src)
        if not ch:
            continue
        total += len(ch)
        print(f"\n{p}  ({len(ch)}곳)")
        for ln, a, b in ch[:12]:
            print(f"  {ln:4}  - {a}\n        + {b}")
        if len(ch) > 12:
            print(f"  … 그 외 {len(ch) - 12}곳")
        if write:
            with open(p, "w", encoding="utf-8", newline="\n") as f:
                f.write(new)
    if total == 0:
        print("이미 v2.0 스타일이거나, 자동으로 바꿀 게 없어요.")
    elif write:
        print(f"\n{total}곳 고쳤어요.  `poi check .` 로 확인하세요.")
    else:
        print(f"\n미리보기만 했어요. 적용하려면  poi migrate {' '.join(files)} --write")
    return 0

"""새 버전 알림.

`poi run` / `poi version` 을 쓸 때, 하루에 한 번 조용히 원격 버전을 확인하고
새 버전이 있으면 터미널에 한 줄 안내를 띄운다. 네트워크가 없거나 느리면 그냥 넘어간다.

원격 소스 (순서대로 시도):
  1) https://hagora.kr/poi/VERSION         — 첫 줄=버전, 나머지=안내 메시지
  2) raw.githubusercontent.com .../poi/__init__.py 의 __version__
"""
from __future__ import annotations

import json
import os
import re
import time
import urllib.request

from . import __version__

_CACHE = os.path.join(os.path.expanduser("~"), ".poi", "update_check.json")
_TTL = 60 * 60 * 24  # 하루
_TIMEOUT = 2.5
_VERSION_URL = "https://hagora.kr/poi/VERSION"
_RAW_INIT = "https://raw.githubusercontent.com/siwon2da/POI/main/poi/__init__.py"
_RELEASES = "https://github.com/siwon2da/POI/releases"


def _parse_ver(s: str):
    nums = re.findall(r"\d+", s or "")
    return tuple(int(n) for n in nums[:3]) or (0,)


def _fetch(url: str) -> str | None:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"POI/{__version__}"})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
            return r.read().decode("utf-8", "replace")
    except Exception:
        return None


def _remote():
    """(latest_version_str, message | None) 또는 None."""
    body = _fetch(_VERSION_URL)
    if body and body.strip():
        lines = [ln.rstrip() for ln in body.strip().splitlines()]
        return lines[0].strip(), ("\n".join(lines[1:]).strip() or None)
    body = _fetch(_RAW_INIT)
    if body:
        m = re.search(r"__version__\s*=\s*[\"']([^\"']+)[\"']", body)
        if m:
            return m.group(1), None
    return None


def _load_cache() -> dict:
    try:
        with open(_CACHE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(d: dict) -> None:
    try:
        os.makedirs(os.path.dirname(_CACHE), exist_ok=True)
        with open(_CACHE, "w", encoding="utf-8") as f:
            json.dump(d, f)
    except Exception:
        pass


def check(force: bool = False) -> dict:
    """{'current','latest','behind','message'} 반환. 실패해도 예외 없음."""
    now = time.time()
    cache = _load_cache()
    if not force and (now - cache.get("checked_at", 0) < _TTL) and "latest" in cache:
        latest, message = cache["latest"], cache.get("message")
    else:
        got = _remote()
        latest, message = (got if got else (cache.get("latest", __version__),
                                            cache.get("message")))
        _save_cache({"checked_at": now, "latest": latest, "message": message})
    behind = _parse_ver(latest) > _parse_ver(__version__)
    return {"current": __version__, "latest": latest, "behind": behind, "message": message}


def notice_line() -> str | None:
    """새 버전이 있으면 안내 문자열, 없으면 None. (조용한 호출용)"""
    try:
        info = check(force=False)
    except Exception:
        return None
    if not info["behind"]:
        return None
    msg = info.get("message") or "새 버전으로 올리려면:  git -C <POI 폴더> pull   또는   설치본을 다시 받으세요."
    return (f"\n  ┌ POI {info['latest']} 나왔습니다 (지금 {info['current']}).\n"
            f"  └ {msg}\n    {_RELEASES}\n")


def run_update() -> int:
    """`poi update` — 어떻게 올릴지 안내하고, git 체크아웃이면 pull 을 시도."""
    info = check(force=True)
    print(f"설치된 버전 : POI {info['current']}")
    print(f"최신 버전   : POI {info['latest']}")
    if info.get("message"):
        print(f"안내        : {info['message']}")
    if not info["behind"]:
        print("\n최신입니다. 할 일 없음.")
        return 0

    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.isdir(os.path.join(repo_root, ".git")):
        print(f"\ngit 체크아웃 감지: {repo_root}")
        code = os.system(f'git -C "{repo_root}" pull --ff-only')
        return 0 if code == 0 else 1
    print("\n올리는 법:")
    print("  · git 으로 받았으면:  git -C <POI 폴더> pull")
    print("  · 설치본을 받았으면:  아래에서 최신 설치본을 다시 받아 설치")
    print(f"    {_RELEASES}")
    print("    https://hagora.kr/poi/")
    return 0

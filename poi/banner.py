"""부팅 배너 — `poi` 로고가 켜질 때.

터미널에서 POI 를 그냥 실행하거나 REPL 을 켜면, ASCII 블록 글자 "POI" 가
한 줄씩 살아나고 "Power Of Imagination" 이 뜬다. 색은 #0af 계열.

끄기:  POI_NO_BANNER=1   또는   출력이 터미널이 아닐 때 자동으로 조용.
"""
from __future__ import annotations

import os
import sys
import time

_ART = [
    r" ██████╗   ██████╗  ██╗",
    r" ██╔══██╗ ██╔═══██╗ ██║",
    r" ██████╔╝ ██║   ██║ ██║",
    r" ██╔═══╝  ██║   ██║ ██║",
    r" ██║      ╚██████╔╝ ██║",
    r" ╚═╝       ╚═════╝  ╚═╝",
]

_ART_ASCII = [
    r"  ____    ___    ___ ",
    r" |  _ \  / _ \  |_ _|",
    r" | |_) || | | |  | | ",
    r" |  __/ | |_| |  | | ",
    r" |_|     \___/  |___|",
]


def _art_for(stream):
    enc = (getattr(stream, "encoding", None) or "").lower()
    if enc in ("utf-8", "utf8", "utf-16", "utf-16-le", "cp65001"):
        return _ART
    try:
        "█╗╔╝".encode(enc or "ascii")
        return _ART
    except (LookupError, UnicodeEncodeError):
        return _ART_ASCII

# #0af 를 중심으로 한 그라데이션 (256색 xterm)
_RAMP = ["\033[38;5;33m", "\033[38;5;39m", "\033[38;5;45m",
         "\033[38;5;51m", "\033[38;5;45m", "\033[38;5;39m"]
_CYAN = "\033[38;5;45m"       # ≈ #0af
_DIM = "\033[38;5;24m"
_RESET = "\033[0m"
_HIDE = "\033[?25l"
_SHOW = "\033[?25h"


def _enabled(stream) -> bool:
    if os.environ.get("POI_NO_BANNER"):
        return False
    try:
        return stream.isatty()
    except Exception:
        return False


def show(stream=None, animate: bool = True) -> None:
    from . import __version__
    out = stream or sys.stderr
    if not _enabled(out):
        return

    # Windows 콘솔 ANSI 켜기
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-11), 7)
            k.SetConsoleMode(k.GetStdHandle(-12), 7)
        except Exception:
            pass

    reduce = os.environ.get("POI_NO_MOTION") or not animate
    art = _art_for(out)
    try:
        out.write("\n")
        if not reduce:
            out.write(_HIDE)
        for i, line in enumerate(art):
            color = _RAMP[i % len(_RAMP)]
            if reduce:
                out.write(f"{color}{line}{_RESET}\n")
            else:
                # 왼쪽에서 오른쪽으로 쓸어 나타나기
                for j in range(2, len(line) + 1, 3):
                    out.write(f"\r{color}{line[:j]}{_RESET}")
                    out.flush()
                    time.sleep(0.006)
                out.write(f"\r{color}{line}{_RESET}\n")
                out.flush()
        tag = "Power Of Imagination"
        if reduce:
            out.write(f"   {_DIM}{tag}{_RESET}   {_DIM}v{__version__}{_RESET}\n\n")
        else:
            out.write("   ")
            for ch in tag:
                out.write(f"{_CYAN}{ch}{_RESET}")
                out.flush()
                time.sleep(0.012)
            out.write(f"   {_DIM}v{__version__}{_RESET}\n\n")
            out.flush()
    except Exception:
        pass  # 배너는 장식일 뿐 — 실패해도 조용히
    finally:
        try:
            if not reduce:
                out.write(_SHOW)
                out.flush()
        except Exception:
            pass


def plain(ascii_only: bool = False) -> str:
    art = _ART_ASCII if ascii_only else _ART
    return "\n".join(art) + "\n   Power Of Imagination\n"

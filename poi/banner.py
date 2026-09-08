"""부팅 배너 — `poi` 로고가 켜질 때.

터미널에서 POI 를 그냥 실행하거나 REPL 을 켜면, 문어 로고(점자 아트)가
위에서 아래로 쫘라락 나타나고 파란 그라데이션으로 물든 뒤
"Power Of Imagination" 이 뜬다.

끄기:  POI_NO_BANNER=1   또는   출력이 터미널이 아닐 때 자동으로 조용.
동작만 끄기:  POI_NO_MOTION=1
"""
from __future__ import annotations

import os
import sys
import time

from .octopus_art import LINES as _OCTO

_WORD = [
    r" ██████╗   ██████╗  ██╗",
    r" ██╔══██╗ ██╔═══██╗ ██║",
    r" ██████╔╝ ██║   ██║ ██║",
    r" ██╔═══╝  ██║   ██║ ██║",
    r" ██║      ╚██████╔╝ ██║",
    r" ╚═╝       ╚═════╝  ╚═╝",
]
_WORD_ASCII = [
    r"  ____    ___    ___ ",
    r" |  _ \  / _ \  |_ _|",
    r" | |_) || | | |  | | ",
    r" |  __/ | |_| |  | | ",
    r" |_|     \___/  |___|",
]

# 로고 파랑 그라데이션 (위=하늘색 → 아래=인디고). 256색 xterm.
_BLUE = [117, 117, 111, 111, 75, 75, 69, 69, 63, 63, 62, 61]
_DIM = "\033[38;5;60m"
_INK = "\033[38;5;75m"
_RESET = "\033[0m"
_HIDE = "\033[?25l"
_SHOW = "\033[?25h"


def _fg(n: int) -> str:
    return f"\033[38;5;{n}m"


def _utf_ok(stream) -> bool:
    enc = (getattr(stream, "encoding", None) or "").lower()
    if enc in ("utf-8", "utf8", "utf-16", "utf-16-le", "cp65001"):
        return True
    try:
        "⠿█╗".encode(enc or "ascii")
        return True
    except (LookupError, UnicodeEncodeError):
        return False


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

    if os.name == "nt":                       # Windows 콘솔 ANSI 켜기
        try:
            import ctypes
            k = ctypes.windll.kernel32
            k.SetConsoleMode(k.GetStdHandle(-11), 7)
            k.SetConsoleMode(k.GetStdHandle(-12), 7)
        except Exception:
            pass

    reduce = bool(os.environ.get("POI_NO_MOTION")) or not animate
    utf = _utf_ok(out)
    word = _WORD if utf else _WORD_ASCII
    try:
        out.write("\n")
        if not reduce:
            out.write(_HIDE)

        if utf:
            n = len(_OCTO)
            for i, line in enumerate(_OCTO):
                col = _fg(_BLUE[min(len(_BLUE) - 1, i * len(_BLUE) // n)])
                out.write(f"  {col}{line}{_RESET}\n")
                if not reduce:
                    out.flush()
                    time.sleep(0.014)          # 쫘라락
            out.write("\n")

        for i, line in enumerate(word):
            col = _fg(_BLUE[min(len(_BLUE) - 1, 4 + i)])
            out.write(f"   {col}{line}{_RESET}\n")
            if not reduce:
                out.flush()
                time.sleep(0.02)

        tag = "Power Of Imagination"
        if reduce:
            out.write(f"   {_DIM}{tag}   ·   v{__version__}{_RESET}\n\n")
        else:
            out.write("   ")
            for ch in tag:
                out.write(f"{_INK}{ch}{_RESET}")
                out.flush()
                time.sleep(0.010)
            out.write(f"   {_DIM}·   v{__version__}{_RESET}\n\n")
            out.flush()
    except Exception:
        pass                                  # 배너는 장식 — 실패해도 조용히
    finally:
        try:
            if not reduce:
                out.write(_SHOW)
                out.flush()
        except Exception:
            pass


def plain(ascii_only: bool = False) -> str:
    word = _WORD_ASCII if ascii_only else _WORD
    octo = "" if ascii_only else "\n".join(_OCTO) + "\n\n"
    return octo + "\n".join(word) + "\n   Power Of Imagination\n"

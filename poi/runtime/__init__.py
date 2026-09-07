"""트랜스파일된 파이썬 코드가 실행되는 전역 네임스페이스를 만든다."""
from __future__ import annotations

from .. import debugtools as _dbg
from . import easter as _easter
from . import gui as _gui
from . import stdmods as _std
from .boxes import Box, boxify
from .builtins import (boolean, number, poi_ask, poi_coalesce, poi_error_value,
                       poi_fmt, poi_getattr, poi_getattr_safe, poi_import_pyfile,
                       poi_show, poi_setattr, poi_std, text)

_RUNTIME = {
    "Box": Box,
    "boxify": boxify,
    "poi_show": poi_show,
    "poi_fmt": poi_fmt,
    "poi_ask": poi_ask,
    "number": number,
    "text": text,
    "boolean": boolean,
    "poi_getattr": poi_getattr,
    "poi_getattr_safe": poi_getattr_safe,
    "poi_setattr": poi_setattr,
    "poi_coalesce": poi_coalesce,
    "poi_error_value": poi_error_value,
    "poi_import_pyfile": poi_import_pyfile,
    "poi_std": poi_std,
    # 디버깅 도구
    "inspect": _dbg.inspect_value,
    "pause": _dbg.poi_pause,
    "watch": _dbg.poi_watch,
    "_poi_trace": _dbg._poi_trace,
    # 표준 모듈: import 없이 바로
    "file": _std.file,
    "json": _std.json,
    "web": _std.web,
    "math": _std.math,
    "time": _std.time,
    # GUI
    "poi_app": _gui.poi_app,
    "poi_window": _gui.poi_window,
    "poi_text": _gui.poi_text,
    "poi_button": _gui.poi_button,
    "poi_input": _gui.poi_input,
    "poi_row": _gui.poi_row,
    "poi_column": _gui.poi_column,
    "poi_card": _gui.poi_card,
    "poi_on": _gui.poi_on,
}


def make_globals() -> dict:
    g = dict(_RUNTIME)
    g["__builtins__"] = __import__("builtins")
    # 이스터에그 (사용자가 덮어쓰면 그대로 덮인다)
    g["pp청춘"] = _easter.CHUNCHEONG
    g["test"] = _easter.TEST
    return g

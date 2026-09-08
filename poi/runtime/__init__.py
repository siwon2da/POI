"""트랜스파일된 파이썬 코드가 실행되는 전역 네임스페이스를 만든다."""
from __future__ import annotations

from .. import debugtools as _dbg
from . import easter as _easter
from . import functional as _fn
from . import gui as _gui
from . import stdlib2 as _std2
from . import stdmods as _std
from . import webserver as _web
from .boxes import Box, boxify
from .builtins import (_ERROR_MAKERS, boolean, number, poi_ask, poi_assert,
                       poi_coalesce, poi_error_is, poi_error_value, poi_fmt,
                       poi_getattr, poi_getattr_safe, poi_import_module,
                       poi_import_pkg, poi_import_pyfile, poi_make_error, poi_range,
                       poi_print, poi_register_test, poi_run_tests, poi_show,
                       poi_setattr, poi_std, text)

_RUNTIME = {
    "Box": Box,
    "boxify": boxify,
    "poi_show": poi_show,
    "print": poi_print,
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
    "poi_import_module": poi_import_module,
    "poi_import_pkg": poi_import_pkg,
    "poi_std": poi_std,
    # 전문 (v1.3)
    "poi_make_error": poi_make_error,
    "poi_assert": poi_assert,
    "poi_register_test": poi_register_test,
    "poi_run_tests": poi_run_tests,
    # v1.8 — 언어 안정화
    "poi_range": poi_range,
    "poi_error_is": poi_error_is,
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
    "regex": _std.regex,
    "csv": _std.csv,
    "datetime": _std.datetime,
    "random": _std.random,
    "stats": _std.stats,
    "env": _std.env,
    "shell": _std.shell,
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
    # 웹 (v1.6)
    "poi_web_register": _web.register,
    "poi_render_page": _web.render_page,
    "poi_html_raw": _web.html_raw,
    "poi_web_redirect": _web.redirect,
    "respond": _web.respond,
    "redirect": _web.redirect,
    "html": _web.html_raw,
    "cookie": _web.set_cookie,
    "session": _web.session,
    # v1.13 — 웹 전문화
    "render": _web.render,
    "on_request": _web.on_request,
    "on_response": _web.on_response,
    "auth": _web.auth,
    # 데이터베이스 (v1.7) — import 없이 바로
    "database": _std2.open_database,
}


_KOREAN_BUILTINS = {
    "문자": "text", "문자열": "text", "글자": "text",
    "숫자": "number", "정수로": "number",
    "참거짓": "boolean",
    "살펴보기": "inspect", "지켜보기": "watch", "멈춤": "pause",
    "묻기값": "poi_ask",
    "걸러내기": "filter", "골라내기": "filter",
    "변환": "map", "매핑": "map",
    "모으기": "reduce", "접기": "reduce",
    "정렬기준": "sort_by", "정렬내림": "sort_desc",
    "묶기": "group_by", "앞에서": "take", "뒤로": "drop",
    "중복제거": "unique", "합계": "sum_of", "평균값": "avg",
    "최댓값": "max_of", "최솟값": "min_of", "개수": "count_of",
    "데이터베이스": "database",
}


def make_globals() -> dict:
    g = dict(_RUNTIME)
    g.update(_ERROR_MAKERS)   # Error / ValueError / FileError ... (raise 용)
    # v1.7 표준 라이브러리 — import 없이 바로 (html 은 web 헬퍼와 겹쳐 제외)
    for _name, _mod in _std2.MODULES.items():
        if _name != "html":
            g[_name] = _mod
    g.update(_fn.EXPORTS)  # map/filter/reduce/sort_by/group_by/take/... (파이프라인)
    g["__builtins__"] = __import__("builtins")
    for ko, en in _KOREAN_BUILTINS.items():
        if en in g:
            g[ko] = g[en]
    # 이스터에그 (사용자가 덮어쓰면 그대로 덮인다)
    g["pp청춘"] = _easter.CHUNCHEONG
    g["test"] = _easter.TEST
    return g

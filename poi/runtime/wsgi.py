"""POI → WSGI 어댑터 (v1.14) — 프로덕션 서버(gunicorn·waitress·uvicorn)에 얹는다.

    # wsgi.py
    from poi.runtime.wsgi import load
    application = load("app.poi")

    gunicorn wsgi:application -w 4 -b 0.0.0.0:8000
    waitress-serve --port=8000 wsgi:application

또는 파일 없이 환경변수로:
    POI_APP=app.poi  gunicorn "poi.runtime.wsgi:app"
"""
from __future__ import annotations

import io
import os
import sys

from . import webserver as _ws

_LOADED = {"path": None}


def load(poi_path: str):
    """`.poi` 파일을 실행해 server{} 라우트를 등록하고 WSGI application 을 돌려준다."""
    poi_path = os.path.abspath(poi_path)
    from ..interpreter import compile_source
    from . import make_globals

    src = open(poi_path, encoding="utf-8").read()
    py, linemap, cn = compile_source(src, os.path.basename(poi_path))
    g = make_globals()
    g["__name__"] = "__main__"
    g["__poi_file__"] = poi_path
    g["__poi_dir__"] = os.path.dirname(poi_path)
    g["__poi_source__"] = src
    os.environ["POI_NO_SERVE"] = "1"        # exec 이 blocking serve 로 안 빠지게
    _ws.reset()
    exec(compile(py, cn, "exec"), g)        # noqa: S102
    if not _ws._APPS:
        raise RuntimeError(f"{poi_path} 에 server {{ }} 가 없습니다.")
    _LOADED["path"] = poi_path
    return application


def application(environ, start_response):
    """PEP 3333 WSGI 엔트리."""
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")
    qs = environ.get("QUERY_STRING", "")
    full = path + ("?" + qs if qs else "")

    try:
        length = int(environ.get("CONTENT_LENGTH") or 0)
    except ValueError:
        length = 0
    raw = environ["wsgi.input"].read(length) if length else b""

    headers = {}
    for k, v in environ.items():
        if k.startswith("HTTP_"):
            headers[k[5:].replace("_", "-").title()] = v
    if environ.get("CONTENT_TYPE"):
        headers["Content-Type"] = environ["CONTENT_TYPE"]
    ip = environ.get("REMOTE_ADDR", "?")

    try:
        status, data, ctype, extra = _ws.serve_request(method, full, raw, headers, ip)
    except Exception as e:  # noqa: BLE001
        status, data, ctype, extra = _ws._err_response(500, f"서버 오류: {e}")

    if isinstance(data, str):
        data = data.encode("utf-8")
    out = [(k, str(v)) for k, v in dict(extra or {}).items()]
    out.append(("Content-Type", ctype))
    out.append(("Content-Length", str(len(data))))
    for k, v in _ws._SECURITY_HEADERS.items():
        out.append((k, v))
    start_response(f"{status} {_STATUS.get(status, 'OK')}", out)
    return [data]


_STATUS = {200: "OK", 201: "Created", 204: "No Content", 301: "Moved Permanently",
          302: "Found", 303: "See Other", 304: "Not Modified", 400: "Bad Request",
          401: "Unauthorized", 403: "Forbidden", 404: "Not Found",
          405: "Method Not Allowed", 413: "Payload Too Large",
          429: "Too Many Requests", 500: "Internal Server Error"}


# POI_APP 환경변수로 즉시 로드 (gunicorn "poi.runtime.wsgi:app")
_ENV_APP = os.environ.get("POI_APP")
if _ENV_APP and os.path.isfile(_ENV_APP):
    app = load(_ENV_APP)
else:
    app = application

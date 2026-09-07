"""POI 표준 모듈: file / json / web / math / time.

파이썬 표준 라이브러리만 사용 (외부 의존성 0). requests 가 필요하면
언제든 `use py:requests` 로 진짜 requests 를 쓸 수 있다.
"""
from __future__ import annotations

import json as _json
import math as _math
import os as _os
import random as _random
import time as _time
import urllib.error as _urlerr
import urllib.parse as _urlparse
import urllib.request as _urlreq
from types import SimpleNamespace

from ..errors import POIError
from .boxes import boxify

# -- file --------------------------------------------------------------


def _read(path, encoding="utf-8"):
    with open(path, "r", encoding=encoding) as f:
        return f.read()


def _write(path, content, encoding="utf-8"):
    with open(path, "w", encoding=encoding) as f:
        f.write(content if isinstance(content, str) else str(content))
    return True


def _append(path, content, encoding="utf-8"):
    with open(path, "a", encoding=encoding) as f:
        f.write(content if isinstance(content, str) else str(content))
    return True


def _lines(path, encoding="utf-8"):
    return _read(path, encoding).splitlines()


def _delete(path):
    try:
        _os.remove(path)
        return True
    except FileNotFoundError:
        return False


def _list_dir(path="."):
    return sorted(_os.listdir(path))


file = SimpleNamespace(
    read=_read, write=_write, append=_append, lines=_lines,
    exists=_os.path.exists, delete=_delete, list=_list_dir,
)

# -- json ------------------------------------------------------------


def _json_parse(s):
    try:
        return boxify(_json.loads(s))
    except _json.JSONDecodeError as e:
        raise POIError(f"JSON 형식이 잘못됐습니다: {e.msg} ({e.lineno}번째 줄)", "P140")


def _json_stringify(obj, pretty=True):
    return _json.dumps(obj, ensure_ascii=False,
                       indent=2 if pretty else None, default=str)


def _json_read(path):
    return _json_parse(_read(path))


def _json_write(path, obj, pretty=True):
    return _write(path, _json_stringify(obj, pretty))


json = SimpleNamespace(
    parse=_json_parse, stringify=_json_stringify,
    read=_json_read, write=_json_write,
)

# -- web -----------------------------------------------------------


class Response:
    def __init__(self, status, text, headers):
        self.status = status
        self.text = text
        self.headers = dict(headers)
        self.ok = 200 <= status < 300

    @property
    def json(self):
        return _json_parse(self.text)

    def __repr__(self):
        return f"<Response {self.status} ({len(self.text)} chars)>"


def _request(url, method="GET", body=None, headers=None):
    headers = dict(headers or {})
    data = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = _json.dumps(body).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        else:
            data = str(body).encode("utf-8")
    headers.setdefault("User-Agent", "POI/0.1")
    req = _urlreq.Request(url, data=data, method=method, headers=headers)
    try:
        with _urlreq.urlopen(req, timeout=30) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return Response(resp.status, raw.decode(charset, "replace"),
                            resp.headers.items())
    except _urlerr.HTTPError as e:
        raw = e.read()
        return Response(e.code, raw.decode("utf-8", "replace"), e.headers.items())
    except _urlerr.URLError as e:
        raise POIError(f"요청을 보낼 수 없습니다: {e.reason}", "P141",
                       hint="인터넷 연결과 주소(URL)를 확인하세요.")


def _web_get(url, headers=None, params=None):
    if params:
        url = url + ("&" if "?" in url else "?") + _urlparse.urlencode(params)
    return _request(url, "GET", None, headers)


def _web_post(url, body=None, headers=None):
    return _request(url, "POST", body, headers)


def _web_download(url, path):
    resp = _web_get(url)
    _write(path, resp.text)
    return path


web = SimpleNamespace(get=_web_get, post=_web_post, download=_web_download,
                      Response=Response)

# -- math -----------------------------------------------------------


def _pick(seq):
    return _random.choice(list(seq))


def _clamp(x, lo, hi):
    return max(lo, min(hi, x))


math = SimpleNamespace(
    pi=_math.pi, e=_math.e, tau=_math.tau,
    sqrt=_math.sqrt, floor=_math.floor, ceil=_math.ceil, round=round,
    abs=abs, pow=pow, min=min, max=max, sum=sum,
    sin=_math.sin, cos=_math.cos, tan=_math.tan, log=_math.log,
    random=_random.random, randint=_random.randint, pick=_pick, clamp=_clamp,
)

# -- time -----------------------------------------------------------


def _now():
    from datetime import datetime
    return datetime.now()


def _today():
    from datetime import date
    return date.today().isoformat()


def _format(dt, fmt="%Y-%m-%d %H:%M:%S"):
    return dt.strftime(fmt)


time = SimpleNamespace(
    now=_now, today=_today, timestamp=_time.time,
    sleep=_time.sleep, format=_format,
)

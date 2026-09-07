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

# -- regex -----------------------------------------------------------
import re as _re  # noqa: E402


def _rx_match(pattern, text):
    m = _re.search(pattern, text)
    if not m:
        return None
    return boxify({"text": m.group(0), "start": m.start(), "end": m.end(),
                   "groups": list(m.groups())})


def _rx_all(pattern, text):
    return _re.findall(pattern, text)


def _rx_replace(pattern, text, repl):
    return _re.sub(pattern, repl, text)


def _rx_split(pattern, text):
    return _re.split(pattern, text)


def _rx_test(pattern, text):
    return _re.search(pattern, text) is not None


regex = SimpleNamespace(match=_rx_match, all=_rx_all, replace=_rx_replace,
                        split=_rx_split, test=_rx_test)

# -- csv -------------------------------------------------------------
import csv as _csv  # noqa: E402
import io as _io  # noqa: E402


def _csv_parse(text, header=True):
    rows = list(_csv.reader(_io.StringIO(text)))
    if not rows:
        return []
    if header:
        head = rows[0]
        return [boxify(dict(zip(head, r))) for r in rows[1:]]
    return rows


def _csv_format(rows):
    buf = _io.StringIO()
    if rows and isinstance(rows[0], dict):
        w = _csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    else:
        _csv.writer(buf).writerows(rows)
    return buf.getvalue()


def _csv_read(path, header=True):
    return _csv_parse(_read(path), header)


def _csv_write(path, rows):
    return _write(path, _csv_format(rows))


csv = SimpleNamespace(parse=_csv_parse, format=_csv_format,
                      read=_csv_read, write=_csv_write)

# -- datetime ------------------------------------------------------
from datetime import datetime as _dt, timedelta as _td  # noqa: E402


def _dt_now():
    return _dt.now()


def _dt_parse(s, fmt="%Y-%m-%d"):
    return _dt.strptime(s, fmt)


def _dt_format(d, fmt="%Y-%m-%d %H:%M:%S"):
    return d.strftime(fmt)


def _dt_add(d, days=0, hours=0, minutes=0, seconds=0):
    return d + _td(days=days, hours=hours, minutes=minutes, seconds=seconds)


def _dt_diff_days(a, b):
    return (a - b).days


def _dt_parts(d):
    return boxify({"year": d.year, "month": d.month, "day": d.day,
                   "hour": d.hour, "minute": d.minute, "second": d.second,
                   "weekday": d.isoweekday()})


datetime = SimpleNamespace(now=_dt_now, parse=_dt_parse, format=_dt_format,
                           add=_dt_add, diff_days=_dt_diff_days, parts=_dt_parts)

# -- random --------------------------------------------------------
random = SimpleNamespace(
    int=_random.randint, float=_random.random,
    range=lambda a, b: _random.uniform(a, b),
    choice=lambda xs: _random.choice(list(xs)),
    sample=lambda xs, k: _random.sample(list(xs), k),
    shuffle=lambda xs: _random.sample(list(xs), len(list(xs))),
    seed=_random.seed, chance=lambda p=0.5: _random.random() < p,
)

# -- stats --------------------------------------------------------
import statistics as _stats  # noqa: E402


def _st_mode(xs):
    try:
        return _stats.mode(xs)
    except _stats.StatisticsError:
        return None


stats = SimpleNamespace(
    mean=lambda xs: _stats.fmean(xs) if xs else 0,
    median=lambda xs: _stats.median(xs) if xs else 0,
    mode=_st_mode,
    stdev=lambda xs: _stats.pstdev(xs) if len(xs) > 0 else 0,
    variance=lambda xs: _stats.pvariance(xs) if len(xs) > 0 else 0,
    sum=lambda xs: sum(xs), min=lambda xs: min(xs) if xs else None,
    max=lambda xs: max(xs) if xs else None,
    range=lambda xs: (max(xs) - min(xs)) if xs else 0,
)

# -- env / args --------------------------------------------------
env = SimpleNamespace(
    get=lambda name, default=None: _os.environ.get(name, default),
    set=lambda name, value: _os.environ.__setitem__(name, str(value)),
    has=lambda name: name in _os.environ,
    all=lambda: boxify(dict(_os.environ)),
)

# -- shell — 어떤 언어·도구든 (node, go 바이너리, git, ffmpeg …) ------
import shlex as _shlex  # noqa: E402
import subprocess as _sp  # noqa: E402


def _sh_run(cmd, stdin="", timeout=60):
    args = cmd if isinstance(cmd, list) else _shlex.split(cmd, posix=(_os.name != "nt"))
    try:
        p = _sp.run(args, input=stdin, capture_output=True, text=True,
                    encoding="utf-8", errors="replace", timeout=timeout)
        return boxify({"out": p.stdout, "err": p.stderr, "code": p.returncode,
                       "ok": p.returncode == 0})
    except FileNotFoundError:
        raise POIError(f"명령을 찾을 수 없습니다: {args[0] if args else cmd}", "P160")
    except _sp.TimeoutExpired:
        return boxify({"out": "", "err": f"시간 초과 ({timeout}s)", "code": 124,
                       "ok": False})


def _sh_text(cmd, stdin="", timeout=60):
    return _sh_run(cmd, stdin, timeout).out.rstrip("\n")


shell = SimpleNamespace(run=_sh_run, text=_sh_text)

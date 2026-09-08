"""POI 표준 라이브러리 2 — 백엔드 · 보안 · 시스템 (v1.7).

파이썬 표준 라이브러리만 사용한다 (외부 의존성 0). 여기 있는 모듈은
`use std:crypto` 처럼 불러온다. `database(...)` 만 import 없이 바로 쓴다.

포함: crypto · password · jwt · path · url · html · compress · log ·
      cache · bench · dotenv · system · uuid · (database 빌더)
"""
from __future__ import annotations

import base64 as _b64
import binascii as _binascii
import hashlib as _hashlib
import hmac as _hmac
import json as _json
import os as _os
import platform as _platform
import secrets as _secrets
import sqlite3 as _sqlite3
import sys as _sys
import time as _time
import urllib.parse as _uparse
import uuid as _uuidmod
from types import SimpleNamespace

from ..errors import POIError
from .boxes import Box, boxify


def _as_bytes(v) -> bytes:
    if isinstance(v, bytes):
        return v
    if isinstance(v, bytearray):
        return bytes(v)
    return str(v).encode("utf-8")


# ── crypto ─────────────────────────────────────────────────────────────

def _digest(name, data):
    return _hashlib.new(name, _as_bytes(data)).hexdigest()


def _hmac_hex(key, msg, name="sha256"):
    return _hmac.new(_as_bytes(key), _as_bytes(msg), name).hexdigest()


def _b64_encode(data, urlsafe=False):
    raw = _as_bytes(data)
    enc = _b64.urlsafe_b64encode if urlsafe else _b64.b64encode
    return enc(raw).decode("ascii")


def _b64_decode(s, urlsafe=False, as_text=True):
    s = str(s)
    pad = "=" * (-len(s) % 4)
    dec = _b64.urlsafe_b64decode if urlsafe else _b64.b64decode
    raw = dec(s + pad)
    return raw.decode("utf-8", "replace") if as_text else raw


crypto = SimpleNamespace(
    sha256=lambda s: _digest("sha256", s),
    sha512=lambda s: _digest("sha512", s),
    sha1=lambda s: _digest("sha1", s),
    md5=lambda s: _digest("md5", s),
    blake2=lambda s: _digest("blake2b", s),
    hmac=lambda key, msg, algo="sha256": _hmac_hex(key, msg, algo),
    hmac_sha256=lambda key, msg: _hmac_hex(key, msg, "sha256"),
    base64_encode=_b64_encode,
    base64_decode=_b64_decode,
    hex_encode=lambda s: _as_bytes(s).hex(),
    hex_decode=lambda s: bytes.fromhex(str(s)).decode("utf-8", "replace"),
    random_bytes=lambda n=16: _secrets.token_bytes(int(n)),
    random_hex=lambda n=16: _secrets.token_hex(int(n)),
    token=lambda n=32: _secrets.token_urlsafe(int(n)),
    uuid=lambda: str(_uuidmod.uuid4()),
    number=lambda lo=0, hi=100: _secrets.randbelow(int(hi) - int(lo)) + int(lo),
    constant_eq=lambda a, b: _hmac.compare_digest(_as_bytes(a), _as_bytes(b)),
)

# ── password (PBKDF2-HMAC-SHA256) ──────────────────────────────────────

_PW_ITERS = 240_000


def _pw_hash(pw, iterations=_PW_ITERS):
    salt = _secrets.token_bytes(16)
    dk = _hashlib.pbkdf2_hmac("sha256", _as_bytes(pw), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${dk.hex()}"


def _pw_verify(pw, stored):
    try:
        algo, iters, salt_hex, hash_hex = str(stored).split("$")
        if algo != "pbkdf2_sha256":
            return False
        dk = _hashlib.pbkdf2_hmac("sha256", _as_bytes(pw),
                                  bytes.fromhex(salt_hex), int(iters))
        return _hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


password = SimpleNamespace(
    hash=_pw_hash, verify=_pw_verify,
    strong=lambda p: (len(str(p)) >= 8 and any(c.isdigit() for c in str(p))
                      and any(c.isalpha() for c in str(p))),
)

# ── jwt (HS256, 의존성 0) ─────────────────────────────────────────────


def _jwt_b64(raw: bytes) -> str:
    return _b64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _jwt_unb64(seg: str) -> bytes:
    seg = seg + "=" * (-len(seg) % 4)
    return _b64.urlsafe_b64decode(seg.encode("ascii"))


def _jwt_sign(payload, secret, expires_in=None):
    body = dict(payload) if isinstance(payload, dict) else {"sub": payload}
    now = int(_time.time())
    body.setdefault("iat", now)
    if expires_in:
        body["exp"] = now + int(expires_in)
    head = {"alg": "HS256", "typ": "JWT"}
    h = _jwt_b64(_json.dumps(head, separators=(",", ":")).encode())
    p = _jwt_b64(_json.dumps(body, separators=(",", ":"), default=str).encode())
    sig = _hmac.new(_as_bytes(secret), f"{h}.{p}".encode(), _hashlib.sha256).digest()
    return f"{h}.{p}.{_jwt_b64(sig)}"


def _jwt_verify(token, secret):
    try:
        h, p, s = str(token).split(".")
    except ValueError:
        return None
    expected = _hmac.new(_as_bytes(secret), f"{h}.{p}".encode(),
                         _hashlib.sha256).digest()
    if not _hmac.compare_digest(_jwt_b64(expected), s):
        return None
    body = _json.loads(_jwt_unb64(p))
    if "exp" in body and int(_time.time()) >= int(body["exp"]):
        return None
    return boxify(body)


def _jwt_decode(token):
    try:
        _h, p, _s = str(token).split(".")
        return boxify(_json.loads(_jwt_unb64(p)))
    except (ValueError, _json.JSONDecodeError):
        return None


jwt = SimpleNamespace(sign=_jwt_sign, verify=_jwt_verify, decode=_jwt_decode)

# ── path ──────────────────────────────────────────────────────────────

path = SimpleNamespace(
    join=lambda *parts: _os.path.join(*[str(p) for p in parts]).replace("\\", "/"),
    base=lambda p: _os.path.basename(str(p)),
    dir=lambda p: _os.path.dirname(str(p)).replace("\\", "/"),
    ext=lambda p: _os.path.splitext(str(p))[1],
    stem=lambda p: _os.path.splitext(_os.path.basename(str(p)))[0],
    abs=lambda p: _os.path.abspath(str(p)).replace("\\", "/"),
    norm=lambda p: _os.path.normpath(str(p)).replace("\\", "/"),
    exists=lambda p: _os.path.exists(str(p)),
    is_file=lambda p: _os.path.isfile(str(p)),
    is_dir=lambda p: _os.path.isdir(str(p)),
    split=lambda p: list(_os.path.split(str(p))),
    parts=lambda p: [x for x in str(p).replace("\\", "/").split("/") if x],
    home=lambda: _os.path.expanduser("~").replace("\\", "/"),
    cwd=lambda: _os.getcwd().replace("\\", "/"),
    size=lambda p: _os.path.getsize(str(p)),
)

# ── url ───────────────────────────────────────────────────────────────


def _url_parse(u):
    r = _uparse.urlsplit(str(u))
    q = {k: v[0] if len(v) == 1 else v
         for k, v in _uparse.parse_qs(r.query).items()}
    return boxify({
        "scheme": r.scheme, "host": r.hostname or "", "port": r.port,
        "path": r.path, "query": q, "fragment": r.fragment,
        "user": r.username or "", "password": r.password or "",
    })


def _url_build(scheme="https", host="", path="/", query=None, fragment=""):
    q = _uparse.urlencode(query or {}, doseq=True)
    return _uparse.urlunsplit((scheme, host, path, q, fragment))


url = SimpleNamespace(
    parse=_url_parse, build=_url_build,
    encode=lambda s: _uparse.quote(str(s), safe=""),
    decode=lambda s: _uparse.unquote(str(s)),
    query_encode=lambda d: _uparse.urlencode(d or {}, doseq=True),
    query_parse=lambda s: boxify({k: v[0] if len(v) == 1 else v
                                  for k, v in _uparse.parse_qs(str(s)).items()}),
    join=lambda base, rel: _uparse.urljoin(str(base), str(rel)),
)

# ── html ─────────────────────────────────────────────────────────────
import html as _htmlmod  # noqa: E402
import re as _re  # noqa: E402

_TAG_RE = _re.compile(r"<[^>]+>")

htmlmod = SimpleNamespace(
    escape=lambda s: _htmlmod.escape(str(s), quote=True),
    unescape=lambda s: _htmlmod.unescape(str(s)),
    strip_tags=lambda s: _TAG_RE.sub("", str(s)),
    attr=lambda s: _htmlmod.escape(str(s), quote=True),
)

# ── compress ─────────────────────────────────────────────────────────
import gzip as _gzip  # noqa: E402
import zlib as _zlib  # noqa: E402
import io as _io  # noqa: E402
import zipfile as _zipfile  # noqa: E402


def _zip_read(zpath):
    out = {}
    with _zipfile.ZipFile(str(zpath)) as z:
        for name in z.namelist():
            if not name.endswith("/"):
                out[name] = z.read(name)
    return boxify(out)


def _zip_make(zpath, files):
    with _zipfile.ZipFile(str(zpath), "w", _zipfile.ZIP_DEFLATED) as z:
        for name, content in dict(files).items():
            z.writestr(str(name), content if isinstance(content, (bytes, bytearray))
                       else str(content))
    return str(zpath)


compress = SimpleNamespace(
    gzip=lambda data: _gzip.compress(_as_bytes(data)),
    gunzip=lambda data, as_text=True: (_gzip.decompress(_as_bytes(data)).decode(
        "utf-8", "replace") if as_text else _gzip.decompress(_as_bytes(data))),
    zlib=lambda data: _zlib.compress(_as_bytes(data), 9),
    unzlib=lambda data, as_text=True: (_zlib.decompress(_as_bytes(data)).decode(
        "utf-8", "replace") if as_text else _zlib.decompress(_as_bytes(data))),
    zip_read=_zip_read, zip_make=_zip_make,
)

# ── log ──────────────────────────────────────────────────────────────

_LEVELS = {"debug": 10, "info": 20, "warn": 30, "error": 40}
_log_state = {"level": 20}


def _emit_log(level, *parts):
    if _LEVELS[level] < _log_state["level"]:
        return
    stamp = _time.strftime("%H:%M:%S")
    msg = " ".join(str(p) for p in parts)
    print(f"{stamp} [{level.upper()}] {msg}", file=_sys.stderr, flush=True)


log = SimpleNamespace(
    debug=lambda *m: _emit_log("debug", *m),
    info=lambda *m: _emit_log("info", *m),
    warn=lambda *m: _emit_log("warn", *m),
    error=lambda *m: _emit_log("error", *m),
    level=lambda name: _log_state.__setitem__("level", _LEVELS.get(str(name), 20)),
)

# ── cache ────────────────────────────────────────────────────────────

_cache_store: dict = {}


def _cache_ttl(key, seconds, producer):
    now = _time.time()
    hit = _cache_store.get(key)
    if hit and hit[0] > now:
        return hit[1]
    val = producer() if callable(producer) else producer
    _cache_store[key] = (now + float(seconds), val)
    return val


def _cache_memo(fn):
    box = {}

    def wrapped(*args):
        if args not in box:
            box[args] = fn(*args)
        return box[args]
    return wrapped


cache = SimpleNamespace(
    get=lambda key, default=None: (_cache_store[key][1]
                                   if key in _cache_store else default),
    set=lambda key, value, ttl=3600: _cache_store.__setitem__(
        key, (_time.time() + float(ttl), value)),
    has=lambda key: key in _cache_store and _cache_store[key][0] > _time.time(),
    clear=lambda: _cache_store.clear(),
    ttl=_cache_ttl, memo=_cache_memo,
)

# ── bench ────────────────────────────────────────────────────────────


def _bench_time(fn):
    t0 = _time.perf_counter()
    fn()
    return _time.perf_counter() - t0


def _bench_run(fn, times=1000):
    times = int(times)
    t0 = _time.perf_counter()
    for _ in range(times):
        fn()
    total = _time.perf_counter() - t0
    return boxify({"total": total, "avg": total / times if times else 0,
                   "per_sec": times / total if total else 0, "runs": times})


bench = SimpleNamespace(time=_bench_time, run=_bench_run, now=_time.perf_counter)

# ── dotenv ───────────────────────────────────────────────────────────


def _dotenv_load(path=".env", override=False):
    loaded = {}
    if not _os.path.isfile(path):
        return boxify(loaded)
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key, val = key.strip(), val.strip().strip('"').strip("'")
            loaded[key] = val
            if override or key not in _os.environ:
                _os.environ[key] = val
    return boxify(loaded)


dotenv = SimpleNamespace(load=_dotenv_load)

# ── system ───────────────────────────────────────────────────────────

system = SimpleNamespace(
    platform=lambda: _platform.system().lower(),
    release=lambda: _platform.release(),
    machine=lambda: _platform.machine(),
    python_version=lambda: _platform.python_version(),
    poi_version=lambda: __import__("poi").__version__,
    cpu_count=lambda: _os.cpu_count() or 1,
    hostname=lambda: _platform.node(),
    pid=lambda: _os.getpid(),
    cwd=lambda: _os.getcwd().replace("\\", "/"),
    args=lambda: list(_sys.argv[1:]),
    env=lambda name, default=None: _os.environ.get(name, default),
    exit=lambda code=0: _sys.exit(int(code)),
)

# ── uuid ─────────────────────────────────────────────────────────────

uuid = SimpleNamespace(
    v4=lambda: str(_uuidmod.uuid4()),
    hex=lambda: _uuidmod.uuid4().hex,
    short=lambda: _uuidmod.uuid4().hex[:12],
    is_valid=lambda s: (lambda: (_uuidmod.UUID(str(s)), True)[1])()
    if _re.match(r"^[0-9a-fA-F-]{32,36}$", str(s)) else False,
)

# ── database (sqlite, import 없이) ───────────────────────────────────


class DB:
    """`db = database("app.db")` — 0설정 SQLite. 결과 행은 점 접근 Box."""

    def __init__(self, target=":memory:"):
        self._path = str(target)
        self._con = _sqlite3.connect(self._path, check_same_thread=False)
        self._con.row_factory = _sqlite3.Row
        self._con.execute("PRAGMA journal_mode=WAL")
        self._con.execute("PRAGMA foreign_keys=ON")

    def _params(self, params):
        if params is None:
            return ()
        if isinstance(params, dict):
            return params
        if isinstance(params, (list, tuple)):
            return tuple(params)
        return (params,)

    def run(self, sql, params=None):
        cur = self._con.execute(str(sql), self._params(params))
        self._con.commit()
        return boxify({"changed": cur.rowcount, "id": cur.lastrowid})

    def exec(self, script):
        self._con.executescript(str(script))
        self._con.commit()
        return True

    def query(self, sql, params=None):
        cur = self._con.execute(str(sql), self._params(params))
        return [boxify({k: row[k] for k in row.keys()}) for row in cur.fetchall()]

    def one(self, sql, params=None):
        cur = self._con.execute(str(sql), self._params(params))
        row = cur.fetchone()
        return boxify({k: row[k] for k in row.keys()}) if row else None

    def value(self, sql, params=None):
        cur = self._con.execute(str(sql), self._params(params))
        row = cur.fetchone()
        return row[0] if row else None

    def insert(self, table, data):
        d = dict(data)
        cols = ", ".join(d.keys())
        marks = ", ".join(["?"] * len(d))
        cur = self._con.execute(
            f"INSERT INTO {table} ({cols}) VALUES ({marks})", tuple(d.values()))
        self._con.commit()
        return cur.lastrowid

    def tables(self):
        cur = self._con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return [r[0] for r in cur.fetchall()]

    def close(self):
        self._con.close()
        return True

    def __repr__(self):
        return f"<database {self._path!r}>"


def open_database(target=":memory:"):
    return DB(target)


# ── ai — LLM (하온 백엔드: Groq → 로컬 Ollama) ───────────────────────

def _ai_chat(prompt, system=None, model=None, code=""):
    from ..apps import haon
    return haon.chat(str(prompt), str(code or ""), None,
                     system=str(system or ""), model=str(model or ""))


ai = SimpleNamespace(
    chat=_ai_chat,
    ask=lambda p: _ai_chat(p, system="사용자에게 한국어로, 3문장 안쪽으로 답해."),
    code=lambda p, lang="poi": _ai_chat(
        "다음 요청대로 " + str(lang) + " 코드만 출력해 (설명·마크다운 없이):\n" + str(p),
        system="너는 정확한 코드 생성기다. 코드 블록 표시 없이 코드만."),
    summarize=lambda text: _ai_chat("아래 내용을 3줄로 요약해:\n" + str(text)),
    backends=lambda: __import__("poi.apps.haon",
                                fromlist=["detect"]).detect(),
    install=lambda: __import__("poi.apps.haon", fromlist=["ensure_model"])
    .ensure_model(print),
)


from .uikit import uikit as _uikit
from .concurrency import task as _task
from .net import http as _http, net as _net
from .scene3d import scene3d as _scene3d

MODULES = {
    "ai": ai,
    "uikit": _uikit,
    "task": _task,
    "http": _http,
    "net": _net,
    "scene3d": _scene3d,
    "crypto": crypto,
    "password": password,
    "jwt": jwt,
    "path": path,
    "url": url,
    "html": htmlmod,
    "compress": compress,
    "log": log,
    "cache": cache,
    "bench": bench,
    "dotenv": dotenv,
    "system": system,
    "uuid": uuid,
}

# 한국어 별칭
KO_MODULES = {
    "암호": crypto, "비밀번호": password, "토큰": jwt, "경로": path,
    "주소": url, "압축": compress, "기록": log, "캐시": cache,
    "성능측정": bench, "시스템": system, "유아이": _uikit, "지유아이": _uikit,
    "작업": _task, "동시성": _task, "요청": _http, "망": _net, "네트워크": _net,
    "삼차원": _scene3d, "입체": _scene3d,
}

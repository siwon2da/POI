"""POI 웹 (v1.6) — 내장 HTTP 서버 + 선언형 페이지.

파이썬/JS 백엔드보다 나은 것을 목표로:
  · 보안 기본값 — HTML 자동 이스케이프, CSRF 토큰 자동, 보안 헤더, 정적 경로 차단, 본문 크기 제한
  · 성능 — 컴파일된 라우트, 스레드 풀, 정적 파일 ETag/캐시, HTTP/1.1 keep-alive
  · UX/UI — 만들자마자 예쁜 반응형·다크 대응 페이지 (설정 0)

    server {
        get "/" { return "<h1>안녕</h1>" }
        get "/api/합/:a/:b" { return { 합: number(params.a) + number(params.b) } }
        post "/echo" { return body }
        static "./public"
    }

    webapp "메모장" {
        state 메모 = []
        page "/" {
            heading "메모장"
            for m in 메모 { card { text m } }
            form "/추가" { field "새 메모" -> 내용   button "추가" }
        }
        action "/추가" { 메모.add(내용) }
    }
"""
from __future__ import annotations

import gzip as _gzip
import hashlib
import html as _html
import json as _json
import os
import re as _re
import secrets
import time as _time
import urllib.parse as _up
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace

from ..errors import POIError
from .boxes import Box, boxify

_APPS: list = []
_STATE: dict = {}
_CSRF = secrets.token_urlsafe(24)      # 개발 서버 = 단일 프로세스
_SECRET = secrets.token_bytes(32)     # 서명 쿠키/세션용
_MAX_BODY = 2 * 1024 * 1024
_GZIP_MIN = 900
_GZIP_TYPES = ("text/", "application/json", "application/javascript",
               "image/svg+xml", "application/xml")

# ── 레이트 리밋 (토큰 버킷, IP 당) ──────────────────────────────────
_RATE: dict = {}
_RATE_MAX = int(os.environ.get("POI_RATE_MAX", "600"))   # 창당 요청 수
_RATE_WINDOW = float(os.environ.get("POI_RATE_WINDOW", "60"))


def _rate_ok(ip: str) -> bool:
    if _RATE_MAX <= 0:
        return True
    now = _time.monotonic()
    tokens, last = _RATE.get(ip, (_RATE_MAX, now))
    tokens = min(_RATE_MAX, tokens + (now - last) * (_RATE_MAX / _RATE_WINDOW))
    if tokens < 1:
        _RATE[ip] = (tokens, now)
        return False
    _RATE[ip] = (tokens - 1, now)
    return True


# ── 서명 쿠키 / 세션 ────────────────────────────────────────────────

def _sign(raw: str) -> str:
    mac = hashlib.blake2b(str(raw).encode("utf-8"), key=_SECRET,
                          digest_size=12).hexdigest()
    return f"{raw}.{mac}"


def _unsign(token):
    token = str(token or "")
    raw, _, mac = token.rpartition(".")
    if not raw:
        return None
    good = hashlib.blake2b(raw.encode("utf-8"), key=_SECRET,
                           digest_size=12).hexdigest()
    return raw if secrets.compare_digest(mac, good) else None


def set_cookie(name, value, days=7, path="/", http_only=True,
               same_site="Lax", signed=True, secure=False):
    v = _sign(value) if signed else str(value)
    parts = [f"{name}={_up.quote(v)}", f"Path={path}",
             f"Max-Age={int(float(days) * 86400)}", f"SameSite={same_site}"]
    if http_only:
        parts.append("HttpOnly")
    if secure:
        parts.append("Secure")
    return "; ".join(parts)


def read_cookie(headers, name, signed=True):
    raw = headers.get("Cookie") or headers.get("cookie") or "" \
        if hasattr(headers, "get") else ""
    for chunk in str(raw).split(";"):
        k, _, val = chunk.strip().partition("=")
        if k == name:
            val = _up.unquote(val)
            return _unsign(val) if signed else val
    return None


session = SimpleNamespace(cookie=set_cookie, read=read_cookie,
                          sign=_sign, open=_unsign)

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy":
        "default-src 'self'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; script-src 'self' 'unsafe-inline'",
}


def reset():
    _APPS.clear()
    _STATE.clear()


def register(app: dict):
    _APPS.append(app)


def state_get(name, default=None):
    return _STATE.get(name, default)


def state_set(name, value):
    _STATE[name] = value


# ── 라우트 ───────────────────────────────────────────────────────────

def _compile_path(path: str):
    parts = []
    for seg in path.strip("/").split("/"):
        if seg.startswith(":"):
            parts.append(f"(?P<{seg[1:]}>[^/]+)")
        elif seg == "*":
            parts.append(r".*")
        elif seg:
            parts.append(_re.escape(seg))
    return _re.compile("^/" + "/".join(parts) + "/?$")


# ── 응답 헬퍼 (POI 전역: respond / redirect / html) ──────────────────

def respond(body="", status=200, headers=None, content_type=None):
    return {"__poi_response__": True, "status": status, "body": body,
            "headers": headers or {}, "content_type": content_type}


def redirect(location, status=303):
    return {"__poi_response__": True, "status": status, "body": "",
            "headers": {"Location": location or "/"}, "content_type": "text/plain"}


def html_raw(s):
    return {"__poi_html__": str(s)}


def _coerce(value):
    if isinstance(value, dict) and value.get("__poi_response__"):
        b = value["body"]
        if isinstance(b, (dict, list)):
            data = _json.dumps(b, ensure_ascii=False, default=str).encode("utf-8")
            ct = value["content_type"] or "application/json; charset=utf-8"
        else:
            data = str(b).encode("utf-8")
            ct = value["content_type"] or "text/html; charset=utf-8"
        return value["status"], data, ct, dict(value["headers"])
    if isinstance(value, (dict, list)):
        return (200, _json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"),
                "application/json; charset=utf-8", {})
    if value is None:
        return 204, b"", "text/plain", {}
    s = str(value)
    ct = ("text/html; charset=utf-8" if s.lstrip()[:1] == "<"
          else "text/plain; charset=utf-8")
    return 200, s.encode("utf-8"), ct, {}


# ── 페이지 렌더 (예쁜 기본 디자인) ─────────────────────────────────

_PAGE_CSS = """
:root{--bg:#f2f4f6;--card:#fff;--ink:#191f28;--ink2:#4e5968;--ink3:#8b95a1;
--line:#e5e8eb;--blue:#3182f6;--blue2:#1b64da;--wash:#ebf2fe;--good:#12b886;--warn:#f59f00;
--r:16px;--sh:0 1px 3px rgba(25,31,40,.05),0 8px 24px -14px rgba(25,31,40,.12)}
@media(prefers-color-scheme:dark){:root{--bg:#16181d;--card:#1e2026;--ink:#eaecef;
--ink2:#a9aeb8;--ink3:#767c87;--line:#2b2e36;--blue:#4b93f8;--wash:#1c2a42;
--sh:0 1px 3px rgba(0,0,0,.4),0 10px 30px -16px rgba(0,0,0,.6)}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);line-height:1.7;
font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic",
"Noto Sans KR",Segoe UI,sans-serif;word-break:keep-all;-webkit-font-smoothing:antialiased}
.poi-wrap{max-width:680px;margin:0 auto;padding:clamp(20px,5vw,40px) 20px 96px}
h1.poi,h2.poi{margin:0 0 6px;line-height:1.25;letter-spacing:-.01em}
h1.poi{font-size:clamp(1.6rem,5vw,2.1rem)}h2.poi{font-size:1.3rem;margin-top:22px}
.poi-sub{color:var(--ink2);margin:2px 0 18px;font-size:1.02rem}
p.poi{margin:10px 0}
.poi-card{background:var(--card);border:1px solid var(--line);border-radius:var(--r);
padding:18px 20px;margin:12px 0;box-shadow:var(--sh)}
.poi-card>*:first-child{margin-top:0}.poi-card>*:last-child{margin-bottom:0}
.poi-row{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-start;margin:12px 0}
.poi-row>*{flex:1 1 auto;margin:0}
.poi-col{display:flex;flex-direction:column;gap:10px;margin:12px 0}
a.poi-link{color:var(--blue);text-decoration:none;font-weight:600}
a.poi-link:hover{text-decoration:underline}
.poi-badge{display:inline-block;background:var(--wash);color:var(--blue);
border-radius:999px;padding:3px 12px;font-size:.82rem;font-weight:700}
hr.poi{border:0;border-top:1px solid var(--line);margin:20px 0}
img.poi{max-width:100%;border-radius:12px;display:block;margin:12px 0}
.poi-alert{background:var(--wash);border:1px solid color-mix(in srgb,var(--blue) 30%,transparent);
border-radius:12px;padding:12px 16px;margin:12px 0;font-size:.95rem}
.poi-notice{background:color-mix(in srgb,var(--warn) 14%,var(--card));
border:1px solid color-mix(in srgb,var(--warn) 40%,transparent);
border-radius:12px;padding:12px 16px;margin:12px 0;font-size:.95rem}
form.poi{margin:14px 0;display:flex;flex-direction:column;gap:10px}
.poi-field{display:flex;flex-direction:column;gap:5px}
.poi-field label{font-size:.85rem;color:var(--ink3);font-weight:600}
input.poi,textarea.poi,select.poi{width:100%;padding:12px 14px;border:1px solid var(--line);
border-radius:12px;font:inherit;background:var(--card);color:var(--ink);transition:border-color .15s}
input.poi:focus,textarea.poi:focus,select.poi:focus{outline:0;border-color:var(--blue)}
textarea.poi{min-height:90px;resize:vertical}
.poi-check{display:flex;align-items:center;gap:9px;font-size:.95rem}
.poi-check input{width:18px;height:18px;accent-color:var(--blue)}
button.poi{background:var(--blue);color:#fff;border:0;border-radius:13px;padding:13px 22px;
font:inherit;font-weight:700;cursor:pointer;transition:background .15s,transform .1s}
button.poi:hover{background:var(--blue2)}button.poi:active{transform:translateY(1px)}
button.poi[disabled]{opacity:.6;cursor:default}
.poi-foot{margin-top:40px;color:var(--ink3);font-size:.8rem;text-align:center}
""".strip()

_PAGE_JS = """
document.addEventListener('submit',function(e){
 var b=e.target.querySelector('button[type=submit]');
 if(b){b.disabled=true;b.dataset._t=b.textContent;b.textContent='...';}
},true);
""".strip()


def render_page(nodes, title="POI"):
    body = _render_nodes(nodes)
    return (
        "<!doctype html><html lang=ko><head><meta charset=utf-8>"
        "<meta name=viewport content='width=device-width,initial-scale=1'>"
        f"<meta name=csrf-token content='{_CSRF}'>"
        f"<title>{_esc(title)}</title><style>{_PAGE_CSS}</style></head>"
        f"<body><div class=poi-wrap>{body}"
        "<div class=poi-foot>made with POI</div></div>"
        f"<script>{_PAGE_JS}</script></body></html>"
    )


def _esc(s):
    return _html.escape(str(s), quote=True)


def _render_nodes(nodes):
    return "".join(_render_node(n) for n in nodes)


def _render_node(n):
    if not isinstance(n, dict):
        return f"<p class=poi>{_esc(n)}</p>"
    if n.get("__poi_html__") is not None:
        return n["__poi_html__"]
    t = n.get("t")
    kids = _render_nodes(n.get("kids", []))
    if t in ("title", "heading"):
        return f"<h1 class=poi>{_esc(n['text'])}</h1>"
    if t == "subtitle":
        return f"<p class=poi-sub>{_esc(n['text'])}</p>"
    if t == "text":
        return f"<p class=poi>{_esc(n['text'])}</p>"
    if t == "badge":
        return f"<span class=poi-badge>{_esc(n['text'])}</span>"
    if t == "alert":
        return f"<div class=poi-alert>{_esc(n['text'])}</div>"
    if t == "notice":
        return f"<div class=poi-notice>{_esc(n['text'])}</div>"
    if t == "divider":
        return "<hr class=poi>"
    if t == "spacer":
        return f"<div style='height:{int(n.get('px', 24))}px'></div>"
    if t == "image":
        return f"<img class=poi src='{_esc(n['src'])}' alt=''>"
    if t == "link":
        return f"<a class=poi-link href='{_esc(n['href'])}'>{_esc(n['text'])}</a>"
    if t == "card":
        return f"<div class=poi-card>{kids}</div>"
    if t == "row":
        return f"<div class=poi-row>{kids}</div>"
    if t == "col":
        return f"<div class=poi-col>{kids}</div>"
    if t == "form":
        csrf = f"<input type=hidden name=_csrf value='{_CSRF}'>"
        return (f"<form class=poi method=post action='{_esc(n['action'])}'>"
                f"{csrf}{kids}</form>")
    if t == "input":
        return _input_html(n.get("label", ""), n["name"],
                           secret=n.get("secret"), multiline=n.get("multiline"))
    if t == "field":
        ph = _esc(n.get("label", ""))
        return (f"<div class=poi-field><label>{ph}</label>"
                f"<input class=poi type=text name='{_esc(n['name'])}'></div>")
    if t == "select":
        opts = "".join(f"<option>{_esc(o)}</option>" for o in (n.get("options") or []))
        return (f"<div class=poi-field><label>{_esc(n.get('label',''))}</label>"
                f"<select class=poi name='{_esc(n['name'])}'>{opts}</select></div>")
    if t == "checkbox":
        return (f"<label class=poi-check><input type=checkbox name='{_esc(n['name'])}' "
                f"value=1>{_esc(n.get('label',''))}</label>")
    if t == "button":
        return f"<button class=poi type=submit>{_esc(n['text'])}</button>"
    return kids


def _input_html(label, name, secret=False, multiline=False):
    ph = _esc(label)
    if multiline:
        return f"<textarea class=poi name='{_esc(name)}' placeholder='{ph}'></textarea>"
    typ = "password" if secret else "text"
    return f"<input class=poi type={typ} name='{_esc(name)}' placeholder='{ph}'>"


# ── 서버 ─────────────────────────────────────────────────────────────

def _make_handler(routes, static_dirs, title, csrf_paths=None):
    compiled = [(m, _compile_path(p), fn) for (m, p), fn in routes.items()]
    action_paths = {p.rstrip("/") for p in (csrf_paths or ())}

    class H(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        server_version = "POI"

        def log_message(self, *a):
            pass

        def _dispatch(self, method):
            if not _rate_ok(self.client_address[0]):
                return self._send(429, "요청이 너무 많습니다.".encode("utf-8"),
                                  "text/plain; charset=utf-8",
                                  {"Retry-After": "10"})
            parsed = _up.urlparse(self.path)
            path = _up.unquote(parsed.path)
            query = boxify({k: v[0] for k, v in _up.parse_qs(parsed.query).items()})
            length = int(self.headers.get("Content-Length", 0) or 0)
            if length > _MAX_BODY:
                return self._send(413, b"too large", "text/plain", {})
            raw = self.rfile.read(length) if length else b""
            ctype = self.headers.get("Content-Type", "")
            body = Box()
            if raw:
                try:
                    if "json" in ctype:
                        body = boxify(_json.loads(raw.decode("utf-8")))
                    else:
                        body = boxify({k: v[0] for k, v in
                                       _up.parse_qs(raw.decode("utf-8")).items()})
                except Exception:
                    body = Box({"raw": raw.decode("utf-8", "replace")})

            # CSRF — webapp 폼(POST + 등록된 액션 경로)에만. server{} 의 API POST 는 제외.
            if method == "POST" and path.rstrip("/") in action_paths:
                if body.get("_csrf") != _CSRF:
                    return self._send(403,
                                      "CSRF 토큰이 없거나 틀립니다.".encode("utf-8"),
                                      "text/plain; charset=utf-8", {})

            for m, rx, fn in compiled:
                if m != method:
                    continue
                mt = rx.match(path)
                if not mt:
                    continue
                try:
                    result = fn(boxify(mt.groupdict()), query, body,
                               boxify({k: v for k, v in self.headers.items()}), method)
                except Exception as e:  # noqa: BLE001
                    return self._send(500, f"핸들러 오류: {e}".encode("utf-8"),
                                      "text/plain; charset=utf-8", {})
                st, data, ct, extra = _coerce(result)
                return self._send(st, data, ct, extra)

            if self._try_static(path):
                return
            self._send(404, "<h1>404</h1><p>없는 경로입니다.</p>".encode("utf-8"),
                       "text/html; charset=utf-8", {})

        def _try_static(self, path):
            import mimetypes
            for d in static_dirs:
                base = os.path.abspath(d)
                fp = os.path.normpath(os.path.join(base, path.lstrip("/")))
                if not fp.startswith(base) or not os.path.isfile(fp):
                    continue
                stt = os.stat(fp)
                etag = f'"{stt.st_mtime_ns:x}-{stt.st_size:x}"'
                if self.headers.get("If-None-Match") == etag:
                    self._send(304, b"", "text/plain", {"ETag": etag})
                    return True
                with open(fp, "rb") as f:
                    data = f.read()
                self._send(200, data,
                           mimetypes.guess_type(fp)[0] or "application/octet-stream",
                           {"ETag": etag, "Cache-Control": "public, max-age=3600"})
                return True
            return False

        def _send(self, status, data: bytes, ctype, extra):
            extra = dict(extra or {})
            if (len(data) >= _GZIP_MIN and status == 200
                    and any(ctype.startswith(t) for t in _GZIP_TYPES)
                    and "gzip" in self.headers.get("Accept-Encoding", "")):
                data = _gzip.compress(data, 6)
                extra["Content-Encoding"] = "gzip"
                extra["Vary"] = "Accept-Encoding"
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            for k, v in _SECURITY_HEADERS.items():
                self.send_header(k, v)
            for k, v in extra.items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(data)

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

        def do_PUT(self):
            self._dispatch("PUT")

        def do_DELETE(self):
            self._dispatch("DELETE")

        def do_HEAD(self):
            self._dispatch("GET")

    return H


def _build_handler():
    routes: dict = {}
    static_dirs: list = []
    csrf_paths: list = []
    title = "POI"
    for app in _APPS:
        routes.update(app.get("routes", {}))
        static_dirs.extend(app.get("static", []))
        csrf_paths.extend(app.get("csrf_paths", []))
        if app.get("title"):
            title = app["title"]
    return _make_handler(routes, static_dirs, title, csrf_paths), routes, static_dirs


def start(port: int = 8080, host: str = "127.0.0.1", on_log=None):
    """블로킹하지 않고 서버를 띄운다 (POI IDLE 용). (httpd, url) 반환.
    on_log(str) 가 있으면 요청 로그를 그리로 보낸다."""
    import threading
    if not _APPS:
        return None, None
    handler, routes, static_dirs = _build_handler()
    if on_log:
        base = handler

        class H2(base):
            def log_message(self, fmt, *args):
                try:
                    on_log("  %s  %s\n" % (self.command,
                                           (fmt % args).split('"')[0].strip()
                                           or self.path))
                except Exception:
                    pass
        handler = H2
    try:
        httpd = ThreadingHTTPServer((host, port), handler)
    except OSError as e:
        raise POIError(f"포트 {port} 를 열 수 없습니다: {e}", "P170",
                       hint="다른 포트를 쓰거나, 쓰던 서버를 먼저 멈추세요.")
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://{host}:{port}"


def run_all(port: int = 8080, host: str = "127.0.0.1") -> int:
    if not _APPS:
        return 0
    handler, routes, static_dirs = _build_handler()
    try:
        httpd = ThreadingHTTPServer((host, port), handler)
    except OSError as e:
        raise POIError(f"포트 {port} 를 열 수 없습니다: {e}", "P170",
                       hint="다른 프로그램이 쓰고 있으면 poi run --port 3000 처럼 바꾸세요.")
    print(f"\n  POI 웹 서버  →  http://{host}:{port}\n")
    for (m, p) in sorted(routes):
        print(f"    {m:6} {p}")
    if static_dirs:
        print(f"    STATIC {', '.join(static_dirs)}")
    print("\n  Ctrl+C 로 종료\n", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n서버 종료.")
    finally:
        httpd.server_close()
    return 0

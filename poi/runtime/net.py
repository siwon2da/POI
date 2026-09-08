"""POI 네트워크 — HTTP 클라이언트 + TCP (v1.12).

파이썬 표준 라이브러리(urllib·socket·http.server)만 쓴다. 외부 의존성 0.
안전 모드에서는 전부 막힌다 (P210).

    use 없이 바로:  http , net

  http.get(url, headers?, params?)         -> 응답
  http.post(url, body?, json?, headers?)   -> 응답   (put/patch/delete 도 있음)
  http.request(method, url, ...)           -> 응답
  http.download(url, 파일경로)              -> 저장한 바이트 수
  응답 = Box{ status, ok, text, json, headers, url }

  net.tcp(host, port, timeout?)     -> 소켓 (.send / .recv / .line / .close)
  net.listen(port, handler, host?)  -> 서버 (.stop());  handler(conn) 는 연결마다 스레드에서
  net.resolve(host) / net.local_ip() / net.free_port()
"""
from __future__ import annotations

import json as _json
import socket as _socket
import threading as _threading
import urllib.error as _uerr
import urllib.parse as _uparse
import urllib.request as _ureq
from types import SimpleNamespace

from ..errors import POIError
from .boxes import Box, boxify

_UA = "POI/1.12 (+https://hagora.kr/poi)"
_TIMEOUT = 30


def _net_error(msg, code="P330", hint=None):
    return POIError(msg, code, hint=hint)


def _mk_response(resp, url, body_bytes):
    text = ""
    try:
        text = body_bytes.decode("utf-8")
    except Exception:
        try:
            text = body_bytes.decode("latin-1")
        except Exception:
            text = ""
    parsed = None
    ctype = ""
    try:
        ctype = resp.headers.get("Content-Type", "") if resp.headers else ""
    except Exception:
        ctype = ""
    if text and ("json" in ctype.lower() or text[:1] in "{["):
        try:
            parsed = boxify(_json.loads(text))
        except Exception:
            parsed = None
    headers = Box()
    try:
        for k, v in (resp.headers.items() if resp.headers else []):
            headers[k] = v
    except Exception:
        pass
    status = getattr(resp, "status", None) or getattr(resp, "code", 0) or 0
    return Box({
        "status": int(status),
        "ok": 200 <= int(status) < 300,
        "text": text,
        "json": parsed,
        "headers": headers,
        "url": url,
    })


def _do(method, url, *, headers=None, params=None, body=None, json=None,
        timeout=None):
    url = str(url)
    if params:
        q = _uparse.urlencode({str(k): str(v) for k, v in dict(params).items()})
        url = url + ("&" if "?" in url else "?") + q
    data = None
    hdrs = {"User-Agent": _UA}
    if headers:
        for k, v in dict(headers).items():
            hdrs[str(k)] = str(v)
    if json is not None:
        data = _json.dumps(json, ensure_ascii=False).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json; charset=utf-8")
    elif body is not None:
        if isinstance(body, (dict, Box)):
            data = _uparse.urlencode(
                {str(k): str(v) for k, v in body.items()}).encode("utf-8")
            hdrs.setdefault("Content-Type",
                            "application/x-www-form-urlencoded")
        elif isinstance(body, (bytes, bytearray)):
            data = bytes(body)
        else:
            data = str(body).encode("utf-8")
    req = _ureq.Request(url, data=data, headers=hdrs, method=method.upper())
    try:
        with _ureq.urlopen(req, timeout=timeout or _TIMEOUT) as resp:
            return _mk_response(resp, url, resp.read())
    except _uerr.HTTPError as e:  # 4xx/5xx 도 응답으로 돌려준다
        try:
            payload = e.read()
        except Exception:
            payload = b""
        return _mk_response(e, url, payload)
    except _uerr.URLError as e:
        raise _net_error(f"요청 실패 ({url}): {e.reason}", "P331",
                         hint="주소가 맞는지, 인터넷 연결이 되는지 확인하세요.")
    except _socket.timeout:
        raise _net_error(f"요청 시간 초과 ({url})", "P332")


def _download(url, path, timeout=None):
    resp_req = _ureq.Request(str(url), headers={"User-Agent": _UA})
    try:
        with _ureq.urlopen(resp_req, timeout=timeout or _TIMEOUT) as resp:
            data = resp.read()
    except (_uerr.URLError, _socket.timeout) as e:
        raise _net_error(f"내려받기 실패 ({url}): {e}", "P331")
    with open(str(path), "wb") as fh:
        fh.write(data)
    return len(data)


http = SimpleNamespace(
    get=lambda url, headers=None, params=None, timeout=None:
        _do("GET", url, headers=headers, params=params, timeout=timeout),
    post=lambda url, body=None, json=None, headers=None, timeout=None:
        _do("POST", url, body=body, json=json, headers=headers, timeout=timeout),
    put=lambda url, body=None, json=None, headers=None, timeout=None:
        _do("PUT", url, body=body, json=json, headers=headers, timeout=timeout),
    patch=lambda url, body=None, json=None, headers=None, timeout=None:
        _do("PATCH", url, body=body, json=json, headers=headers, timeout=timeout),
    delete=lambda url, headers=None, timeout=None:
        _do("DELETE", url, headers=headers, timeout=timeout),
    request=lambda method, url, headers=None, params=None, body=None, json=None,
    timeout=None: _do(method, url, headers=headers, params=params, body=body,
                      json=json, timeout=timeout),
    download=_download,
)


# ── TCP ────────────────────────────────────────────────────────────────

class Socket:
    __slots__ = ("_s", "_buf")

    def __init__(self, sock):
        self._s = sock
        self._buf = b""

    def send(self, data):
        if isinstance(data, str):
            data = data.encode("utf-8")
        self._s.sendall(bytes(data))
        return len(data)

    def recv(self, n=4096):
        if self._buf:
            out, self._buf = self._buf[:n], self._buf[n:]
            return out.decode("utf-8", "replace")
        return self._s.recv(int(n)).decode("utf-8", "replace")

    def recv_bytes(self, n=4096):
        if self._buf:
            out, self._buf = self._buf[:n], self._buf[n:]
            return out
        return self._s.recv(int(n))

    def line(self, timeout=None):
        if timeout is not None:
            self._s.settimeout(timeout)
        while b"\n" not in self._buf:
            chunk = self._s.recv(4096)
            if not chunk:
                break
            self._buf += chunk
        if b"\n" in self._buf:
            ln, self._buf = self._buf.split(b"\n", 1)
            return ln.decode("utf-8", "replace").rstrip("\r")
        out, self._buf = self._buf, b""
        return out.decode("utf-8", "replace")

    def close(self):
        try:
            self._s.close()
        except Exception:
            pass
        return True

    def __repr__(self):
        return "<socket>"


class TCPServer:
    __slots__ = ("_srv", "_stop", "_thread")

    def __init__(self, port, handler, host):
        self._srv = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
        self._srv.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
        self._srv.bind((host, int(port)))
        self._srv.listen(64)
        self._srv.settimeout(0.5)
        self._stop = _threading.Event()
        self._thread = _threading.Thread(target=self._loop, args=(handler,),
                                         name="poi-tcp-server", daemon=True)
        self._thread.start()

    def _loop(self, handler):
        while not self._stop.is_set():
            try:
                conn, _addr = self._srv.accept()
            except _socket.timeout:
                continue
            except OSError:
                break
            _threading.Thread(target=self._serve, args=(handler, conn),
                              daemon=True).start()

    def _serve(self, handler, conn):
        sock = Socket(conn)
        try:
            handler(sock)
        except BaseException:  # noqa: BLE001
            import traceback
            traceback.print_exc()
        finally:
            sock.close()

    def stop(self):
        self._stop.set()
        try:
            self._srv.close()
        except Exception:
            pass
        return True

    def __repr__(self):
        return "<tcp-server>"


def _tcp(host, port, timeout=None):
    s = _socket.create_connection((str(host), int(port)),
                                  timeout=timeout or _TIMEOUT)
    return Socket(s)


def _free_port():
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
    s.bind(("", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _local_ip():
    s = _socket.socket(_socket.AF_INET, _socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


net = SimpleNamespace(
    tcp=_tcp,
    connect=_tcp,
    listen=lambda port, handler, host="127.0.0.1": TCPServer(port, handler, host),
    resolve=lambda host: _socket.gethostbyname(str(host)),
    hostname=lambda: _socket.gethostname(),
    local_ip=_local_ip,
    free_port=_free_port,
    get=lambda url, **kw: http.get(url, **kw),
    get_json=lambda url, **kw: http.get(url, **kw).json,
)

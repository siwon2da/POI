"""허가된 환경을 위한 방어 보안 연구 표준 모듈.

기본 네트워크 대상은 loopback/사설망으로 제한하고 한 번에 256개 포트까지만
점검한다. 공개 주소는 호출 인자와 환경변수를 모두 명시해야 한다.
"""
from __future__ import annotations

import hashlib as _hashlib
import hmac as _hmac
import ipaddress as _ipaddress
import math as _math
import os as _os
import socket as _socket
from concurrent.futures import ThreadPoolExecutor as _ThreadPoolExecutor
from types import SimpleNamespace

from ..errors import POIError
from .boxes import boxify


def _bytes(data):
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    return str(data).encode("utf-8")


def _hash(data, algorithm="sha256"):
    try:
        return _hashlib.new(str(algorithm), _bytes(data)).hexdigest()
    except ValueError:
        raise POIError(f"지원하지 않는 해시 알고리즘입니다: {algorithm}", "P380")


def _file_hash(path, algorithm="sha256", chunk_size=65536):
    try:
        digest = _hashlib.new(str(algorithm))
        with open(str(path), "rb") as fh:
            for chunk in iter(lambda: fh.read(int(chunk_size)), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError as e:
        raise POIError(f"파일 해시를 계산할 수 없습니다: {e}", "P381")


def _entropy(data):
    raw = _bytes(data)
    if not raw:
        return 0.0
    counts = [raw.count(i) for i in set(raw)]
    return -sum((n / len(raw)) * _math.log2(n / len(raw)) for n in counts)


def _password_report(value):
    s = str(value)
    classes = sum((any(c.islower() for c in s), any(c.isupper() for c in s),
                   any(c.isdigit() for c in s), any(not c.isalnum() for c in s)))
    score = min(100, len(s) * 4 + classes * 10)
    warnings = []
    if len(s) < 12:
        warnings.append("12자 이상을 권장합니다")
    if classes < 3:
        warnings.append("서로 다른 문자 종류를 더 섞으세요")
    if s.lower() in {"password", "admin", "qwerty", "12345678"}:
        warnings.append("널리 알려진 비밀번호입니다")
        score = min(score, 10)
    return boxify({"score": score, "length": len(s), "classes": classes,
                   "strong": score >= 70 and len(s) >= 12, "warnings": warnings})


def _resolved_ips(host):
    try:
        return {_ipaddress.ip_address(row[4][0])
                for row in _socket.getaddrinfo(str(host), None)}
    except (_socket.gaierror, ValueError) as e:
        raise POIError(f"대상 주소를 확인할 수 없습니다 ({host}): {e}", "P382")


def _check_target(host, allow_public=False):
    ips = _resolved_ips(host)
    local = all(ip.is_loopback or ip.is_private or ip.is_link_local for ip in ips)
    unlocked = (allow_public is True and
                _os.environ.get("POI_SECURITY_ALLOW_PUBLIC") == "1")
    if not local and not unlocked:
        raise POIError(
            f"공개 네트워크 대상은 기본적으로 차단됩니다: {host}", "P383",
            hint="소유하거나 허가받은 대상만 점검하세요. 공개 대상은 "
                 "allow_public=true와 POI_SECURITY_ALLOW_PUBLIC=1을 모두 설정해야 합니다.")
    return ips


def _port_open(host, port, timeout=0.25, allow_public=False):
    _check_target(host, allow_public)
    port = int(port)
    if not 1 <= port <= 65535:
        raise POIError("포트는 1~65535 사이여야 합니다.", "P384")
    try:
        with _socket.create_connection((str(host), port), timeout=min(float(timeout), 2.0)):
            return True
    except (OSError, _socket.timeout):
        return False


def _scan_ports(host="127.0.0.1", ports=None, start=None, end=None,
                timeout=0.2, workers=32, allow_public=False):
    _check_target(host, allow_public)
    if ports is None:
        lo = 1 if start is None else int(start)
        hi = 1024 if end is None else int(end)
        ports = list(range(lo, hi + 1))
    else:
        ports = [int(p) for p in ports]
    ports = sorted(set(ports))
    if len(ports) > 256:
        raise POIError("한 번에 최대 256개 포트만 점검할 수 있습니다.", "P385",
                       hint="범위를 나눠서 실행하세요.")
    if any(p < 1 or p > 65535 for p in ports):
        raise POIError("포트는 1~65535 사이여야 합니다.", "P384")
    timeout = max(0.01, min(float(timeout), 2.0))
    worker_count = max(1, min(int(workers), 32, len(ports) or 1))

    def probe(port):
        try:
            with _socket.create_connection((str(host), port), timeout=timeout):
                return port
        except (OSError, _socket.timeout):
            return None

    with _ThreadPoolExecutor(max_workers=worker_count) as pool:
        open_ports = [p for p in pool.map(probe, ports) if p is not None]
    return boxify({"host": str(host), "checked": len(ports),
                   "open": open_ports, "closed": len(ports) - len(open_ports)})


_SECURITY_HEADERS = {
    "content-security-policy": "콘텐츠 보안 정책(CSP)이 없습니다",
    "x-content-type-options": "X-Content-Type-Options가 없습니다",
    "referrer-policy": "Referrer-Policy가 없습니다",
    "permissions-policy": "Permissions-Policy가 없습니다",
}


def _analyze_headers(headers):
    normalized = {str(k).lower(): str(v) for k, v in dict(headers or {}).items()}
    missing = [message for name, message in _SECURITY_HEADERS.items()
               if name not in normalized]
    if "strict-transport-security" not in normalized:
        missing.append("HTTPS 사이트라면 HSTS를 설정하세요")
    return boxify({"score": max(0, 100 - len(missing) * 20),
                   "missing": missing, "headers": normalized})


security = SimpleNamespace(
    hash=_hash,
    sha256=lambda data: _hash(data, "sha256"),
    file_hash=_file_hash,
    hmac=lambda key, data, algorithm="sha256":
        _hmac.new(_bytes(key), _bytes(data), str(algorithm)).hexdigest(),
    constant_equal=lambda a, b: _hmac.compare_digest(_bytes(a), _bytes(b)),
    entropy=_entropy,
    password_report=_password_report,
    port_open=_port_open,
    scan_ports=_scan_ports,
    analyze_headers=_analyze_headers,
    private_target=lambda host: all(
        ip.is_loopback or ip.is_private or ip.is_link_local
        for ip in _resolved_ips(host)),
)

security_lab = security

__all__ = ["security", "security_lab"]

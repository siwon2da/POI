"""POI 전용 단일 EXE 컨테이너.

설치된 ``poi.exe``/``poi-idle.exe``를 실행 스텁으로 재사용하고 컴파일된
POI 앱을 PyInstaller CArchive 쿠키 바로 앞에 삽입한다. 쿠키는 파일 끝에
유지되므로 기존 부트로더 호환성을 깨뜨리지 않는다.
"""
from __future__ import annotations

import hashlib
import json
import marshal
import os
import struct
import sys
import tempfile
import types
import zlib


_CARCHIVE_MAGIC = b"MEI\014\013\012\013\016"
_APP_MAGIC = b"POIAPP01"
_FOOTER = struct.Struct("!II8s")
_MAX_PAYLOAD = 64 * 1024 * 1024
_MAX_MANIFEST = 64 * 1024


class PackageError(ValueError):
    """손상됐거나 지원하지 않는 POI EXE 컨테이너."""


def _cookie_position(data: bytes) -> int:
    pos = data.rfind(_CARCHIVE_MAGIC)
    if pos < 0 or len(data) - pos not in (24, 88):
        raise PackageError("POI 실행 스텁의 아카이브 쿠키를 찾지 못했습니다.")
    return pos


def _encode_code(code: types.CodeType) -> tuple[bytes, str]:
    raw = marshal.dumps(code)
    if len(raw) > _MAX_PAYLOAD:
        raise PackageError("컴파일된 앱이 POI 패키지 크기 제한(64MB)을 넘었습니다.")
    return zlib.compress(raw, 9), hashlib.sha256(raw).hexdigest()


def package_executable(stub_path: str, output_path: str, code: types.CodeType,
                       metadata: dict | None = None) -> dict:
    """실행 스텁에 앱을 넣어 단일 EXE를 원자적으로 만든다."""
    if os.path.abspath(stub_path) == os.path.abspath(output_path):
        raise PackageError("실행 중인 POI 스텁을 출력 파일로 덮어쓸 수 없습니다.")
    with open(stub_path, "rb") as f:
        stub = f.read()
    cookie_pos = _cookie_position(stub)
    if cookie_pos >= _FOOTER.size:
        try:
            if _FOOTER.unpack(stub[cookie_pos - _FOOTER.size:cookie_pos])[2] == _APP_MAGIC:
                raise PackageError("이미 앱이 들어 있는 EXE는 빌드 스텁으로 쓸 수 없습니다.")
        except struct.error:
            pass

    payload, code_hash = _encode_code(code)
    manifest = {
        "format": "poi-exe",
        "format_version": 1,
        "engine_version": str((metadata or {}).get("engine_version", "")),
        "name": str((metadata or {}).get("name", "POI app")),
        "source_file": str((metadata or {}).get("source_file", "")),
        "mode": str((metadata or {}).get("mode", "compiled")),
        "console": bool((metadata or {}).get("console", False)),
        "author": str((metadata or {}).get("author", "")),
        "app_version": str((metadata or {}).get("app_version", "1.0.0")),
        "linemap": dict((metadata or {}).get("linemap", {})),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "code_sha256": code_hash,
    }
    manifest_bytes = json.dumps(
        manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    if len(payload) > _MAX_PAYLOAD or len(manifest_bytes) > _MAX_MANIFEST:
        raise PackageError("POI 앱 컨테이너가 허용 크기를 넘었습니다.")

    insertion = payload + manifest_bytes + _FOOTER.pack(
        len(payload), len(manifest_bytes), _APP_MAGIC)
    cookie = bytearray(stub[cookie_pos:])
    package_length = struct.unpack("!I", cookie[8:12])[0]
    new_length = package_length + len(insertion)
    if new_length > 0xFFFFFFFF:
        raise PackageError("완성 EXE가 4GB CArchive 한계를 넘습니다.")
    cookie[8:12] = struct.pack("!I", new_length)

    output_path = os.path.abspath(output_path)
    out_dir = os.path.dirname(output_path)
    os.makedirs(out_dir, exist_ok=True)
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(
                prefix=".poi-pack-", suffix=".tmp", dir=out_dir, delete=False) as f:
            temp_path = f.name
            f.write(stub[:cookie_pos])
            f.write(insertion)
            f.write(cookie)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp_path, output_path)
    except Exception:
        if temp_path:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
        raise
    manifest["file_sha256"] = _file_hash(output_path)
    manifest["size"] = os.path.getsize(output_path)
    return manifest


def _file_hash(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_package(path: str) -> tuple[types.CodeType, dict] | None:
    """EXE의 POI 앱을 검증해 읽는다. 일반 POI 실행 파일이면 None."""
    with open(path, "rb") as f:
        data = f.read()
    cookie_pos = _cookie_position(data)
    footer_pos = cookie_pos - _FOOTER.size
    if footer_pos < 0:
        return None
    payload_len, manifest_len, magic = _FOOTER.unpack(data[footer_pos:cookie_pos])
    if magic != _APP_MAGIC:
        return None
    if payload_len > _MAX_PAYLOAD or manifest_len > _MAX_MANIFEST:
        raise PackageError("POI 앱 컨테이너의 크기 정보가 안전 한계를 넘습니다.")
    start = footer_pos - manifest_len - payload_len
    if start < 0:
        raise PackageError("POI 앱 컨테이너 길이가 손상됐습니다.")
    payload = data[start:start + payload_len]
    manifest_bytes = data[start + payload_len:footer_pos]
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageError("POI 앱 메타데이터가 손상됐습니다.") from exc
    if not isinstance(manifest, dict):
        raise PackageError("POI 앱 메타데이터 형식이 잘못됐습니다.")
    if manifest.get("format") != "poi-exe" or manifest.get("format_version") != 1:
        raise PackageError("지원하지 않는 POI 앱 컨테이너 형식입니다.")
    if hashlib.sha256(payload).hexdigest() != manifest.get("payload_sha256"):
        raise PackageError("POI 앱 페이로드 무결성 검사가 실패했습니다.")
    decoder = zlib.decompressobj()
    try:
        raw = decoder.decompress(payload, _MAX_PAYLOAD + 1)
    except zlib.error as exc:
        raise PackageError("POI 앱 압축 데이터가 손상됐습니다.") from exc
    if (len(raw) > _MAX_PAYLOAD or not decoder.eof
            or decoder.unconsumed_tail or decoder.unused_data):
        raise PackageError("POI 앱 압축 데이터가 손상됐거나 안전 한계를 넘습니다.")
    if hashlib.sha256(raw).hexdigest() != manifest.get("code_sha256"):
        raise PackageError("POI 앱 코드 무결성 검사가 실패했습니다.")
    try:
        code = marshal.loads(raw)
    except Exception as exc:
        raise PackageError("POI 앱 바이트코드를 읽을 수 없습니다.") from exc
    if not isinstance(code, types.CodeType):
        raise PackageError("POI 앱 컨테이너에 실행 코드가 없습니다.")
    return code, manifest


def run_embedded_app() -> int | None:
    """현재 EXE에 앱이 있으면 실행하고, 일반 런처면 None을 돌려준다."""
    if not getattr(sys, "frozen", False):
        return None
    try:
        packaged = read_package(sys.executable)
    except (OSError, PackageError) as exc:
        print(f"POI 패키지 오류: {exc}", file=sys.stderr)
        return 1
    if packaged is None:
        return None
    code, manifest = packaged
    from .runtime import make_globals
    globals_ = make_globals()
    globals_["__name__"] = "__main__"
    globals_["__poi_dir__"] = os.path.dirname(os.path.abspath(sys.executable))
    globals_["__poi_file__"] = manifest.get("source_file") or manifest.get("name")
    globals_["__poi_source__"] = ""
    raw_linemap = manifest.get("linemap", {})
    try:
        linemap = {int(k): int(v) for k, v in raw_linemap.items()}
    except (AttributeError, TypeError, ValueError):
        print("POI 패키지 오류: 줄 정보가 손상됐습니다.", file=sys.stderr)
        return 1
    globals_["__poi_linemap__"] = linemap
    globals_["poi_argv"] = sys.argv[1:]
    try:
        exec(code, globals_)
        return 0
    except SystemExit as exc:
        return int(exc.code or 0) if isinstance(exc.code, (int, type(None))) else 1
    except Exception as exc:  # noqa: BLE001
        from .errors import translate_exception
        print(translate_exception(exc, "", linemap, "<poi app>").render(),
              file=sys.stderr)
        return 1

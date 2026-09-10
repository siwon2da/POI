from __future__ import annotations

import os
import struct
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest import mock

from poi import packager
from poi import build as poi_build
from poi import cli


def _stub_bytes() -> bytes:
    cookie = (
        packager._CARCHIVE_MAGIC
        + struct.pack("!IIII", 88, 0, 0, 313)
        + b"python313.dll".ljust(64, b"\0")
    )
    return b"MZ-POI-TEST-STUB" + cookie


class NativePackagerTests(unittest.TestCase):
    def test_package_round_trip_and_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = os.path.join(tmp, "poi.exe")
            output = os.path.join(tmp, "app.exe")
            with open(stub, "wb") as f:
                f.write(_stub_bytes())
            info = packager.package_executable(
                stub, output, compile("answer = 40 + 2", "<app>", "exec"),
                {"engine_version": "test", "name": "demo", "console": True})

            loaded = packager.read_package(output)
            self.assertIsNotNone(loaded)
            code, manifest = loaded
            scope = {}
            exec(code, scope)
            self.assertEqual(42, scope["answer"])
            self.assertEqual("demo", manifest["name"])
            self.assertEqual(info["file_sha256"], packager._file_hash(output))
            with open(output, "rb") as f:
                packaged_bytes = f.read()
            cookie_pos = packaged_bytes.rfind(packager._CARCHIVE_MAGIC)
            package_length = struct.unpack(
                "!I", packaged_bytes[cookie_pos + 8:cookie_pos + 12])[0]
            self.assertEqual(
                len(packaged_bytes) - len(b"MZ-POI-TEST-STUB"), package_length)

    def test_corrupt_payload_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = os.path.join(tmp, "poi.exe")
            output = os.path.join(tmp, "app.exe")
            with open(stub, "wb") as f:
                f.write(_stub_bytes())
            packager.package_executable(
                stub, output, compile("value = 1", "<app>", "exec"))
            with open(output, "rb") as f:
                data = bytearray(f.read())
            cookie_pos = data.rfind(packager._CARCHIVE_MAGIC)
            payload_len, manifest_len, _ = packager._FOOTER.unpack(
                data[cookie_pos - packager._FOOTER.size:cookie_pos])
            payload_start = cookie_pos - packager._FOOTER.size - manifest_len - payload_len
            data[payload_start] ^= 0x01
            with open(output, "wb") as f:
                f.write(data)
            with self.assertRaisesRegex(packager.PackageError, "무결성"):
                packager.read_package(output)

    def test_embedded_app_exit_code_is_forwarded(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = os.path.join(tmp, "poi.exe")
            output = os.path.join(tmp, "app.exe")
            with open(stub, "wb") as f:
                f.write(_stub_bytes())
            packager.package_executable(
                stub, output, compile("raise SystemExit(7)", "<app>", "exec"))
            with mock.patch.object(packager.sys, "frozen", True, create=True), \
                    mock.patch.object(packager.sys, "executable", output):
                self.assertEqual(7, packager.run_embedded_app())

    def test_frozen_build_uses_native_packager_without_pyinstaller(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = os.path.join(tmp, "poi.exe")
            source = os.path.join(tmp, "hello.poi")
            with open(stub, "wb") as f:
                f.write(_stub_bytes())
            with open(source, "w", encoding="utf-8") as f:
                f.write('show "hello"')
            previous = os.getcwd()
            try:
                os.chdir(tmp)
                with mock.patch.object(poi_build.sys, "frozen", True, create=True), \
                     mock.patch.object(poi_build.sys, "executable", stub):
                    rc = poi_build.build([source, "--console", "-o", "hello-app"])
            finally:
                os.chdir(previous)
            self.assertEqual(0, rc)
            packaged = packager.read_package(os.path.join(tmp, "dist", "hello-app.exe"))
            self.assertIsNotNone(packaged)

    def test_verify_command_checks_native_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = os.path.join(tmp, "poi.exe")
            output = os.path.join(tmp, "app.exe")
            with open(stub, "wb") as f:
                f.write(_stub_bytes())
            packager.package_executable(
                stub, output, compile("value = 1", "<app>", "exec"),
                {"name": "검증 앱", "engine_version": "test"})
            stdout = StringIO()
            with redirect_stdout(stdout):
                rc = cli.cmd_verify([output])
            self.assertEqual(0, rc)
            self.assertIn("무결성 검증 완료", stdout.getvalue())
            self.assertIn("검증 앱", stdout.getvalue())

    def test_native_build_rejects_windows_device_name_with_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = os.path.join(tmp, "poi.exe")
            source = os.path.join(tmp, "hello.poi")
            with open(stub, "wb") as f:
                f.write(_stub_bytes())
            with open(source, "w", encoding="utf-8") as f:
                f.write('show "hello"')
            with mock.patch.object(poi_build.sys, "frozen", True, create=True), \
                    mock.patch.object(poi_build.sys, "executable", stub):
                rc = poi_build.build([source, "--console", "-o", "CON.txt"])
            self.assertEqual(1, rc)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import os
import struct
import tempfile
import unittest

from poi import packager
from poi.protect import decompile_exe


def _stub_bytes() -> bytes:
    cookie = (packager._CARCHIVE_MAGIC
              + struct.pack("!IIII", 88, 0, 0, 313)
              + b"python313.dll".ljust(64, b"\0"))
    return b"MZ-POI-DECOMPILE-STUB" + cookie


class NativeDecompileTests(unittest.TestCase):
    def test_native_package_is_detected_without_dumping_stub_archive(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = os.path.join(tmp, "poi.exe")
            exe = os.path.join(tmp, "app.exe")
            out = os.path.join(tmp, "recovered")
            with open(stub, "wb") as f:
                f.write(_stub_bytes())
            packager.package_executable(
                stub, exe, compile("answer = 42", "<app>", "exec"),
                {"name": "demo", "mode": "compiled"})
            result = decompile_exe(exe, out)
            self.assertTrue(result["native"])
            self.assertEqual(1, result["entries"])
            self.assertEqual(2, len(result["files"]))
            self.assertTrue(os.path.isfile(os.path.join(out, "_poi_app.bytecode.txt")))
            with open(os.path.join(out, "poi-package.json"), encoding="utf-8") as f:
                self.assertEqual("demo", json.load(f)["name"])

    def test_protected_native_package_only_exports_metadata(self):
        with tempfile.TemporaryDirectory() as tmp:
            stub = os.path.join(tmp, "poi.exe")
            exe = os.path.join(tmp, "app.exe")
            out = os.path.join(tmp, "recovered")
            with open(stub, "wb") as f:
                f.write(_stub_bytes())
            packager.package_executable(
                stub, exe, compile("answer = 42", "<app>", "exec"),
                {"mode": "obfuscated"})
            result = decompile_exe(exe, out)
            self.assertEqual(1, len(result["files"]))
            self.assertFalse(os.path.exists(os.path.join(out, "_poi_app.bytecode.txt")))


if __name__ == "__main__":
    unittest.main()

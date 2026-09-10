from __future__ import annotations

import io
import os
import tempfile
import unittest
import zipfile

from poi.ecosystem import _extract_package


def _zip(entries: dict[str, bytes]) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return out.getvalue()


class RegistryExtractionTests(unittest.TestCase):
    def test_zip_path_traversal_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "밖으로"):
                _extract_package(_zip({"../escaped.poi": b"show 1"}),
                                 "https://example.test/pkg.zip", tmp, "demo")
            self.assertFalse(os.path.exists(os.path.join(tmp, "..", "escaped.poi")))

    def test_single_archive_root_is_stripped_safely(self):
        with tempfile.TemporaryDirectory() as tmp:
            _extract_package(_zip({"demo-1.0/main.poi": b"show 1"}),
                             "https://example.test/pkg.zip", tmp, "demo")
            self.assertTrue(os.path.isfile(os.path.join(tmp, "main.poi")))


if __name__ == "__main__":
    unittest.main()

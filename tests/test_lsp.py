import io
import types
import unittest
from unittest.mock import patch

from poi import lsp
from poi.lsp import _diagnostics, _line_range


class LspTests(unittest.TestCase):
    def test_line_range_stays_inside_real_line(self):
        self.assertEqual(
            _line_range("  show 1\n", 0),
            {"start": {"line": 0, "character": 2},
             "end": {"line": 0, "character": 8}},
        )

    def test_type_diagnostic_range_is_not_magic_200_columns(self):
        source = "x: Int = \"text\"\n"
        diagnostics = _diagnostics(source)
        self.assertTrue(diagnostics)
        for item in diagnostics:
            line = source.splitlines()[item["range"]["end"]["line"]]
            self.assertLessEqual(item["range"]["end"]["character"], len(line))

    def test_bad_json_message_does_not_look_like_end_of_stream(self):
        raw = b"Content-Length: 1\r\n\r\n{" \
              b"Content-Length: 2\r\n\r\n{}"
        fake_stdin = types.SimpleNamespace(buffer=io.BytesIO(raw))
        with patch.object(lsp.sys, "stdin", fake_stdin):
            self.assertIs(lsp._read_msg(), lsp._INVALID)
            self.assertEqual(lsp._read_msg(), {})

    def test_bad_content_length_is_recoverable(self):
        fake_stdin = types.SimpleNamespace(
            buffer=io.BytesIO(b"Content-Length: nope\r\n\r\n"))
        with patch.object(lsp.sys, "stdin", fake_stdin):
            self.assertIs(lsp._read_msg(), lsp._INVALID)


if __name__ == "__main__":
    unittest.main()

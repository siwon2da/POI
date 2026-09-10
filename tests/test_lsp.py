import unittest

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


if __name__ == "__main__":
    unittest.main()

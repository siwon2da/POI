import unittest

from poi.apps.haon import autofix


class HaonAutofixTests(unittest.TestCase):
    def test_unfixable_error_keeps_original_source(self):
        source = "fn f(x, x) { return x }\n"
        fixed, log = autofix(source)
        self.assertEqual(fixed, source)
        self.assertTrue(any("자동으로 못 고친" in line for line in log))

    def test_fixable_foreign_syntax_changes_source(self):
        source = "def hello() { show True }\n"
        fixed, log = autofix(source)
        self.assertNotEqual(fixed, source)
        self.assertIn("fn hello", fixed)
        self.assertIn("true", fixed)
        self.assertTrue(log)


if __name__ == "__main__":
    unittest.main()

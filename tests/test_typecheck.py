from __future__ import annotations

import unittest

from poi.lexer import Lexer
from poi.parser import Parser
from poi import typecheck


def _codes(source: str) -> list[str]:
    tokens = Lexer(source, "<typecheck-test>").tokenize()
    program = Parser(tokens, source, "<typecheck-test>").parse()
    return [finding.code for finding in typecheck.check(program)]


class AssertTypeTests(unittest.TestCase):
    def test_valid_assert_types(self):
        self.assertEqual([], _codes('assert 2 + 2 == 4, "덧셈 실패"'))

    def test_assert_condition_must_be_bool(self):
        self.assertIn("P406", _codes('assert 123, "숫자는 조건이 아님"'))

    def test_assert_message_must_be_text(self):
        self.assertIn("P407", _codes("assert true, 123"))


class ConditionTypeTests(unittest.TestCase):
    def test_valid_boolean_conditions(self):
        source = """if 1 < 2 { show \"ok\" }
while false { show \"never\" }
값 = \"예\" if true else \"아니오\"
"""
        self.assertNotIn("P408", _codes(source))

    def test_if_condition_must_be_bool(self):
        self.assertIn("P408", _codes('if 123 { show "잘못된 조건" }'))

    def test_while_condition_must_be_bool(self):
        self.assertIn("P408", _codes('while "계속" { pass }'))

    def test_ternary_condition_must_be_bool(self):
        self.assertIn("P408", _codes('값 = "예" if 1 else "아니오"'))


class FunctionCallTypeTests(unittest.TestCase):
    def test_default_and_named_arguments_are_accepted(self):
        source = 'fn greet(name: Text, count: Int = 1) { show name }\ngreet(count: 2, name: "POI")'
        self.assertEqual([], _codes(source))

    def test_missing_required_argument(self):
        source = 'fn add(a: Int, b: Int) -> Int => a + b\nshow add(1)'
        self.assertIn("P409", _codes(source))

    def test_named_argument_type_is_checked(self):
        source = 'fn greet(name: Text) { show name }\ngreet(name: 123)'
        self.assertIn("P403", _codes(source))

    def test_unknown_named_argument(self):
        source = 'fn greet(name: Text) { show name }\ngreet(who: "POI")'
        self.assertIn("P410", _codes(source))

    def test_duplicate_argument(self):
        source = 'fn greet(name: Text) { show name }\ngreet("POI", name: "again")'
        self.assertIn("P411", _codes(source))


if __name__ == "__main__":
    unittest.main()

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


if __name__ == "__main__":
    unittest.main()

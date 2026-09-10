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


if __name__ == "__main__":
    unittest.main()

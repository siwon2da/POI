from __future__ import annotations

import unittest

from poi.errors import POIError
from poi.lexer import Lexer
from poi.parser import Parser


def _parse(source: str):
    tokens = Lexer(source, "<parser-test>").tokenize()
    return Parser(tokens, source, "<parser-test>").parse()


class FunctionParameterTests(unittest.TestCase):
    def test_required_parameter_cannot_follow_default(self):
        with self.assertRaises(POIError) as caught:
            _parse("fn greet(greeting = \"안녕\", name) { show name }")
        self.assertEqual("P023", caught.exception.code)
        self.assertEqual(1, caught.exception.line)
        self.assertIn("name", caught.exception.hint)

    def test_required_parameters_before_defaults_are_valid(self):
        program = _parse("fn greet(name, greeting = \"안녕\") { show name }")
        self.assertEqual("FnDecl", program.body[0].kind)


if __name__ == "__main__":
    unittest.main()

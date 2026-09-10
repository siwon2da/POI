from __future__ import annotations

import os
import unittest

from poi.errors import POIError
from poi.interpreter import compile_source, run_source
from poi.playground import _isolated_env


class SafeModeTests(unittest.TestCase):
    def test_internal_member_is_rejected_before_execution(self):
        with self.assertRaises(POIError) as caught:
            compile_source('show "x".__class__', "unsafe.poi", safe=True)
        self.assertEqual("P213", caught.exception.code)

    def test_dynamic_internal_member_is_rejected_at_runtime(self):
        rc = run_source('show poi_getattr("x", "__class__")', safe=True)
        self.assertEqual(1, rc)

    def test_playground_environment_does_not_forward_secrets(self):
        os.environ["POI_TEST_SECRET"] = "must-not-leak"
        try:
            env = _isolated_env()
        finally:
            os.environ.pop("POI_TEST_SECRET", None)
        self.assertNotIn("POI_TEST_SECRET", env)
        self.assertEqual("1", env["POI_SAFE_MODE"])


if __name__ == "__main__":
    unittest.main()

import os
import tempfile
import unittest

from poi.interpreter import run_file


class MultiFileSafeTests(unittest.TestCase):
    def test_relative_poi_module_runs_in_safe_mode(self):
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "lib.poi"), "w", encoding="utf-8") as f:
                f.write('함수 두배(x: Int) -> Int { 반환 x * 2 }\n')
            main = os.path.join(d, "main.poi")
            with open(main, "w", encoding="utf-8") as f:
                f.write('use "./lib.poi" as lib\n보여주기 lib.두배(21)\n')
            self.assertEqual(run_file(main, safe=True), 0)


if __name__ == "__main__":
    unittest.main()

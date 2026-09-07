"""POI 회귀 테스트.

tests/cases/*.poi 를 실행해 tests/cases/*.out 과 stdout 을 비교한다.
*.err 파일이 있으면 그 문자열이 stderr 에 포함돼야 한다(오류 테스트).
"""
from __future__ import annotations

import io
import os
import sys
from contextlib import redirect_stderr, redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from poi.interpreter import run_source  # noqa: E402

CASES = os.path.join(HERE, "cases")


def run_one(poi_path: str):
    with open(poi_path, "r", encoding="utf-8") as f:
        src = f.read()
    out_buf, err_buf = io.StringIO(), io.StringIO()
    with redirect_stdout(out_buf), redirect_stderr(err_buf):
        rc = run_source(src, os.path.basename(poi_path))
    return rc, out_buf.getvalue(), err_buf.getvalue()


def main() -> int:
    cases = sorted(f for f in os.listdir(CASES) if f.endswith(".poi"))
    passed = failed = 0
    for name in cases:
        base = name[:-4]
        poi_path = os.path.join(CASES, name)
        out_path = os.path.join(CASES, base + ".out")
        err_path = os.path.join(CASES, base + ".err")
        rc, out, err = run_one(poi_path)

        ok = True
        detail = ""
        if os.path.exists(err_path):
            with open(err_path, encoding="utf-8") as f:
                needle = f.read().strip()
            if needle not in err:
                ok = False
                detail = f"stderr 에 {needle!r} 없음\n--- stderr ---\n{err}"
        elif os.path.exists(out_path):
            with open(out_path, encoding="utf-8") as f:
                expect = f.read()
            if out != expect:
                ok = False
                detail = f"--- 기대 ---\n{expect}\n--- 실제 ---\n{out}\n--- stderr ---\n{err}"
        else:
            if rc != 0:
                ok = False
                detail = f"rc={rc}\n{err}"

        if ok:
            passed += 1
            print(f"  ok   {name}")
        else:
            failed += 1
            print(f"  FAIL {name}\n{detail}")

    print(f"\n{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

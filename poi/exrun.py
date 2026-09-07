"""연습문제 300제 실행·채점 (v1.2).

    poi exercises                # 전체 실행, 통과/실패 요약
    poi exercises 042            # 한 문제만
    poi exercises --topic 반복    # 주제별
    poi exercises --show 042     # 문제 코드와 정답 보기
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from contextlib import redirect_stdout, redirect_stderr

_HERE = os.path.dirname(os.path.abspath(__file__))
_EX = os.path.join(os.path.dirname(_HERE), "exercises")


def _load_manifest() -> list[dict]:
    mf = os.path.join(_EX, "manifest.json")
    if not os.path.isfile(mf):
        print("연습문제 폴더를 찾을 수 없습니다 (exercises/).")
        print("저장소를 받아서 실행하세요:  git clone https://github.com/siwon2da/POI.git")
        raise SystemExit(2)
    with open(mf, encoding="utf-8") as f:
        return json.load(f)["problems"]


def _run_one(name: str) -> tuple[bool, str, str, float]:
    from .interpreter import run_source
    poi_path = os.path.join(_EX, name + ".poi")
    out_path = os.path.join(_EX, name + ".out")
    with open(poi_path, encoding="utf-8") as f:
        src = f.read()
    with open(out_path, encoding="utf-8") as f:
        expected = f.read()
    buf, err = io.StringIO(), io.StringIO()
    t0 = time.perf_counter()
    with redirect_stdout(buf), redirect_stderr(err):
        rc = run_source(src, name + ".poi")
    dt = (time.perf_counter() - t0) * 1000
    got = buf.getvalue()
    ok = (rc == 0) and (got == expected)
    detail = ""
    if not ok:
        detail = (f"    기대:\n{_indent(expected)}\n    실제:\n{_indent(got)}"
                  f"\n    (rc={rc}) {err.getvalue().strip()}")
    return ok, name, detail, dt


def _indent(s: str) -> str:
    return "\n".join("      " + ln for ln in s.splitlines()) or "      (없음)"


def main(argv: list[str]) -> int:
    problems = _load_manifest()

    topic = None
    show_id = None
    only = []
    it = iter(argv)
    for a in it:
        if a == "--topic":
            topic = next(it, None)
        elif a == "--show":
            show_id = next(it, None)
        elif a.lstrip("0").isdigit() or (a.isdigit()):
            only.append(int(a))

    if show_id is not None:
        want = int(show_id)
        p = next((x for x in problems if x["id"] == want), None)
        if not p:
            print(f"{want}번 문제가 없습니다.")
            return 1
        print(f"[{p['id']:03d}] {p['title']}  ({p['topic']}, 난이도 {p['difficulty']})\n")
        print("── 코드 " + "─" * 32)
        print(open(os.path.join(_EX, p["name"] + ".poi"), encoding="utf-8").read())
        print("── 정답 출력 " + "─" * 27)
        print(open(os.path.join(_EX, p["name"] + ".out"), encoding="utf-8").read())
        return 0

    sel = problems
    if topic:
        sel = [p for p in sel if topic in p["topic"]]
    if only:
        sel = [p for p in sel if p["id"] in only]

    passed = failed = 0
    slow = []
    fails = []
    for p in sel:
        ok, name, detail, dt = _run_one(p["name"])
        if dt > 60:
            slow.append((name, dt))
        if ok:
            passed += 1
        else:
            failed += 1
            fails.append((p, detail))

    for p, detail in fails:
        print(f"  실패 [{p['id']:03d}] {p['title']}")
        print(detail)
    print()
    print(f"연습문제 {passed + failed}개 중  통과 {passed} · 실패 {failed}")
    if slow:
        print(f"  (느린 문제 {len(slow)}개: " +
              ", ".join(f"{n} {d:.0f}ms" for n, d in slow[:5]) + ")")
    return 1 if failed else 0

"""POI 연습문제 300제 생성기.

    python exercises/gen.py

각 문제의 정답 출력은 POI 레퍼런스 구현으로 직접 실행해서 뽑는다.
= 300개의 실행 회귀 테스트. `poi exercises` 로 다시 돌려 검증한다.
"""
from __future__ import annotations

import io
import json
import os
import sys
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from poi.interpreter import compile_source  # noqa: E402
from poi.runtime import make_globals  # noqa: E402


def run(code: str) -> str:
    py, _lm, name = compile_source(code, "<gen>")
    g = make_globals()
    g["__name__"] = "__main__"
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(compile(py, name, "exec"), g)
    return buf.getvalue()


# ── 문제 밴드들 ──────────────────────────────────────────────────────
# 각 함수는 (제목, 난이도, 코드) 리스트를 돌려준다.

def band_output():
    out = []
    greetings = ["안녕하세요", "Hello", "POI 입니다", "반갑습니다", "오늘도 화이팅"]
    for i, g in enumerate(greetings):
        out.append((f'"{g}" 출력하기', 1, f'show "{g}"'))
    for n in [0, 7, 42, 100, 2026, -5, 3.14, 1000000]:
        out.append((f"숫자 {n} 출력하기", 1, f"show {n}"))
    for a, b in [(1, 2), (10, 20), (3, 4, 5)] if False else [(1, 2), (10, 20)]:
        out.append((f"{a} 와 {b} 한 줄에 출력", 1, f'show "{a} {b}"'))
    out.append(("여러 줄 출력", 1, 'show "첫째 줄"\nshow "둘째 줄"\nshow "셋째 줄"'))
    out.append(("빈 값과 참/거짓 출력", 1, "show true\nshow false\nshow null"))
    out.append(("이름표 붙여 출력", 1, 'name = "시원"\nshow "이름: {name}"'))
    for w in ["별", "달", "해", "구름", "바다", "산", "강", "숲", "빛", "밤"]:
        out.append((f'"{w}" 세 번 출력', 1,
                    f'repeat 3 {{\n    show "{w}"\n}}'))
    for x in [11, 22, 33, 44, 55, 66]:
        out.append((f"{x} 두 배 출력", 1, f"show {x} * 2"))
    return out


def band_arith():
    out = []
    pairs = [(3, 4), (10, 5), (7, 2), (100, 7), (15, 4), (9, 3), (8, 8),
             (12, 5), (20, 6), (2, 10)]
    for a, b in pairs:
        out.append((f"{a} + {b}", 1, f"show {a} + {b}"))
        out.append((f"{a} - {b}", 1, f"show {a} - {b}"))
        out.append((f"{a} × {b}", 1, f"show {a} * {b}"))
        out.append((f"{a} ÷ {b}", 2, f"show {a} / {b}"))
    for a, b in pairs[:6]:
        out.append((f"{a} 를 {b} 로 나눈 나머지", 2, f"show {a} % {b}"))
    out.append(("연산자 우선순위 2 + 3 * 4", 2, "show 2 + 3 * 4"))
    out.append(("괄호 (2 + 3) * 4", 2, "show (2 + 3) * 4"))
    out.append(("음수 다루기", 2, "show -5 + 3\nshow -(4 - 9)"))
    out.append(("실수 계산", 2, "show 0.1 + 0.2\nshow 3.0 * 2"))
    out.append(("사각형 넓이", 2, "w = 6\nh = 4\nshow w * h"))
    out.append(("평균 구하기", 2, "a = 80\nb = 90\nc = 100\nshow (a + b + c) / 3"))
    out.append(("초를 분·초로", 3, "t = 200\nshow t / 60\nshow t % 60"))
    out.append(("math.sqrt", 2, "show math.sqrt(144)"))
    out.append(("math.floor / ceil", 2, "show math.floor(3.7)\nshow math.ceil(3.2)"))
    out.append(("math.pi 반올림", 2, "show math.round(math.pi, 2)"))
    out.append(("거듭제곱", 2, "show 2 * 2 * 2 * 2"))
    out.append(("복리 한 해", 3, "money = 10000\nshow money + money * 0.03"))
    return out


def band_strings():
    out = []
    words = ["POI", "Imagination", "안녕", "코딩", "Language", "hello world",
             "Power", "우주", "python", "banana"]
    for w in words:
        out.append((f'"{w}" 길이', 1, f'show "{w}".length'))
        out.append((f'"{w}" 대문자', 1, f'show "{w}".upper()'))
        out.append((f'"{w}" 소문자', 1, f'show "{w}".lower()'))
        out.append((f'"{w}" 뒤집기', 2, f'show "{w}".reverse()'))
    out.append(('"O" 가 들어있나', 2, 'show "POI".contains("O")'))
    out.append(('"z" 가 들어있나', 2, 'show "POI".contains("z")'))
    out.append(("이름 인사", 1, 'name = "예성"\nshow "{name}님 안녕하세요"'))
    out.append(("문장 나누기", 2, 'show "a b c d".words()'))
    out.append(("두 문자열 잇기", 1, 'a = "안녕"\nb = "세상"\nshow a + " " + b'))
    out.append(("이름 길이로 판단", 2,
                'name = "가"\nshow "짧다" if name.length < 2 else "괜찮다"'))
    out.append(("여러 번 반복 출력", 2, 's = "야! "\nrepeat 3 { show s }'))
    out.append(("시작/끝 확인", 2,
                'w = "hello.poi"\nshow w.ends_with(".poi")\nshow w.starts_with("hello")'))
    out.append(("공백 제거", 2, 'show "  가운데  ".trim()'))
    out.append(("문자열 비었나", 2, 'show "".is_empty\nshow "x".is_empty'))
    return out


def band_cond():
    out = []
    for n in [3, 10, 17, 0, -4, 88, 21, 19, 20, 100]:
        out.append((f"{n} 양수/음수/0", 1,
                    f'x = {n}\nif x > 0 {{ show "양수" }} else if x < 0 {{ show "음수" }} '
                    f'else {{ show "영" }}'))
    for a in [15, 18, 19, 20, 7, 13, 64, 30, 22, 11]:
        out.append((f"{a}세 10대인가", 2,
                    f'age = {a}\nif age between 10 and 19 {{ show "10대" }} '
                    f'else {{ show "아님" }}'))
    for a, b in [(3, 5), (9, 2), (7, 7), (0, 1), (100, 100)]:
        out.append((f"{a} 와 {b} 중 큰 값", 2,
                    f'a = {a}\nb = {b}\nshow a if a >= b else b'))
    for n in [2, 3, 4, 12, 15, 16, 17, 18, 20, 25]:
        out.append((f"{n} 짝/홀", 1,
                    f'if {n} % 2 is 0 {{ show "짝수" }} else {{ show "홀수" }}'))
    out.append(("and / or", 2,
               'x = 7\nif x > 0 and x < 10 { show "한 자리 양수" }'))
    out.append(("not", 2, 'done = false\nif not done { show "아직 안 끝남" }'))
    out.append(("등급 매기기", 3,
               'score = 85\nif score >= 90 { show "A" } else if score >= 80 { show "B" } '
               'else { show "C" }'))
    out.append(("윤년 판단", 3,
               'y = 2024\nif y % 4 is 0 and y % 100 is not 0 { show "윤년" } '
               'else { show "평년" }'))
    out.append(("연쇄 비교", 2, 'x = 5\nshow 1 < x and x < 10'))
    out.append(("is 로 문자 비교", 1, 'name = "시원"\nif name is "시원" { show "어서와" }'))
    return out


def band_loops():
    out = []
    for n in [3, 5, 7, 10]:
        out.append((f"1부터 {n} 까지 출력", 1,
                    f"repeat {n} as i {{\n    show i + 1\n}}"))
    for n in [5, 10, 20, 100]:
        out.append((f"1부터 {n} 까지 합", 2,
                    f"total = 0\nrepeat {n} as i {{\n    total = total + i + 1\n}}\n"
                    f"show total"))
    for xs in [[1, 2, 3], [10, 20, 30, 40], [5, 5, 5], [7], [2, 4, 6, 8, 10]]:
        out.append((f"목록 {xs} 원소 출력", 1,
                    f"for x in {xs} {{\n    show x\n}}"))
        out.append((f"목록 {xs} 합", 2,
                    f"s = 0\nfor x in {xs} {{\n    s = s + x\n}}\nshow s"))
    for xs in [[3, 1, 4, 1, 5], [9, 2, 6], [10, 10, 1]]:
        out.append((f"목록 {xs} 최댓값", 3,
                    f"best = {xs}[0]\nfor x in {xs} {{\n    if x > best {{ best = x }}\n}}\n"
                    f"show best"))
    for n in [3, 4, 5]:
        out.append((f"{n}×{n} 곱셈 구구단 한 줄", 3,
                    f"repeat {n} as a {{\n    line = \"\"\n    repeat {n} as b {{\n"
                    f"        line = line + text((a+1)*(b+1)) + \" \"\n    }}\n"
                    f"    show line.trim()\n}}"))
    for w in ["star", "moon", "sun"]:
        out.append((f'"{w}" 별표처럼 쌓기', 2,
                    f'repeat 4 as i {{\n    row = ""\n    repeat i + 1 {{ row = row + "*" }}\n'
                    f'    show row\n}}'))
    for n in [10, 15, 20]:
        out.append((f"{n} 까지 짝수만", 2,
                    f"repeat {n} as i {{\n    if (i + 1) % 2 is 0 {{ show i + 1 }}\n}}"))
    out.append(("카운트다운", 2, 'repeat 5 as i {\n    show 5 - i\n}\nshow "발사!"'))
    out.append(("리스트 평균", 3,
               'xs = [80, 90, 100, 70]\ns = 0\nfor x in xs { s = s + x }\n'
               'show s / xs.length'))
    return out


def band_funcs():
    out = []
    out.append(("두 수 더하기 함수", 1,
               "fn add(a, b) {\n    return a + b\n}\nshow add(3, 4)"))
    out.append(("두 배 함수 (한 줄)", 1, "fn double(x) => x * 2\nshow double(21)"))
    out.append(("제곱 함수", 1, "fn sq(x) => x * x\nshow sq(9)"))
    out.append(("인사 함수 (기본값)", 2,
               'fn greet(name, msg = "안녕") {\n    return msg + ", " + name\n}\n'
               'show greet("시원")\nshow greet("예성", "반가워")'))
    out.append(("세 수 중 최대", 2,
               "fn max3(a, b, c) {\n    m = a\n    if b > m { m = b }\n    if c > m { m = c }\n"
               "    return m\n}\nshow max3(3, 9, 5)"))
    out.append(("팩토리얼", 3,
               "fn fact(n) {\n    r = 1\n    repeat n as i {\n        r = r * (i + 1)\n    }\n"
               "    return r\n}\nshow fact(5)"))
    out.append(("절댓값", 2, "fn myabs(x) => x if x >= 0 else -x\nshow myabs(-7)\nshow myabs(4)"))
    out.append(("섭씨→화씨", 2,
               "fn to_f(c) => c * 9 / 5 + 32\nshow to_f(0)\nshow to_f(100)"))
    out.append(("원 넓이", 2, "fn area(r) => math.round(math.pi * r * r, 2)\nshow area(3)"))
    out.append(("짝수 개수 세기", 3,
               "fn count_even(xs) {\n    n = 0\n    for x in xs {\n        if x % 2 is 0 { n = n + 1 }\n"
               "    }\n    return n\n}\nshow count_even([1, 2, 3, 4, 5, 6])"))
    out.append(("합계 함수", 2,
               "fn total(xs) {\n    s = 0\n    for x in xs { s = s + x }\n    return s\n}\n"
               "show total([10, 20, 30])"))
    out.append(("n번째 홀수", 2, "fn odd(n) => n * 2 - 1\nshow odd(1)\nshow odd(5)"))
    out.append(("문자열 n번 반복", 2,
               'fn repeatstr(s, n) {\n    r = ""\n    repeat n { r = r + s }\n    return r\n}\n'
               'show repeatstr("ab", 3)'))
    out.append(("최소값 함수", 2,
               "fn least(xs) {\n    m = xs[0]\n    for x in xs { if x < m { m = x } }\n    return m\n}\n"
               "show least([5, 2, 8, 1, 9])"))
    out.append(("BMI 계산", 3,
               "fn bmi(w, h) => math.round(w / (h * h), 1)\nshow bmi(64, 1.72)"))
    return out


def band_arrays():
    out = []
    lists = [[3, 1, 2], [9, 7, 5, 3, 1], [4], [10, 10, 20], [8, 6, 7, 5, 3, 0, 9]]
    for xs in lists:
        out.append((f"{xs} 길이", 1, f"show {xs}.length"))
        out.append((f"{xs} 첫·끝", 1, f"show {xs}.first\nshow {xs}.last"))
        out.append((f"{xs} 정렬해서 잇기", 2, f'show {xs}.sort().join("-")'))
    out.append(("원소 추가", 1, "xs = [1, 2, 3]\nxs.add(4)\nshow xs.length\nshow xs.last"))
    out.append(("포함 확인", 2, "xs = [2, 4, 6]\nshow xs.contains(4)\nshow xs.contains(5)"))
    out.append(("역순", 2, "show [1, 2, 3, 4].reverse()"))
    out.append(("짝수만 골라 담기", 3,
               "xs = [1, 2, 3, 4, 5, 6]\neven = []\nfor x in xs {\n    if x % 2 is 0 { even.add(x) }\n}\n"
               "show even.join(\", \")"))
    out.append(("두 배로 만든 새 목록", 3,
               "xs = [1, 2, 3]\ndbl = []\nfor x in xs { dbl.add(x * 2) }\nshow dbl.join(\" \")"))
    out.append(("이름 목록 인사", 2,
               'names = ["시원", "예성", "민수"]\nfor n in names {\n    show "{n}님 환영합니다"\n}'))
    out.append(("합과 평균", 2,
               "xs = [10, 20, 30, 40]\ns = 0\nfor x in xs { s = s + x }\n"
               "show s\nshow s / xs.length"))
    out.append(("가장 긴 단어", 3,
               'ws = ["a", "bbb", "cc", "dddd"]\nbest = ws[0]\nfor w in ws {\n'
               '    if w.length > best.length { best = w }\n}\nshow best'))
    return out


def band_objects():
    out = []
    out.append(("사용자 만들고 읽기", 1,
               'u = { name: "시원", age: 16 }\nshow u.name\nshow u.age'))
    out.append(("관리자 여부", 1,
               'u = { name: "시원", admin: true }\nshow u.admin'))
    out.append(("없는 값은 기본값", 2,
               'u = { name: "시원" }\nshow u?.nick ?? "별명없음"'))
    out.append(("값 바꾸기", 2,
               'u = { name: "시원", age: 16 }\nu.age = 17\nshow u.age'))
    out.append(("항목 개수", 2, 'u = { a: 1, b: 2, c: 3 }\nshow u.length'))
    out.append(("키가 있나", 2, 'u = { name: "x" }\nshow u.has("name")\nshow u.has("age")'))
    out.append(("중첩 객체", 2,
               'u = { name: "시원", pet: { kind: "고양이", age: 2 } }\nshow u.pet.kind'))
    out.append(("객체 목록 순회", 2,
               'people = [{ name: "시원", age: 16 }, { name: "예성", age: 17 }]\n'
               'for p in people {\n    show "{p.name} ({p.age})"\n}'))
    out.append(("나이 합", 3,
               'people = [{ age: 16 }, { age: 17 }, { age: 15 }]\ns = 0\n'
               'for p in people { s = s + p.age }\nshow s'))
    out.append(("성인만 세기", 3,
               'people = [{ age: 20 }, { age: 15 }, { age: 33 }, { age: 12 }]\nn = 0\n'
               'for p in people {\n    if p.age >= 18 { n = n + 1 }\n}\nshow n'))
    out.append(("키 목록 / 값 목록", 2,
               'u = { x: 1, y: 2 }\nshow u.keys()\nshow u.values()'))
    out.append(("장바구니 총액", 3,
               'cart = [{ price: 1200 }, { price: 3400 }, { price: 900 }]\ntotal = 0\n'
               'for item in cart { total = total + item.price }\nshow total'))
    return out


def band_capstone():
    out = []
    out.append(("FizzBuzz (1~20)", 3,
               'repeat 20 as i {\n    n = i + 1\n    if n % 15 is 0 { show "FizzBuzz" }\n'
               '    else if n % 3 is 0 { show "Fizz" }\n    else if n % 5 is 0 { show "Buzz" }\n'
               '    else { show n }\n}'))
    out.append(("피보나치 10개", 3,
               'a = 0\nb = 1\nrepeat 10 {\n    show a\n    next = a + b\n    a = b\n    b = next\n}'))
    out.append(("문자열 뒤집기 (직접)", 3,
               's = "imagination"\nr = ""\nrepeat s.length as i {\n'
               '    r = r + s[s.length - 1 - i]\n}\nshow r'))
    out.append(("모음 개수 세기", 3,
               's = "power of imagination"\nn = 0\nrepeat s.length as i {\n'
               '    c = s[i]\n    if c is "a" or c is "e" or c is "i" or c is "o" or c is "u" '
               '{ n = n + 1 }\n}\nshow n'))
    out.append(("회문 판별", 3,
               's = "level"\nrev = ""\nrepeat s.length as i { rev = rev + s[s.length - 1 - i] }\n'
               'if s is rev { show "회문" } else { show "아님" }'))
    out.append(("최대공약수 (반복)", 3,
               'a = 48\nb = 18\nrepeat 100 {\n    if b is not 0 {\n        t = a % b\n'
               '        a = b\n        b = t\n    }\n}\nshow a'))
    out.append(("100 이하 소수 개수", 3,
               'count = 0\nrepeat 99 as k {\n    n = k + 2\n    isp = true\n    d = 2\n'
               '    repeat n {\n        if d < n and n % d is 0 { isp = false }\n        d = d + 1\n'
               '    }\n    if isp { count = count + 1 }\n}\nshow count'))
    out.append(("세 자리 수 자릿수 합", 3,
               'n = 476\nh = math.floor(n / 100)\nt = math.floor((n % 100) / 10)\n'
               'o = n % 10\nshow h + t + o'))
    out.append(("구구단 7단", 2,
               'repeat 9 as i {\n    show "7 x {i + 1} = " + text(7 * (i + 1))\n}'))
    out.append(("온도 변환표", 3,
               'repeat 6 as i {\n    c = i * 20\n    f = c * 9 / 5 + 32\n    show "{c}C = {f}F"\n}'))
    return out


BANDS = [
    band_output, band_arith, band_strings, band_cond, band_loops,
    band_funcs, band_arrays, band_objects, band_capstone,
]
BAND_TOPIC = {
    "band_output": "출력", "band_arith": "산술", "band_strings": "문자열",
    "band_cond": "조건", "band_loops": "반복", "band_funcs": "함수",
    "band_arrays": "배열", "band_objects": "객체", "band_capstone": "종합",
}


def slug(title: str, i: int) -> str:
    keep = []
    for ch in title.lower():
        if ch.isalnum():
            keep.append(ch)
        elif ch in " -_":
            keep.append("_")
    s = "".join(keep).strip("_")[:32] or "problem"
    return f"{i:03d}_{s}"


def main() -> int:
    problems = []
    for band in BANDS:
        topic = BAND_TOPIC[band.__name__]
        for title, diff, code in band():
            problems.append((topic, title, diff, code))

    # 300 으로 맞추기: 부족하면 산술 드릴로 채운다
    filler = 2
    while len(problems) < 300:
        a, b = filler * 3 + 1, filler + 2
        problems.append(("산술", f"{a} + {b} × 2 계산", 1,
                         f"show {a} + {b} * 2"))
        filler += 1
    problems = problems[:300]

    manifest = []
    made = skipped = 0
    for idx, (topic, title, diff, code) in enumerate(problems, 1):
        name = slug(title, idx)
        try:
            expected = run(code)
        except Exception as e:  # noqa: BLE001
            print(f"  건너뜀 {name}: {e}")
            skipped += 1
            continue
        with open(os.path.join(HERE, name + ".poi"), "w", encoding="utf-8",
                  newline="\n") as f:
            f.write(code.rstrip("\n") + "\n")
        with open(os.path.join(HERE, name + ".out"), "w", encoding="utf-8",
                  newline="\n") as f:
            f.write(expected)
        manifest.append({"id": idx, "name": name, "topic": topic,
                         "title": title, "difficulty": diff})
        made += 1

    with open(os.path.join(HERE, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"count": made, "problems": manifest}, f,
                  ensure_ascii=False, indent=1)
    print(f"\n생성 {made}개, 건너뜀 {skipped}개  →  exercises/manifest.json")
    return 0 if skipped == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

# POI

**Python Powered, Human First** — 파이썬 생태계를 그대로 쓰면서 문법·GUI·자동화는 훨씬 간단한 언어.

```poi
name = ask "이름: "

if name.length >= 2 {
    show "안녕하세요 {name}님"
} else {
    show "이름이 너무 짧습니다"
}
```

POI 코드는 → POI 파서 → POI AST → **파이썬 소스로 트랜스파일** → CPython 에서 실행.
그래서 `numpy` `pandas` `requests` `torch` 같은 파이썬 라이브러리를 그대로 쓸 수 있다.

---

## 30초 시작

설치 없이:

```bash
python -m poi run examples/hello.poi
# 또는 Windows
poi.cmd run examples\hello.poi
```

설치해서 쓰기:

```bash
pip install -e .
poi run examples/basics.poi
```

## 명령어

| 명령 | 하는 일 |
|---|---|
| `poi run [파일.poi]` | 실행 (기본: `src/main.poi` → `main.poi`) |
| `poi run 파일.poi --emit-python` | 트랜스파일된 파이썬 코드만 출력 |
| `poi new <이름>` | 새 프로젝트 폴더 생성 |
| `poi check <파일.poi>` | 문법만 검사 |
| `poi repl` | 대화형 셸 |
| `poi version` | 버전 |

## 핵심 4가지

1. **쉬운 문법** — `show`, `ask`, `repeat 10`, `fn f() => ...`, `if x between 1 and 10`
2. **파이썬 호환** — `use py:numpy as np`, `python { ... }`, `use pyfile "./ai.py"`
3. **내장 GUI** — `app "제목" { window {...} button "눌러" { ... } }`
4. **사람 친화 오류** — 파이썬 traceback 대신 POI 줄 + 한국어 설명 + 해결 힌트

## 예제

`examples/` 폴더:

- `hello.poi` — 최소 프로그램
- `basics.poi` — 변수·조건·반복·함수·객체
- `collections.poi` — 배열/객체/문자열 편의 기능
- `pyinterop.poi` — 파이썬 모듈/코드 섞어쓰기
- `errors_demo.poi` — 사람 친화 오류 메시지
- `gui_hello.poi`, `gui_login.poi` — 선언형 GUI (tkinter)

## 문서

- [문법 명세 (docs/SPEC.md)](docs/SPEC.md)
- [오류 코드표 (docs/ERRORS.md)](docs/ERRORS.md)
- [로드맵 (docs/ROADMAP.md)](docs/ROADMAP.md)

## 상태

**v0.1 (작동하는 뼈대).** 코어 언어 + 파이썬 인터롭 + 기본 GUI + 사람 친화 오류 + CLI + 회귀 테스트 13개.
웹앱/서버, DB DSL, 패키지 매니저, 네이티브 빌드, LSP 는 로드맵 참고.

## 라이선스

MIT

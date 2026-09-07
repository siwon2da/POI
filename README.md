# POI — Power Of Imagination

**우리가 만든 언어.** 문법 자체가 파이썬보다 쉽고, 쓸 수 있는 범위는 더 넓게 —
입문자도 한 줄로 이해하고, 전문가는 끝까지 씁니다.
자체 문법 · 타입 · 오류 · GUI 모델을 가지며, 실행은 CPython 위에서 하므로
`numpy` · `pandas` · `torch` 같은 파이썬 라이브러리 수십만 개를 첫날부터 그대로 씁니다.

**라이브 소개: https://hagora.kr/poi/**

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
| `poi run 파일.poi --emit-python` | 낮춰진 중간 표현만 출력 |
| `poi run 파일.poi --trace / --vars / --explain` | 디버깅 추적 |
| `poi debug 파일.poi` | 추적 + 변수 + 사후 분석 |
| `poi new <이름>` | 새 프로젝트 폴더 생성 |
| `poi check <파일.poi>` | 문법만 검사 |
| `poi repl` | 대화형 셸 |
| `poi update` | 새 버전 확인 / 올리기 |
| `poi version` | 버전 |

## 핵심

1. **쉬운 문법** — `show`, `ask`, `repeat 10`, `fn f() => ...`, `if x between 1 and 10`
2. **파이썬 호환** — `use py:numpy as np`, `python { ... }`, `use pyfile "./ai.py"`
3. **내장 GUI** — `app "제목" { window {...} button "눌러" { ... } }`
4. **사람 친화 오류** — 파이썬 traceback 대신 POI 줄 + 한국어 설명 + 해결 힌트
5. **디버깅 도구 (v1.1)** — `inspect(x)` · `watch(x)` · `pause()` · `poi run --trace/--vars/--explain` · `poi debug`
6. **새 버전 알림 (v1.1)** — `poi run` 이 하루 1회 확인, 새 버전이면 터미널에서 안내

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
- [디버깅 (docs/DEBUGGING.md)](docs/DEBUGGING.md)
- [오류 코드표 (docs/ERRORS.md)](docs/ERRORS.md)
- [로드맵 (docs/ROADMAP.md)](docs/ROADMAP.md)
- [변경 이력 (CHANGELOG.md)](CHANGELOG.md)

## 랜딩 페이지

**라이브: https://hagora.kr/poi/**

`site/landing.html` (Artifact 조각) · `site/hagora/` (배포된 독립 실행본). 문법·동작 원리·오류 메시지·GUI·로드맵.

## 상태

**v1.1 (작동하는 언어).** 코어 문법 + 파이썬 인터롭 + GUI + 사람 친화 오류 + **디버깅 도구** + 새 버전 알림 + CLI + 회귀 테스트 14개.
웹앱/서버, DB DSL, 한국어 키워드, 패키지 매니저, 네이티브 빌드, LSP 는 [로드맵](docs/ROADMAP.md) 참고.

## 내려받기

- **Windows 설치 마법사**: `installer/poi.iss` (Inno Setup 으로 빌드) 또는 `installer/install.ps1` (서명·관리자 불필요).
- **어디서나**: 저장소를 받아 `python -m poi run <파일>` (파이썬만 있으면 됨).

## 라이선스

MIT

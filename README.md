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

POI 는 자체 문법 · 타입 · 오류 · GUI 를 갖는 독립 언어. 실행만 CPython 위에서 하므로
`numpy` `pandas` `torch` 같은 파이썬 라이브러리를 첫날부터 그대로 씁니다.
블록은 중괄호·콜론·`end`·들여쓰기·세미콜론 다 되고, 키워드는 한국어로도 씁니다.

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
| `poi debug 파일.poi` | 추적 + 변수 + 사후 분석 |
| `poi test 파일.poi` | test 블록 실행·채점 |
| `poi build 파일.poi` | Python 없이 POI 전용 패키저로 단일 EXE 생성 |
| `poi verify 파일.exe` | 전용 EXE 형식·코드·SHA-256 무결성 검사 |
| `poi build --app idle` | POI IDLE 을 `poi-idle.exe` 로 |
| `poi idle [파일]` | POI 로 만든 코드 편집기 (문법 강조·F5 실행) |
| `poi fmt [파일\|.]` · `poi lint [파일\|.]` | 소스 정리 · 가벼운 점검 |
| `poi run 파일.poi --safe` | 샌드박스 실행 |
| `poi serve` / `poi exercises` | 플레이그라운드 / 300제 |
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
7. **형식 자유 (v1.2)** — 중괄호·들여쓰기 없이 `end` / 콜론 · 삼항식 · 안전 모드 · 플레이그라운드 · 300제
8. **전문 분야 (v1.3)** — 람다 + 함수형 파이프라인(`map`/`filter`/`reduce`/`group_by`…) · `test`/`assert` + `poi test` ·
   `use "./x.poi"` 모듈 · `raise` · `regex`/`csv`/`datetime`/`random`/`stats`/`env` · `poi build` → 단일 exe
9. **한국어 · match · 호환성 (v1.4)** — `보여주기`/`만약`/`반복`/`함수`/`끝` … 한국어 키워드 · `match`/`when` 패턴 매칭 ·
   들여쓰기·`;` 세미콜론까지 (5방식 혼용) · `shell` 로 어떤 언어·도구든 호출
10. **선택적 정적 타입 · 모바일 (v1.5)** — `poi check --types` (오탐 없음) · 한국어 타입명·키워드·내장함수 대폭 확장 · 랜딩 모바일 UX
11. **웹 (v1.6)** — `server { get "/" { } }` 내장 HTTP · `webapp { page "/" { } }` 선언형 페이지 · CSRF·보안 헤더·ETag 기본값 · 설정 0으로 예쁜 반응형·다크 페이지
12. **표준 라이브러리 · 백엔드/보안 · IDLE (v1.7)** — `crypto`·`password`·`jwt`·`path`·`url`·`html`·`compress`·`log`·`cache`·`bench`·`dotenv`·`system`·`uuid` ·
    `database(...)` SQLite 0설정 · 서명 쿠키/세션·레이트리밋·gzip · `poi idle` / `poi build --app idle`
13. **언어 안정화 (v1.8)** — `break`/`continue`/`while` · 진짜 `const` · 범위 `1..10` · `match` 식 · `catch ValueError as e` + `raise Error(...)` ·
   `export` · 반환 타입 검사 · `poi fmt` · `poi lint` · `poi check .` · `elif`→`else if` 같은 오류 안내
14. **전자·Arduino·보안 연구 (v1.16)** — `electronics`로 직렬 포트·센서·PWM·회로 계산·가상 보드를 사용하고,
    `security`로 해시·HMAC·엔트로피·보안 헤더와 허가된 로컬/사설망 포트를 점검. 공개망은 이중 안전 해제가 필요
15. **멀티파일·하온·신뢰성 (v1.18)** — 여러 `.poi` 파일 프로젝트를 하온이 함께 읽고 검사·실행 · wheel/IDLE/EXE 호환성 강화 ·
    안전 모드·레지스트리 공급망 방어 · 제네릭 타입 검사
16. **전용 EXE 패키저 (v1.17)** — 설치본의 안전한 실행 스텁에 최적화된 바이트코드를 직접 담아 수초 안에 EXE 생성 ·
    Python/PyInstaller/셸 호출 불필요 · SHA-256 검증 · 원자적 출력 · 난독화·비밀번호 잠금
14. **전자·Arduino·보안 연구 (v1.16)** — `electronics`로 직렬 포트·센서·PWM·회로 계산·가상 보드를 사용하고,
    `security`로 해시·HMAC·엔트로피·보안 헤더와 허가된 로컬/사설망 포트를 점검. 공개망은 이중 안전 해제가 필요

## 예제

`examples/` 폴더:

- `hello.poi` — 최소 프로그램
- `basics.poi` — 변수·조건·반복·함수·객체
- `collections.poi` — 배열/객체/문자열 편의 기능
- `pyinterop.poi` — 파이썬 모듈/코드 섞어쓰기
- `errors_demo.poi` — 사람 친화 오류 메시지
- `gui_hello.poi`, `gui_login.poi` — 선언형 GUI (tkinter)
- `arduino_serial.poi` — Arduino 직렬 프로토콜·ADC·PWM (가상 보드로 즉시 실행)
- `security_lab.poi` — 해시·엔트로피·보안 헤더·로컬 포트 방어 연구
- `arduino_serial.poi` — Arduino 직렬 프로토콜·ADC·PWM (가상 보드로 즉시 실행)
- `security_lab.poi` — 해시·엔트로피·보안 헤더·로컬 포트 방어 연구

## 문서

- [문법 명세 (docs/SPEC.md)](docs/SPEC.md)
- [전체 문법 정리 — LLM 프롬프트용 (docs/POI_전체문법.md)](docs/POI_전체문법.md) · `hagora.kr/poi/POI_전체문법.md` — ChatGPT 등에 붙여넣으면 POI 코드를 정확히 씀
- [연습문제 300제 · 안전 모드 · 플레이그라운드 · match · 한국어 키워드 — 전부 SPEC 참고](docs/SPEC.md)
- [디버깅 (docs/DEBUGGING.md)](docs/DEBUGGING.md)
- [오류 코드표 (docs/ERRORS.md)](docs/ERRORS.md)
- [로드맵 (docs/ROADMAP.md)](docs/ROADMAP.md)
- [전자·Arduino·보안 연구실 (docs/LABS.md)](docs/LABS.md)
- [POI 전용 EXE 패키저 (docs/PACKAGING.md)](docs/PACKAGING.md)
- [전자·Arduino·보안 연구실 (docs/LABS.md)](docs/LABS.md)
- [변경 이력 (CHANGELOG.md)](CHANGELOG.md)

## 랜딩 페이지

**라이브: https://hagora.kr/poi/**

`site/landing.html` (Artifact 조각) · `site/hagora/` (배포된 독립 실행본). 문법·동작 원리·오류 메시지·GUI·로드맵.

## 상태

**v1.18.6.** 코어 문법 + 파이썬 인터롭 + GUI + 사람 친화 오류 + 디버깅 도구 + 선택적 정적 타입 +
**내장 웹서버/선언형 페이지** + **백엔드·보안 표준 라이브러리** + **`database(...)` SQLite** +
**POI IDLE** (POI 로 작성) + **언어 안정화**(break/continue·진짜 const·범위·match 식·타입 catch·export·poi fmt/lint) +
CLI + 전자·Arduino·방어 보안 연구 모듈 + 멀티파일 하온 에이전트 + POI 전용 EXE 패키저 + 회귀 테스트 + 연습문제 300제.
패키지 매니저, async, LSP 는 [로드맵](docs/ROADMAP.md) 참고.

## 내려받기

- **Windows 설치 마법사**: `installer/poi.iss` (Inno Setup 으로 빌드) 또는 `installer/install.ps1` (서명·관리자 불필요).
- **어디서나**: 저장소를 받아 `python -m poi run <파일>` (파이썬만 있으면 됨).

## 라이선스

MIT

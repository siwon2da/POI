# POI 로드맵

POI 의 포지션: **우리가 만든 독립 언어.** 자체 문법 · 자체 타입 체계 · 자체 오류 체계 ·
자체 GUI 모델을 가지며, 실행만 세계에서 가장 검증된 런타임(CPython) 위에서 한다.
그래서 "새 언어인데 첫날부터 라이브러리 수십만 개".

목표는 **파이썬보다 더 큰 우주** — 문법 자체는 파이썬보다 쉽고(중괄호도 들여쓰기도 강제 안 함),
쓸 수 있는 범위는 파이썬보다 넓게(GUI·웹·자동화·데이터가 기본기), 입문자도 실무 전문가도.
`POI` 라는 이름의 가상 우주를 짓는 일.

```
입문
 │
 ├──── POI ── GUI · Web · AI · Automation · Data · (파이썬 생태계 전부)
 │
 └──────────── 전문 개발
```

핵심 축: **쉬운 문법 · 파이썬 호환 · 내장 UI · 사람 친화 오류 · 디버깅 도구**

---

## v1.7 — 표준 라이브러리 · 백엔드/보안 · POI IDLE  ✅ (현재)

- [x] **백엔드/보안 모듈** (외부 의존성 0) — `crypto` · `password`(PBKDF2) · `jwt`(HS256) · `path` · `url` · `html` · `compress` · `log` · `cache` · `bench` · `dotenv` · `system` · `uuid`
- [x] **`database(...)`** — import 없이 SQLite 0설정, 결과 행은 점 접근 (`run`/`query`/`one`/`value`/`insert`/`tables`)
- [x] **웹서버 강화** — 서명 쿠키/세션(`cookie`·`session`), IP 레이트 리밋(429), gzip 응답 자동 압축
- [x] **POI IDLE** — `poi idle` / `poi build --app idle`. POI 로 작성, 문법 강조·F5 실행(스레드+타임아웃)·저장/열기
- [x] REPL `help`, `poi help` 에 test/build/idle, 안전 모드에서 database/compress/system 차단, 회귀 28

## v1.6 — 웹  ✅

- [x] **내장 HTTP 서버** `server { get/post/put/delete "path" { } }` — 경로 파라미터 :id, JSON/폼 body, static, respond/redirect
- [x] **선언형 페이지** `webapp { page "/" { } }` — heading·card·form·field·select… + state + action (POST-redirect-GET)
- [x] **보안 기본값** — HTML 자동 이스케이프, CSRF 토큰 자동, 보안 헤더(CSP·X-Frame·nosniff), 본문 제한, traversal 차단
- [x] **설정 0으로 예쁜 반응형·다크 페이지** (내장 디자인 시스템), 정적 파일 ETag/캐시
- [x] `poi run --port N`, 안전 모드에서 server/webapp 차단, 회귀 27

## v1.5 — 선택적 정적 타입 · 한국어 확장 · 모바일  ✅

- [x] **선택적 정적 타입** — `poi check --types` / `poi run --types` (오탐 없음, 실행 무영향)
  - 타입 붙은 선언·반환·인자 불일치, `Text+Int` 등. 타입명 한국어(`정수·문자·목록…`)·`List<T>`·`Int?`
- [x] **한국어 키워드 대폭 확장** — 기능·되풀이·각각·결과·만일·아니라면·붙잡기·마침 … + 한국어 타입명 + 한국어 내장함수(`문자·숫자·걸러내기·변환·합계…`)
- [x] **랜딩 모바일 UX** — 하단 고정 CTA, 여백/글자 축소, 코드 가로 스크롤, overflow 안전망

## v1.4 — 한국어 · match · 호환성 끝판왕  ✅

- [x] **한국어 키워드 별칭** — 보여주기·만약·아니면·반복·순회·함수·돌려주기·끝·분기·경우 … (영문과 혼용 가능)
- [x] **match / when** 패턴 매칭 — 여러 값 · `> 100` 비교 · `between a and b`
- [x] **들여쓰기 블록** — 콜론도 `end` 도 없이 (오프사이드 규칙). `{ }` · `:` · `end` · 들여쓰기 · `;` 다 되고 섞어도 됨
- [x] **shell 모듈** — `shell.run/text` 로 어떤 언어·도구든 호출 (안전 모드 차단)
- [x] 버그 정리 — `show test` 이스터에그 복구, 안전 모드 shell/env/module 차단, 회귀 22개

## v1.3 — 전문 분야에서도  ✅

- [x] **람다** `x => x*2` · `(a,b) => a+b` (값으로)
- [x] **함수형 파이프라인** — map·filter·reduce·group_by·sort_by·take·unique·chunk … 30여 개
- [x] **test 블록 + `poi test`** · `assert` (실패 시 소스와 함께)
- [x] **`use "./파일.poi"`** POI 모듈 임포트 · **`raise`**
- [x] **표준 모듈** regex · csv · datetime · random · stats · env
- [x] **`poi build`** → 단일 실행파일 (PyInstaller)
- [x] `.` 뒤 예약어 허용, 보간이 `{3}` 정규식 수량자 안 건드림

## v1.2 — 파이썬보다 자유롭게  ✅

- [x] **블록 3방식** — 중괄호 · 콜론 한 줄 · `end` 로 닫기(중괄호·들여쓰기 불필요)
- [x] **삼항식** `값 if 조건 else 다른값`
- [x] **연습문제 300제** (`poi exercises`) — 정답이 실행 회귀 테스트
- [x] **안전 모드** `poi run --safe` — python{}·use py·파일·네트워크·위험 내장 차단 + 시간·출력 제한
- [x] **플레이그라운드 서버** `poi serve` + `run.php` — 별도 프로세스 격리 실행
- [x] **부팅 배너** — `poi` / `poi repl` 시 ASCII 로고 애니메이션
- [x] **POI 입문서** (20장, hagora.kr/poi/book/)

## v1.1 — 작동하는 언어  ✅

- [x] Lexer / Parser / AST / POI 컴파일러 / 런타임
- [x] 변수·상수·타입표기(무시)·문자열 보간
- [x] `if / else if / else`, `is`, `between`, 연쇄 비교
- [x] `repeat N`, `repeat N as i`, `for x in xs`
- [x] `fn`, 한 줄 함수 `=>`, 기본값 인자
- [x] 배열·객체(점 접근)·문자열/배열 편의 메서드
- [x] `?.`, `??`, 파이프라인 `|>`, `try / catch`
- [x] `use py:...`, `python { }`, `use pyfile` — 파이썬 생태계 전부
- [x] 표준 모듈: `file json web math time` (외부 의존성 0)
- [x] 선언형 GUI: `app / window / text / title / button / row / column / card / input / state / on`
- [x] 사람 친화 오류 (P-코드 + POI 줄 + 힌트)
- [x] **디버깅 도구**: `inspect` · `watch` · `pause` · `--trace` · `--vars` · `--explain` · `poi debug`
- [x] **새 버전 알림**: `poi run` / `poi version` 이 하루 1회 확인, `poi update`
- [x] CLI: `run / debug / new / check / repl / update / version`
- [x] Windows 설치 마법사 (`poi.iss` + `install.ps1`) · 로고 · 회귀 테스트 14개
- [x] 한생(Galmuri)/토스 감성 소개 페이지 (hagora.kr/poi)

## v1.7 — 언어 다듬기

- [ ] `const` 재대입 금지 실제 적용, 스코프 규칙 문서화
- [ ] 리스트 컴프리헨션 대체 문법: `[x * 2 for x in xs where x > 0]`
- [ ] 구조 분해: `a, b = pair`, `{ name, age } = user`
- [ ] `every 1 second { }`, `background { }`, `async fn` / `await` 고수준 동시성
- [ ] 문자열 보간 형식 지정: `"{price:money}"`, `"{ratio:%}"`
- [ ] 타입 추론 강화 (List<T> 원소 타입, Member/Index 추적), `did you mean` 오타 제안

## v1.8 — 표준 라이브러리 확장

- [ ] `database("x.db")` SQLite DSL
- [ ] `ai` 모듈: `ai.chat(model:, prompt:)` (openai / gemini / ollama)
- [ ] `net`(소켓/websocket) · `crypto` · `path` · `http.server` 고수준
- [ ] 데이터프레임 유사 API (`table`), 플로팅 헬퍼

## v1.9 — 웹 심화

- [ ] 클라이언트 반응형 (state 변경 → 부분 갱신, 새로고침 없이)
- [ ] 세션/쿠키·인증 헬퍼, 미들웨어, 웹소켓
- [ ] `poi build --web` (정적 번들)

## v1.10 — GUI 2.0

- [ ] 반응형 렌더 (`state` 변경 → 부분 갱신), `grid`, 전역 `style`
- [ ] 웹뷰 / Qt 백엔드 선택, 테마 시스템

## v2.1 — 패키지 매니저 · 빌드 심화

- [ ] `poi add <이름>` / `poi add py:numpy` — 프로젝트 전용 venv
- [ ] `poi.lock`, POI 패키지 레지스트리
- [ ] `poi build --native`(Nuitka) · `--web`(정적 번들) · 코드 서명 훅

## v2.2 — 도구 생태계

- [ ] **POI Language Server (LSP)** — 자동완성/정의이동/진단/리네임
- [ ] VS Code 확장, `poi fmt` 정식 구현, `poi doctor`

## v2.3 — 안정화

- [ ] 문법 안정화 + 하위호환 정책
- [ ] **play.poi.dev** — 브라우저 실행 (Pyodide)
- [ ] 튜토리얼 · 레퍼런스 · 예제 갤러리 · 성능(AST 캐시)

---

## 설계 원칙 (바뀌지 않는 것)

1. **파이썬 라이브러리를 절대 버리지 않는다.** POI 생태계 = 파이썬 생태계 + POI 표준.
2. **입문자는 타입/괄호/import 를 몰라도 되고, 전문가는 다 쓸 수 있다.** 강요하지 않되 막지도 않는다.
3. **오류는 사람의 말로.** 파이썬 traceback 을 사용자에게 그대로 노출하지 않는다.
4. **GUI/웹은 언어 기본기.** "Hello World 다음이 창 띄우기" 가 되어야 한다.
5. **자체 언어, 검증된 런타임.** 새 VM 을 만들지 않는다 — 실행은 CPython 위에서.
6. **막히면 안이 보여야 한다.** 디버깅은 애드온이 아니라 언어 기본기.
7. **형식을 강요하지 않는다.** 중괄호·들여쓰기·세미콜론 중 무엇도 필수가 아니다. 쓰고 싶으면 쓴다.
8. **모르는 사람의 코드도 안전하게 돌린다.** 안전 모드 + 프로세스 격리로 "실행해 보세요" 가 위험하지 않게.

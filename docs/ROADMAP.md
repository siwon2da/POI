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

## v1.2 — 파이썬보다 자유롭게  ✅ (현재)

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

## v1.3 — 언어 다듬기

- [ ] `const` 재대입 금지 실제 적용, 스코프 규칙 문서화
- [ ] **한국어 키워드 별칭** — `보여주기`=`show`, `만약`=`if`, `아니면`=`else`, `반복`=`repeat`,
      `함수`=`fn`, `돌려주기`=`return` … (영문 키워드와 완전 호환, 섞어 써도 됨)
- [ ] `match` / `when` 패턴 매칭
- [ ] 리스트 컴프리헨션 대체 문법: `[x * 2 for x in xs where x > 0]`
- [ ] 파이프라인 확장: `|> filter(x => x > 0)`, `|> map(...)`, `|> sort(by: age)`, `|> take(10)`
- [ ] 구조 분해: `a, b = pair`, `{ name, age } = user`
- [ ] `every 1 second { }`, `background { }`, `async fn` / `await` 고수준 동시성
- [ ] 문자열 보간에서 형식 지정: `"{price:money}"`, `"{ratio:%}"`
- [ ] 더 나은 오류: "did you mean" 오타 제안, 다중 프레임

## v1.4 — 선택적 정적 타입

- [ ] `Int Float Text Bool List<T> Map<K,V> Option<T>` 타입 체커 (opt-in)
- [ ] 함수 시그니처 검사, 반환 타입 추론
- [ ] `poi check --types`
- [ ] 타입 오류도 P-코드로

## v1.5 — 표준 라이브러리 확장

- [ ] `database("x.db")` SQLite DSL: `db.table "users" { ... }`, `db.users.add {...}`, `db.users.where(...)`, `db.sql """..."""`
- [ ] `ai` 모듈: `ai.chat(model:, prompt:)`, provider adapter (openai / gemini / ollama)
- [ ] `net` (소켓/websocket), `crypto`, `datetime` 확장, `csv`, `env`
- [ ] `test { }` 블록 + `poi test`

## v1.6 — 웹

- [ ] `webapp "..." { page "/" { ... } }` — GUI 와 같은 문법으로 정적/SPA 페이지
- [ ] `server { get "/api/x" { return {...} } }` — `poi run` 하면 서버 기동
- [ ] 상태 관리 + 반응형 재렌더 (`state` 바뀌면 UI 갱신) — 데스크톱 GUI 에도 소급 적용
- [ ] 라우팅 / 미들웨어 / 세션 / 정적 파일

## v1.7 — GUI 2.0

- [ ] 반응형 렌더: `state` 변경 → diff → 부분 갱신 (`for user in users` 자동 리스트)
- [ ] `grid columns=3 { }`, `style Button { ... }` 전역 스타일, 인라인 `style { }`
- [ ] 이벤트: `on change`, `on key "ESC"`, 드래그/포커스
- [ ] tkinter 백엔드 → 선택적으로 웹뷰/Qt 백엔드
- [ ] 테마 시스템 (라이트/다크)

## v1.8 — 패키지 매니저

- [ ] `poi add <이름>` / `poi add py:numpy` — 프로젝트 전용 venv 자동 생성
- [ ] `poi remove / update`, `poi.lock`
- [ ] POI 패키지 레지스트리 (초기엔 git URL 허용)

## v1.9 — 빌드 / 배포

- [ ] `poi build` → 단일 실행파일 (초기 PyInstaller, 이후 Nuitka)
- [ ] `poi build --native`, `poi build --web` (정적 번들)
- [ ] 크로스 플랫폼 아이콘/메타데이터, 코드 서명 훅

## v2.0 — 도구 생태계

- [ ] **POI Language Server (LSP)** — 자동완성/정의이동/진단/리네임
- [ ] VS Code 확장: 하이라이팅 · 포매터(`poi fmt`) · Run/Debug 버튼 · LSP
- [ ] `poi fmt` 정식 구현 (현재는 미구현)
- [ ] `poi doctor` — 환경 진단

## v2.1 — 안정화

- [ ] 문법 안정화 + 하위호환 정책
- [ ] **play.poi.dev** — 브라우저에서 바로 실행되는 플레이그라운드 (Pyodide)
- [ ] 튜토리얼 · 레퍼런스 · 예제 갤러리
- [ ] 성능: 자주 쓰는 경로 트랜스파일 최적화, AST 캐시

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

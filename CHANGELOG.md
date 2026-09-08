# 변경 이력

## v1.7.0 — 2026-09-08  (대규모 업데이트 — 표준 라이브러리 · 백엔드/보안 · POI IDLE)

파이썬이 하는 건 다 하고, 더 한다. 새 모듈은 `import` 없이 바로, 또는 `use 이름`.

**백엔드 · 보안 표준 라이브러리** (외부 의존성 0, 전부 파이썬 표준 라이브러리 위)
```poi
h = password.hash("hunter2")            # PBKDF2-HMAC-SHA256, 솔트 자동
password.verify("hunter2", h)           # → true (상수시간 비교)
tok = jwt.sign({ id: 7 }, "secret", 3600)   # HS256, 의존성 0
jwt.verify(tok, "secret")               # → {id: 7, ...}  (만료·서명 검사)
crypto.sha256(s) · crypto.hmac(k, m) · crypto.token(32) · crypto.uuid()
```
- `crypto` — sha256/512·md5·blake2·hmac·base64·hex·random_bytes·token·uuid·constant_eq
- `password` — hash·verify·strong
- `jwt` — sign·verify·decode (HS256)
- `path` — join·base·dir·ext·stem·abs·norm·exists·is_file·is_dir·parts·home·cwd
- `url` — parse(→ scheme/host/port/path/query/fragment)·build·encode·decode·query_encode/parse·join
- `html` — escape·unescape·strip_tags·attr
- `compress` — gzip·gunzip·zlib·unzlib·zip_read·zip_make (안전 모드 차단)
- `log` — debug·info·warn·error·level
- `cache` — get·set·has·clear·ttl·memo
- `bench` — time(fn)·run(fn, times)→{total,avg,per_sec}
- `dotenv` — load(".env")  (안전 모드 차단)
- `system` — platform·release·python_version·poi_version·cpu_count·hostname·pid·cwd·args·env  (안전 모드 차단)
- `uuid` — v4·hex·short·is_valid

**데이터베이스 — `database(...)` (import 없이, SQLite 0설정)**
```poi
db = database("app.db")                 # 또는 database(":memory:")
db.exec("create table note(id integer primary key, body text)")
db.run("insert into note(body) values(?)", ["안녕"])   # → {changed, id}
db.query("select * from note")          # → [{id:1, body:"안녕"}]  (점 접근)
db.one(sql, p) · db.value(sql, p) · db.insert("note", {body:"x"}) · db.tables()
```
- 안전 모드에서는 `database(...)` 차단

**내장 웹서버 강화 (v1.6 → v1.7)**
- **서명 쿠키 / 세션** — `cookie("sid", token)` (HttpOnly·SameSite·Max-Age, blake2 서명),
  `session.read(headers, "sid")` → 위조 시 `null`
- **레이트 리밋** — IP 당 토큰 버킷 (`POI_RATE_MAX`, `POI_RATE_WINDOW`), 초과 시 429
- **gzip 응답 압축** — `Accept-Encoding: gzip` + 텍스트/JSON + 900바이트 이상일 때 자동
- 라우트: `put`/`delete` 에 더해 안정화, 500 핸들러 오류 사람 말 렌더

**POI IDLE — POI 로 작성한 코드 편집기** (`poi/apps/idle.poi`)
- `poi idle` 로 실행, `poi build --app idle` 로 `poi-idle.exe`
- 다크 UI · 문법 강조(키워드·문자열·주석·숫자·함수) · 줄:칸 표시 · 예제 버튼
- **F5 실행** — 별도 스레드에서 in-process 실행, 콘솔에 스트리밍, 8초 넘으면 자동 중단
- 새로(Ctrl+N) · 열기(Ctrl+O) · 저장(Ctrl+S) · 다른 이름 저장(Ctrl+Shift+S)
- tkinter 위에서 순수 POI 문법(`fn`·`if`·`for`·문자열 보간·`=>` 람다)으로 작성

**REPL**
- `help` / `?` / `도움말` — REPL 도움말
- `poi help` 에 `test` · `build` · `idle` 추가

**회귀**: 28개 케이스 + 300 연습문제 통과.

---

## v1.6.0 — 2026-09-08  (대규모 업데이트 — 웹)

파이썬/JS 백엔드보다 나은 것을 목표로. `poi run app.poi` → 서버가 뜬다 (기본 :8080, `--port`).

**내장 HTTP 서버**
```poi
server {
    get "/" { return "<h1>안녕</h1>" }              # 문자열 → HTML
    get "/api/합/:a/:b" { return { 합: number(params.a) + number(params.b) } }  # dict → JSON
    post "/echo" { return body }
    static "./public"
}
```
- 경로 파라미터 `:id` · `query` · `body`(JSON+폼 자동 파싱) · `headers` · `method` 주입
- `respond(body, status, headers)` · `redirect("/x")` · `html("<raw>")` 헬퍼
- `ThreadingHTTPServer` + HTTP/1.1 keep-alive, 정적 파일 **ETag + Cache-Control**(304 지원)

**선언형 페이지 `webapp`**
```poi
webapp "메모장" {
    state 메모 = []
    page "/" {
        heading "메모장"
        for m in 메모 { card { text m } }
        form "/추가" { field "새 메모" -> 내용   button "추가" }
    }
    action "/추가" { 메모.add(내용) }
}
```
- 노드: heading·subtitle·text·badge·alert·notice·divider·spacer·image·link·card·row·column·
  form·field·input·password·textarea·select·checkbox·button·html · 안에서 `for`/`if`
- `state` + `action` — 폼 제출 → 액션 실행 → 상태 갱신 → 페이지 재렌더 (POST-redirect-GET)
- **설정 0으로 예쁜 반응형·다크 대응 페이지** (내장 디자인 시스템)

**보안 기본값**
- HTML **자동 이스케이프** (`_html.escape`)
- **CSRF 토큰** 자동 — 모든 webapp 폼에 hidden `_csrf` 주입, 액션 POST 에서 검증 (틀리면 403)
- 보안 헤더 기본: `Content-Security-Policy` · `X-Frame-Options: DENY` · `X-Content-Type-Options: nosniff` · `Referrer-Policy`
- 본문 크기 제한(2MB), 정적 경로 traversal 차단, 클라이언트에 스택트레이스 안 보냄
- 안전 모드(`--safe`)에서는 `server`/`webapp` 차단

**기타**
- CLI `poi run --port N`, `POI_NO_SERVE=1` 로 서버 시작 안 함(테스트용)
- 회귀 테스트 26 → 27

## v1.5.1 — 2026-09-08  (디버깅 QA 후 버그 수정)

- **빈 블록** — `if true {}`, `fn f() end`, `for x in [] {}`, `match x {}`, `else {}` 가
  `pass` 를 잘못된 들여쓰기로 뱉어 SyntaxError(P098) → `block()`/`block_gui()` 수정
- **정규식/이스케이프** — `"\d{2}"` 같은 문자열이 파이썬 `SyntaxWarning` 을 내고
  이스케이프가 어긋나던 것 → 트랜스파일러가 POI 이스케이프를 먼저 처리하고 `repr()` 로 안전 방출
  (`\n \t \" \\` 는 그대로, `\d` 등 모르는 건 백슬래시 유지)
- **`test` 를 변수명으로** — `test = 5`, `for test in xs` 가능 (test 는 `test "이름" {` 일 때만 키워드)
- **assert 메시지** — `add ( 1 , 1 )` → `add(1, 1)` 로 정리
- 회귀 테스트 24 → 26 (빈 블록·이스케이프 케이스 추가)

## v1.5.0 — 2026-09-08  (대규모 업데이트 — 선택적 정적 타입 · 한국어 확장 · 모바일)

**선택적 정적 타입** (쓰고 싶을 때만, 실행엔 영향 없음)
- `poi check --types 파일.poi` — 타입 표기를 실제로 검사, 오류 있으면 exit 1
- `poi run --types 파일.poi` — 경고만 찍고 그냥 실행
- 잡는 것: 타입 붙은 선언 불일치(`x: Int = "hi"` → P400), 반환 타입 불일치(P405),
  인자 타입/개수 불일치(P403/P404), `Text + Int`(P401), `Text` 에 산술(P402)
- **오탐 안 함** — 양쪽 타입이 확실할 때만 지적. `Any` 는 항상 통과
- 타입명: `Int Float Number Text Bool List Map Fn Any Null` + 한국어 `정수·실수·문자·목록·사전…` + `List<T>` `Int?`

**한국어 키워드 대폭 확장** (영문과 혼용)
- show: 보여주기·출력·보이기·찍기·말하기 / if: 만약·만일·가령 / else: 아니면·아니라면·그외
- repeat: 반복·되풀이 / for: 순회·각각·모든 / fn: 함수·기능·정의 / return: 돌려주기·결과·내보내기
- try/catch: 시도·해보기 / 잡기·붙잡기 / end: 끝·마침 / and: 그리고·또한·이고 / …
- **한국어 타입명**: `정수·실수·숫자·문자·문자열·참거짓·목록·배열·사전·맵·객체·함수·아무거나`
- **한국어 내장함수**: `문자`=text · `숫자`=number · `참거짓`=boolean · `걸러내기`=filter ·
  `변환`=map · `모으기`=reduce · `합계`=sum_of · `평균값`=avg · `묶기`=group_by · `살펴보기`=inspect …

**랜딩 모바일 UX**
- 하단 고정 CTA(시작하기·입문서·실행), 히어로/섹션 여백·글자 축소, 코드블록 가로 스크롤,
  버튼 풀너비, `overflow-x:hidden` 안전망
- 버그: `.promise:nth-child(even)` 규칙이 모바일 스택을 막던 것 제거

## v1.4.0 — 2026-09-08  (대규모 업데이트 — 한국어 · match · 호환성 끝판왕)

**한국어 키워드 별칭** (영문과 완전 호환, 한 파일에서 섞어도 됨)
- `보여주기`·`출력`=show, `물어보기`=ask, `만약`=if, `아니면`·`그밖에`=else,
  `반복`=repeat, `순회`=for, `안에`=in, `마다`=as, `함수`=fn, `돌려주기`·`반환`=return,
  `참`/`거짓`/`없음`, `그리고`/`또는`/`아님`, `시도`/`잡기`, `끝`=end, `상수`=const,
  `사용`=use, `던지기`=raise, `분기`=match, `경우`=when, `검사`=test, `확인`=assert,
  `사이`=between, `파이썬`=python

**match / when 패턴 매칭**
```poi
match x {
    when 1 { ... }
    when 2, 3 { ... }          # 여러 값
    when > 100 { ... }         # 비교 패턴
    when between 4 and 10 { ... }
    else { ... }
}
```
중괄호·`end`·콜론 다 됨.

**블록 = 형식 자유 (호환성 끝판왕)**
- 이제 **들여쓰기만으로도** 블록이 됨 (콜론도 `end` 도 없이 — 파이썬처럼):
  ```poi
  if x > 0
      show "양수"
  else
      show "음수"
  ```
- 5가지 다 되고 **섞어도 됨**: `{ }` · `: 한 줄` · `end` · **들여쓰기** · `;` 세미콜론.
- 오프사이드 규칙(첫 문장 열 > 여는 키워드 열 → 들여쓰기 블록), 없으면 `end` 스타일.

**shell 모듈 — 어떤 언어·도구든**
- `shell.run("node app.js")` → `{out, err, code, ok}`, `shell.text("git rev-parse HEAD")`.
- node·go 바이너리·git·ffmpeg 등 무엇이든. (안전 모드 차단)

**버그 정리**
- `test` 를 예약어로 만들면서 깨졌던 이스터에그 `show test` 복구 (문맥 키워드로).
- 안전 모드가 `shell`·`env`·`use "./x.poi"` 도 확실히 차단.
- 회귀 테스트 18 → 22.

## v1.3.0 — 2026-09-08  (대규모 업데이트 — 전문 분야)

입문자만이 아니라 실무에서 파이썬보다 잘 쓰이게.

**함수형 데이터 처리**
- 람다: `x => x * 2`, `(a, b) => a + b` (값으로).
- 파이프라인 표준 함수 30여 개 (첫 인자가 목록 → `|>` 와 자연스럽게):
  `map filter reject reduce each find find_index count_where any_of all_of
  sort_by sort_desc group_by partition take drop take_while drop_while unique
  flatten chunk zip_with sum_of avg min_of max_of count_of reverse_of range_list repeat_list`
- 예: `nums |> filter(x => x > 0) |> map(x => x * x) |> sort_desc |> take(3)`

**테스트가 언어 안에**
- `test "이름" { ... assert 조건 ... }` + `poi test 파일.poi` → 통과/실패 요약, 실패 시 exit 1.
- `assert a == b` — 실패하면 그 소스와 함께 P301.
- 일반 `poi run` 에서는 test 블록을 정의만 하고 실행하지 않음.

**모듈**
- `use "./유틸.poi" as u` → 그 파일의 함수·변수를 `u.함수()` 로. 경로는 현재 파일 기준.
- `raise "메시지"` (또는 `raise 값`) — `try/catch` 로 잡힘.

**표준 모듈 7종 추가** (import 없이): `regex` `csv` `datetime` `random` `stats` `env`
- `regex.match/all/replace/split/test`, `csv.parse/format/read/write`,
  `datetime.now/parse/format/add/diff_days/parts`, `random.int/choice/sample/shuffle/chance`,
  `stats.mean/median/mode/stdev/variance`, `env.get/set/has/all` (안전 모드에선 env 차단)

**빌드**
- `poi build app.poi [-o 이름] [--console]` → PyInstaller 로 단일 `.exe`. 파이썬 없는 곳에서도 실행.

**기타**
- `.` 뒤 예약어 허용 (`regex.test`, `x.end` 등).
- 문자열 보간에서 `{3}` `{4}` 같은 순수 숫자/문자 리터럴은 보간 안 함 (정규식 수량자 보호).
- 회귀 테스트 16 → 18.

## v1.2.0 — 2026-09-08  (대규모 업데이트)

**문법 — 파이썬보다 자유롭게**
- 블록 3방식: 중괄호 `{ }` · 콜론 한 줄 `if x: show y` · `end` 로 닫기(중괄호·들여쓰기 불필요).
  `if/else if/else` 는 체인 전체를 하나의 `end` 로.
- 삼항식: `값 if 조건 else 다른값`.

**연습문제 300제**
- `exercises/` 에 300개 (출력·산술·문자열·조건·반복·함수·배열·객체·종합), 주제별 난이도 순.
- 정답 출력은 레퍼런스 구현으로 생성 = 300개의 실행 회귀 테스트.
- `poi exercises [번호|--topic 주제|--show 번호]`.

**안전 모드 + 플레이그라운드 (서버 실행 · 악용 방지)**
- `poi run --safe [--time N]` — `python{}`·`use py`·`use pyfile`·파일·네트워크·위험 내장 차단,
  벽시계 시간 제한 + 출력 상한 + 재귀 제한.
- `poi serve [폴더] [--port]` — 정적 서빙 + `POST /run` (별도 프로세스 격리 실행).
- `site/hagora/run.php` — hagora 용 PHP 엔드포인트(proc_open + 타임아웃 + 세마포어).
- 랜딩에 "지금 바로 실행" 위젯 (백엔드 없으면 안내로 폴백).

**부팅 배너**
- `poi` (인자 없이) / `poi repl` 시 ASCII 블록 "POI" + "Power Of Imagination" 애니메이션(#0af 계열).
- `POI_NO_BANNER=1` / 비-TTY 자동 skip / 레거시 콘솔용 ASCII 폴백.

**POI 입문서**
- `site/book.html` (라이브: hagora.kr/poi/book/) — 20장, 예제 전부 실행됨. 랜딩 nav 연결.

**기타**
- 로고 애니메이션/부팅 연출, 렉서 BOM `lstrip`, 회귀 테스트 14 → 16.
- 로드맵 v1.x 로 재정렬, 목표 문구 "파이썬보다 더 큰 우주".

## v1.1.0 — 2026-09-08  (대규모 업데이트)

**정체성**
- POI = **Power Of Imagination**. "파이썬 위의 래퍼" 가 아니라 **우리가 만든 독립 언어**로 문서/페이지 재정의.
- 자체 문법·타입·오류·GUI 모델. 실행만 검증된 런타임(CPython) 위에서.

**디버깅 도구 (신규)**
- `inspect(x)` — 값의 타입·구조·길이·미리보기를 예쁘게 출력, x 를 그대로 반환.
- `watch(x)` — inspect 하고 그대로 반환. 흐름을 안 끊음. `final = watch(f(x))`.
- `pause()` — 그 줄에서 멈춰 지역 변수 보기 / 식 계산 / 계속.
- `poi run --trace` — 문장마다 줄번호·소스 출력. `--vars` 로 변수 변화까지.
- `poi run --explain` — 오류가 난 프레임의 지역 변수까지 사후 분석.
- `poi debug <파일>` — 위를 한 번에.

**새 버전 알림**
- `poi run` / `poi version` 이 하루 1회 원격 버전 확인, 새 버전이면 터미널에 한 줄 안내.
- 원격: `hagora.kr/poi/VERSION` → GitHub `raw` 폴백. `POI_NO_UPDATE_CHECK=1` 로 끔.
- `poi update` — git 체크아웃이면 `git pull` 시도, 아니면 안내.

**배포물**
- Windows 설치 마법사: `installer/poi.iss` (Inno Setup) + `installer/install.ps1` (서명·관리자 불필요).
  PATH 등록, `.poi` 연결, 시작 메뉴 항목, `poi.ico`.
- 로고: `site/assets/poi-mark.svg` (파란 스퀘어클 안 픽셀 P). 페이지 favicon/헤더에 사용.

**소개 페이지**
- 폰트/디자인 전면 교체 — 한생의 **Galmuri** 픽셀 폰트(임베드) + 토스 스타일 레이아웃(넓은 여백, 파란 단색 강조, 둥근 카드).
- 라이브: https://hagora.kr/poi/  ·  Claude Artifact 사본.

**기타**
- 이스터에그 `show test` — 성경 구절/출처 제거, "강하고 담대하라" 배너만.
- 렉서 BOM 방어 강화 (`lstrip`).
- 회귀 테스트 13 → 14.

## v0.1.0 — 2026-09-07

- Lexer / Parser / AST / 파이썬 트랜스파일 / 런타임.
- 코어 문법: 변수·상수·문자열 보간·조건·반복·함수·객체·배열·`?.`·`??`·`|>`·try/catch.
- 파이썬 인터롭: `use py:` · `python { }` · `use pyfile`.
- 표준 모듈: file · json · web · math · time (외부 의존성 0).
- 선언형 GUI (tkinter). 사람 친화 오류 (P-코드). CLI: run/new/check/repl.

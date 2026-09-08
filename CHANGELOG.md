# 변경 이력

## v1.9.9 — 2026-09-09  (v2.0 앞의 대통합 — 생태계 · 게임 · 3D · 하온 에이전트)

> v1.14 · v1.15 의 내용(WSGI · 프로덕션 · scene3d · htmx-lite · 정적 굽기 등)을 포함해
> **2.0 직전의 모든 것**을 하나로 낸다.

**생태계 & 프로젝트**
- **`poi.toml [project]`** — `name` `version` `entry` `type`. `poi run` 이 `entry` 를 기본 진입점으로.
- **`poi init`** — 대화형: 콘솔 / 웹 / REST API / GUI / 게임 / 데이터 / 빈 프로젝트 → 스캐폴딩 + `poi.toml`.
- **패키지 레지스트리** — `poi search <말>` · `poi add <이름>` (인덱스에 있으면 `poi_modules/` 로 받고
  `poi.toml [poi-packages]` 기록, 없으면 pip 폴백) · `poi publish` (묶음 + 등록 안내).
- **`poi migrate <파일|.> [--write]`** — 2.0 스타일로 정리: `def→fn` · `elif→else if` ·
  `True/False/None→true/false/null` · `if x: 문장` 한 줄 → `if x { 문장 }`. 미리보기 후 `--write`.
- **REPL 개편** — `:type <식>` · `:vars` · `:clear` · `:reset` · 마지막 식은 자동으로 값이 찍힘 · 여러 줄 입력.
- **`poi doctor`** — 실행 환경 진단.

**게임 — `game` (2D, tkinter Canvas, 의존성 0)**
```poi
win = game.window("POI Jump", 800, 500)
p = game.sprite(win, { x: 100, y: 300, w: 40, h: 40, color: "#5b9dff" })
game.on_key(win, "space", () => p.jump(14))
game.on_key(win, "Left", () => p.move(-6, 0))
game.every_frame(win, (dt) => {
    p.vy = p.vy + 0.6
    p.move(0, p.vy)
})
game.run(win)
```
- `window sprite text on_key on_hold every_frame hits/collide out_of_bounds score close run`
- 스프라이트: `.x .y .vx .vy .move(dx,dy) .to(x,y) .jump(power) .set(...) .remove() .cx .cy`. 별칭 `게임`.

**3D 웹 — `scene3d`** (v1.15 에서 들어옴): 선언형 씬 → 자체 완결 HTML(Three.js@cdnjs). box/sphere/torus/…,
spin/float/pulse, orbit/grid. `scene3d.render()` / `scene3d.page()`.

**웹** (v1.14~v1.15): WSGI(`poi wsgi`), `/healthz`, `POI_ENV=production`, `poi run --host/--prod`,
`render()` 템플릿 엔진 + `{% component %}` + `{% include %}`, htmx-lite(`data-poi-get/post/target/load/every`),
multipart 업로드(`body.files`), `poi build --site`(정적 굽기), `auth`·미들웨어·`respond.*`.

**하온 — ChatGPT 연결 + 에이전트**
- **`poi haon login`** — 브라우저로 **ChatGPT 계정에 OAuth(PKCE)** 로그인 (API 키 불필요, Codex CLI 와 같은 흐름).
  `poi haon status` / `poi haon logout`. 백엔드 우선순위: ChatGPT → Groq → 로컬 Ollama → 규칙.
- **`poi haon agent <폴더> "<할 일>"`** — 정해진 폴더 안에서 스스로 `.poi` 파일을 쓰고 `poi check`/`run` 으로
  검증하며 반복 (Claude Code / Codex 처럼). GPT 는 번들된 POI 레퍼런스를 시스템 프롬프트로 받는다.
- `poi haon fix <파일> [--write]` — 규칙 기반 자동 수정(실제 컴파일러 구동).

**EXE 보호 — `poi build`**
- **`--obfuscate`** — 트랜스파일 결과의 이름 치환·문자열 인코딩·marshal 포장 (쉽게 못 읽게).
- **`--lock <비번>`** — 코드 객체를 비번으로 암호화(PBKDF2 + Fernet, 없으면 stdlib 스트림). 기본은
  비번을 exe 안에 숨겨 넣고, **`--ask-password`** 를 붙이면 실행할 때 물어본다 (비번을 모르면 코드가 안 풀림).
- IDLE 툴바 **`📦 EXE`** 버튼 — 난독화·콘솔·비밀번호를 골라 빌드.

**소개 페이지** — 다른 언어를 언급하지 않도록 문구 정리 (POI 는 그 자체로).

## v1.15.0 — 2026-09-09  (대규모 업데이트 — 웹 최강 + 3D 웹)

**`scene3d` — POI 로 3D 웹** (import 없이, `poi/runtime/scene3d.py`)
```poi
장면 = scene3d.scene({ bg: "#0b0e14", camera: [4, 3, 7] })
scene3d.box(장면,    { color: "#5b9dff", spin: true })
scene3d.sphere(장면, { pos: [2.6, 0, 0], color: "#37d39b", float: true })
scene3d.torus(장면,  { pos: [-2.6, 0, 0], color: "#ffb454", spin: true })
scene3d.dodeca(장면, { pos: [0, 2.2, -1], color: "#c792ea", pulse: true })
scene3d.light(장면, "sun")
scene3d.orbit(장면)          # 드래그 회전 · 휠 줌 (외부 컨트롤 의존 없음)
scene3d.autorotate(장면)
scene3d.grid(장면)
html scene3d.render(장면, { height: 480 })   # webapp{} 안에서
# 또는:  file.write("3d.html", scene3d.page(장면))   # 완전한 문서
```
- 선언형 씬 그래프 → **자체 완결 HTML** (Three.js r160 은 cdnjs, 셋업 JS 인라인). **서버 불필요** — 정적 호스트에 그대로.
- 도형: `box sphere plane cylinder cone torus dodeca` · `model(url)`(glTF 자리) · `light("sun"|"ambient"|"point")`
- 노드 옵션: `pos scale rotate color size` + 애니메이션 `spin`(`spinSpeed`) · `float` · `pulse`
- 미니 오빗 컨트롤 내장. 한국어 별칭: `삼차원` · `입체`.

**htmx-lite — 새로고침 없는 부분 갱신**
```html
<button data-poi-get="/frag" data-poi-target="#slot">불러오기</button>
<div id=slot data-poi-load="/stats" data-poi-every="3000"></div>
<form data-poi-post="/save" data-poi-target="#msg" data-poi-swap="inner">…</form>
```
- 라우트가 HTML 조각을 돌려주면 클라이언트가 지정한 자리에 끼운다. `render()` 결과에
  `data-poi-*` 가 있으면 ~1KB 런타임을 자동 주입. `data-poi-swap` = `inner`(기본)·`outer`·`append`·`prepend`.

**템플릿 `{% component %}` · 파일 업로드 · 정적 굽기**
- `{% component "card.html" title="시원" n=95 %}` — 인자를 넘겨 부분 템플릿 렌더 (`{% include %}` 와 달리 스코프 지정).
- **multipart 업로드** — `post` 핸들러에서 `body.files` → `[{ name, filename, content_type, data, text, size }]`, 일반 필드는 `body.<이름>`.
- **`poi build --site 앱.poi -o dist`** — 파라미터 없는 GET 라우트를 정적 HTML 로 구워서 `dist/` 에.
  `static "..."` 폴더도 복사. 아무 호스트에나 올릴 수 있는 사이트가 나온다.

## v1.14.0 — 2026-09-09  (대규모 업데이트 — 프로덕션 & 개발자 경험)

**WSGI — 진짜 프로덕션 서버에 얹는다**
```bash
poi wsgi src/main.poi          # wsgi.py 생성 + 배포 명령 안내
gunicorn wsgi:application -w 4 -b 0.0.0.0:8000
waitress-serve --port=8000 wsgi:application
uvicorn --interface wsgi wsgi:application --port 8000
```
- `poi/runtime/wsgi.py` — `.poi` 파일을 실행해 `server{}` 라우트를 등록하고 PEP 3333
  `application(environ, start_response)` 를 돌려준다. `POI_APP=app.poi gunicorn "poi.runtime.wsgi:app"` 도 됨.
- 내부 리팩터링: `serve_request(method, path, raw, headers, ip)` 공용 디스패치 함수 —
  개발 서버(`ThreadingHTTPServer`)와 WSGI 어댑터가 **같은 코드**로 라우팅·미들웨어·정적파일을 처리.
  라우트 컴파일은 `_APPS` 버전 카운터로 캐시.

**프로덕션 하드닝**
- **`/healthz`** (그리고 `/_health`) — 모든 서버에 자동. `{"status":"ok"}`.
- **`POI_ENV=production`** — 핸들러·미들웨어 오류의 상세를 숨기고 `{"error":"internal error"}` 만.
- `poi run 앱.poi --host 0.0.0.0 --port 80 --prod` — 바인드 주소·포트·운영 모드.
- 폼 body 파싱이 잘못된 인코딩에도 안 죽음(utf-8 replace).

**개발자 경험**
- **`poi doctor`** — 파이썬·tkinter·Pillow·컴파일 캐시·git·gunicorn/waitress·하온 백엔드 점검 (✓/-- 표).
- **`poi new <이름> --web | --api | --cli`** — 바로 도는 시작점 생성.
  `--web` 은 `views/home.html` 템플릿까지. 공유 상태는 Box 로 (전역 재대입 함정 회피).
- **`examples/showcase/`** — `app.poi` 한 파일 + `views/*.html` 로 만든 완전한 웹사이트.
  랜딩 · 로그인/대시보드(auth+미들웨어 가드) · 실시간 DB 집계 API ·
  `/play` 에서 **POI 가 POI 를 `--safe` 로 실행**. 바탕화면 `POI 쇼케이스.bat` 런처.

## v1.13.0 — 2026-09-08  (대규모 업데이트 — 전문화: 성능 · 웹 · GUI)

**성능 — 컴파일 캐시**
- 안 바뀐 `.poi` 는 **렉싱·파싱·트랜스파일·compile 을 통째로 건너뛴다**. 캐시는
  `~/.poi/cache/` (또는 `POI_CACHE_DIR`), 키 = SHA-256(버전+소스). `.json`(중간 표현) +
  `.code`(marshal 된 코드 객체) 둘 다 저장.
- 큰 파일(42KB idle.poi)에서 `compile_source` 38ms → 1ms (**39배**). 테스트 루프·IDLE F5·웹 리로드가 즉시.
- `poi cache` (상태) / `poi cache clear` / `poi run --no-cache` / `POI_NO_CACHE=1`.
- 안전 모드(`--safe`)는 매번 `assert_safe` 를 해야 하므로 캐시를 쓰지 않는다.

**웹 전문화**
```poi
server {
    get "/" {
        render("home.html", { title: "POI", users: 회원목록 })   # 템플릿 엔진
    }
    post "/api/login" {
        u = 사용자찾기(body.id)
        if u == null or not auth.check(body.pw, u.hash) {
            return respond.error(401, "로그인 실패")
        }
        respond(true, 200, { "Set-Cookie": auth.issue({ id: u.id, name: u.name }) })
    }
    get "/me" {
        나 = auth.current(headers)
        if 나 == null { return redirect("/login") }
        respond.json(나)
    }
}
on_request(auth.guard("/login"))    # 전역 로그인 가드 (미들웨어)
```
- **`render(name, data)`** — `views/` · `templates/` · cwd 에서 템플릿을 찾아 채운다.
  `{{ 식 }}` (자동 이스케이프, `{{ x | raw }}` 는 안 함), `{% for x in xs %}…{% endfor %}`,
  `{% if 조건 %}…{% endif %}`, `{% include "부분.html" %}`. 파일 mtime 캐시.
- **`respond.json / text / html / status(code) / error(code, msg) / file(path) / redirect`**
- **`auth`** — 서명 쿠키 로그인: `auth.issue(claims)` → Set-Cookie 값, `auth.current(headers)` →
  claims(Box)/null, `auth.require(headers, to)` → redirect/null, `auth.guard(to)` → 미들웨어,
  `auth.hash/check` (PBKDF2 위임), `auth.logout()`.
- **미들웨어** — `on_request(fn)` (요청 전, 응답 돌려주면 거기서 끝), `on_response(fn)` (핸들러 뒤, 교체 가능).
  핸들러에 `req` Box(`path·method·query·body·headers·params·ip`) 전달.

**GUI 전문화 — `uikit`**
```poi
st = uikit.state({ 이름: "시원", 나이: 17 })
e  = uikit.entry(폼, "", 20, null)
uikit.bind(e, st, "이름")                         # 양방향 — 하나 바뀌면 둘 다

폼 = uikit.form(win, [
    { name: "id",  label: "아이디", required: true },
    { name: "pw",  label: "비밀번호", type: "password", required: true },
    { name: "나이", label: "나이",   type: "number" },
    { name: "역할", label: "역할",   type: "select", options: ["학생", "교사"] }
], (값) => 가입(값))                                # 검증 실패면 자동 경고

uikit.chart(win, "bar",  [["월", 3], ["화", 7], ["수", 5]], 420, 220, "주간")
uikit.chart(win, "line", [1, 4, 2, 8, 5])
uikit.toast(win, "저장했어요", "ok")
카드 = uikit.card(win, "설정")                     # 제목 있는 테두리 프레임
좌우 = uikit.split(win, "h")                       # 드래그로 크기 조절
```
- `bind(widget, state, field)` · `form(parent, fields, on_submit)` → `.values()/.get()/.set()/.errors()/.valid()`
- `chart(parent, "bar"|"line", data, w, h, title)` — Canvas 에 축·격자·라벨까지
- `toast(win, msg, kind)` · `card(parent, title)` · `split(parent, "h"|"v")`

**IDLE — 하온 채팅 입력칸 레이아웃 수정**
- 편집기 영역이 폭을 다 먹어 하온 패널이 32px 로 눌리고 입력칸이 안 보이던 문제 수정
  (`W.mid` `pack_propagate(false)` + 편집기 `width:1`, 입력줄을 아래에 고정). `POI_IDLE_SELFTEST=1` 자체 점검 추가.

## v1.12.0 — 2026-09-08  (대규모 업데이트 — 확장성: 동시성 · 네트워크)

**동시성 — `task` (import 없이 바로)**
```poi
fn 제곱(x) => x * x
show task.all(제곱, [1, 2, 3, 4, 5])      # [1, 4, 9, 16, 25]  (전부 병렬)

h = task.run(무거운작업)                    # 바로 시작, 핸들 반환
show task.wait(h)                          # 결과 (오류는 그대로 다시 던짐)

ch = task.channel()                        # 스레드 사이 큐
task.run(() => ch.send(1))
for v in ch { show v }                     # close 까지 순회
```
- `task.run / wait / gather` · `task.all(fn, 목록)` · `task.race([...])` ·
  `task.map(fn, 목록, workers=8)` (동시 개수 제한) · `task.sleep(초)` ·
  `task.every(초, fn)` / `task.after(초, fn)` → 타이머(`.stop()`) ·
  `task.channel()` (`.send .recv .close .take_all`, `for` 순회) ·
  `task.lock()` (`.run(fn)` 또는 `.acquire()/.release()`) · `task.cpu_count()`
- 스레드 기반. 새 VM·이벤트 루프 없음. 파이썬 `threading`/`queue` 만 사용.

**문장 문법 — `background` · `every`**
```poi
background {                 # 백그라운드 스레드에서 실행
    긴계산()
}

every 1 second {             # 프로그램이 사는 동안 반복
    상태.틱 = 상태.틱 + 1
}
every 500 ms { ... }         # 단위: ms · sec/second(s) · min/minute(s) · hour(s) · 초/분/시간
```
- `fn` 처럼 바깥 변수는 읽기만 됨 — 공유 상태는 Box(`상태.x = ...`)로.

**네트워크 — `http` · `net` (import 없이, 안전 모드 차단)**
```poi
r = http.get("https://api.example.com/things", headers: { Authorization: 키 })
show r.status                              # 200
show r.json.items[0].name                  # JSON 자동 파싱
http.post(url, json: { name: "시원" })
http.download("https://.../big.zip", "big.zip")

s = net.tcp("example.com", 80)             # 원시 TCP
s.send("GET / HTTP/1.0\r\n\r\n")
show s.line()
net.listen(9010, (conn) => conn.send("hi"))  # 연결마다 스레드
```
- `http.get/post/put/patch/delete/request/download` — `urllib` 만. 응답 =
  `Box{ status, ok, text, json, headers, url }`. 4xx/5xx 도 예외 없이 응답으로.
- `net.tcp/connect · listen · resolve · local_ip · free_port · hostname`
- 한국어 별칭: `작업`(task) · `요청`(http) · `망`/`네트워크`(net)
- 안전 모드: `http` · `net` · `task` · `background` · `every` 전부 차단 (P210/P211)

**`poi.lock` — 재현 가능한 설치**
- `poi add` / `poi install` 이 설치 후 `poi.lock` 에 정확한 버전을 기록.
- `poi install` 은 lock 이 있으면 그 버전으로 좁혀 설치. `poi install --frozen` 은
  `poi.lock` 만 그대로 설치 (CI 재현용).

**폴리글롯 — 파이썬 문법을 POI 에 그대로 (합병)**
```poi
def add(a, b):          # def = fn.  func / function / fun 도.  : 블록은 원래 POI 문법
    return a + b

def grade(n):
    if n >= 90:
        return "A"
    elif n >= 80:        # elif = else if
        return "B"
    else:
        return "F"

print("합", add(2, 3))   # print(...) — 파이썬 print 호환 (sep=/end= 도)
sq = lambda x: x * x     # lambda a, b: 식  →  화살표 함수
ok = True                # True / False / None  =  true / false / null
msg = f"값 {add(1, 2)}"   # f"..." 접두사 허용 (POI 문자열은 원래 보간됨)

def noop():
    pass                 # pass = 아무것도 안 함
```
- 파서/렉서 레벨에서 흡수 — `def func function fun` → `fn`, `True/False/None` →
  `true/false/null`, `elif` → `else if`, `lambda`/`pass` 는 정식 문법, `f"..."` 는 접두사만 무시.
- `//` `/* */` 주석, `;` 문장 구분은 이미 됨. C/자바 상호운용은 `use py:ctypes` / `use py:jpype`.
- `_FOREIGN_HINT` 는 이제 정말 안 되는 것만 안내 (`var`/`let`/`echo`/`switch`/`case`…).

**블록 화살표 함수 `() => { ... }`**
```poi
task.run(() => {
    x = 무거운계산()
    저장(x)
})
```
- 지금까지 `x => 식` 만 됐는데, 이제 여러 줄 본문도 됨 (컴파일러가 이름 있는 함수로 호이스트).

**POI IDLE 대개편 — 하온 채팅창 + UX/UI**
- **하온이 채팅창이 됐다** — 말풍선(나 오른쪽 / 하온 왼쪽), 여러 줄 입력(Enter 전송,
  Shift+Enter 줄바꿈), "생각 중…" 이 자리에서 답으로 바뀜, 최근 6턴 대화 맥락 유지,
  `＋ 코드 첨부` 토글, `대화 지우기`.
- **명령 팔레트** `Ctrl+Shift+P` — 모든 동작을 검색해서 실행.
- **툴바** 그룹별 구분선 + `⌘ 팔레트` 버튼. **상태줄** 이 커서 위치·모드·하온 백엔드·버전·단축키.
- 현재 줄 하이라이트, 하온 도크 `Ctrl+J` 토글, 문법 강조에 `def`/`elif`/`lambda`/`background`/`task` 등 추가.

## v1.11.0 — 2026-09-08  (대규모 업데이트 — 확장성 · GUI 라이브러리 · 사진 편집기)

**확장성 — 재사용 모듈 & 패키지**
```poi
use pkg:그림도구            # poi_modules/그림도구/main.poi  (또는 .poi / .py)
show 그림도구.blur(사진)
```
- `use pkg:이름` — `./poi_modules/` → `~/.poi/modules/` → `POI_PATH` 순으로 찾는다.
  폴더면 `main.poi`/`__init__.poi`/`<이름>.poi`, 아니면 `<이름>.poi` / `<이름>.py`.
  `export` 를 쓴 모듈은 명시한 것만 공개. 안전 모드 차단.
- **`poi add <패키지>`** / `poi remove` / `poi install` — 프로젝트 전용 `.venv` +
  `poi.toml [dependencies]`. `poi run` 은 `.venv` 가 있으면 자동으로 그 site-packages 를
  import 경로 앞에 넣는다 → `use py:numpy` 가 프로젝트 venv 를 쓴다.

**`uikit` — POI 전용 GUI 라이브러리** (명령형, tkinter 위, import 없이)

tkinter 의 색·폰트·pack·이벤트 보일러플레이트를 걷어낸다.

```poi
uikit.theme("dark")
win = uikit.window("제목", 900, 600)
bar = uikit.row(win)
uikit.button(bar, "열기", 열기, true)
s   = uikit.slider(bar, 0, 100, 바뀜, 50, 200, "밝기")
탭  = uikit.tabs(win, ["편집", "설정"])
uikit.tree(win, ["이름","점수"], [["시원","90"]], null, 8)
uikit.run(win)
```
- 위젯: `window title row column grid cell tabs label button entry slider canvas
  listbox text statusbar menu checkbox radio select progress image scroll tree
  dialog tooltip`
- 헬퍼: `theme(light/dark) value(위젯[,v]) set_text ask_open ask_save ask_color
  alert confirm every on bind_key run close`
- **반응형** `state(초기값)` + `watch(st, fn)` — `st.v = 3` 하면 watcher 자동 호출
- 선언형 `app { window { } }` 는 그대로. `uikit` 은 동적 UI 용. 안전 모드 차단.

**`poi photo` — POI 로 작성한 사진 편집기** (`uikit` + Pillow)
- 열기·저장(PNG/JPEG), 밝기·대비·채도·선명 슬라이더 (원본에서 실시간 재계산)
- 필터: 흑백·세피아·반전·블러·샤픈·윤곽·자동 보정
- 회전(90°)·좌우/상하 뒤집기, **undo/redo**(Ctrl+Z/Y), 원본으로
- `poi photo [사진]`, `poi build --app photo` (Pillow 없으면 `poi add pillow` 안내)

**회귀**: 31 케이스 + 300 연습문제.

---

## v1.10.0 — 2026-09-08

**`ai` 모듈** — import 없이 바로 (하온과 같은 백엔드: Groq → 로컬 Ollama)
```poi
show ai.ask("POI 가 뭐야?")                # 짧게
code = ai.code("1부터 100까지 소수 출력")   # POI 코드만
show ai.summarize(긴글)
show ai.backends().mode                     # groq / ollama / rules
ai.install()                                # 로컬 LLM 자동 설치
```
- `ai.chat(prompt, system:, model:)` — 시스템 프롬프트·모델 지정 가능
- 안전 모드에서 `ai` 차단 (network). `system`·`dotenv`·`compress` 전역도 이제 안전 모드에서 차단

**구조 분해**
```poi
user = { name: "시원", age: 16 }
{ name, age } = user           # name = user.name; age = user.age
[a, b, c] = [10, 20, 30]       # 순서대로
[first, second] = 목록
```
- `const` 로 잡힌 이름을 구조 분해로 덮어쓰면 P019

**회귀**: 31 케이스 + 300 연습문제.

---

## v1.9.1 — 2026-09-08

**하온 백엔드 확장** — Groq · 로컬 Ollama · 자동 설치
- **Groq** — `GROQ_API_KEY` 환경변수 / `~/.poi/groq.key` / `.env` 에서 키를 자동으로 찾아 사용
  (`llama-3.3-70b-versatile`). **사용자별 레이트 리밋** 기본 5분에 12회
  (`POI_HAON_MAX` / `POI_HAON_WINDOW`), 초과 시 규칙 기반으로 안내
- **로컬 Ollama** — 돌고 있으면 그걸로 (GPU 자동)
- **`⬇ 로컬 LLM 자동 설치·실행`** — 둘 다 없을 때 버튼 한 번으로:
  winget(또는 OllamaSetup.exe) 로 Ollama 설치 → `ollama serve` → `qwen2.5-coder:1.5b` pull,
  진행 상황을 하온 패널에 스트리밍. 끝나면 자동으로 LLM 모드 전환
- 우선순위: Groq → Ollama → 규칙 기반. 규칙 기반 오토픽스는 항상 동작
- 하온 패널 뱃지가 현재 백엔드/남은 횟수 표시

**문서** — 문법 문서의 `§반복` 예제가 `users`/`n` 을 안 만들고 써서 붙여넣어 실행하면
P102 가 나던 것을, 그 자체로 실행되도록 수정.

---

## v1.9.0 — 2026-09-08  (대규모 업데이트 — POI IDLE 대개편)

POI IDLE 을 본격 편집기로. (언어 자체는 v1.8 그대로 + 웹서버 non-blocking `start()`.)

**라이트 모드 기본**
- 화이트 테마가 기본값, `◐ 테마` / 보기 메뉴로 다크 토글 (`~/.poi/idle.json` 에 저장)
- 라이트/다크 각각 에디터·거터·콘솔·툴바·상태바·문법색 팔레트

**UX/UI**
- 메뉴바 — 파일 / 편집 / 실행 / 보기 / 도움말
- 툴바 정리 — 새로·열기·최근·저장·실행·터미널·웹 폴더·예제·콘솔·하온·테마
- 자동 들여쓰기·괄호 자동닫기·Tab 블록·Ctrl+/ 주석·Ctrl+F 찾기·Ctrl+± 확대 (v1.7 유지)

**웹 서버 임시 켜기**
- `server` / `webapp` 파일에서 **F5** → IDLE 이 서버를 띄우고 브라우저 자동 오픈
- 요청 로그가 콘솔에 실시간, 실행 버튼이 `■ 서버 중지` 로
- `📁 웹 폴더` — 디렉토리 선택 → 그 안의 `main.poi`/`app.poi`… 중 `server`/`webapp` 파일 자동 실행,
  없으면 `server { static "<dir>" }` 로 정적 서버
- `webserver.start(port, host, on_log)` — 블로킹하지 않는 서버 기동 API 추가

**하온 — 로컬 에이전트** (`poi/apps/haon.py`)
- `🐙 하온` 패널 (오른쪽). 백엔드 자동 감지: GPU(nvidia-smi) · Ollama(`localhost:11434`)
- **규칙 기반 오토픽스** — `🔧 이 파일 오류 자동 수정`: 실제 POI 컴파일러를 돌려
  오류 코드(P0xx)를 읽고 타겟 수정을 반복 (elif→else if, def→fn, True→true,
  안 닫힌 `{`·`end`·`"""`, const 재대입 등). 모델 없이도 동작
- **LLM 모드** — Ollama 가 있으면 POI 문법을 시스템 프롬프트로 주고 질문 (모델은
  qwen2.5-coder 등 자동 선택, GPU 는 Ollama 가 자동). 없으면 규칙 기반으로 안내
- 모델 본체는 exe 에 번들하지 않음 — 있으면 쓰고 없으면 규칙 기반

**설치 (poi.exe __install__ · 마법사 둘 다)**
- 바탕화면에 `POI IDLE` 바로가기 생성
- 설치 직후 POI IDLE 자동 실행 (`POI_NO_LAUNCH=1` 로 끔)
- 제거 시 바탕화면 바로가기도 정리

**회귀**: 30 케이스 + 300 연습문제 통과.

---

## v1.8.0 — 2026-09-08  (대규모 업데이트 — 언어 안정화)

기능을 더 넣기보다 **문법 정리 · 개발 편의성 · 오류 메시지**에 집중.

**제어 흐름**
```poi
repeat 100 as i {
    if i is 20 { break }
    if i % 2 is 0 { continue }
}
while n > 0 { n = n - 1 }
```
- `break` / `continue` (반복문 밖이면 컴파일 오류 P018)
- `while 조건 { }` 정식 추가

**진짜 `const`**
```poi
const PI = 3.14159
PI = 4        # POI Error P019 — 상수는 다시 대입할 수 없어요
```

**범위 `1..10` / `1..<10`**
```poi
for i in 1..10 { show i }      # 1..10 포함
show 1..<4                     # [1, 2, 3]
```

**`match` 식 (값을 돌려준다)**
```poi
grade = match score {
    when >= 90 => "A"
    when >= 80 => "B"
    else => "F"
}
```

**타입 있는 catch · 오류 타입**
```poi
try {
    raise ValueError("잘못된 값")
} catch ValueError as e {
    show e.message      # "잘못된 값"
    show e.type         # "ValueError"
}
```
- `raise Error(...)` · `raise ValueError(...)` · `FileError` · `AuthError` · `NotFoundError` …
- `catch <타입> as e` — 타입이 다르면 그대로 다시 던짐 (다른 catch/상위로)
- 안 잡힌 `raise ValueError("x")` → `POI Error P300  [ValueError] x`

**모듈 `export`**
```poi
# math.poi
export fn add(a, b) => a + b
export const V = "1.8"
fn hidden() => 42          # export 안 함 → 밖에서 안 보임
```
`export` 를 하나라도 쓰면 명시한 것만 공개, 안 쓰면 예전처럼 전부 공개.

**타입 검사 강화** — 중첩된 `if`/`for`/`while`/`try` 안의 `return` 까지 반환 타입 검사 (P405).

**도구**
- `poi fmt [파일 | .] [--check]` — 탭→4칸, 줄 끝 공백, 블록 깊이 재들여쓰기, 빈 줄 정리.
  `end`/콜론 스타일이면 공백만 정리(안전). 정리 후 파싱 안 되면 원본 유지.
- `poi lint [파일 | .] [--strict]` — 안 쓴 변수(POI-W101), const 재선언(W102), return 뒤 죽은 코드(W103)
- `poi check .` / `poi fmt .` / `poi lint .` — 폴더 전체의 `.poi` 를 한 번에

**오류 메시지** — 다른 언어 습관을 문장 첫머리에서 잡아 안내:
`elif`→`else if`, `def`/`func`→`fn`, `foreach`→`for`, `switch`→`match`, `var`/`let`→(키워드 없이), `echo`/`puts`→`show` …

**한국어 키워드 추가** — `멈추기`(break) · `계속`(continue) · `동안`(while) · `공개`(export)

**회귀**: 30 케이스 + 300 연습문제 통과. 예제/케이스 일부 `poi fmt` 적용.

---

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

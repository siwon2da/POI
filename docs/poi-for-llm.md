# POI 언어 — 전체 문법 정리 (LLM 프롬프트용)

> 이 문서 하나를 그대로 붙여넣으면 ChatGPT / Claude 등이 **POI 코드를 정확히** 쓸 수 있습니다.
> POI = **Power Of Imagination**. 파이썬 위에서 도는, 자체 문법·타입·오류·GUI·웹 모델을 가진 독립 언어.
> 버전 기준: **POI v1.8**. 공식: https://hagora.kr/poi/ · 저장소: https://github.com/siwon2da/POI

---

## 0. 이 언어를 쓸 때의 규칙 (LLM 필독)

1. **파이썬이 아니다.** `def`·`elif`·`lambda`·`True/False/None`·`print()`·`f"..."`·`import` 를 쓰지 마라.
   → `fn`·`else if`·`x => ...`·`true/false/null`·`show`·`"{...}"`·`use` 를 쓴다.
2. **불리언/널은 소문자**: `true`, `false`, `null`. (출력도 `true/false/null` 로 나온다.)
3. **출력은 `show`**, 입력은 `ask` (항상 문자열 반환). 문자열 보간은 `"{식}"` (f-접두사 없음).
4. **블록은 자유**: 중괄호 `{ }`, 콜론 한 줄 `:`, `end` 로 닫기, 파이썬식 들여쓰기 — 아무거나, 섞어도 됨.
   가장 안전한 기본값: **중괄호** 또는 **들여쓰기 4칸**. 한 파일 안에서 일관되게.
5. **함수는 `fn`**, 한 줄 함수는 `fn 이름(인자) => 식`. 반환은 `return`.
6. **객체는 점 접근**: `user.name` (파이썬처럼 `user["name"]` 안 해도 된다). 객체 리터럴은 `{ name: "시원", age: 16 }`.
7. **변수 선언 키워드가 없다**: 그냥 `x = 10`. (`let`/`var` 없음.) `const` 는 진짜 상수 — 다시 대입하면 컴파일 오류.
8. **한글 식별자 OK**: `이름 = "시원"`, `fn 인사(사람) => "안녕 {사람}"`.
9. **표준 모듈은 import 없이 바로**: `math.sqrt(2)`, `file.read("a.txt")`, `crypto.sha256("x")`, `database(":memory:")`.
   파이썬 라이브러리가 필요하면 `use py:numpy as np`.
10. **세미콜론 선택**. 한 줄에 여러 문장: `a = 1; b = 2; show a + b`.
11. 함수 안에서 **바깥(전역) 변수를 재대입할 수 없다** (파이썬 클로저 제약과 같음).
    여러 함수가 공유하는 상태는 **객체에 담아** `상태.값 = ...` 처럼 바꾼다.

---

## 1. 어휘

- **주석**: `# ...`  또는  `// ...`  (줄 끝까지),  `/* ... */`  (여러 줄)
- **줄바꿈 = 문장 구분자.** 단 `(` `[` 안, 이항 연산자 뒤, 다음 줄이 `.` 또는 `|>` 로 시작할 때는 이어진다.
  `{ }` 는 줄바꿈을 삼키지 않는다(블록/객체 안에서 줄이 의미를 가진다).
- **숫자**: `42`, `3.14`
- **문자열**: `"..."`, 여러 줄은 `"""..."""`. 이스케이프 `\n \t \" \\ \r \0`.
  보간: `"{식}"`. 리터럴 중괄호는 `{{`, `}}`.
- **크기 리터럴**: `500x300` → 문자열 `"500x300"` (GUI `size:` 용).
- **식별자**: 유니코드 letter/`_` 로 시작. 한글 가능.
- **예약어**: `if else for in fn return const show ask use python try catch true false null
  is between and or not repeat while as end raise assert match when break continue export`
  (`test` 는 `test "이름" { }` 형태일 때만 키워드. GUI/웹 단어는 문맥에서만.)
- **범위 연산자**: `1..10` (양끝 포함), `1..<10` (끝 미포함)

### 한국어 키워드 별칭 (영문과 100% 호환, 섞어도 됨)

| 영문 | 한국어 |
|---|---|
| show | 보여주기 · 출력 · 보이기 · 찍기 · 말하기 |
| ask | 물어보기 · 묻기 |
| if / else | 만약·만일·가령 / 아니면·아니라면·그밖에·그외 |
| for / in / as | 순회·각각·모든 / 안에 / 마다·로·으로 |
| repeat | 반복 · 되풀이 |
| fn / return | 함수·기능·정의 / 돌려주기·반환·결과·내보내기 |
| and / or / not | 그리고·또한·이고 / 또는·혹은 / 아님·부정 |
| try / catch | 시도·해보기 / 잡기·붙잡기 |
| end / const | 끝·마침 / 상수·불변·고정 |
| use / raise | 사용·가져오기·불러오기 / 던지기·발생 |
| match / when / between | 분기·고르기 / 경우·케이스 / 사이·범위 |
| assert / python | 확인·단언 / 파이썬 |

### 한국어 내장함수

`문자`=text · `숫자`=number · `참거짓`=boolean · `걸러내기`=filter · `변환`=map ·
`모으기`=reduce · `합계`=sum_of · `평균값`=avg · `묶기`=group_by · `앞에서`=take ·
`중복제거`=unique · `살펴보기`=inspect · `지켜보기`=watch · `데이터베이스`=database

---

## 2. 값과 자료형

```poi
name   = "POI"                     # 문자열 Text
age    = 16                        # 정수 Int
height = 172.5                     # 실수 Float
alive  = true                      # 불리언  true / false
none   = null                      # 없음
users  = ["시원", "예성"]          # 배열 List
user   = { name: "시원", age: 16 } # 객체 Box (점 접근 되는 dict)
user.name        # "시원"
users.first      # "시원"
```

---

## 3. 변수 · 상수 · (선택적) 정적 타입

```poi
x = 10
const PI = 3.14159         # 진짜 상수 — 다시 대입하면 컴파일 오류

name: Text = "시원"        # 타입 표기 — 안 쓰면 무시, 쓰면 poi check --types 로 검사
나이: 정수 = 16             # 한국어 타입명 가능
scores: List<Int> = [90, 88]
maybe: Int? = null         # nullable
```

- 타입명: `Int Float Number Text Bool List Map Fn Any Null` · `List<T>` · `Int?`
- 한국어: `정수 실수 숫자 문자 문자열 참거짓 목록 배열 사전 맵 객체 함수 아무거나`
- 타입은 **완전 선택**. 안 쓰면 그냥 동적 언어. 오탐 안 함(양쪽 타입이 확실할 때만 지적).

---

## 4. 출력 · 입력 · 문자열 보간

```poi
show "Hello"
show 1 + 2
show "이름 {name}, 나이 {age}"        # 보간
show("괄호도 됨")

answer = ask "질문: "                  # 항상 문자열
n = number(ask "숫자: ")               # 숫자로 변환
```

보간 규칙: `{ ... }` 안이 올바른 POI 식이면 값으로, 아니면(예: JSON 조각) 글자 그대로 둔다.

---

## 5. 연산자

| 종류 | 연산자 |
|---|---|
| 산술 | `+ - * / %` |
| 비교 | `== != < > <= >=` — 연쇄 가능 `1 < x < 10` |
| 사람식 | `x is 5` · `x is not 5` · `x between 1 and 10` |
| 논리 | `and or not` (또는 `&& || !`) |
| null 병합 | `a ?? b` — a 가 null 이면 b |
| null 안전 | `a?.b` — a 가 null 이거나 b 없으면 null |
| 삼항식 | `값 if 조건 else 다른값` |
| 람다 | `x => x * 2` · `(a, b) => a + b` |
| 파이프 | `x |> f` · `x |> f(a)` → `f(x)` · `f(x, a)` |

### 함수형 데이터 처리 (전부 목록이 첫 인자)

```poi
result = 매출
    |> filter(r => r.month is 9)
    |> map(r => r.amount)
    |> sort_desc
    |> take(5)

top = 점수 |> sort_desc |> take(10)
```

사용 가능: `map filter reject reduce each find find_index count_where any_of all_of
sort_by sort_desc group_by partition take drop take_while drop_while unique flatten
chunk zip_with sum_of avg min_of max_of count_of reverse_of range_list repeat_list`

---

## 6. 블록 — 5가지, 섞어도 됨

```poi
if x > 0 { show "양수" }              # 1) 중괄호
if x > 0: show "양수"                 # 2) 콜론 한 줄
if x > 0                              # 3) end 로 닫기
    show "양수"
end
if x > 0                              # 4) 들여쓰기만 (파이썬식) — 권장 기본값
    show "양수"
else
    show "음수"
a = 1; b = 2; show a + b              # 5) 세미콜론
```

규칙: 여는 키워드(`if`/`fn`/`for`/`repeat`/`try`/`match`) 다음 첫 문장이 더 깊이 들여쓰이면 들여쓰기 블록.
`if / else if / else` 체인은 통째로 하나의 dedent 또는 `end` 로 닫는다.

---

## 7. 조건 · match

```poi
if age >= 18 {
    show "성인"
} else if age >= 13 {
    show "청소년"
} else {
    show "어린이"
}

if name is "시원" { show "어서와" }
if age between 10 and 19 { show "10대" }

match x {
    when 1 { show "하나" }
    when 2, 3 { show "둘 또는 셋" }
    when > 100 { show "큼" }
    when between 4 and 10 { show "중간" }
    else { show "그밖에" }
}

# match 식 — 값을 돌려준다 (절마다 `=> 식`)
grade = match score {
    when >= 90 => "A"
    when >= 80 => "B"
    when >= 70 => "C"
    else => "F"
}
```

---

## 8. 반복

```poi
users = ["시원", "예성"]

repeat 10 { show "안녕" }              # 10번
repeat 10 as i { show i }              # i = 0..9
for user in users { show user }        # 배열 순회
for i in 1..10 { show i }              # 범위 (양끝 포함)
for i in 1..<10 { show i }             # 10 미포함

n = 3
while n > 0 { n = n - 1 }              # 조건 반복

repeat 100 as i {
    if i is 20 { break }              # 가장 안쪽 반복 탈출
    if i % 2 is 0 { continue }        # 다음 회로
}
```

- `1..10` / `1..<10` 는 값으로도: `nums = 1..5` → `[1,2,3,4,5]`. 끝<시작이면 빈 리스트. 역순은 `reverse_of(1..10)`.
- `break` / `continue` 는 반복문 안에서만 (밖이면 컴파일 오류).

---

## 9. 함수

```poi
fn add(a, b) {
    return a + b
}
fn double(x) => x * 2                       # 한 줄
fn greet(name, greeting = "안녕") {         # 기본값 인자
    return greeting + ", " + name
}
fn 세금(가격: Int, 율: Float) -> Float {    # 타입 표기(선택)
    return 가격 + 가격 * 율
}
```

이름 인자 호출: `greet(name: "시원", greeting: "야")`.
**함수 안에서 전역 변수 재대입 불가** → 공유 상태는 객체 필드로: `상태.카운트 = 상태.카운트 + 1`.

---

## 10. 배열 · 문자열 · 객체 메서드

- 문자열: `.length .is_empty .upper() .lower() .trim() .reverse() .contains(s)
  .starts_with(s) .ends_with(s) .replace(a,b) .split(sep) .words()`
- 배열: `.length .is_empty .first .last .add(x) .remove(x) .contains(x) .reverse() .sort() .join(sep)`
- 객체: `.length .keys() .values() .has(key)` + 점 접근
- 파이썬 기본 메서드(`.append` `.strip` 등)도 그대로 동작한다.

---

## 11. 오류 처리 · 테스트

```poi
try {
    text = file.read("hello.txt")
} catch error {
    show "실패: {error}"          # error: 문자열이면서 .message / .type 도 있음
}

# 오류 타입 + 타입 있는 catch
try {
    raise ValueError("잘못된 값")   # Error ValueError TypeError FileError AuthError
} catch ValueError as e {           # NotFoundError PermissionError TimeoutError ...
    show e.message                  # "잘못된 값"
    show e.type                     # "ValueError"
}
# catch 타입이 다르면 그대로 다시 던져진다 (바깥 try / 상위로).

fn 나이확인(n) {
    if n < 0 { raise "나이는 음수일 수 없습니다" }   # 문자열 raise 도 그대로 됨
    return n
}

fn add(a, b) => a + b
test "덧셈" {
    assert add(2, 3) == 5
    assert add(0, 0) == 0
}
```

`poi test 파일.poi` 로 test 블록만 실행. 일반 `poi run` 은 test 를 정의만 하고 안 돌린다.

---

## 12. 모듈 · 파이썬 상호운용

```poi
# 내보내기 (export 를 하나라도 쓰면 명시한 것만 공개)
export fn add(a, b) => a + b
export const V = "1.8"

use "./유틸.poi" as u          # 다른 POI 파일 (경로는 현재 파일 기준)
use pyfile "./ai.py"           # 파이썬 파일을 모듈로 → ai.predict(...)
use py:numpy as np             # import numpy as np
use py:requests                # import requests

python {                       # 파이썬 코드 그대로 (블록 안 변수는 이후 POI 에서 보임)
    import sys
    ver = sys.version
}
show ver
```

명시적 표준 모듈 로드도 가능: `use math` / `use crypto` / `use 암호`.

---

## 13. 표준 모듈 (import 없이 바로)

| 모듈 | 함수 |
|---|---|
| `file` | `read(p) write(p,s) append(p,s) exists(p) lines(p) delete(p) list(dir)` |
| `json` | `parse(s) stringify(o, pretty) read(p) write(p,o)` |
| `web` | `get(url, headers, params) post(url, body, headers) download(url, p)` → `.text .status .json .ok` |
| `math` | `pi e tau sqrt floor ceil round abs pow min max sum sin cos tan log random randint pick clamp` |
| `time` | `now() today() timestamp() sleep(s) format(dt, fmt)` |
| `regex` | `match(p,t) all(p,t) replace(p,t,r) split(p,t) test(p,t)` |
| `csv` | `parse(text, header) format(rows) read(path) write(path, rows)` |
| `datetime` | `now() parse(s,fmt) format(d,fmt) add(d, days=…) diff_days(a,b) parts(d)` |
| `random` | `int(a,b) float() range(a,b) choice(xs) sample(xs,k) shuffle(xs) chance(p) seed(n)` |
| `stats` | `mean median mode stdev variance sum min max range` — 모두 `(xs)` |
| `env` | `get(name, default) set(name,v) has(name) all()` — 안전 모드 차단 |
| `shell` | `run(cmd, stdin, timeout)` → `{out,err,code,ok}` · `text(cmd)` — 안전 모드 차단 |

### 백엔드 · 보안 (v1.7)

| 모듈 | 함수 |
|---|---|
| `crypto` | `sha256/sha512/sha1/md5/blake2(s) hmac(k,m,algo) base64_encode/decode hex_encode/decode random_bytes(n) token(n) uuid() constant_eq(a,b)` |
| `password` | `hash(pw)` → `pbkdf2_sha256$…` · `verify(pw, stored)` (상수시간) · `strong(pw)` |
| `jwt` | `sign(payload, secret, expires_in?)` · `verify(token, secret)` → payload/`null` · `decode(token)` (HS256) |
| `path` | `join(*p) base(p) dir(p) ext(p) stem(p) abs(p) norm(p) exists/is_file/is_dir(p) parts(p) home() cwd() size(p)` |
| `url` | `parse(u)` → `{scheme,host,port,path,query,fragment}` · `build(…)` · `encode/decode(s)` · `query_encode/parse` · `join(base,rel)` |
| `html` | `escape(s) unescape(s) strip_tags(s) attr(s)` |
| `compress` | `gzip/gunzip zlib/unzlib zip_read(path) zip_make(path, files)` — 안전 모드 차단 |
| `log` | `debug/info/warn/error(*m)` · `level(name)` |
| `cache` | `get(k,default) set(k,v,ttl) has(k) clear() ttl(k,sec,fn) memo(fn)` |
| `bench` | `time(fn)` → 초 · `run(fn, times)` → `{total,avg,per_sec,runs}` |
| `dotenv` | `load(path)` → Box (`os.environ` 반영) — 안전 모드 차단 |
| `system` | `platform() release() python_version() poi_version() cpu_count() hostname() pid() cwd() args() env(name)` — 안전 모드 차단 |
| `uuid` | `v4() hex() short() is_valid(s)` |

한국어 별칭: `암호`(crypto) `비밀번호`(password) `경로`(path) `주소`(url) `압축`(compress) `기록`(log) `캐시`(cache) `시스템`(system).

---

## 14. 데이터베이스 — `database(...)` (import 없이, 0설정 SQLite)

```poi
db = database("app.db")                    # 또는 database(":memory:")
db.exec("create table note(id integer primary key, body text)")
db.run("insert into note(body) values(?)", ["안녕"])   # → { changed, id }
db.query("select * from note order by id")             # → [{ id: 1, body: "안녕" }]  (점 접근)
db.one("select * from note where id = ?", [1])         # → Box 또는 null
db.value("select count(*) from note")                  # → 스칼라
db.insert("note", { body: "빠르게" })                  # → 새 id
db.tables()                                            # → ["note"]
```

`?` 파라미터는 리스트, `:name` 파라미터는 객체로 넘긴다.

---

## 15. 웹 — `server` / `webapp`

### 15.1 HTTP 서버

```poi
server {
    get "/" { return "<h1>안녕</h1>" }                          # 문자열 → HTML
    get "/api/합/:a/:b" {
        return { 합: number(params.a) + number(params.b) }      # dict → JSON
    }
    post "/echo" { return body }
    static "./public"
}
```

핸들러에 주입: `params`(경로 `:id`) · `query` · `body`(JSON·폼 자동 파싱) · `headers` · `method`.
헬퍼: `respond(body, status, headers)` · `redirect("/x")` · `html("<raw>")` ·
`cookie("sid", token)` (서명·HttpOnly·SameSite) · `session.read(headers, "sid")` → 위조 시 `null`.

`poi run app.poi` 하면 서버가 뜬다 (기본 `:8080`, `poi run --port 3000`).

### 15.2 선언형 페이지

```poi
webapp "메모장" {
    state 메모 = []
    page "/" {
        heading "메모장"
        for m in 메모 { card { text m } }
        form "/추가" { field "새 메모" -> 내용   button "추가" }
    }
    action "/추가" { 메모.add(내용) }        # 폼 제출 → 상태 갱신 → 재렌더
}
```

노드: `heading subtitle text badge alert notice divider spacer image link
card row column form field input password textarea select checkbox button html`
— 안에서 `for` / `if` 가능.

기본 제공: HTML 자동 이스케이프 · CSRF 토큰 자동 · 보안 헤더(CSP·X-Frame·nosniff·Referrer-Policy) ·
본문 크기 제한 · 정적 경로 traversal 차단 · 정적 파일 ETag/304 · IP 레이트 리밋(429) ·
gzip 응답 압축 · 설정 0으로 예쁜 반응형·다크 페이지.

### 15.3 백엔드 예제 (회원가입/로그인 API)

```poi
db = database(":memory:")
db.exec("create table users(id integer primary key, email text unique, pw text)")
비밀 = "change-me"

server {
    post "/signup" {
        if db.one("select id from users where email = ?", [body.email]) != null {
            return respond({ error: "이미 가입됨" }, 409)
        }
        id = db.insert("users", { email: body.email, pw: password.hash(body.pw) })
        return { id: id, token: jwt.sign({ uid: id }, 비밀, 3600) }
    }
    post "/login" {
        u = db.one("select * from users where email = ?", [body.email])
        if u == null or not password.verify(body.pw, u.pw) {
            return respond({ error: "이메일 또는 비밀번호가 틀립니다" }, 401)
        }
        return { token: jwt.sign({ uid: u.id }, 비밀, 3600) }
    }
    get "/me" {
        claims = jwt.verify(query.token, 비밀)
        if claims == null { return respond({ error: "토큰 없음/만료" }, 401) }
        return db.one("select id, email from users where id = ?", [claims.uid])
    }
}
```

---

## 16. GUI (선언형, tkinter 기반)

```poi
app "제목" {
    window { title: "POI 앱"   size: 480x320   center: true }
    state username = ""
    column {
        title "로그인"
        text "설명 문구"
        input "아이디" -> username
        password "비밀번호" -> pw
        button "확인" { show "눌림: {username}" }
    }
    on "start" { show "앱 시작됨" }
}
```

노드: `window text title button row column card input password state on` + 안에서 `for`/`if`/일반 문장.
`app.close()` 로 창을 닫는다. (데스크톱 + tkinter 필요.)

---

## 17. 명령어

| 명령 | 하는 일 |
|---|---|
| `poi run [파일]` | 실행 (server/webapp 이면 서버가 뜸). 기본 진입점 `src/main.poi` → `main.poi` → `app.poi` |
| `poi run 파일 --emit-python` | 낮춰진 파이썬 중간 표현 출력 |
| `poi run 파일 --safe [--time N]` | 샌드박스 실행 |
| `poi run 파일 --trace / --vars / --explain` | 추적 / 변수 변화 / 오류 시 사후 분석 |
| `poi check 파일 [--types]` | 문법(+선택적 타입) 검사, 실행 안 함 |
| `poi test 파일` | test 블록 실행·채점 |
| `poi debug 파일` | trace + vars + explain 한 번에 |
| `poi build 파일 [-o 이름]` | 단일 실행파일(.exe) 로 (PyInstaller) |
| `poi build --app idle` | POI IDLE 을 `poi-idle.exe` 로 |
| `poi idle [파일]` | POI IDLE — POI 로 만든 편집기 (문법 강조·F5 실행) |
| `poi fmt [파일\|.] [--check]` | 소스 정리 (탭·공백·들여쓰기) |
| `poi lint [파일\|.] [--strict]` | 안 쓴 변수 등 가벼운 점검 |
| `poi check/fmt/lint .` | 폴더 전체의 .poi 를 한 번에 |
| `poi new <이름>` | 프로젝트 폴더 생성 |
| `poi repl` | 대화형 셸 (`help` 입력 시 도움말) |
| `poi update` · `poi version` | 새 버전 확인·올리기 · 버전 |

환경변수: `POI_NO_UPDATE_CHECK=1` · `POI_NO_BANNER=1` · `POI_NO_SERVE=1`(서버 자동 기동 끄기) ·
`POI_RATE_MAX` / `POI_RATE_WINDOW`(웹 레이트 리밋).

### 안전 모드 `--safe` 가 막는 것

`python { }` · `use py:` · `use pyfile` · `file.*` · `web.*` · `shell.*` · `env.*` · `system.*` ·
`compress.*` · `dotenv.*` · `database(...)` · `server`/`webapp` · 위험한 파이썬 내장 · 무한 루프 · 출력 폭탄.
`crypto` `password` `jwt` `path` `url` `html` `cache` `bench` `log` `math` `json` `regex` 등은 허용.

---

## 18. 자주 하는 실수 (LLM 체크리스트)

| ✗ 파이썬 습관 | ✓ POI |
|---|---|
| `def f(x):` | `fn f(x) {` … `}`  또는  `fn f(x) => 식` |
| `elif` | `else if` |
| `True` / `False` / `None` | `true` / `false` / `null` |
| `print(x)` | `show x` |
| `f"{x}"` | `"{x}"` |
| `lambda x: x+1` | `x => x + 1` |
| `import math` | (필요 없음 — `math.sqrt(2)` 바로)  ·  외부는 `use py:name` |
| `d["k"]` | `d.k` |
| `for i in range(10):` | `repeat 10 as i {` … `}` |
| `x = []` 후 함수 안에서 `x.append` **그리고 재대입** | 재대입 금지 — `상태.목록.add(v)` 처럼 필드 변경 |
| `try: ... except E as e:` | `try { ... } catch e { ... }` |
| `raise ValueError("msg")` | `raise "msg"` |
| `assert x == y, "msg"` | `assert x == y`  (test 블록 안) |

작성 순서 권장: ① 블록 스타일 하나 고정(중괄호 또는 들여쓰기) → ② `fn`/`show`/`true` 확인 →
③ 공유 상태는 객체 필드로 → ④ 표준 모듈은 import 없이, 외부는 `use py:`.

---

## 19. 붙여넣기용 한 줄 요약 (초압축)

> POI 는 파이썬 위에서 도는 독립 언어다. `def→fn`, `elif→else if`, `True/False/None→true/false/null`,
> `print→show`, `f"..."→"..."`, `lambda→=>`, `d["k"]→d.k`, `for i in range(n)→repeat n as i`,
> `try/except→try/catch`, `raise "msg"`. 변수는 그냥 `x = 1`. 블록은 `{ }` 또는 들여쓰기.
> 표준 모듈(math, file, json, crypto, jwt, password, path, url, database, …)은 import 없이 바로.
> 파이썬 라이브러리는 `use py:이름`. 웹은 `server { get "/" { } }` / `webapp { page "/" { } }`.

# POI v1.16.2 문법 명세

> **POI = Power Of Imagination.** 우리가 만든 독립 언어.

이 문서는 **현재 구현된** POI 를 설명한다. 아직 안 된 것은 [ROADMAP](ROADMAP.md).
디버깅 도구는 [DEBUGGING.md](DEBUGGING.md).

## 0. 실행 모델

POI 는 자체 문법 · 자체 의미론 · 자체 오류 체계 · 자체 GUI 모델을 가진 **독립 언어**다.
실행 단계에서만 세계에서 가장 검증된 런타임인 CPython 을 빌린다.

```
POI 소스 → Lexer → Parser → POI AST → POI 컴파일러 → (CPython 바이트코드) → 실행
```

- POI 컴파일러는 POI AST 를 CPython 이 바로 실행할 수 있는 형태로 낮춘다. 성능은 CPython 급.
- 그래서 "새 언어인데 첫날부터 라이브러리 수십만 개" — `use py:...` 한 줄로 파이썬 생태계 전부.
- 실행 중 오류가 나면 내부 줄번호를 POI 줄번호로 되돌려(`linemap`) 사람의 말로 된 메시지를 만든다.
- `poi run x.poi --emit-python` 으로 낮춰진 중간 표현을 직접 볼 수 있다.

## 1. 어휘 (Lexical)

- **주석**: `# ...` 또는 `// ...` (줄 끝까지), `/* ... */` (여러 줄)
- **줄바꿈**: 문장 구분자. 단 `(` `[` 안, 연산자 뒤, 다음 줄이 `.`/`|>` 로 이어질 때는 무시.
  중괄호 `{ }` 는 줄바꿈을 무시하지 않는다.
- **숫자**: `42`, `3.14`
- **크기 리터럴**: `500x300` → 문자열 `"500x300"` (GUI `size:` 용)
- **문자열**: `"..."`, 여러 줄은 `"""..."""`. `\n \t \" \\` 이스케이프. `{{` `}}` 는 리터럴 중괄호.
- **식별자**: 유니코드 letter/underscore 로 시작 → 한글 변수명 OK (`이름 = "시원"`).
- **예약어**: `if else for in fn return const show ask use python try catch true false null
  is between and or not repeat while as end raise assert match when break continue export`
  (`test` 는 문맥 키워드 — `test "이름" { }` 일 때만; GUI 단어도 문맥으로 인식)
- **연산자**: 위 5절 + 범위 `..` `..<`
- **한국어 키워드 별칭** — 영문과 완전 호환, 한 파일에서 섞어도 됨:
  show=`보여주기·출력·보이기·찍기·말하기` · ask=`물어보기·묻기` · if=`만약·만일·가령` ·
  else=`아니면·아니라면·그밖에·그외` · repeat=`반복·되풀이` · for=`순회·각각·모든` · in=`안에` ·
  as=`마다·로·으로` · fn=`함수·기능·정의` · return=`돌려주기·반환·결과·내보내기` ·
  and=`그리고·또한·이고` · or=`또는·혹은` · not=`아님·부정` · try=`시도·해보기` · catch=`잡기·붙잡기` ·
  end=`끝·마침` · const=`상수·불변·고정` · use=`사용·가져오기·불러오기` · raise=`던지기·발생` ·
  match=`분기·고르기` · when=`경우·케이스` · assert=`확인·단언` · between=`사이·범위` · python=`파이썬`
- **한국어 내장함수**: `문자`=text · `숫자`=number · `참거짓`=boolean · `걸러내기`=filter ·
  `변환`=map · `모으기`=reduce · `합계`=sum_of · `평균값`=avg · `묶기`=group_by ·
  `앞에서`=take · `중복제거`=unique · `살펴보기`=inspect · `지켜보기`=watch …

## 2. 값과 자료형

```poi
name = "POI"        # 문자열 (Text)
age = 16            # 정수 (Int)
height = 172.5      # 실수 (Float)
alive = true        # 불리언 (true / false)
nothing = null      # 없음
users = ["시원", "예성"]         # 배열 (List)
user = { name: "시원", age: 16 } # 객체 (Box - 점 접근 되는 dict)
```

객체 접근은 점으로: `user.name` (파이썬처럼 `user["name"]` 안 해도 됨).
`show` 나 문자열 보간에서 `true/false/null` 로 표시된다 (파이썬 `True/None` 아님).

## 3. 변수 · 상수 · 선택적 정적 타입

```poi
x = 10
const PI = 3.14159      # 진짜 상수 — 다시 대입하면 컴파일 오류 (P019)

name: Text = "시원"     # 타입 표기 — 안 쓰면 무시, 쓰면 검사 가능
나이: 정수 = 16          # 한국어 타입명도 됨
```

`const` 로 선언한 이름에 다시 `=` 하면 `POI Error P019`. 값을 바꿔야 하면 `const` 를 빼세요.

### 구조 분해 (v1.10)

```poi
user = { name: "시원", age: 16 }
{ name, age } = user           # name = user.name;  age = user.age
[a, b, c] = [10, 20, 30]       # 순서대로
[첫, 둘] = 목록
```

**타입은 옵션이다.** 안 쓰면 그냥 동적 언어. 쓰면 `poi check --types` 로 검사한다:

```bash
poi check --types 파일.poi     # 타입 오류 있으면 exit 1
poi run --types 파일.poi       # 경고만 찍고 그냥 실행
```

- 타입명: `Int Float Number Text Bool List Map Fn Any Null` · `List<T>` · `Int?`(nullable)
- 한국어: `정수 실수 숫자 문자 문자열 참거짓 목록 배열 사전 맵 객체 함수 아무거나`
- 잡는 것: 선언 불일치(`x: Int = "hi"`), 반환 타입 불일치, 인자 타입·개수 불일치, `Text + Int` 등
- **오탐 안 한다** — 양쪽 타입이 확실할 때만. `Any` 는 항상 통과.
- 함수:

```poi
fn 세금(가격: Int, 율: Float) -> Float
    return 가격 + 가격 * 율
```

## 4. 출력 · 입력

```poi
show "Hello"
show 1 + 2
show "이름은 {name}, 나이는 {age}"   # 문자열 보간
show("괄호도 허용")

answer = ask "질문: "               # 항상 문자열 반환
n = number(ask "숫자: ")            # 숫자로 변환
```

**보간 규칙**: `{ ... }` 안이 올바른 POI 표현식이면 값으로 치환하고, 아니면(JSON 등) 글자 그대로 둔다.

## 5. 연산자

| 종류 | 연산자 |
|---|---|
| 산술 | `+ - * / %` |
| 비교 | `== != < > <= >=` (`a < b < c` 연쇄 가능) |
| 사람식 비교 | `x is 5`, `x is not 5`, `x between 1 and 10` |
| 논리 | `and or not` (`&& || !` 도 됨) |
| null 병합 | `a ?? b` — a 가 null 이면 b |
| null 안전 접근 | `a?.b` — a 가 null 이거나 b 가 없으면 null |
| 삼항식 | `값 if 조건 else 다른값` (파이썬과 같은 순서) |
| 람다 | `x => x * 2`, `(a, b) => a + b` — 값으로 |
| 파이프라인 | `x |> f`, `x |> f(a)` → `f(x)`, `f(x, a)` |

### 함수형 데이터 처리 (파이프라인용 표준 함수)

전부 목록을 첫 인자로 받는다.

```poi
nums
    |> filter(x => x > 0)
    |> map(x => x * x)
    |> sort_desc
    |> take(3)
```

`map filter reject reduce each find find_index count_where any_of all_of
sort_by sort_desc group_by partition take drop take_while drop_while unique
flatten chunk zip_with sum_of avg min_of max_of count_of reverse_of
range_list repeat_list`

## 5.5 블록 — 여러 방식 (섞어도 됨)

POI 의 블록은 **다섯 가지**로 쓸 수 있고, 한 파일에서 **섞어도 된다**. 무엇도 강제하지 않는다.
**권장은 `{ }` 또는 들여쓰기.** `end` · 콜론 한 줄은 v2.0 에서 비권장 예정 (`poi fmt` 도 이 둘은 건드리지 않는다).

```poi
if x > 0 { show "양수" }          # 1) 중괄호
if x > 0: show "양수"             # 2) 콜론 — 한 줄
if x > 0                          # 3) end 로 닫기
show "양수"
end
if x > 0                          # 4) 들여쓰기 (콜론도 end 도 없이 — 파이썬처럼)
    show "양수"
else
    show "음수"
a = 1; b = 2; show a + b          # 5) 세미콜론으로 한 줄에 여러 문장
```

**규칙**: 여는 키워드(`if`/`fn`/`repeat`/`for`/`try`) 다음 첫 문장의 열이 여는 키워드보다
깊으면 → 들여쓰기 블록(뒤따르는 덜 들여쓴 줄에서 끝). 아니면 → `end` 로 닫는 형태.
어느 방식이든 뒤에 `end` 가 있으면 그냥 먹는다(호환).

`if / else if / else` 는 체인 전체를 하나의 `end`(또는 dedent)로 닫는다.
`fn` `repeat` `for` `try/catch` 도 같은 3방식을 쓴다. 들여쓰기는 순전히 장식이다.

## 6. 조건문

```poi
if age >= 18 {
    show "성인"
} else if age >= 13 {
    show "청소년"
} else {
    show "어린이"
}
# 또는 중괄호 없이:
if age >= 18
    show "성인"
else if age >= 13
    show "청소년"
else
    show "어린이"
end

if name is "시원" { show "어서와" }
if age between 10 and 19 { show "10대" }
```

## 6.5 match / when — 패턴 매칭

```poi
match x {
    when 1 { show "하나" }
    when 2, 3 { show "둘 또는 셋" }        # 여러 값
    when > 100 { show "큼" }               # 비교 패턴 (> < >= <= == !=)
    when between 4 and 10 { show "중간" }
    else { show "그밖에" }
}
```

`{ }` · `:` 한 줄 · `end` 다 된다. 한국어로는 `분기` / `경우` / `그밖에`.

### match 식 — 값을 돌려준다 (v1.8)

```poi
grade = match score {
    when >= 90 => "A"
    when >= 80 => "B"
    when >= 70 => "C"
    else => "F"
}
```

절마다 `=> 식` 하나. 통계문 `match` (절이 `{ }` 블록)와 구분된다 — `=>` 를 쓰면 식.

## 7. 반복문

```poi
users = ["시원", "예성"]

repeat 10 {           # 10번
    show "안녕"
}
repeat 10 as i {      # 인덱스 0..9
    show i
}
for user in users {   # 배열 순회
    show user
}
for i in 1..10 { show i }     # 범위 1..10 (양끝 포함)
for i in 1..<10 { show i }    # 1..<10 (10 미포함)

n = 3
while n > 0 { n = n - 1 }     # 조건 반복
```

- `1..10` / `1..<10` 는 식으로도 쓸 수 있다 (`nums = 1..5` → `[1,2,3,4,5]`).
  끝이 시작보다 작으면 빈 리스트 (`5..1` → `[]`). 역순은 `reverse_of(1..10)`.
- `break` / `continue` — 가장 안쪽 반복문에서 탈출 / 다음 회로. 반복문 밖이면 컴파일 오류 (P018).

## 8. 함수

```poi
fn add(a, b) {
    return a + b
}
fn double(x) => x * 2                    # 한 줄 함수
fn greet(name, greeting = "안녕") {      # 기본값
    return greeting + ", " + name
}
```

## 9. 배열 · 문자열 편의 기능

문자열: `.length .is_empty .upper() .lower() .trim() .reverse() .contains(s) .starts_with(s) .ends_with(s) .replace(a,b) .split(sep) .words()`

배열: `.length .is_empty .first .last .add(x) .remove(x) .contains(x) .reverse() .sort() .join(sep)`

객체: `.length .keys() .values() .has(key)` + 점 접근

> 참고: 파이썬 기본 메서드(`.append`, `.strip` 등)도 그대로 쓸 수 있다.

## 10. 오류 처리

```poi
try {
    text = file.read("hello.txt")
} catch error {
    show "실패: {error}"
}
```

`catch error` 로 잡힌 값은 사람이 읽기 좋은 문자열이면서 `.message` · `.type` 도 갖는다.

직접 던지기 — 문자열 또는 오류 타입:

```poi
raise "나이는 음수일 수 없습니다"
raise ValueError("잘못된 값")
raise FileError("파일 없음")     # Error ValueError TypeError NameError KeyError
                                 # IndexError RuntimeError FileError AuthError
                                 # NotFoundError PermissionError TimeoutError
```

### 타입 있는 catch (v1.8)

```poi
try {
    raise ValueError("잘못된 값")
} catch ValueError as e {
    show e.message      # "잘못된 값"
    show e.type         # "ValueError"
}
```

`catch <타입> as e` 는 그 타입(및 `Error`/`Exception`)만 잡고, 다르면 **그대로 다시 던진다**
(바깥 `try` / 상위로). 안 잡힌 `raise ValueError("x")` → `POI Error P300  [ValueError] x`.

## 10.5 테스트 (`test` / `assert` / `poi test`)

```poi
fn add(a, b) => a + b

test "덧셈"
assert add(2, 3) == 5
assert add(0, 0) == 0
assert add(2, 2) == 4, "덧셈 결과가 잘못됐습니다"
end
```

`poi test 파일.poi` 로 실행 → 통과/실패 요약, 실패 시 exit 1.
쉼표 뒤에 실패 설명을 붙일 수 있으며, 조건이 실패할 때만 설명 식을 평가한다.
`poi run` 에서는 `test` 블록을 정의만 하고 실행하지 않는다.

## 10.7 다른 POI 파일 불러오기

```poi
use "./유틸.poi" as u      # 경로는 현재 파일 기준
show u.함수(1, 2)
```

파이썬 파일은 `use pyfile "./x.py"`, 파이썬 라이브러리는 `use py:이름`.

### 재사용 모듈 — `use pkg:이름` (v1.11)

```poi
use pkg:도형          # ./poi_modules/도형/main.poi  →  또는 __init__.poi / <이름>.poi / <이름>.py
show 도형.넓이(10, 4)
```

찾는 순서: `./poi_modules/` → `~/.poi/modules/` → `POI_PATH`(경로 목록). `export` 를 쓴 모듈은 명시한 것만 공개.

### 파이썬 의존성 — `poi add` (v1.11)

```bash
poi add numpy pillow      # 프로젝트 .venv 에 설치 + poi.toml [dependencies] 기록
poi remove numpy
poi install               # poi.toml 의 의존성 전부
```

`.venv` 가 있으면 `poi run` 이 자동으로 그 site-packages 를 import 경로 앞에 넣는다.

### 3D 웹 — `scene3d` (v1.15)

선언형 3D 씬 그래프 → 자체 완결 HTML(Three.js 는 cdnjs, 셋업 JS 인라인). 서버 불필요.

```poi
장면 = scene3d.scene({ bg: "#0b0e14", camera: [4,3,7], fov: 55 })
scene3d.box(장면,    { color: "#5b9dff", spin: true })
scene3d.sphere(장면, { pos: [2.6,0,0], color: "#37d39b", float: true })
scene3d.torus(장면,  { pos: [-2.6,0,0], color: "#ffb454", spin: true, spinSpeed: 1.6 })
scene3d.light(장면, "sun")          # "ambient" · "point" 도. { pos, intensity }
scene3d.orbit(장면);  scene3d.autorotate(장면);  scene3d.grid(장면)
html scene3d.render(장면, { height: 480 })          # webapp{} / render() 안에서
# file.write("3d.html", scene3d.page(장면))         # 완전한 문서로
```

도형 `box sphere plane cylinder cone torus dodeca` · `model(url)` · `light(kind)`.
노드 옵션: `pos scale rotate color size` + 애니메이션 `spin`(`spinSpeed`) `float` `pulse`.
한국어 별칭 `삼차원` · `입체`.

### htmx-lite — 새로고침 없는 부분 갱신 (v1.15)

라우트가 HTML 조각을 돌려주면 클라이언트가 지정한 자리에 끼운다. `render()` 결과에
`data-poi-*` 가 있으면 ~1KB 런타임을 자동 주입.

```html
<button data-poi-get="/frag" data-poi-target="#slot">불러오기</button>
<div id=slot data-poi-load="/stats" data-poi-every="3000"></div>
<form data-poi-post="/save" data-poi-target="#msg">…</form>
```
`data-poi-swap` = `inner`(기본) · `outer` · `append` · `prepend`.

### 템플릿 `{% component %}` · 파일 업로드 · 정적 굽기 (v1.15)

- `{% component "card.html" title="시원" n=95 %}` — 인자를 넘겨 부분 템플릿 렌더.
- multipart 업로드 — `body.files` → `[{ name, filename, content_type, data, text, size }]`.
- `poi build --site 앱.poi -o dist` — 파라미터 없는 GET 라우트를 정적 HTML 로. `static` 폴더도 복사.

### 컴파일 캐시 (v1.13)

안 바뀐 `.poi` 는 렉싱·파싱·트랜스파일·`compile()` 을 건너뛴다 — `~/.poi/cache/`
(또는 `POI_CACHE_DIR`). `poi cache` 로 상태, `poi cache clear` 로 비움, `poi run --no-cache`
또는 `POI_NO_CACHE=1` 로 끔. 안전 모드는 캐시를 쓰지 않는다.

### 웹 전문화 (v1.13)

- **`render(name, data)`** — `views/` · `templates/` · cwd 에서 템플릿을 찾아 HTML 응답.
  `{{ 식 }}` (자동 이스케이프; `{{ x | raw }}` 는 그대로), `{% for x in xs %}…{% endfor %}`,
  `{% if 조건 %}…{% endif %}`, `{% include "부분.html" %}`.
- **`respond`** 에 메서드: `respond.json(obj,status)` · `.text` · `.html` · `.status(code)` ·
  `.error(code,msg)` · `.file(path,download_as)` · `.redirect(to)`.
- **`auth`** (서명 쿠키): `auth.issue(claims,days)` → Set-Cookie 값, `auth.current(headers)` →
  claims(Box)/null, `auth.require(headers,to)` → redirect/null, `auth.guard(to)` → 미들웨어 함수,
  `auth.hash(pw)` / `auth.check(pw,h)` (PBKDF2), `auth.logout()`.
- **미들웨어**: `on_request(fn)` — 요청 전, `fn(req)` 가 응답을 돌려주면 거기서 끝(가드).
  `on_response(fn)` — 핸들러 뒤, `fn(req, result)` 가 돌려준 값으로 교체. `req` =
  `Box{ path, method, query, body, headers, params, ip }`.
- 안전 모드에서 `render`·`auth`·`on_request`·`on_response` 차단.

### GUI 전문화 — `uikit` (v1.13)

- `uikit.bind(widget, state, "field")` — 양방향 데이터 바인딩.
- `uikit.form(parent, fields, on_submit?, submit_text?)` — `fields = [{name,label?,type?,options?,required?,value?}]`
  (`type` ∈ text·password·number·check·select). 돌려주는 Box: `.get(name)` `.set(name,v)`
  `.values()` `.errors()` `.valid()` `.submit()`.
- `uikit.chart(parent, "bar"|"line", data, w?, h?, title?)` — `data = [값…]` 또는 `[[라벨,값]…]`.
- `uikit.toast(win, msg, kind?, ms?)` (kind ∈ info·ok·warn·error) · `uikit.card(parent, title?)` →
  안쪽 프레임 · `uikit.split(parent, "h"|"v")` → PanedWindow (`.add(자식)`).

### 폴리글롯 — 파이썬 문법 흡수 (v1.12)

파이썬 습관이 오류가 아니라 그대로 동작한다: `def`/`func`/`function`/`fun` = `fn`,
`elif` = `else if`, `True`/`False`/`None` = `true`/`false`/`null`, `lambda a, b: 식` =
화살표 함수, `pass` = 무동작 문장, `print(...)` = 파이썬 `print` 호환 출력, `f"..."` =
접두사만 무시(POI 문자열은 원래 보간). `//` `/* */` 주석, `;` 문장 구분도 이미 됨.
C·자바는 `use py:ctypes` / `use py:jpype` / `python { }` 로.

### 블록 화살표 함수 (v1.12)

`x => 식` 뿐 아니라 `(a, b) => { 문장들 }` 도 된다 (컴파일러가 이름 있는 함수로 올린다).

### 동시성 — `task` · `background` · `every` (v1.12)

```poi
fn 제곱(x) => x * x
show task.all(제곱, [1, 2, 3, 4])       # [1, 4, 9, 16]  전부 병렬
h = task.run(무거운작업)                 # 바로 시작, 핸들
show task.wait(h)                       # 결과 (오류는 그대로 다시 던짐)

ch = task.channel()                     # 스레드 사이 큐
task.run(() => ch.send(1))
for v in ch { show v }                  # close 까지 순회

background { 긴계산() }                  # 백그라운드 스레드
every 1 second { 상태.틱 = 상태.틱 + 1 } # 프로그램이 사는 동안 반복
every 500 ms { ... }                    # ms · sec/second(s) · min/minute(s) · hour(s) · 초 · 분 · 시간
```

`task`: `run · wait · gather · all(fn,목록) · race([...]) · map(fn,목록,workers=8) ·
sleep(초) · every/after(초,fn)→타이머(.stop()) · channel()(.send .recv .close .take_all, for 순회) ·
lock()(.run(fn)) · cpu_count()`. 스레드 기반 — `fn` 처럼 바깥 변수는 읽기만, 공유 상태는 Box 로.

### 네트워크 — `http` · `net` (v1.12)

```poi
r = http.get("https://api.example.com/x", headers: { Authorization: 키 })
show r.status                          # 200 ;  r.ok / r.text / r.json / r.headers / r.url
http.post(url, json: { name: "시원" }) # body: 는 폼, json: 는 JSON
http.download(url, "big.zip")

s = net.tcp("example.com", 80)
s.send("GET / HTTP/1.0\r\n\r\n")
show s.line()
net.listen(9010, (conn) => conn.send("hi"))
```

응답은 `Box{ status, ok, text, json, headers, url }` — 4xx/5xx 도 예외 없이 응답으로 돌려준다.
한국어 별칭: `작업`(task) · `요청`(http) · `망`/`네트워크`(net). 안전 모드 전부 차단.

### 재현 가능한 설치 — `poi.lock` (v1.12)

`poi add` / `poi install` 은 설치 후 `poi.lock` 에 정확한 버전을 적는다. `poi install` 은
lock 이 있으면 그 버전으로 좁혀 설치하고, `poi install --frozen` 은 `poi.lock` 만 그대로 설치한다.

### export (v1.8)

```poi
# 유틸.poi
export fn add(a, b) => a + b
export const V = "1.8"
fn _내부() => 42            # export 안 함 → 다른 파일에서 안 보임
```

파일에 `export` 가 하나라도 있으면 **명시한 것만** 공개된다. 없으면 예전처럼 전부 공개.

## 11. 파이썬 상호운용

```poi
use py:numpy as np           # import numpy as np
use py:requests              # import requests
use pyfile "./ai.py"         # ai.py 를 모듈로 로드 → ai.predict(...)

python {                     # 파이썬 코드 그대로
    import sys
    print(sys.version)
}
```

`python { }` 안에서 만든 변수는 이후 POI 코드에서 그대로 보인다.

## 12. 표준 모듈 (import 없이)

| 모듈 | 함수 |
|---|---|
| `file` | `read(p) write(p,s) append(p,s) exists(p) lines(p) delete(p) list(dir)` |
| `json` | `parse(s) stringify(o, pretty) read(p) write(p,o)` |
| `web`  | `get(url, headers, params) post(url, body, headers) download(url, p)` → `.text .status .json .ok` |
| `math` | `pi e tau sqrt floor ceil round abs pow min max sum sin cos tan log random randint pick clamp` |
| `time` | `now() today() timestamp() sleep(s) format(dt, fmt)` |
| `regex` | `match(p,t) all(p,t) replace(p,t,r) split(p,t) test(p,t)` |
| `csv` | `parse(text, header) format(rows) read(path) write(path, rows)` |
| `datetime` | `now() parse(s,fmt) format(d,fmt) add(d, days=…) diff_days(a,b) parts(d)` |
| `random` | `int(a,b) float() range(a,b) choice(xs) sample(xs,k) shuffle(xs) chance(p) seed(n)` |
| `stats` | `mean median mode stdev variance sum min max range` (모두 `(xs)`) |
| `env` | `get(name, default) set(name, v) has(name) all()` (안전 모드 차단) |
| `shell` | `run(cmd, stdin, timeout)` → `{out,err,code,ok}` · `text(cmd)` → stdout (안전 모드 차단) |
| `electronics` / `arduino` | `ports connect/arduino mock voltage adc ohm series parallel divider sample` (실제 보드는 pyserial) |
| `security` | `hash sha256 file_hash hmac constant_equal entropy password_report analyze_headers port_open scan_ports` (허가된 환경 전용) |

### 백엔드 · 보안 (v1.7)

| 모듈 | 함수 |
|---|---|
| `crypto` | `sha256/sha512/sha1/md5/blake2(s) hmac(k,m,algo) base64_encode/decode hex_encode/decode random_bytes(n) token(n) uuid() constant_eq(a,b)` |
| `password` | `hash(pw)` → `pbkdf2_sha256$…` · `verify(pw, stored)` (상수시간) · `strong(pw)` |
| `jwt` | `sign(payload, secret, expires_in?)` · `verify(token, secret)` → payload/`null` · `decode(token)` (HS256) |
| `path` | `join(*p) base(p) dir(p) ext(p) stem(p) abs(p) norm(p) exists/is_file/is_dir(p) parts(p) home() cwd() size(p)` |
| `url` | `parse(u)` → `{scheme,host,port,path,query,fragment}` · `build(…)` · `encode/decode(s)` · `query_encode/parse` · `join(base,rel)` |
| `html` | `escape(s) unescape(s) strip_tags(s) attr(s)` |
| `compress` | `gzip/gunzip zlib/unzlib zip_read(path) zip_make(path, files)` (안전 모드 차단) |
| `log` | `debug/info/warn/error(*m)` · `level(name)` |
| `cache` | `get(k,default) set(k,v,ttl) has(k) clear() ttl(k,sec,fn) memo(fn)` |
| `bench` | `time(fn)` → 초 · `run(fn, times)` → `{total,avg,per_sec,runs}` |
| `dotenv` | `load(path)` → 읽은 값 Box, `os.environ` 에도 반영 (안전 모드 차단) |
| `system` | `platform() release() python_version() poi_version() cpu_count() hostname() pid() cwd() args() env(name)` (안전 모드 차단) |
| `uuid` | `v4() hex() short() is_valid(s)` |
| `uikit` | `window row column label button entry slider canvas listbox text statusbar menu ask_open ask_save ask_color alert confirm every on run close` · `state(v)` + `watch(st, fn)` — 명령형 GUI. 안전 모드 차단 |
| `ai` | `chat(prompt, system:, model:) ask(p) code(p, lang) summarize(t) backends() install()` — 하온과 같은 백엔드(Groq → 로컬 Ollama). 안전 모드 차단 |

`shell` 로 node·go 바이너리·git·ffmpeg 등 **어떤 언어·도구든** 부른다. `python { }` · `use py:` ·
`use pyfile` · `use "./x.poi"` 와 함께 POI 는 사실상 모든 것과 이어진다.

명시하고 싶으면 `use file` / `use json` / `use crypto` / ... 도 가능. 한국어 별칭:
`암호`(crypto) · `비밀번호`(password) · `경로`(path) · `주소`(url) · `압축`(compress) · `기록`(log) · `캐시`(cache) · `시스템`(system).

## 12.5 데이터베이스 — `database(...)` (import 없이)

0설정 SQLite. 결과 행은 점 접근이 되는 `Box`.

```poi
db = database("app.db")                     # 파일 · 또는 database(":memory:")
db.exec("create table note(id integer primary key, body text)")
db.run("insert into note(body) values(?)", ["안녕"])   # → {changed, id}
db.query("select * from note order by id")   # → [{id: 1, body: "안녕"}]
db.one("select * from note where id = ?", [1])   # → Box 또는 null
db.value("select count(*) from note")            # → 스칼라
db.insert("note", { body: "빠르게" })            # → 새 id
db.tables()                                       # → ["note"]
```

`?` 파라미터는 리스트로, 이름 파라미터(`:name`)는 객체로. 안전 모드에서는 `database(...)` 차단.

## 12.6 웹 — `server` / `webapp` (v1.6, v1.7 강화)

```poi
server {
    get "/" { return "<h1>안녕</h1>" }                  # 문자열 → HTML
    get "/api/합/:a/:b" { return { 합: number(params.a) + number(params.b) } }  # dict → JSON
    post "/echo" { return body }
    static "./public"
}
```

핸들러에 주입되는 것: `params`(경로 `:id`) · `query` · `body`(JSON·폼 자동 파싱) · `headers` · `method`.
헬퍼: `respond(body, status, headers)` · `redirect("/x")` · `html("<raw>")` ·
`cookie("sid", token)`(서명·HttpOnly·SameSite) · `session.read(headers, "sid")` → 위조 시 `null`.

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

노드: `heading` `subtitle` `text` `badge` `alert` `notice` `divider` `spacer` `image` `link`
`card` `row` `column` `form` `field` `input` `password` `textarea` `select` `checkbox` `button` `html`
— 안에서 `for` / `if` 가능. `state` + `action` = 폼 제출 → 액션 → 상태 갱신 → 재렌더(POST-redirect-GET).

기본 제공: HTML 자동 이스케이프 · **CSRF 토큰 자동** · 보안 헤더(CSP·X-Frame-Options·nosniff·Referrer-Policy) ·
본문 크기 제한 · 정적 경로 traversal 차단 · 정적 파일 ETag/`Cache-Control`(304) ·
**IP 레이트 리밋**(`POI_RATE_MAX`/`POI_RATE_WINDOW`, 초과 시 429) · **gzip 응답 자동 압축** ·
설정 0으로 예쁜 반응형·다크 대응 페이지.

`poi run app.poi` → 서버가 뜬다 (기본 `:8080`, `poi run --port 3000`). 안전 모드에서는 `server`/`webapp` 차단.

## 13. GUI (선언형, tkinter 기반)

```poi
app "제목" {
    window {
        title: "POI 앱"
        size: 480x320
        center: true
    }

    state username = ""

    column {                     # 세로 배치 (row 는 가로)
        title "로그인"           # 큰 제목
        text "설명 문구"

        input "아이디" -> username        # 입력 → 변수 바인딩
        password "비밀번호" -> pw

        button "확인" {
            show "눌림: {username}"
        }
    }

    on "start" { show "앱 시작됨" }       # start / close / key ...
}
```

지원 노드: `window` `text` `title` `button` `row` `column` `card` `input` `password` `state` `on` + 블록 안에서 `for` / `if` / 일반 문장.

`app.close()` 로 창을 닫는다. GUI 는 데스크톱 환경 + tkinter 필요.

## 14. 디버깅 (요약 — 자세히는 DEBUGGING.md)

코드 안: `inspect(x)` (구조 출력 + x 반환) · `watch(x)` (출력하며 흘려보냄) · `pause()` (그 자리서 멈춤).

실행할 때:

```bash
poi run x.poi --trace      # 문장마다 줄번호·소스
poi run x.poi --vars       # + 변수 변화
poi run x.poi --explain    # 오류 시 그때 값들까지
poi debug x.poi            # 위 전부
```

## 15. 명령어

| 명령 | 하는 일 |
|---|---|
| `poi run [파일]` | 실행 (기본 `src/main.poi` → `main.poi` → `app.poi`) |
| `poi run 파일 --emit-python` | 낮춰진 중간 표현 출력 |
| `poi run 파일 --safe [--time N]` | 샌드박스 실행 (python{}·use py·파일·네트워크 차단, 시간 제한) |
| `poi debug 파일` | 추적 + 변수 + 사후 분석 |
| `poi test 파일` | 파일 안의 `test` 블록 실행·채점 |
| `poi build 파일 [-o 이름]` | 단일 실행파일로 (PyInstaller 필요) |
| `poi build --app idle` | POI IDLE 을 `poi-idle.exe` 로 빌드 |
| `poi idle [파일]` | POI IDLE — 라이트 모드·메뉴바·웹서버 임시 켜기·하온(로컬 에이전트) |
| `poi photo [사진]` | POI 로 작성한 사진 편집기 (Pillow 필요) |
| `poi add / remove / install` | 프로젝트 파이썬 의존성 (`.venv` + `poi.toml [dependencies]`) |
| `poi fmt [파일\|.] [--check]` | 소스 정리 (탭·공백·블록 깊이). end/콜론 스타일은 공백만 |
| `poi lint [파일\|.] [--strict]` | 안 쓴 변수(POI-W101)·const 재선언(W102)·죽은 코드(W103) |
| `poi serve [폴더] [--port]` | 플레이그라운드 서버 (정적 서빙 + 안전 실행 `/run`) |
| `poi exercises [번호\|--topic\|--show]` | 연습문제 300제 실행·채점 |
| `poi new <이름>` | 프로젝트 폴더 생성 |
| `poi check <파일\|.> [--types]` | 문법(+선택적 타입) 검사. `.` 면 폴더 전체 |
| `poi repl` | 대화형 셸 (부팅 배너) |
| `poi update` | 새 버전 확인 / 올리기 |
| `poi version` | 버전 |

환경변수: `POI_NO_UPDATE_CHECK=1` (버전 확인 끄기) · `POI_NO_BANNER=1` (배너 끄기).

### 안전 모드 (`--safe`)

모르는 사람의 코드를 받아 실행할 때(플레이그라운드) 쓴다. 막는 것:
`python { }` · `use py:` · `use pyfile` · `file.*` · `web.*` · `shell.*` · `env.*` · `system.*` · `compress.*` · `dotenv.*` ·
`database(...)` · `server`/`webapp` · `http`/`net`/`task` · `background`/`every` · `ai` · `uikit` ·
위험한 파이썬 내장(`open`/`eval`/`exec`/`__import__` 등) ·
무한 루프(벽시계 제한) · 출력 폭탄(바이트 상한). `crypto`·`password`·`jwt`·`path`·`url`·`html`·`cache`·`bench`·`log` 는 허용.
`poi serve` 는 여기에 **별도 프로세스 격리**를 더한다.

## 16. 프로젝트 구조

```
my-app/
├─ poi.toml        # 프로젝트 설정
├─ src/main.poi    # 진입점
├─ assets/
└─ tests/
```

`poi run` 은 `src/main.poi` → `main.poi` → `app.poi` 순으로 진입점을 찾는다.

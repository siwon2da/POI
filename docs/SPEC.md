# POI v1.1 문법 명세

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
- **예약어**: `if else for in fn return const show ask use python try catch true false null is between and or not repeat as`
  (GUI 단어 `app window text button ...` 은 예약어가 아니라 문맥으로 인식)

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

## 3. 변수 · 상수

```poi
x = 10
const PI = 3.14159      # 관례상 상수 (v0.1 에선 재대입 막지 않음)
name: Text = "시원"     # 타입 표기 가능 (v0.1 에선 검사 안 함)
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
| 파이프라인 | `x |> f`, `x |> f(a)` → `f(x)`, `f(x, a)` |

## 6. 조건문

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
```

## 7. 반복문

```poi
repeat 10 {           # 10번
    show "안녕"
}
repeat 10 as i {      # 인덱스 0..9
    show i
}
for user in users {   # 배열 순회
    show user
}
```

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

`catch` 로 잡힌 값은 사람이 읽기 좋은 문자열로 변환된다.

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

명시하고 싶으면 `use file` / `use json` / ... 도 가능.

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
| `poi debug 파일` | 추적 + 변수 + 사후 분석 |
| `poi new <이름>` | 프로젝트 폴더 생성 |
| `poi check <파일>` | 문법만 검사 |
| `poi repl` | 대화형 셸 |
| `poi update` | 새 버전 확인 / 올리기 |
| `poi version` | 버전 |

환경변수 `POI_NO_UPDATE_CHECK=1` — 자동 새 버전 확인 끄기.

## 16. 프로젝트 구조

```
my-app/
├─ poi.toml        # 프로젝트 설정
├─ src/main.poi    # 진입점
├─ assets/
└─ tests/
```

`poi run` 은 `src/main.poi` → `main.poi` → `app.poi` 순으로 진입점을 찾는다.

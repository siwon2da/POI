# 변경 이력

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

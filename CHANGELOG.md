# 변경 이력

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

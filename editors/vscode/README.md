# POI Language Support (Preview)

`.poi` 파일에 구문 강조 · 진단 · 자동완성 · 호버 · 정의로 이동을 붙인다.

## 설치 (npm 없이 — 가장 간단)

이 폴더(`editors/vscode`)를 통째로 복사해서 확장 폴더에 넣고 VS Code 를 다시 시작한다.

- Windows: `%USERPROFILE%\.vscode\extensions\poi-language\`
- macOS/Linux: `~/.vscode/extensions/poi-language/`

```bash
# 예 (저장소 루트에서)
cp -r editors/vscode ~/.vscode/extensions/poi-language
```

그다음 `.poi` 파일을 열면 자동으로 켜진다. `poi` 명령이 PATH 에 있어야 하며,
없으면 설정에서 `poi.path` 에 절대경로를 넣는다.

## 개발용 실행

VS Code 로 `editors/vscode` 폴더를 열고 **F5** → 확장 개발 호스트가 뜬다.

## `.vsix` 패키지 (선택)

```bash
npm install -g @vscode/vsce
cd editors/vscode
vsce package        # poi-language-0.1.0.vsix 생성 → code --install-extension poi-language-0.1.0.vsix
```

## 완전한 LSP 모드 (실험적)

`poi lsp` 는 stdio LSP 서버다 (Neovim·Helix 등에서도 쓸 수 있다).
VS Code 에서 쓰려면 `vscode-languageclient` 를 넣고 설정에서 `poi.lsp` 를 켠다:

```bash
cd editors/vscode && npm install vscode-languageclient
```

설정 `"poi.lsp": true` → 확장이 `poi lsp` 프로세스에 연결한다.

## 제공 기능

| 기능 | 내장 모드 | LSP 모드 |
|---|---|---|
| 구문 강조 (TextMate) | ✓ | ✓ |
| 진단 (문법 P-코드 · 린트 · 타입) | 저장 시 `poi check` | 입력하는 즉시 |
| 자동완성 (키워드 · 표준 모듈 · 이 파일의 함수) | ✓ | ✓ |
| 호버 (키워드·모듈 설명) | ✓ | ✓ |
| 정의로 이동 (`fn 이름`) | ✓ | ✓ |
| 문서 심볼 (함수·변수 개요) | ✓ | ✓ |
| 이름 바꾸기 | — | ✓ |

## 명령 (Ctrl+Shift+P)

- `POI: 이 파일 실행` — 터미널에서 `poi run`
- `POI: 문법 검사` — `poi check` 진단 갱신
- `POI: EXE 로 빌드` — `poi build`

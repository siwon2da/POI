"""POI Language Server (LSP, stdio) — 1.9.9 프리뷰.

    poi lsp            # stdin/stdout 으로 LSP 프로토콜

제공: 진단(문법·타입·린트) · 호버 · 자동완성 · 정의로 이동 · 문서 심볼 · 이름 바꾸기.
표준 라이브러리만 쓴다 (외부 의존성 0). VS Code·Neovim·Helix 등에서 붙일 수 있다.
"""
from __future__ import annotations

import json
import re
import sys

from . import __version__

_DOCS = {}            # uri -> text

_KEYWORDS = [
    "if", "else", "for", "in", "fn", "return", "const", "show", "ask", "use",
    "try", "catch", "true", "false", "null", "is", "between", "and", "or",
    "not", "repeat", "while", "as", "end", "raise", "assert", "match", "when",
    "break", "continue", "export", "elif", "pass", "lambda", "background", "every",
    "server", "webapp", "app", "python",
]
_STDLIB = [
    "math", "file", "json", "time", "regex", "csv", "datetime", "random",
    "stats", "crypto", "password", "jwt", "path", "url", "html", "cache",
    "bench", "uuid", "database", "env", "shell", "system", "dotenv", "compress",
    "ai", "uikit", "task", "http", "net", "scene3d", "game", "render", "respond",
    "auth", "on_request", "on_response", "electronics", "arduino", "hardware",
    "security", "security_lab",
]
_HOVER = {
    "fn": "함수 정의.  `fn 이름(인자) { ... }`  또는 한 줄  `fn 이름(인자) => 식`",
    "show": "값 출력.  `show \"안녕 {name}\"`  — 문자열 보간은 `\"{식}\"`",
    "ask": "표준 입력을 문자열로 받는다.  `n = number(ask \"숫자: \")`",
    "const": "진짜 상수. 다시 대입하면 컴파일 오류(P019).",
    "match": "패턴 매칭.  식으로 쓰면 값을 돌려준다:  `x = match v { when >= 90 => \"A\" else => \"F\" }`",
    "use": "`use math` (표준) · `use py:numpy as np` · `use pkg:이름` · `use \"./x.poi\" as u`",
    "server": "내장 HTTP 서버.  `server { get \"/\" { ... } post \"/x\" { ... } }`",
    "webapp": "선언형 페이지.  `webapp \"제목\" { page \"/\" { } action \"/x\" { } }`",
    "task": "동시성.  `task.run(fn)` · `task.all(fn, 목록)` · `task.channel()` · `task.every(초, fn)`",
    "scene3d": "3D 웹.  `장면 = scene3d.scene({})` · `scene3d.box(장면, {spin:true})` · `scene3d.render(장면)`",
    "game": "2D 게임.  `game.window(...)` · `game.sprite(win, {...})` · `game.on_key` · `game.run(win)`",
    "render": "템플릿 렌더.  `render(\"home.html\", { title: \"POI\" })`  — `{{ }}` `{% for %}` `{% if %}`",
    "auth": "서명 쿠키 로그인.  `auth.issue(claims)` · `auth.current(headers)` · `auth.guard(to)`",
    "electronics": "전자·Arduino. `electronics.ports()` · `.arduino(\"COM3\")` · `.mock()` · `.voltage(raw)`",
    "arduino": "`electronics` 별칭. 직렬 센서·digital/PWM 연구용.",
    "security": "방어 보안 연구. 해시·엔트로피·헤더 분석·허가된 로컬/사설망 포트 점검.",
}

# ── JSON-RPC over stdio ──────────────────────────────────────────────

def _read_msg():
    headers = {}
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        line = line.decode("ascii", "replace").strip()
        if line == "":
            break
        if ":" in line:
            k, v = line.split(":", 1)
            headers[k.strip().lower()] = v.strip()
    n = int(headers.get("content-length", 0))
    if n <= 0:
        return None
    body = sys.stdin.buffer.read(n)
    if not body:
        return None
    try:
        return json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None


def _send(obj):
    data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
    sys.stdout.buffer.write(b"Content-Length: %d\r\n\r\n" % len(data))
    sys.stdout.buffer.write(data)
    sys.stdout.buffer.flush()


def _notify(method, params):
    _send({"jsonrpc": "2.0", "method": method, "params": params})


def _reply(mid, result):
    _send({"jsonrpc": "2.0", "id": mid, "result": result})


# ── 언어 기능 ───────────────────────────────────────────────────────

def _diagnostics(text):
    out = []
    from .interpreter import compile_source
    try:
        compile_source(text, "lsp.poi")
    except Exception as e:  # noqa: BLE001
        ln = max(0, (getattr(e, "line", 1) or 1) - 1)
        col = max(0, (getattr(e, "col", 1) or 1) - 1)
        out.append({
            "range": {"start": {"line": ln, "character": col},
                      "end": {"line": ln, "character": col + 1}},
            "severity": 1,
            "code": getattr(e, "code", "P000"),
            "source": "poi",
            "message": getattr(e, "message", str(e))
            + (("\n해결: " + e.hint) if getattr(e, "hint", None) else ""),
        })
        return out
    try:
        from .lint import lint_source
        for w in lint_source(text, "lsp.poi"):
            ln = max(0, (w.line or 1) - 1)
            out.append({
                "range": _line_range(text, ln),
                "severity": 2, "code": w.code, "source": "poi", "message": w.msg,
            })
    except Exception:
        pass
    try:
        from .lexer import Lexer
        from .parser import Parser
        from . import typecheck as tc
        prog = Parser(Lexer(text, "lsp.poi").tokenize(), text).parse()
        for f in tc.check(prog):
            if not f.line:
                continue
            ln = max(0, f.line - 1)
            out.append({
                "range": _line_range(text, ln),
                "severity": 2 if f.level == "warning" else 1,
                "code": f.code, "source": "poi-types", "message": f.msg,
            })
    except Exception:
        pass
    return out


def _publish(uri):
    _notify("textDocument/publishDiagnostics",
            {"uri": uri, "diagnostics": _diagnostics(_DOCS.get(uri, ""))})


_FN_RE = re.compile(r"(?m)^\s*(?:fn|def)\s+([^\W\d][\w가-힣]*)\s*\(")
_ASSIGN_RE = re.compile(r"(?m)^\s*(?:const\s+)?([^\W\d][\w가-힣]*)\s*=")


def _word_at(text, line, char):
    lines = text.splitlines()
    if line >= len(lines):
        return ""
    s = lines[line]
    a = char
    while a > 0 and (s[a - 1].isalnum() or s[a - 1] in "_가-힣" or ord(s[a - 1]) > 128):
        a -= 1
    b = char
    while b < len(s) and (s[b].isalnum() or s[b] == "_" or ord(s[b]) > 128):
        b += 1
    return s[a:b]


def _symbols(text):
    syms = []
    for m in _FN_RE.finditer(text):
        ln = text[:m.start(1)].count("\n")
        col = m.start(1) - (text.rfind("\n", 0, m.start(1)) + 1)
        syms.append({"name": m.group(1), "kind": 12,  # Function
                     "range": _rng(ln, col, len(m.group(1))),
                     "selectionRange": _rng(ln, col, len(m.group(1)))})
    for m in _ASSIGN_RE.finditer(text):
        ln = text[:m.start(1)].count("\n")
        if any(s["range"]["start"]["line"] == ln for s in syms):
            continue
        col = m.start(1) - (text.rfind("\n", 0, m.start(1)) + 1)
        syms.append({"name": m.group(1), "kind": 13,  # Variable
                     "range": _rng(ln, col, len(m.group(1))),
                     "selectionRange": _rng(ln, col, len(m.group(1)))})
    return syms


def _rng(ln, col, length):
    return {"start": {"line": ln, "character": col},
            "end": {"line": ln, "character": col + length}}


def _line_range(text, ln):
    """LSP 범위를 실제 줄 길이 안으로 제한하고 앞쪽 들여쓰기는 제외한다."""
    lines = text.splitlines()
    if not (0 <= ln < len(lines)):
        return _rng(max(0, ln), 0, 0)
    line = lines[ln]
    start = len(line) - len(line.lstrip())
    end = len(line)
    return {"start": {"line": ln, "character": start},
            "end": {"line": ln, "character": max(start, end)}}


def _completions(text, line, char):
    items = []
    for k in _KEYWORDS:
        items.append({"label": k, "kind": 14, "detail": "키워드"})
    for m in _STDLIB:
        items.append({"label": m, "kind": 9, "detail": "표준 모듈"})
    for m in _FN_RE.finditer(text):
        items.append({"label": m.group(1), "kind": 3, "detail": "이 파일의 함수"})
    seen = set()
    uniq = []
    for it in items:
        if it["label"] in seen:
            continue
        seen.add(it["label"])
        uniq.append(it)
    return uniq


def _definition(uri, text, line, char):
    w = _word_at(text, line, char)
    if not w:
        return None
    for m in _FN_RE.finditer(text):
        if m.group(1) == w:
            ln = text[:m.start(1)].count("\n")
            col = m.start(1) - (text.rfind("\n", 0, m.start(1)) + 1)
            return {"uri": uri, "range": _rng(ln, col, len(w))}
    return None


def _rename(uri, text, line, char, new_name):
    w = _word_at(text, line, char)
    if not w:
        return None
    edits = []
    for m in re.finditer(r"(?<![\w.])" + re.escape(w) + r"(?![\w])", text):
        ln = text[:m.start()].count("\n")
        col = m.start() - (text.rfind("\n", 0, m.start()) + 1)
        edits.append({"range": _rng(ln, col, len(w)), "newText": new_name})
    return {"changes": {uri: edits}}


# ── 메인 루프 ───────────────────────────────────────────────────────

def main() -> int:
    while True:
        msg = _read_msg()
        if msg is None:
            return 0
        method = msg.get("method")
        mid = msg.get("id")
        params = msg.get("params") or {}

        if method == "initialize":
            _reply(mid, {
                "capabilities": {
                    "textDocumentSync": {
                        "openClose": True,
                        "change": 1,                 # full
                        "save": {"includeText": True},
                    },
                    "hoverProvider": True,
                    "completionProvider": {"triggerCharacters": [".", " "]},
                    "definitionProvider": True,
                    "documentSymbolProvider": True,
                    "renameProvider": True,
                },
                "serverInfo": {"name": "poi-lsp", "version": __version__},
            })
        elif method == "initialized":
            pass
        elif method == "shutdown":
            _reply(mid, None)
        elif method == "exit":
            return 0
        elif method == "textDocument/didOpen":
            d = params["textDocument"]
            _DOCS[d["uri"]] = d["text"]
            _publish(d["uri"])
        elif method == "textDocument/didChange":
            uri = params["textDocument"]["uri"]
            changes = params.get("contentChanges") or [{"text": ""}]
            _DOCS[uri] = changes[-1]["text"]
            _publish(uri)
        elif method == "textDocument/didClose":
            uri = params["textDocument"]["uri"]
            _DOCS.pop(uri, None)
            _notify("textDocument/publishDiagnostics", {"uri": uri, "diagnostics": []})
        elif method == "textDocument/didSave":
            uri = params["textDocument"]["uri"]
            if "text" in params:
                _DOCS[uri] = params["text"]
            _publish(uri)
        elif method == "textDocument/hover":
            uri = params["textDocument"]["uri"]
            p = params["position"]
            w = _word_at(_DOCS.get(uri, ""), p["line"], p["character"])
            txt = _HOVER.get(w) or (f"`{w}` — 표준 모듈" if w in _STDLIB else None)
            _reply(mid, {"contents": {"kind": "markdown", "value": txt}} if txt else None)
        elif method == "textDocument/completion":
            uri = params["textDocument"]["uri"]
            p = params["position"]
            _reply(mid, _completions(_DOCS.get(uri, ""), p["line"], p["character"]))
        elif method == "textDocument/definition":
            uri = params["textDocument"]["uri"]
            p = params["position"]
            _reply(mid, _definition(uri, _DOCS.get(uri, ""), p["line"], p["character"]))
        elif method == "textDocument/documentSymbol":
            uri = params["textDocument"]["uri"]
            _reply(mid, _symbols(_DOCS.get(uri, "")))
        elif method == "textDocument/rename":
            uri = params["textDocument"]["uri"]
            p = params["position"]
            _reply(mid, _rename(uri, _DOCS.get(uri, ""), p["line"],
                                p["character"], params["newName"]))
        elif mid is not None:
            _reply(mid, None)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

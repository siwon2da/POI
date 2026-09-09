// POI Language Support (Preview) — 의존성 0 버전.
// 기본: poi CLI 를 불러 진단·자동완성·호버·정의로 이동을 제공.
// 옵션(poi.lsp=true): vscode-languageclient 가 있으면 poi lsp 서버에 연결.
"use strict";
const vscode = require("vscode");
const cp = require("child_process");
const path = require("path");

let diag;
let client = null;

function poiCmd() {
  return vscode.workspace.getConfiguration("poi").get("path", "poi");
}

function run(args, cwd, input) {
  return new Promise((resolve) => {
    const p = cp.spawn(poiCmd(), args, { cwd, shell: process.platform === "win32" });
    let out = "", err = "";
    p.stdout.on("data", (d) => (out += d));
    p.stderr.on("data", (d) => (err += d));
    p.on("error", () => resolve({ code: -1, out, err: "poi 실행 실패 (poi.path 확인)" }));
    p.on("close", (code) => resolve({ code, out, err }));
    if (input) { p.stdin.write(input); p.stdin.end(); }
  });
}

// poi check 출력에서 진단 파싱
function parseDiagnostics(text) {
  const items = [];
  // "POI Error P0xx" 블록 + "> NN | ..." 프레임
  const re = /POI Error (P\d+)\s*\n\s*\n\s*(.+?)(?:\n[\s\S]*?>\s*(\d+)\s*\|)?/g;
  let m;
  while ((m = re.exec(text))) {
    const line = m[3] ? parseInt(m[3], 10) - 1 : 0;
    items.push(new vscode.Diagnostic(
      new vscode.Range(line, 0, line, 500),
      m[2].trim(), vscode.DiagnosticSeverity.Error));
  }
  // 린트 "  파일:NN  POI-W1xx  메시지"
  const lre = /(POI-W\d+)\s+(.+)/g;
  while ((m = lre.exec(text))) {
    items.push(new vscode.Diagnostic(
      new vscode.Range(0, 0, 0, 0), m[2].trim(),
      vscode.DiagnosticSeverity.Warning));
  }
  return items;
}

async function checkDoc(doc) {
  if (doc.languageId !== "poi") return;
  const cwd = doc.uri.fsPath ? path.dirname(doc.uri.fsPath) : undefined;
  const r = await run(["check", doc.uri.fsPath], cwd);
  if (r.code === 0) { diag.set(doc.uri, []); return; }
  diag.set(doc.uri, parseDiagnostics((r.err || "") + "\n" + (r.out || "")));
}

const KEYWORDS = ["if", "else", "elif", "for", "in", "while", "repeat", "fn", "return",
  "const", "show", "ask", "use", "try", "catch", "match", "when", "break", "continue",
  "export", "raise", "assert", "true", "false", "null", "and", "or", "not", "between",
  "server", "webapp", "app", "background", "every", "lambda", "pass"];
const STDLIB = ["math", "file", "json", "time", "regex", "csv", "datetime", "random",
  "stats", "crypto", "password", "jwt", "path", "url", "html", "cache", "bench", "uuid",
  "database", "env", "shell", "system", "ai", "uikit", "task", "http", "net", "scene3d",
  "game", "render", "respond", "auth", "electronics", "arduino", "hardware", "security",
  "security_lab"];
const HOVER = {
  fn: "함수 정의.  `fn 이름(인자) { ... }`  또는  `fn 이름(인자) => 식`",
  show: "값 출력.  `show \"안녕 {name}\"` — 보간은 `\"{식}\"`",
  match: "패턴 매칭. 식이면 값 반환:  `x = match v { when >= 90 => \"A\" else => \"F\" }`",
  server: "내장 HTTP 서버.  `server { get \"/\" { ... } }`",
  scene3d: "3D 웹.  `scene3d.scene({})` · `scene3d.box(s, {spin:true})` · `scene3d.render(s)`",
  game: "2D 게임.  `game.window(...)` · `game.sprite(w, {...})` · `game.run(w)`",
  task: "동시성.  `task.run` · `task.all(fn, 목록)` · `task.channel()` · `task.every`",
  render: "템플릿.  `render(\"home.html\", { title: \"x\" })` — `{{ }}` `{% for %}` `{% if %}`",
  electronics: "전자·Arduino. `electronics.ports()` · `.arduino(\"COM3\")` · `.mock()` · `.voltage(raw)`",
  security: "방어 보안 연구. 해시·엔트로피·헤더 분석·허가된 로컬/사설망 포트 점검"
};

function activate(context) {
  diag = vscode.languages.createDiagnosticCollection("poi");
  context.subscriptions.push(diag);

  const cfg = vscode.workspace.getConfiguration("poi");

  // 실험적 LSP
  if (cfg.get("lsp", false)) {
    try {
      const lc = require("vscode-languageclient/node");
      client = new lc.LanguageClient("poi", "POI LSP",
        { command: poiCmd(), args: ["lsp"] },
        { documentSelector: [{ language: "poi" }] });
      client.start();
      context.subscriptions.push({ dispose: () => client && client.stop() });
      return; // LSP 가 모든 기능을 담당
    } catch (e) {
      vscode.window.showWarningMessage(
        "poi.lsp=true 인데 vscode-languageclient 가 없어 내장 모드로 동작합니다.");
    }
  }

  // 내장 모드 — 진단
  if (cfg.get("checkOnSave", true)) {
    context.subscriptions.push(
      vscode.workspace.onDidSaveTextDocument(checkDoc),
      vscode.workspace.onDidOpenTextDocument(checkDoc));
    vscode.workspace.textDocuments.forEach(checkDoc);
  }

  // 자동완성
  context.subscriptions.push(vscode.languages.registerCompletionItemProvider("poi", {
    provideCompletionItems(doc) {
      const items = [];
      for (const k of KEYWORDS) {
        const it = new vscode.CompletionItem(k, vscode.CompletionItemKind.Keyword);
        items.push(it);
      }
      for (const m of STDLIB) {
        items.push(new vscode.CompletionItem(m, vscode.CompletionItemKind.Module));
      }
      const txt = doc.getText();
      const re = /(?:fn|def)\s+([^\W\d][\w가-힣]*)/g;
      let mm;
      while ((mm = re.exec(txt))) {
        items.push(new vscode.CompletionItem(mm[1], vscode.CompletionItemKind.Function));
      }
      return items;
    }
  }, ".", " "));

  // 호버
  context.subscriptions.push(vscode.languages.registerHoverProvider("poi", {
    provideHover(doc, pos) {
      const w = doc.getText(doc.getWordRangeAtPosition(pos));
      const md = HOVER[w] || (STDLIB.includes(w) ? "`" + w + "` — 표준 모듈" : null);
      return md ? new vscode.Hover(new vscode.MarkdownString(md)) : null;
    }
  }));

  // 정의로 이동
  context.subscriptions.push(vscode.languages.registerDefinitionProvider("poi", {
    provideDefinition(doc, pos) {
      const w = doc.getText(doc.getWordRangeAtPosition(pos));
      if (!w) return null;
      const txt = doc.getText();
      const m = new RegExp("(?:fn|def)\\s+" + w + "\\b").exec(txt);
      if (!m) return null;
      const at = doc.positionAt(m.index + m[0].indexOf(w));
      return new vscode.Location(doc.uri, at);
    }
  }));

  // 문서 심볼
  context.subscriptions.push(vscode.languages.registerDocumentSymbolProvider("poi", {
    provideDocumentSymbols(doc) {
      const out = [];
      const txt = doc.getText();
      let m;
      const fnRe = /(?:^|\n)\s*(?:fn|def)\s+([^\W\d][\w가-힣]*)/g;
      while ((m = fnRe.exec(txt))) {
        const at = doc.positionAt(m.index + m[0].indexOf(m[1]));
        out.push(new vscode.SymbolInformation(m[1], vscode.SymbolKind.Function, "",
          new vscode.Location(doc.uri, at)));
      }
      return out;
    }
  }));

  // 명령
  const term = () => vscode.window.activeTerminal || vscode.window.createTerminal("POI");
  const file = () => vscode.window.activeTextEditor && vscode.window.activeTextEditor.document.uri.fsPath;
  context.subscriptions.push(
    vscode.commands.registerCommand("poi.run", () => { const f = file(); if (f) { const t = term(); t.show(); t.sendText(`${poiCmd()} run "${f}"`); } }),
    vscode.commands.registerCommand("poi.check", () => { const d = vscode.window.activeTextEditor; if (d) checkDoc(d.document); }),
    vscode.commands.registerCommand("poi.build", () => { const f = file(); if (f) { const t = term(); t.show(); t.sendText(`${poiCmd()} build "${f}"`); } })
  );
}

function deactivate() { return client ? client.stop() : undefined; }

module.exports = { activate, deactivate };

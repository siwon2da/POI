# poi lsp — 프로토콜 왕복 (테스트 러너가 .py 도 실행하면 여기서, 아니면 참고용)
import json
import subprocess
import sys


def _frame(o):
    b = json.dumps(o).encode()
    return b"Content-Length: %d\r\n\r\n" % len(b) + b


def main():
    p = subprocess.Popen([sys.executable, "-m", "poi", "lsp"],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    doc = "fn 더하기(a, b)\n    return a + b\n\nx = 더하기(2, 3)\nnope = 1\n"
    msgs = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        {"jsonrpc": "2.0", "method": "textDocument/didOpen", "params": {
            "textDocument": {"uri": "file:///t.poi", "languageId": "poi",
                             "version": 1, "text": doc}}},
        {"jsonrpc": "2.0", "id": 2, "method": "textDocument/documentSymbol",
         "params": {"textDocument": {"uri": "file:///t.poi"}}},
        {"jsonrpc": "2.0", "id": 3, "method": "shutdown", "params": {}},
        {"jsonrpc": "2.0", "method": "exit", "params": {}},
    ]
    for m in msgs:
        p.stdin.write(_frame(m))
    p.stdin.flush()
    out = p.stdout.read().decode("utf-8", "replace")
    p.wait()
    assert '"capabilities"' in out, "initialize 응답 없음"
    assert "hoverProvider" in out
    assert "POI-W101" in out, "미사용 변수 진단 없음"
    assert "더하기" in out, "documentSymbol 에 함수 없음"
    print("37_lsp OK")


if __name__ == "__main__":
    main()

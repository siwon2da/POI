"""POI 플레이그라운드 서버 (v1.2).

    poi serve [정적폴더] [--port 8900]

- 정적 파일을 서빙하고,
- POST /run  {"code": "...", "stdin": "..."}  →  {"ok", "stdout", "stderr", "exit"}
  코드는 **별도 프로세스**에서 `poi run --safe` 로 돌린다. 시간·출력 제한 + 프로세스 강제 종료.

바이러스/악용 방지: 안전 모드가 python{}·use py·파일·네트워크·위험 내장을 막고,
서버는 그 위에 프로세스 격리 + 벽시계 타임아웃 + 출력 상한을 더 씌운다.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MAX_CODE = 20_000
RUN_TIMEOUT = 6.0
OUT_CAP = 64_000
_sema = threading.Semaphore(4)  # 동시 실행 제한


def _run_snippet(code: str, stdin: str = "") -> dict:
    if len(code) > MAX_CODE:
        return {"ok": False, "stdout": "", "stderr": "코드가 너무 깁니다.", "exit": 1}
    with _sema:
        d = tempfile.mkdtemp(prefix="poi_pg_")
        path = os.path.join(d, "snippet.poi")
        with open(path, "w", encoding="utf-8") as f:
            f.write(code)
        try:
            proc = subprocess.run(
                [sys.executable, "-X", "utf8", "-m", "poi", "run", "--safe",
                 "--no-banner", "--time", str(RUN_TIMEOUT - 1), path],
                input=stdin, capture_output=True,
                encoding="utf-8", errors="replace", timeout=RUN_TIMEOUT,
                cwd=d, env={**os.environ, "POI_NO_UPDATE_CHECK": "1",
                            "POI_NO_BANNER": "1", "PYTHONIOENCODING": "utf-8"},
            )
            out = proc.stdout or ""
            err = proc.stderr or ""
            rc = proc.returncode
        except subprocess.TimeoutExpired as te:
            out = (te.stdout or "") if isinstance(te.stdout, str) else ""
            err = f"시간이 초과됐습니다 ({RUN_TIMEOUT:g}초). 무한 루프가 아닌지 보세요."
            rc = 1
        except Exception as e:  # noqa: BLE001
            out, err, rc = "", f"실행 오류: {e}", 1
        finally:
            try:
                os.remove(path)
                os.rmdir(d)
            except OSError:
                pass
        return {"ok": rc == 0, "stdout": out[:OUT_CAP], "stderr": err[:OUT_CAP],
                "exit": rc}


def make_handler(root: str):
    class H(BaseHTTPRequestHandler):
        server_version = "POI-Playground"

        def log_message(self, *a):
            pass

        def _send(self, code, body: bytes, ctype="application/json; charset=utf-8"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_POST(self):
            if self.path.split("?", 1)[0].rstrip("/") not in ("/run", "/run.php"):
                self._send(404, b'{"error":"not found"}')
                return
            try:
                n = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(n) or b"{}")
                result = _run_snippet(str(payload.get("code", "")),
                                      str(payload.get("stdin", "")))
            except Exception as e:  # noqa: BLE001
                result = {"ok": False, "stdout": "", "stderr": f"요청 오류: {e}",
                          "exit": 1}
            self._send(200, json.dumps(result, ensure_ascii=False).encode("utf-8"))

        def do_GET(self):
            rel = self.path.split("?", 1)[0].lstrip("/") or "index.html"
            fp = os.path.normpath(os.path.join(root, rel))
            if not fp.startswith(os.path.normpath(root)) or not os.path.isfile(fp):
                self._send(404, b"not found", "text/plain; charset=utf-8")
                return
            ctype = {
                ".html": "text/html; charset=utf-8",
                ".css": "text/css", ".js": "text/javascript",
                ".svg": "image/svg+xml", ".png": "image/png",
                ".json": "application/json", ".md": "text/markdown; charset=utf-8",
            }.get(os.path.splitext(fp)[1], "application/octet-stream")
            with open(fp, "rb") as f:
                self._send(200, f.read(), ctype)

    return H


def serve(root: str = ".", port: int = 8900) -> int:
    root = os.path.abspath(root)
    httpd = ThreadingHTTPServer(("127.0.0.1", port), make_handler(root))
    print(f"POI 플레이그라운드:  http://127.0.0.1:{port}")
    print(f"  정적 폴더: {root}")
    print("  실행 엔드포인트: POST /run   (안전 모드 · 프로세스 격리)")
    print("  멈추려면 Ctrl+C")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n종료.")
    finally:
        httpd.server_close()
    return 0

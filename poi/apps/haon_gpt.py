# -*- coding: utf-8 -*-
"""하온 ↔ ChatGPT (openai-oauth 방식) + 하온 에이전트.

ChatGPT 로그인은 사용자의 ChatGPT 계정으로 OAuth(PKCE) 한다 — API 키 불필요.
참고: github.com/EvanZhouDev/openai-oauth · OpenAI Codex CLI 와 같은 흐름.
"""
from __future__ import annotations

import base64 as _b64
import contextlib as _ctx
import hashlib as _hl
import io as _io
import json
import os
import re
import secrets as _sec
import threading as _th
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser as _wb
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import haon as _h

_OAI_ISSUER = "https://auth.openai.com"
_OAI_CLIENT = os.environ.get("POI_OAI_CLIENT", "app_EMoamEEZ73f0CkXaXp7hrann")
_OAI_REDIRECT = "http://localhost:1455/auth/callback"
_OAI_SCOPE = "openid profile email offline_access"
_CG_TOKENS = os.path.join(os.path.expanduser("~"), ".poi", "chatgpt.json")
_CG_RESP_URL = os.environ.get(
    "POI_CG_URL", "https://chatgpt.com/backend-api/codex/responses")
_CG_MODEL = os.environ.get("POI_CG_MODEL", "gpt-5")


# ── OAuth ────────────────────────────────────────────────────────────

def _pkce():
    v = _b64.urlsafe_b64encode(_sec.token_bytes(64)).rstrip(b"=").decode()
    c = _b64.urlsafe_b64encode(_hl.sha256(v.encode()).digest()).rstrip(b"=").decode()
    return v, c


def _load():
    try:
        with open(_CG_TOKENS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(d):
    os.makedirs(os.path.dirname(_CG_TOKENS), exist_ok=True)
    with open(_CG_TOKENS, "w", encoding="utf-8") as f:
        json.dump(d, f)
    with _ctx.suppress(OSError):
        os.chmod(_CG_TOKENS, 0o600)


def _claims(tok):
    try:
        p = tok.split(".")[1]
        p += "=" * (-len(p) % 4)
        return json.loads(_b64.urlsafe_b64decode(p))
    except Exception:
        return {}


def status():
    d = _load()
    if not d.get("access_token"):
        return {"logged_in": False}
    cl = _claims(d["access_token"])
    email = cl.get("email") or _claims(d.get("id_token", "")).get("email", "")
    return {"logged_in": True, "email": email,
            "account_id": d.get("account_id", ""),
            "expired": time.time() > d.get("expires_at", 0) - 60}


def logout():
    with _ctx.suppress(OSError):
        os.remove(_CG_TOKENS)
    return True


def _token_exchange(payload: dict):
    body = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(
        _OAI_ISSUER + "/oauth/token", data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def login(log=print, timeout=180):
    verifier, challenge = _pkce()
    state = _sec.token_urlsafe(16)
    params = urllib.parse.urlencode({
        "response_type": "code", "client_id": _OAI_CLIENT,
        "redirect_uri": _OAI_REDIRECT, "scope": _OAI_SCOPE,
        "code_challenge": challenge, "code_challenge_method": "S256",
        "state": state, "id_token_add_organizations": "true", "prompt": "login",
    })
    auth_url = _OAI_ISSUER + "/oauth/authorize?" + params
    got = {}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if "code" in q:
                got["code"] = q["code"][0]
                got["state"] = q.get("state", [""])[0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.end_headers()
                self.wfile.write(
                    "<h2>POI 하온 · ChatGPT 로그인 완료</h2>"
                    "<p>이 창을 닫고 터미널로 돌아가세요.</p>".encode("utf-8"))
            else:
                self.send_response(400)
                self.end_headers()

    try:
        srv = HTTPServer(("127.0.0.1", 1455), H)
    except OSError as e:
        log(f"1455 포트를 열 수 없어요: {e}")
        return False
    _th.Thread(target=srv.serve_forever, daemon=True).start()
    log("브라우저에서 ChatGPT 로그인 창을 엽니다…")
    log("안 열리면 이 주소를 직접 여세요:\n  " + auth_url)
    with _ctx.suppress(Exception):
        _wb.open(auth_url)
    t0 = time.time()
    while "code" not in got and time.time() - t0 < timeout:
        time.sleep(0.3)
    srv.shutdown()
    if "code" not in got:
        log("시간 초과 — 다시 시도하세요.")
        return False
    if got.get("state") != state:
        log("보안 검증(state) 불일치 — 다시 시도하세요.")
        return False
    try:
        tok = _token_exchange({
            "grant_type": "authorization_code", "client_id": _OAI_CLIENT,
            "code": got["code"], "redirect_uri": _OAI_REDIRECT,
            "code_verifier": verifier,
        })
    except Exception as e:  # noqa: BLE001
        log(f"토큰 교환 실패: {e}")
        return False
    cl = _claims(tok.get("id_token", "") or tok.get("access_token", ""))
    acct = ((cl.get("https://api.openai.com/auth") or {}).get("chatgpt_account_id")
            or cl.get("chatgpt_account_id") or "")
    _save({
        "access_token": tok.get("access_token", ""),
        "refresh_token": tok.get("refresh_token", ""),
        "id_token": tok.get("id_token", ""),
        "account_id": acct,
        "expires_at": time.time() + int(tok.get("expires_in", 3600)),
    })
    log("로그인 완료:  " + (cl.get("email") or "(ChatGPT 계정)"))
    return True


def _access():
    d = _load()
    if not d.get("access_token"):
        return None, None
    if time.time() > d.get("expires_at", 0) - 60 and d.get("refresh_token"):
        with _ctx.suppress(Exception):
            tok = _token_exchange({
                "grant_type": "refresh_token", "client_id": _OAI_CLIENT,
                "refresh_token": d["refresh_token"], "scope": _OAI_SCOPE,
            })
            d["access_token"] = tok.get("access_token", d["access_token"])
            if tok.get("refresh_token"):
                d["refresh_token"] = tok["refresh_token"]
            d["expires_at"] = time.time() + int(tok.get("expires_in", 3600))
            _save(d)
    return d.get("access_token"), d.get("account_id")


def chat(prompt: str, code: str = "", system: str = "", model: str = "") -> str:
    access, acct = _access()
    if not access:
        return ""
    user = (f"[현재 코드]\n{code[:8000]}\n\n" if code else "") + prompt
    payload = json.dumps({
        "model": model or _CG_MODEL,
        "instructions": system or _h._POI_RULES,
        "input": [{"role": "user",
                   "content": [{"type": "input_text", "text": user}]}],
        "stream": True, "store": False,
    }).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + access,
        "Content-Type": "application/json",
        "OpenAI-Beta": "responses=experimental",
        "originator": "poi-haon",
    }
    if acct:
        headers["chatgpt-account-id"] = acct
    try:
        req = urllib.request.Request(_CG_RESP_URL, data=payload, headers=headers)
        out = []
        with urllib.request.urlopen(req, timeout=180) as r:
            for raw in r:
                s = raw.decode("utf-8", "replace").strip()
                if not s.startswith("data:"):
                    continue
                s = s[5:].strip()
                if s in ("", "[DONE]"):
                    continue
                try:
                    ev = json.loads(s)
                except Exception:
                    continue
                if ev.get("type") == "response.output_text.delta":
                    out.append(ev.get("delta", ""))
                elif ev.get("type") in ("response.completed", "response.done"):
                    break
        return "".join(out).strip() or "(ChatGPT 응답 없음)"
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            return "CHATGPT_AUTH_EXPIRED"
        return f"ChatGPT 호출 실패 ({e.code})."
    except Exception as e:  # noqa: BLE001
        return f"ChatGPT 호출 실패: {e}"


# ── 에이전트 ─────────────────────────────────────────────────────────

_AGENT_SYS = """너는 '하온', POI 언어 코딩 에이전트다. 사용자가 시킨 걸 정해진 폴더 안에서
POI 코드로 직접 만든다 (Claude Code / Codex 처럼).
매 턴, 다음 형식의 JSON 하나만 출력한다 (설명 문장 절대 금지):

{"thought":"무엇을 왜 하는지 한 줄","actions":[...],"done":false,"message":""}

actions:
  {"tool":"write","path":"src/main.poi","content":"<파일 전체>"}
  {"tool":"read","path":"src/main.poi"}
  {"tool":"list","path":"."}
  {"tool":"check","path":"src/main.poi"}   # poi 문법 검사
  {"tool":"run","path":"src/main.poi"}     # 잠깐 실행(웹/GUI는 자동 스킵)

끝나면 {"thought":"...","actions":[],"done":true,"message":"완료 요약"}.

POI 규칙: 파이썬 아님. def→fn, elif→else if, True/False/None→true/false/null,
print→show, f"{x}"→"{x}", d["k"]→d.k. 변수는 x = 1 (let/var 없음). 블록은 { } 또는 들여쓰기.
웹은  server { get "/" { render("home.html", {}) } }  또는  webapp { page "/" { } }.
표준모듈 import 없이: math file json crypto jwt password path url database time regex."""


def _safe(folder, p):
    full = os.path.normpath(os.path.join(folder, p or "."))
    if not full.startswith(os.path.normpath(folder)):
        raise ValueError("폴더 밖 경로")
    return full


def _run_tool(folder, act, log):
    t, p = act.get("tool"), act.get("path", "")
    try:
        if t == "write":
            fp = _safe(folder, p)
            os.makedirs(os.path.dirname(fp) or folder, exist_ok=True)
            with open(fp, "w", encoding="utf-8", newline="\n") as f:
                f.write(act.get("content", ""))
            log(f"  ✎ {p}  ({len(act.get('content',''))}자)")
            return "wrote " + p
        if t == "read":
            return open(_safe(folder, p), encoding="utf-8").read()[:8000]
        if t == "list":
            return "\n".join(sorted(os.listdir(_safe(folder, p)))) or "(빈 폴더)"
        if t in ("check", "run"):
            fp = _safe(folder, p)
            src = open(fp, encoding="utf-8").read()
            from ..interpreter import compile_source, run_source
            if t == "check":
                try:
                    compile_source(src, os.path.basename(fp))
                    return "OK: 문법 통과"
                except Exception as e:  # noqa: BLE001
                    return "ERROR:\n" + getattr(e, "render", lambda _s: str(e))(src)
            if re.search(r"(?m)^\s*(server|webapp|app|game|use py)", src):
                return "SKIP: 웹/GUI 코드라 실행 생략 (check 로 검증됨)"
            buf = _io.StringIO()
            with _ctx.redirect_stdout(buf), _ctx.redirect_stderr(buf):
                rc = run_source(src, os.path.basename(fp), safe=True, time_limit=4)
            return f"exit={rc}\n{buf.getvalue()[:4000]}"
    except Exception as e:  # noqa: BLE001
        return "ERROR: " + str(e)
    return "알 수 없는 도구"


def _llm(messages, info):
    if info.get("chatgpt"):
        joined = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages[1:])
        r = chat(joined, system=messages[0]["content"])
        if r and r != "CHATGPT_AUTH_EXPIRED":
            return r
    if info.get("groq") and _h._groq_key():
        body = json.dumps({"model": _h.GROQ_MODEL, "messages": messages,
                           "temperature": 0.1, "max_tokens": 2400}).encode()
        try:
            req = urllib.request.Request(
                _h.GROQ_URL, data=body,
                headers={"Authorization": "Bearer " + _h._groq_key(),
                         "Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read())["choices"][0]["message"]["content"]
        except Exception as e:  # noqa: BLE001
            return '{"thought":"LLM 오류 %s","actions":[],"done":true,"message":"실패"}' % e
    if info.get("ollama"):
        mdl = _h._pick_model(info["models"])
        prompt = "\n\n".join(f"[{m['role']}]\n{m['content']}" for m in messages)
        body = json.dumps({"model": mdl, "stream": False, "prompt": prompt,
                           "options": {"temperature": 0.1}}).encode()
        try:
            req = urllib.request.Request(_h.OLLAMA + "/api/generate", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=180) as resp:
                return json.loads(resp.read()).get("response", "")
        except Exception as e:  # noqa: BLE001
            return '{"thought":"%s","actions":[],"done":true,"message":"실패"}' % e
    return ('{"thought":"LLM 백엔드 없음","actions":[],"done":true,'
            '"message":"poi haon login 하거나 GROQ_API_KEY 를 넣으세요."}')


def backend_name(info=None):
    info = info or detect()
    return ("ChatGPT" if info.get("chatgpt") else
            "Groq" if info.get("groq") else
            "로컬 LLM" if info.get("ollama") else "없음")


def detect():
    info = _h.detect()
    st = status()
    info["chatgpt"] = st.get("logged_in") and not st.get("expired")
    if info["chatgpt"]:
        info["mode"] = "chatgpt"
    return info


def agent(task: str, folder: str, log=print, max_rounds: int = 14, info=None):
    folder = os.path.abspath(folder)
    os.makedirs(folder, exist_ok=True)
    info = info or detect()
    log(f"하온 에이전트 · 백엔드 {backend_name(info)} · 폴더 {folder}")
    msgs = [{"role": "system", "content": _AGENT_SYS},
            {"role": "user",
             "content": f"폴더: {folder}\n요청: {task}\n"
             f"현재 파일: {', '.join(sorted(os.listdir(folder))) or '(비어있음)'}"}]
    seen = []
    for rnd in range(1, max_rounds + 1):
        raw = _llm(msgs, info)
        m = re.search(r"\{.*\}", raw or "", re.S)
        if not m:
            log("  (LLM 이 JSON 을 안 줌)")
            return {"ok": False, "message": (raw or "")[:400]}
        try:
            step = json.loads(m.group(0))
        except Exception:
            log("  (JSON 파싱 실패)")
            return {"ok": False, "message": raw[:400]}
        if step.get("thought"):
            log(f"[{rnd}] {step['thought']}")
        # 같은 액션을 3번 반복하면 멈춘다 (작은 모델 무한루프 방지)
        sig = json.dumps(step.get("actions", []), sort_keys=True, ensure_ascii=False)
        seen.append(sig)
        if len(seen) >= 3 and seen[-1] == seen[-2] == seen[-3]:
            log("  (같은 동작 반복 — 멈춤. 더 똑똑한 백엔드는 poi haon login)")
            return {"ok": bool(os.listdir(folder)),
                    "message": "반복 감지로 중단", "files": sorted(os.listdir(folder))}
        msgs.append({"role": "assistant", "content": m.group(0)})
        if step.get("done"):
            log("✓ " + step.get("message", "완료"))
            return {"ok": True, "message": step.get("message", "완료"),
                    "files": sorted(os.listdir(folder))}
        results = []
        for act in step.get("actions", [])[:6]:
            results.append(f"[{act.get('tool')} {act.get('path','')}]\n"
                           + str(_run_tool(folder, act, log))[:4000])
        msgs.append({"role": "user",
                     "content": "\n\n".join(results) or "(액션 없음 — 계속하거나 done)"})
    log("최대 라운드 도달 — 멈춤")
    return {"ok": False, "message": "라운드 초과", "files": sorted(os.listdir(folder))}

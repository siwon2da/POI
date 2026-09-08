# -*- coding: utf-8 -*-
"""하온 — POI IDLE 안의 에이전트.

백엔드 우선순위:
  1. Groq  — 빠른 클라우드 LLM. API 키를 자동으로 찾는다 (환경변수·설정파일).
             사용자별 레이트 리밋(기본 5분에 12번)으로 공용 키가 안 터지게 한다.
  2. Ollama — 로컬에 돌고 있으면. GPU 는 Ollama 가 자동으로 잡는다.
  3. 규칙 기반 — 의존성 0. 실제 POI 컴파일러를 돌려 오류 코드를 읽고 반복 수정.

경량. 모델 본체는 번들하지 않는다.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request

OLLAMA = os.environ.get("POI_OLLAMA", "http://127.0.0.1:11434")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = os.environ.get("POI_GROQ_MODEL", "llama-3.3-70b-versatile")
LOCAL_MODEL = os.environ.get("POI_HAON_MODEL", "qwen2.5-coder:1.5b")

# 사용자별 레이트 리밋 (한 대 = 한 사용자)
_RATE_MAX = int(os.environ.get("POI_HAON_MAX", "12"))
_RATE_WINDOW = int(os.environ.get("POI_HAON_WINDOW", "300"))   # 초
_USAGE = os.path.join(os.path.expanduser("~"), ".poi", "haon_usage.json")


def _groq_key() -> str:
    """Groq API 키를 알아서 찾는다. (하드코딩 안 함 — 보안)"""
    v = os.environ.get("GROQ_API_KEY") or os.environ.get("POI_GROQ_KEY")
    if v and v.strip():
        return v.strip()
    home = os.path.expanduser("~")
    cands = [
        os.path.join(home, ".poi", "groq.key"),
        os.path.join(home, ".poi", "groq_api_key"),
        os.path.join(home, ".groq", "key"),
        os.path.join(home, ".groq_api_key"),
        os.path.join(home, ".config", "groq", "key"),
    ]
    for p in cands:
        try:
            with open(p, encoding="utf-8") as f:
                t = f.read().strip()
            if t.startswith("gsk_"):
                return t
        except Exception:
            pass
    # .env (현재 폴더 → 홈)
    for base in (os.getcwd(), home):
        try:
            with open(os.path.join(base, ".env"), encoding="utf-8") as f:
                for line in f:
                    m = re.match(r"\s*(?:GROQ_API_KEY|POI_GROQ_KEY)\s*=\s*(\S+)",
                                 line)
                    if m:
                        return m.group(1).strip().strip('"').strip("'")
        except Exception:
            pass
    return ""


def _usage_load():
    try:
        with open(_USAGE, encoding="utf-8") as f:
            return [float(x) for x in json.load(f)]
    except Exception:
        return []


def _usage_save(items):
    try:
        os.makedirs(os.path.dirname(_USAGE), exist_ok=True)
        with open(_USAGE, "w", encoding="utf-8") as f:
            json.dump(items[-50:], f)
    except Exception:
        pass


def rate_state():
    """(남은 횟수, 다음 사용까지 초)."""
    now = time.time()
    recent = [t for t in _usage_load() if now - t < _RATE_WINDOW]
    left = max(0, _RATE_MAX - len(recent))
    wait = 0
    if left == 0 and recent:
        wait = int(_RATE_WINDOW - (now - min(recent))) + 1
    return left, wait


def _rate_hit():
    items = [t for t in _usage_load() if time.time() - t < _RATE_WINDOW]
    items.append(time.time())
    _usage_save(items)

_POI_RULES = """너는 '하온'. POI 언어 전문가다. POI 는 파이썬 위에서 도는 독립 언어.
핵심: def→fn, elif→else if, True/False/None→true/false/null, print→show, f"{x}"→"{x}",
lambda→=>, d["k"]→d.k, for i in range(n)→repeat n as i, try/except→try/catch, raise "메시지".
변수는 그냥 x = 1 (let/var 없음). const 는 진짜 상수(재대입 오류). 블록은 { } 또는 들여쓰기.
범위 1..10 / 1..<10. match 식: x = match v { when >= 90 => "A" else => "F" }.
표준모듈 import 없이: math file json crypto jwt password path url database time regex.
웹: server { get "/" { return "<h1>..</h1>" } }  ·  webapp { page "/" { } }.
답은 한국어로 짧게. 코드는 반드시 POI 문법으로만."""


def detect() -> dict:
    """사용 가능한 백엔드를 조사한다. Groq → Ollama → 규칙 순."""
    info = {"gpu": None, "vram_mb": 0, "ollama": False, "models": [],
            "groq": False, "groq_model": GROQ_MODEL, "mode": "rules"}
    if _groq_key():
        info["groq"] = True
        info["mode"] = "groq"
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=4).stdout.strip()
        if out:
            name, mem = (out.splitlines()[0].split(",") + ["0"])[:2]
            info["gpu"] = name.strip()
            info["vram_mb"] = int(re.sub(r"\D", "", mem) or 0)
    except Exception:
        pass
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=2) as r:
            data = json.loads(r.read())
        info["models"] = [m["name"] for m in data.get("models", [])]
        info["ollama"] = bool(info["models"])
    except Exception:
        pass
    if info["mode"] == "rules" and info["ollama"]:
        info["mode"] = "ollama"
    return info


def _groq_chat(prompt: str, code: str) -> str:
    key = _groq_key()
    if not key:
        return ""
    left, wait = rate_state()
    if left <= 0:
        return ("잠깐만요 — 하온은 %d분에 %d번까지예요. "
                "%d초 후에 다시 물어봐 주세요.\n"
                "(오류는 '자동 수정' 버튼이 지금도 컴파일러로 고쳐 줍니다.)"
                % (_RATE_WINDOW // 60, _RATE_MAX, wait))
    msgs = [{"role": "system", "content": _POI_RULES}]
    if code:
        msgs.append({"role": "user",
                     "content": "[현재 코드]\n" + code[:8000]})
    msgs.append({"role": "user", "content": prompt})
    body = json.dumps({"model": GROQ_MODEL, "messages": msgs,
                       "temperature": 0.2, "max_tokens": 900}).encode("utf-8")
    req = urllib.request.Request(
        GROQ_URL, data=body,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + key})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            data = json.loads(r.read())
        _rate_hit()
        return data["choices"][0]["message"]["content"].strip() or "(응답 없음)"
    except urllib.error.HTTPError as e:  # noqa
        if e.code == 429:
            return "Groq 서버가 지금 바빠요. 잠시 후 다시 시도해 주세요."
        return "Groq 호출 실패 (%s). 규칙 기반 '자동 수정' 을 써 보세요." % e.code
    except Exception as e:
        return "Groq 호출 실패: %s" % e


# ── 로컬 LLM 자동 설치 (Ollama + 작은 코더 모델) ─────────────────────

def _ollama_bin() -> str:
    for c in ("ollama",
              os.path.expandvars(r"%LOCALAPPDATA%\Programs\Ollama\ollama.exe"),
              os.path.expandvars(r"%ProgramFiles%\Ollama\ollama.exe"),
              "/usr/local/bin/ollama", "/opt/homebrew/bin/ollama"):
        try:
            if c == "ollama":
                subprocess.run([c, "--version"], capture_output=True, timeout=5)
                return c
            if os.path.isfile(c):
                return c
        except Exception:
            pass
    return ""


def _ollama_up() -> bool:
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=2):
            return True
    except Exception:
        return False


def _run_stream(cmd, log, timeout=1800):
    log("$ " + " ".join(cmd))
    try:
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace",
                             creationflags=getattr(subprocess,
                                                   "CREATE_NO_WINDOW", 0))
    except FileNotFoundError:
        log("  (명령을 찾을 수 없음)")
        return 1
    last = ""
    for line in p.stdout:
        line = line.rstrip()
        if line and line != last:
            log("  " + line[:200])
            last = line
    p.wait(timeout=timeout)
    return p.returncode


def ensure_ollama(log) -> str:
    """Ollama 를 확보한다 (없으면 설치). 실행 중이 아니면 서버도 띄운다.
    성공 시 ollama 바이너리 경로, 실패 시 ""."""
    b = _ollama_bin()
    if not b:
        log("Ollama 가 없어 설치를 시도합니다…")
        if os.name == "nt":
            # 1) winget
            rc = _run_stream(["winget", "install", "--id", "Ollama.Ollama",
                              "-e", "--silent",
                              "--accept-source-agreements",
                              "--accept-package-agreements"], log, timeout=900)
            if rc != 0:
                # 2) 공식 설치 파일 내려받아 조용히 실행
                import tempfile
                dst = os.path.join(tempfile.gettempdir(), "OllamaSetup.exe")
                try:
                    log("  OllamaSetup.exe 내려받는 중…")
                    urllib.request.urlretrieve(
                        "https://ollama.com/download/OllamaSetup.exe", dst)
                    for flags in (["/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                                  ["/S"]):
                        if _run_stream([dst] + flags, log, timeout=900) == 0:
                            break
                except Exception as e:
                    log("  설치 실패: %s" % e)
        elif sys.platform == "darwin":
            _run_stream(["brew", "install", "ollama"], log, timeout=900)
        else:
            log("  리눅스: curl -fsSL https://ollama.com/install.sh | sh  후 다시 시도")
        b = _ollama_bin()
        if not b:
            log("Ollama 설치를 확인하지 못했어요. 새 터미널을 연 뒤 다시 시도해 주세요.")
            return ""
        log("Ollama 준비됨: " + b)
    if not _ollama_up():
        log("Ollama 서버를 시작합니다…")
        try:
            subprocess.Popen([b, "serve"],
                             creationflags=getattr(subprocess,
                                                   "CREATE_NO_WINDOW", 0))
        except Exception as e:
            log("  서버 시작 실패: %s" % e)
        for _ in range(30):
            if _ollama_up():
                break
            time.sleep(1)
    return b if _ollama_up() else ""


def ensure_model(log, model: str = LOCAL_MODEL) -> bool:
    b = ensure_ollama(log)
    if not b:
        return False
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=4) as r:
            have = [m["name"] for m in json.loads(r.read()).get("models", [])]
    except Exception:
        have = []
    if any(h == model or h.startswith(model.split(":")[0]) for h in have):
        log("모델이 이미 있어요: " + model)
        return True
    log("모델 내려받는 중: %s  (한 번만, 1~2GB)" % model)
    rc = _run_stream([b, "pull", model], log, timeout=3600)
    if rc == 0:
        log("완료! 이제 하온이 로컬 LLM 으로 답합니다.")
        return True
    log("모델 내려받기 실패 (코드 %s)." % rc)
    return False


def _pick_model(models: list) -> str:
    pref = ("qwen2.5-coder", "deepseek-coder", "codellama", "codegemma",
            "llama3.2", "llama3.1", "qwen2.5", "phi3", "gemma2", "mistral")
    for p in pref:
        for m in models:
            if m.startswith(p):
                return m
    return models[0] if models else ""


def chat(prompt: str, code: str = "", info: dict | None = None) -> str:
    info = info or detect()
    if info.get("groq"):
        out = _groq_chat(prompt, code)
        if out:
            return out
    if info.get("ollama"):
        model = _pick_model(info["models"])
        body = json.dumps({
            "model": model, "stream": False,
            "system": _POI_RULES,
            "prompt": (f"[현재 코드]\n{code[:6000]}\n\n" if code else "") + prompt,
            "options": {"temperature": 0.2, "num_predict": 700},
        }).encode("utf-8")
        try:
            req = urllib.request.Request(OLLAMA + "/api/generate", data=body,
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read()).get("response", "").strip() or "(응답 없음)"
        except Exception as e:
            return f"LLM 호출 실패: {e}\n규칙 기반으로 '고쳐줘' 를 눌러 보세요."
    return ("LLM 이 없어 규칙 기반으로만 도와요. '이 파일 오류 자동 수정' 은\n"
            "실제 컴파일러로 오류를 잡아 고칩니다.\n"
            "Groq 를 쓰려면:  환경변수 GROQ_API_KEY 를 넣거나\n"
            "  ~/.poi/groq.key  파일에 gsk_… 키를 저장하고 다시 여세요.")


# ── 규칙 기반 오토픽스 (컴파일러 구동) ────────────────────────────────

_FOREIGN = [
    (re.compile(r"(?m)^(\s*)elif\b"), r"\1else if"),
    (re.compile(r"(?m)^(\s*)(?:def|func|function|fun)\s+(\w)"), r"\1fn \2"),
    (re.compile(r"(?m)^(\s*)foreach\b"), r"\1for"),
    (re.compile(r"(?m)^(\s*)(?:var|let)\s+(\w+\s*=)"), r"\1\2"),
    (re.compile(r"(?m)^(\s*)(?:echo|puts)\b"), r"\1show"),
    (re.compile(r"\bconsole\.log\s*\("), "show ("),
]
_LIT = [
    (re.compile(r"(?<![\w.\"'])True\b"), "true"),
    (re.compile(r"(?<![\w.\"'])False\b"), "false"),
    (re.compile(r"(?<![\w.\"'])None\b"), "null"),
]
_STR_SPAN = re.compile(r'"(?:[^"\\]|\\.)*"|"""(?:.|\n)*?"""|#[^\n]*')


def _outside_strings_sub(pattern, repl, text):
    """문자열/주석 밖에서만 치환."""
    spans = [m.span() for m in _STR_SPAN.finditer(text)]

    def guarded(m):
        i = m.start()
        for a, b in spans:
            if a <= i < b:
                return m.group(0)
        return re.sub(pattern, repl, m.group(0))
    return pattern.sub(lambda m: guarded(m), text)


def autofix(src: str, max_rounds: int = 10) -> tuple[str, list[str]]:
    """컴파일 → 오류 읽기 → 한 곳 고치기 → 반복. (고친 소스, 로그)."""
    from ..interpreter import compile_source
    from ..errors import POIError

    log: list[str] = []
    cur = src

    # 1) 무해한 일괄 치환 (다른 언어 습관)
    before = cur
    for pat, rep in _FOREIGN:
        cur = pat.sub(rep, cur)
    for pat, rep in _LIT:
        cur = _outside_strings_sub(pat, rep, cur)
    if cur != before:
        log.append("• 다른 언어 습관 정리 (elif→else if, def→fn, True→true …)")

    # 2) 컴파일 반복
    for _ in range(max_rounds):
        try:
            compile_source(cur, "<haon>")
            log.append("✓ 이제 컴파일됩니다.")
            return cur, log
        except POIError as e:
            fixed = _fix_one(cur, e)
            if fixed is None or fixed == cur:
                log.append(f"✗ 자동으로 못 고친 오류: {e.code} — {e.message}")
                if e.line:
                    log.append(f"   {e.line}번째 줄을 봐 주세요.")
                return cur, log
            log.append(f"• {e.code} 수정 ({e.line}번째 줄)")
            cur = fixed
        except Exception as e:  # noqa: BLE001
            log.append(f"✗ {type(e).__name__}: {e}")
            return cur, log
    log.append("… 라운드 한도에 도달했어요.")
    return cur, log


def _lines(s):
    return s.split("\n")


def _fix_one(src: str, e) -> str | None:
    ls = _lines(src)
    ln = (e.line or 0)
    code = getattr(e, "code", "")
    line = ls[ln - 1] if 1 <= ln <= len(ls) else ""

    if code == "P014" and "elif" in line:
        ls[ln - 1] = line.replace("elif", "else if", 1)
        return "\n".join(ls)
    if code == "P014":
        for bad, good in (("def ", "fn "), ("func ", "fn "), ("switch", "match"),
                          ("foreach", "for")):
            if line.lstrip().startswith(bad):
                ls[ln - 1] = line.replace(bad, good, 1)
                return "\n".join(ls)
    if code in ("P011", "P013"):        # 중괄호 안 닫힘
        return src + "\n}\n"
    if code == "P016":                  # end 필요
        return src.rstrip() + "\nend\n"
    if code in ("P002", "P003"):        # 문자열/블록 안 닫힘
        return src + '\n"""\n' if code == "P002" else src + "\n}\n"
    if code == "P019" and "=" in line:  # const 재대입 → const 선언을 일반 대입으로
        name = line.split("=")[0].strip()
        for i, x in enumerate(ls):
            m = re.match(r"^(\s*)const\s+" + re.escape(name) + r"\b", x)
            if m:
                ls[i] = x.replace("const ", "", 1)
                return "\n".join(ls)
    if code == "P010" and "'{' 이(가) 필요" in e.message:
        ls[ln - 1] = line.rstrip() + " {"
        return "\n".join(ls)
    return None

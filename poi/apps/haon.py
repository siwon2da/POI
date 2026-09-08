# -*- coding: utf-8 -*-
"""하온 — POI IDLE 안의 로컬 에이전트.

두 가지 모드:
  · 규칙 기반 (기본, 의존성 0) — 실제 POI 컴파일러를 돌려 오류 코드를 읽고
    타겟 수정을 반복 적용한다. 모든 P-코드를 이해한다.
  · LLM (Ollama 가 로컬에 있으면) — POI 문법을 시스템 프롬프트로 주고 물어본다.
    GPU 는 Ollama 런타임이 자동으로 잡는다 (CUDA/Metal/Vulkan).

경량. 모델 본체는 번들하지 않는다 — 있으면 쓰고 없으면 규칙 기반.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request

OLLAMA = os.environ.get("POI_OLLAMA", "http://127.0.0.1:11434")

_POI_RULES = """너는 '하온'. POI 언어 전문가다. POI 는 파이썬 위에서 도는 독립 언어.
핵심: def→fn, elif→else if, True/False/None→true/false/null, print→show, f"{x}"→"{x}",
lambda→=>, d["k"]→d.k, for i in range(n)→repeat n as i, try/except→try/catch, raise "메시지".
변수는 그냥 x = 1 (let/var 없음). const 는 진짜 상수(재대입 오류). 블록은 { } 또는 들여쓰기.
범위 1..10 / 1..<10. match 식: x = match v { when >= 90 => "A" else => "F" }.
표준모듈 import 없이: math file json crypto jwt password path url database time regex.
웹: server { get "/" { return "<h1>..</h1>" } }  ·  webapp { page "/" { } }.
답은 한국어로 짧게. 코드는 반드시 POI 문법으로만."""


def detect() -> dict:
    """사용 가능한 백엔드를 조사한다."""
    info = {"gpu": None, "vram_mb": 0, "ollama": False, "models": [], "mode": "rules"}
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
    if info["ollama"]:
        info["mode"] = "llm"
    return info


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
    return ("로컬 LLM(Ollama)이 없어 규칙 기반으로만 도와요.\n"
            "'이 오류 고쳐줘' 버튼은 실제 컴파일러로 오류를 잡아 고칩니다.\n"
            "LLM 을 쓰려면:  ollama pull qwen2.5-coder:1.5b  후 다시 여세요.")


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

"""랜딩 페이지 빌드.

    python site/build.py

_landing.template.html  +  assets/fonts/*.woff2
   → site/landing.html        (Claude Artifact 조각: <title>+<style>+본문+<script>)
   → site/hagora/index.html   (독립 실행본: <!doctype> 로 감싼 것)

폰트(Galmuri)는 base64 로 인라인해서 두 산출물 모두 자체 완결형이다.
"""
from __future__ import annotations

import base64
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def b64(rel: str) -> str:
    with open(os.path.join(HERE, rel), "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def main() -> int:
    tpl = open(os.path.join(HERE, "_landing.template.html"), encoding="utf-8").read()
    frag = tpl.replace("__G11B_B64__", b64("assets/fonts/Galmuri11-Bold.woff2"))

    out_frag = os.path.join(HERE, "landing.html")
    open(out_frag, "w", encoding="utf-8", newline="\n").write(frag)

    # 독립 실행본
    marker = "\n<style>"
    i = frag.index(marker)
    head_bits = [l for l in frag[:i].splitlines() if l.strip()]
    body = frag[i + 1:]
    title = next(l for l in head_bits if l.startswith("<title>"))
    meta = next((l for l in head_bits if l.startswith('<meta name="description"')), "")
    links = [l for l in head_bits if l.startswith("<link")]

    standalone = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#17171c" media="(prefers-color-scheme: dark)">
{title}
{meta}
<meta property="og:title" content="POI">
<meta property="og:description" content="우리가 만든 언어 — 문법 자체가 파이썬보다 쉽고, 쓸 수 있는 범위는 더 넓게.">
<meta property="og:type" content="website">
<meta property="og:url" content="https://hagora.kr/poi/">
<link rel="icon" href="/poi/assets/poi-mark.svg" type="image/svg+xml">
<link rel="apple-touch-icon" href="/poi/assets/poi-mark-256.png">
{chr(10).join(links)}
<style>
  :root {{ color-scheme: light dark; }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; }}
  img {{ max-width: 100%; }}
  [hidden] {{ display: none !important; }}
</style>
</head>
<body>
{body}
</body>
</html>
"""
    hd = os.path.join(HERE, "hagora")
    os.makedirs(hd, exist_ok=True)
    open(os.path.join(hd, "index.html"), "w", encoding="utf-8", newline="\n").write(standalone)

    print("빌드 완료:")
    print(f"  {out_frag}  ({len(frag)//1024} KB)")
    print(f"  {os.path.join(hd, 'index.html')}  ({len(standalone)//1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

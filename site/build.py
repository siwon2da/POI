"""랜딩 + 입문서 빌드.

    python site/build.py

_landing.template.html / _book.template.html  +  assets/fonts/Galmuri14.woff2
   → site/landing.html          (Claude Artifact 조각)
   → site/hagora/index.html     (독립 실행본)
   → site/book.html             (Artifact 조각)
   → site/hagora/book/index.html

폰트(Galmuri14)는 base64 로 인라인해서 산출물이 전부 자체 완결형이다.
"""
from __future__ import annotations

import base64
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def b64(rel: str) -> str:
    with open(os.path.join(HERE, rel), "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def _wrap(frag: str, og_desc: str, og_url: str) -> str:
    marker = "\n<style>"
    i = frag.index(marker)
    head_bits = [l for l in frag[:i].splitlines() if l.strip()]
    body = frag[i + 1:]
    title = next(l for l in head_bits if l.startswith("<title>"))
    meta = next((l for l in head_bits if l.startswith('<meta name="description"')), "")
    links = [l for l in head_bits if l.startswith("<link")]
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#ffffff" media="(prefers-color-scheme: light)">
<meta name="theme-color" content="#17171c" media="(prefers-color-scheme: dark)">
{title}
{meta}
<meta property="og:title" content="POI — Power Of Imagination">
<meta property="og:description" content="{og_desc}">
<meta property="og:type" content="website">
<meta property="og:url" content="{og_url}">
<meta property="og:image" content="https://hagora.kr/poi/assets/poi-og.png">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:image" content="https://hagora.kr/poi/assets/poi-og.png">
<link rel="icon" type="image/png" sizes="32x32" href="/poi/assets/poi-octopus-32.png">
<link rel="icon" type="image/png" sizes="96x96" href="/poi/assets/poi-octopus-96.png">
<link rel="icon" type="image/png" sizes="256x256" href="/poi/assets/poi-octopus-256.png">
<link rel="apple-touch-icon" href="/poi/assets/poi-octopus-256.png">
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


def _sub(tpl: str, font: str, octo: str) -> str:
    return tpl.replace("__G14_B64__", font).replace("__OCTO_B64__", octo)


def main() -> int:
    font = b64("assets/fonts/Galmuri14.woff2")
    octo = b64("assets/poi-octopus-96.png")
    hd = os.path.join(HERE, "hagora")
    os.makedirs(os.path.join(hd, "book"), exist_ok=True)
    done = []

    # 랜딩
    frag = _sub(open(os.path.join(HERE, "_landing.template.html"),
                     encoding="utf-8").read(), font, octo)
    open(os.path.join(HERE, "landing.html"), "w", encoding="utf-8",
         newline="\n").write(frag)
    open(os.path.join(hd, "index.html"), "w", encoding="utf-8", newline="\n").write(
        _wrap(frag, "우리가 만든 언어 — 쉽고, 넓고, 끝까지.", "https://hagora.kr/poi/"))
    done += [("landing.html", frag), ("hagora/index.html", frag)]

    # 입문서
    bfrag = _sub(open(os.path.join(HERE, "_book.template.html"),
                      encoding="utf-8").read(), font, octo)
    open(os.path.join(HERE, "book.html"), "w", encoding="utf-8",
         newline="\n").write(bfrag)
    open(os.path.join(hd, "book", "index.html"), "w", encoding="utf-8",
         newline="\n").write(
        _wrap(bfrag, "POI 입문서 — 설치부터 GUI·디버깅·파이썬 우주까지.",
              "https://hagora.kr/poi/book/"))
    done += [("book.html", bfrag), ("hagora/book/index.html", bfrag)]

    print("빌드 완료:")
    for name, content in done:
        print(f"  {name}  ({len(content) // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

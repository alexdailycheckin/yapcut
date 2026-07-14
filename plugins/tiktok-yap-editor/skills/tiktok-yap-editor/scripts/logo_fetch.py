#!/usr/bin/env python3
"""Fetch a brand's official logo and emit a transparent, box-fitted PNG ready
to overlay as a receipt (see SKILL.md, Evidence inserts).

Source of truth is Wikipedia/Wikimedia: official logo SVGs, stable URLs, no
scraping brand sites through bot walls. Rasterization goes through headless
Chrome with a transparent background (SVG-faithful, no extra deps), then PIL
trims to content and centers into the requested box.

Usage:
  python3 logo_fetch.py --page "Perplexity AI" --box 215x150 --out box_perplexity.png
  python3 logo_fetch.py --file "File:Google 2026 logo.svg" --box 215x150 --out box_google.png

--page lists the article's images and picks the best logo-ish file (prefers
SVG, then 'logo'/'wordmark'/'symbol' in the name); --file skips the guess.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request

UA = {"User-Agent": "yapcut-receipts/1.0"}
CHROME = os.environ.get(
    "CHROME_BIN", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def api(params: dict) -> dict:
    url = "https://en.wikipedia.org/w/api.php?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers=UA)
    return json.load(urllib.request.urlopen(req))


def pick_logo_file(page: str) -> str:
    d = api({"action": "query", "prop": "images", "titles": page,
             "imlimit": "100", "format": "json"})
    p = list(d["query"]["pages"].values())[0]
    names = [im["title"] for im in p.get("images", [])]
    scored = []
    for n in names:
        low = n.lower()
        if any(x in low for x in ("commons-logo", "wikidata", "wikiquote",
                                  "wikiversity", "wikinews", "wiktionary")):
            continue
        score = 0
        if "logo" in low or "wordmark" in low or "symbol" in low:
            score += 4
        if page.split()[0].lower() in low:
            score += 2
        if low.endswith(".svg"):
            score += 1
        if score:
            scored.append((score, n))
    if not scored:
        sys.exit(f"no logo-ish file on page {page!r}; pass --file explicitly. "
                 f"Page images: {names[:12]}")
    return sorted(scored, reverse=True)[0][1]


def file_url(file_title: str) -> str:
    d = api({"action": "query", "prop": "imageinfo", "iiprop": "url",
             "titles": file_title, "format": "json"})
    return list(d["query"]["pages"].values())[0]["imageinfo"][0]["url"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", help="Wikipedia article, e.g. 'Perplexity AI'")
    ap.add_argument("--file", help="exact 'File:...' title, skips the guess")
    ap.add_argument("--box", default="215x150", help="WxH box to fit into; "
                    "150 tall keeps a square symbol above the platform bottom chrome")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    if not (a.page or a.file):
        sys.exit("need --page or --file")

    title = a.file or pick_logo_file(a.page)
    url = file_url(title)
    td = tempfile.mkdtemp(prefix="logo_")
    src = os.path.join(td, os.path.basename(urllib.parse.unquote(url)))
    req = urllib.request.Request(url, headers=UA)  # wikimedia 403s a bare UA
    open(src, "wb").write(urllib.request.urlopen(req).read())

    # rasterize with a REAL alpha channel via headless chrome
    wrap = os.path.join(td, "wrap.html")
    open(wrap, "w").write(
        f'<html><body style="margin:0;background:transparent">'
        f'<img src="{os.path.basename(src)}" style="width:800px;display:block">'
        f"</body></html>")
    shot = os.path.join(td, "shot.png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                    "--hide-scrollbars", "--default-background-color=00000000",
                    "--window-size=820,900", f"--screenshot={shot}",
                    f"file://{wrap}"], check=True, capture_output=True)

    from PIL import Image
    bw, bh = (int(x) for x in a.box.lower().split("x"))
    im = Image.open(shot).convert("RGBA")
    im = im.crop(im.getbbox())
    r = min(bw / im.width, bh / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    canvas = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    canvas.paste(im, ((bw - im.width) // 2, (bh - im.height) // 2), im)
    canvas.save(a.out)
    print(f"{title} -> {a.out} ({bw}x{bh}, transparent)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
    ap.add_argument("--chip", dest="chip", action="store_true", default=True,
                    help="white rounded chip behind the logo (DEFAULT): uniform "
                    "geometry and guaranteed contrast on any footage")
    ap.add_argument("--bare", dest="chip", action="store_false",
                    help="raw transparent logo, no chip")
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
    # contain-box render: a square or tall logo must NEVER outgrow the
    # viewport (a fixed-width img once clipped two square marks at the bottom)
    wrap = os.path.join(td, "wrap.html")
    open(wrap, "w").write(
        f'<html><body style="margin:0;background:transparent">'
        f'<div style="width:800px;height:800px;display:flex">'
        f'<img src="{os.path.basename(src)}" style="max-width:800px;'
        f'max-height:800px;margin:auto;display:block"></div>'
        f"</body></html>")
    shot = os.path.join(td, "shot.png")
    subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                    "--hide-scrollbars", "--default-background-color=00000000",
                    "--window-size=820,840", f"--screenshot={shot}",
                    f"file://{wrap}"], check=True, capture_output=True)

    from PIL import Image
    bw, bh = (int(x) for x in a.box.lower().split("x"))
    im = Image.open(shot).convert("RGBA")
    im = im.crop(im.getbbox())
    r = min(bw / im.width, bh / im.height)
    im = im.resize((round(im.width * r), round(im.height * r)), Image.LANCZOS)
    canvas = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    if a.chip:
        from PIL import ImageDraw, ImageFilter
        pad = max(14, bh // 9)
        shadow = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
        ImageDraw.Draw(shadow).rounded_rectangle(
            [6, 8, bw - 2, bh - 2], radius=bh // 6, fill=(0, 0, 0, 90))
        canvas = Image.alpha_composite(
            canvas, shadow.filter(ImageFilter.GaussianBlur(6)))
        ImageDraw.Draw(canvas).rounded_rectangle(
            [2, 2, bw - 6, bh - 8], radius=bh // 6, fill=(255, 255, 251, 255))
        r2 = min((bw - 2 * pad) / im.width, (bh - 2 * pad) / im.height, 1.0)
        if r2 < 1.0:
            im = im.resize((round(im.width * r2), round(im.height * r2)),
                           Image.LANCZOS)
    canvas.paste(im, ((bw - im.width) // 2, (bh - im.height) // 2), im)
    canvas.save(a.out)
    print(f"{title} -> {a.out} ({bw}x{bh}, "
          f"{'chip' if a.chip else 'transparent'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

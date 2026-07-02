#!/usr/bin/env python3
"""Turn YapCut scripts into LinkedIn carousel PDFs (branded, swipeable docs).

Two ways to run:

  python3 build_carousels.py                 # build every script in the newest
                                             # <workspace>/carousels/carousel-queue-*.json
                                             # (that's what the dashboard's
                                             #  "Export carousel queue" writes)

  python3 build_carousels.py d-2026-06-23-9  # build specific script id(s) by
                                             # pulling them straight from weeks/*.json

All data lives in the workspace (default ~/outlier-radar/), resolved the same
way as build_dashboard.py: --dir <path> | $OUTLIER_RADAR_HOME |
./radar-config.json in the current dir | ~/outlier-radar | legacy: next to
this script. Branding (name on the slides, colours, fonts) comes from the
`brand` block in radar-config.json; neutral defaults apply without one.

For each script it derives a 6-8 slide deck from the labelled fields
(text_hook / spoken_hook / script / value / cta), writes an editable
carousels/<id>.html, then renders carousels/<id>.pdf via headless
Chrome/Chromium (auto-detected; override with CHROME=/path/to/chrome).

The auto-slice is a solid first draft. To hand-tune a deck, edit its .html
and re-run - the pipeline never overwrites an .html you changed unless you
pass --force.
"""
import json, os, sys, glob, re, shutil, subprocess, html as _html

HERE = os.path.dirname(os.path.abspath(__file__))


def resolve_workspace():
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == "--dir" and i + 1 < len(argv):
            return os.path.abspath(os.path.expanduser(argv[i + 1]))
        if a.startswith("--dir="):
            return os.path.abspath(os.path.expanduser(a.split("=", 1)[1]))
    env = os.environ.get("OUTLIER_RADAR_HOME")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    if os.path.exists(os.path.join(os.getcwd(), "radar-config.json")):
        return os.getcwd()
    home = os.path.join(os.path.expanduser("~"), "outlier-radar")
    if os.path.exists(os.path.join(home, "radar-config.json")):
        return home
    return HERE


WS = resolve_workspace()
OUT = os.path.join(WS, "carousels")
os.makedirs(OUT, exist_ok=True)

CFG = {}
_cfgp = os.path.join(WS, "radar-config.json")
if os.path.exists(_cfgp):
    try:
        CFG = json.load(open(_cfgp))
    except Exception as e:
        print("bad radar-config.json, using defaults:", e)

BRAND = CFG.get("brand") or {}
_colors = BRAND.get("colors") or {}
_fonts = BRAND.get("fonts") or {}
NAME = BRAND.get("name") or CFG.get("creator") or "Your Name"
BG = _colors.get("bg") or "#FFFFFF"
INK = _colors.get("ink") or "#17191C"
ACCENT = _colors.get("accent") or "#0F766E"
FONT_DISP = _fonts.get("display") or "Inter"
FONT_BODY = _fonts.get("body") or FONT_DISP
FONT_MONO = _fonts.get("mono") or "Space Mono"
GOOGLE_IMPORT = _fonts.get("google_import") or (
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800"
    "&family=Space+Mono:wght@400;700&display=swap")


def _lane_label(key, default):
    v = CFG.get(key)
    if isinstance(v, dict):
        return v.get("label") or default
    return v or default


PRIMARY_LABEL = _lane_label("primary_lane", "Industry")


def find_chrome():
    env = os.environ.get("CHROME") or os.environ.get("CHROME_PATH")
    if env and os.path.exists(env):
        return env
    for c in ("google-chrome", "google-chrome-stable", "chromium",
              "chromium-browser", "chrome", "brave-browser", "msedge"):
        p = shutil.which(c)
        if p:
            return p
    for p in ("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
              "/Applications/Chromium.app/Contents/MacOS/Chromium",
              "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
              "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"):
        if os.path.exists(p):
            return p
    sys.exit("No Chrome/Chromium found. Install one or set CHROME=/path/to/chrome and re-run.")


# LinkedIn mark, inline so the deck stays self-contained (no external image).
LI_SVG = ('<svg class="li" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" '
          'fill="#0A66C2" aria-label="LinkedIn"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 01-2.063-2.065 2.064 2.064 0 112.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>')
BYLINE = f'<span class="byline">{LI_SVG}<span class="nm">{_html.escape(NAME)}</span></span>'

# ---- deck styling (tokens filled from the config's brand block) -------------
CSS = r"""
  @import url('@GOOGLE_IMPORT@');
  :root{
    --bg:@BG@; --ink:@INK@; --hl:@ACCENT@;
    --ink-55:color-mix(in srgb, @INK@ 56%, transparent);
    --disp:'@FONT_DISP@',system-ui,sans-serif;
    --body:'@FONT_BODY@',system-ui,sans-serif;
    --mono:'@FONT_MONO@',ui-monospace,monospace;
  }
  *{margin:0;padding:0;box-sizing:border-box;}
  @page{ size:1080px 1350px; margin:0; }
  html,body{background:var(--bg);}
  .slide{width:1080px;height:1350px;background:var(--bg);color:var(--ink);
    padding:90px 96px;display:flex;flex-direction:column;
    page-break-after:always;position:relative;overflow:hidden;font-family:var(--body);}
  .slide:last-child{page-break-after:auto;}
  .top{display:flex;justify-content:space-between;align-items:center;}
  .kicker{font-family:var(--mono);font-size:26px;letter-spacing:.02em;color:var(--ink-55);text-transform:uppercase;}
  .num{font-family:var(--mono);font-size:26px;color:var(--ink-55);}
  .main{flex:1;display:flex;flex-direction:column;justify-content:center;}
  .foot{display:flex;justify-content:space-between;align-items:center;}
  .byline{display:flex;align-items:center;gap:14px;}
  .byline .li{width:40px;height:40px;flex:none;}
  .byline .nm{font-family:var(--disp);font-weight:700;font-size:32px;color:var(--ink);letter-spacing:-.01em;}
  .swipe{font-family:var(--mono);font-size:26px;color:var(--hl);}
  h1{font-family:var(--disp);font-weight:700;line-height:1.03;letter-spacing:-.02em;}
  .big{font-size:112px;} .lead{font-size:84px;} .mid{font-size:60px;}
  /* one font for the whole deck: body copy is the display face too, hierarchy
     by size/weight/colour only, never by switching typeface. */
  p.body{font-family:var(--disp);font-size:50px;line-height:1.24;font-weight:600;letter-spacing:-.01em;color:var(--ink);}
  p.body + p.body{margin-top:34px;}
  .muted{color:var(--ink-55);}
  .stat{font-family:var(--disp);font-weight:800;font-size:150px;line-height:.95;letter-spacing:-.03em;}
  .statsub{font-family:var(--mono);font-size:34px;color:var(--ink-55);margin-top:6px;}
  .hl{color:var(--hl);}
  .label{font-family:var(--mono);font-size:34px;color:var(--hl);text-transform:uppercase;letter-spacing:.03em;margin-bottom:32px;}
  .rule{height:6px;width:120px;background:var(--hl);margin:40px 0;border-radius:9999px;}
  .spacer{height:40px;}
"""
CSS = (CSS.replace("@GOOGLE_IMPORT@", GOOGLE_IMPORT)
          .replace("@BG@", BG).replace("@INK@", INK).replace("@ACCENT@", ACCENT)
          .replace("@FONT_DISP@", FONT_DISP).replace("@FONT_BODY@", FONT_BODY)
          .replace("@FONT_MONO@", FONT_MONO))

NUM_RE = re.compile(r"(\$?\d[\d,\.]*\s?(?:%|B|bn|billion|million|M|k|K|x)?\b|\$\d[\d,\.]*)")


def esc(s):
    # element-content escaping: only &, <, >. Apostrophes/quotes stay literal
    # (we are never emitting into an attribute), so no &#x27; junk on slides.
    return _html.escape(s or "", quote=False)


def hl(s):
    """Wrap the first number-ish token in a highlight span for spark.

    Operates on the RAW string and escapes each piece separately, so the
    highlight can never land inside an HTML entity and split it."""
    s = s or ""
    m = NUM_RE.search(s)
    if not m:
        return esc(s)
    return esc(s[:m.start()]) + f'<span class="hl">{esc(m.group(0))}</span>' + esc(s[m.end():])


def split_sentences(text):
    if not text:
        return []
    text = re.sub(r"\s*\n+\s*", " ", str(text))
    parts = re.split(r"(?<=[.?!…])\s+(?=[A-Z\"'‘“£$])", text)
    return [p.strip() for p in parts if p.strip()]


def group(sentences, per=2, cap=4):
    """Bundle sentences into <=cap slides of ~per sentences each."""
    if not sentences:
        return []
    n = max(1, min(cap, (len(sentences) + per - 1) // per))
    per = (len(sentences) + n - 1) // n
    return [sentences[i:i + per] for i in range(0, len(sentences), per)]


def deck_from_script(x):
    """Derive an ordered list of (kicker, html_body, cue) slides from a script."""
    facet = (x.get("facet") or "").strip()
    k_open = facet.replace("-", " ").title() if facet else PRIMARY_LABEL
    slides = []

    # 1) cover: text_hook as the punch, first number blown up if there is one
    hook = x.get("text_hook") or x.get("spoken_hook") or x.get("title") or ""
    m = NUM_RE.search(hook)
    if m and len(m.group(0)) >= 3:
        rest = (hook[:m.start()] + hook[m.end():]).strip(" ?.-–")
        cover = f'<div><span class="stat hl">{esc(m.group(0))}</span></div>'
        if rest:
            cover += f'<div class="spacer"></div><h1 class="lead">{esc(rest)}</h1>'
    else:
        cover = f'<h1 class="lead">{hl(hook)}</h1>'
    slides.append((k_open, cover, "swipe"))

    # 2..n) the argument: sentences of the spoken body, minus the opening hook line
    body = split_sentences(x.get("script") or "")
    hlines = set(split_sentences(x.get("spoken_hook") or ""))
    body = [s for s in body if s not in hlines]
    for chunk in group(body, per=2, cap=4):
        html = "".join(f'<p class="body">{hl(s)}</p>' for s in chunk)
        slides.append(("", html, "swipe"))

    # n-1) the lesson: value line, eyebrowed
    val = x.get("value") or ""
    if val:
        val = re.sub(r"^[A-Z\s]{3,}:\s*", "", val)  # strip a TYPE: prefix if present
        slides.append(("The lesson",
                        f'<div class="label">Steal this</div><h1 class="lead">{hl(val)}</h1>',
                        "swipe"))

    # n) the close: cta if present, else a generic prompt
    cta = x.get("cta")
    if cta:
        close = f'<h1 class="mid">{hl(cta)}</h1>'
    else:
        close = ('<h1 class="lead">Your move.</h1><div class="spacer"></div>'
                 '<p class="body">Save this. Then go use it this week.</p>')
    slides.append(("Your move", close, "follow"))
    return slides


def render_deck(x):
    slides = deck_from_script(x)
    total = len(slides)
    sec = []
    for i, (kicker, body, cue) in enumerate(slides, 1):
        cue_html = ('<span class="swipe">Follow for more &rarr;</span>' if cue == "follow"
                    else '<span class="swipe">swipe &rarr;</span>')
        sec.append(f"""<section class="slide">
  <div class="top"><span class="kicker">{esc(kicker)}</span><span class="num">{i:02d} / {total:02d}</span></div>
  <div class="main">{body}</div>
  <div class="foot">{BYLINE}{cue_html}</div>
</section>""")
    return f"<style>{CSS}</style>\n" + "\n".join(sec)


def to_pdf(chrome, html_path, pdf_path):
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=6000", f"--print-to-pdf={pdf_path}", html_path],
                   check=True, capture_output=True)


def build_one(chrome, x, force=False):
    sid = x.get("id") or "carousel"
    hp = os.path.join(OUT, f"{sid}.html")
    pp = os.path.join(OUT, f"{sid}.pdf")
    if os.path.exists(hp) and not force:
        print(f"  {sid}: .html exists, reusing it (pass --force to regenerate). Rendering PDF.")
    else:
        open(hp, "w").write(render_deck(x))
    to_pdf(chrome, hp, pp)
    print(f"  {sid}: {os.path.relpath(pp, WS)}")


def load_weeks():
    out = []
    files = sorted(glob.glob(os.path.join(WS, "weeks", "*.json")), reverse=True)
    if not files and WS != HERE:
        files = sorted(glob.glob(os.path.join(HERE, "weeks", "*.json")), reverse=True)
    for f in files:
        try:
            out.append(json.load(open(f)))
        except Exception:
            pass
    return out


def find_by_ids(ids):
    want = set(ids)
    found = {}
    for w in load_weeks():
        for x in (w.get("distribution") or []) + (w.get("office") or []):
            if x.get("id") in want:
                found[x["id"]] = x
    return [found[i] for i in ids if i in found]


def main():
    argv = sys.argv[1:]
    args, skip = [], False
    for a in argv:
        if skip:
            skip = False
            continue
        if a == "--dir":
            skip = True
            continue
        if not a.startswith("-"):
            args.append(a)
    force = "--force" in argv
    if args:
        items = find_by_ids(args)
        missing = set(args) - {x.get("id") for x in items}
        if missing:
            print("not found in weeks/*.json:", ", ".join(sorted(missing)))
    else:
        q = sorted(glob.glob(os.path.join(OUT, "carousel-queue-*.json")), reverse=True)
        if not q:
            print(f"No carousel-queue-*.json in {OUT}. Flag scripts in the dashboard "
                  "and click 'Export carousel queue', or pass script id(s) as arguments.")
            return
        print("queue:", os.path.basename(q[0]))
        items = json.load(open(q[0])).get("items", [])
    if not items:
        print("nothing to build.")
        return
    chrome = find_chrome()
    print(f"building {len(items)} carousel(s) ->")
    for x in items:
        build_one(chrome, x, force=force)
    print("done.")


if __name__ == "__main__":
    main()

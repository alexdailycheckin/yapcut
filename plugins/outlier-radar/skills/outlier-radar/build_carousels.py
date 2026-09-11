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
# The byline carries a PHOTO and a TITLE when radar-config supplies them, not just a name.
# A creator's face is the only part of a branded card that is unarguably theirs, and a deck
# that ships with a platform glyph where the face should be is indistinguishable from anyone
# else's deck in the same template. carousel.brand_author has held {name, org, photo} since
# 2026-08-14 and this line ignored all three of them until 2026-09-10.
_AUTHOR = (CFG.get("carousel") or {}).get("brand_author") or {}
_A_NAME = _AUTHOR.get("name") or NAME
_A_ORG = _AUTHOR.get("org") or ""
_A_PHOTO = _AUTHOR.get("photo") or ""


def _photo_uri(path):
    """Inline as a data URI so the deck stays self-contained, same rule as the LinkedIn mark."""
    if not path or not os.path.exists(path):
        return ""
    import base64, mimetypes
    mime = mimetypes.guess_type(path)[0] or "image/png"
    with open(path, "rb") as fh:
        return f"data:{mime};base64," + base64.b64encode(fh.read()).decode()


_A_URI = _photo_uri(_A_PHOTO)
if _A_URI:
    _mark = f'<img class="pfp" src="{_A_URI}" alt="">'
    _who = (f'<span class="who"><span class="nm">{_html.escape(_A_NAME)}</span>'
            + (f'<span class="org">{_html.escape(_A_ORG)}</span>' if _A_ORG else "")
            + '</span>')
    BYLINE = f'<span class="byline">{_mark}{_who}</span>'
else:
    # no photo configured: fall back to the platform mark rather than shipping a bare name
    BYLINE = f'<span class="byline">{LI_SVG}<span class="nm">{_html.escape(NAME)}</span></span>'
    print("carousel byline: no carousel.brand_author.photo in radar-config, "
          "falling back to the LinkedIn mark")

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
  .slide.cover{background:var(--ink);color:var(--bg);}
  /* The bar is not decoration. Inverting the cover fixed luminance, edge and flatness
     but left RMS contrast at 36-41 against a 55 floor and accent at 0-2% against 4%,
     because a near-black frame with small type has neither a bright mass nor a colour
     mass. One full-width accent block supplies both, and it reads as a deliberate rule
     rather than a patch. Sized so it clears the floor on a deck with no stat at all. */
  /* Cover type is set MUCH larger than an interior slide. 84px on a 1080px frame is a
     body size: it left RMS contrast at 38-44 against a 55 floor even on an inverted
     ground, because there was almost no bright mass to vary against the dark. The
     scroll-stop rule is that the subject occupies 40 to 70% of the frame, and on a text
     cover the type IS the subject. */
  .slide.cover h1{font-size:150px;line-height:0.98;}
  .slide.cover .stat{font-size:210px;line-height:0.92;}
  .slide.cover .main::after{content:"";display:block;width:100%;height:150px;
    background:var(--hl);margin-top:64px;flex:none;}
  .slide.cover .kicker,.slide.cover .num{color:color-mix(in srgb,var(--bg) 62%,transparent);}
  .slide.cover h1,.slide.cover .nm{color:var(--bg);}
  .slide.cover .stat{color:var(--hl);}
  .slide.cover .org,.slide.cover .swipe{color:var(--hl);}
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
  .byline .pfp{width:64px;height:64px;flex:none;border-radius:50%;object-fit:cover;}
  .byline .who{display:flex;flex-direction:column;line-height:1.15;}
  .byline .nm{font-family:var(--disp);font-weight:700;font-size:32px;color:var(--ink);letter-spacing:-.01em;}
  .byline .org{font-family:var(--mono);font-size:22px;color:var(--hl);letter-spacing:.02em;}
  .stable{border-top:3px solid var(--ink);margin:8px 0 26px;}
  .srow{display:flex;justify-content:space-between;align-items:baseline;gap:24px;
    padding:26px 0;border-bottom:3px solid var(--ink);}
  .slab{font-size:38px;line-height:1.25;}
  .sval{font-family:var(--disp);font-weight:700;font-size:68px;color:var(--hl);flex:none;}
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

# ---- optional dark skin -----------------------------------------------------
# A workspace holding assets/reach-system/ gets a second skin: near-black ground, real
# fractal-noise grain, a soft bloom, serif display. Opt-in by the presence of those files
# rather than by a config flag, because the skin cannot render without them and a flag that
# silently produces an unstyled deck is worse than no flag. Set carousel.skin "paper" to
# force the light one back on.
SKIN_DIR = os.path.join(WS, "assets", "reach-system")
SKIN = (CFG.get("carousel") or {}).get("skin") or ("reach" if os.path.isdir(SKIN_DIR) else "paper")


def _skin_assets():
    """((grain_svg, filter_id), bloom_uri). Any piece may be empty; the skin degrades."""
    import base64 as _b64
    grain, fid = "", ""
    gp = os.path.join(SKIN_DIR, "grain-and-defs.svg")
    if os.path.exists(gp):
        m = re.search(r"<filter\b.*?</filter>", open(gp).read(), re.S)
        if m:
            grain = m.group(0)
            f = re.search(r'id="([^"]+)"', grain)
            fid = f.group(1) if f else ""
    bloom = ""
    bp = os.path.join(SKIN_DIR, "gradient-bloom-cyan.png")
    if os.path.exists(bp):
        bloom = "data:image/png;base64," + _b64.b64encode(open(bp, "rb").read()).decode()
    return (grain, fid), bloom


DARK_CSS = r"""
  @import url('https://fonts.googleapis.com/css2?family=Hanken+Grotesk:wght@400;500;600;700&family=Space+Mono:wght@400;700&display=swap');
  @font-face{font-family:'Romie';src:url('@ROMIE@') format('truetype');font-weight:500;}
  :root{--bg:#0F0F0F;--ink:#E7E5E4;--hl:@JEWEL@;--dim:#A9A29D;
    --disp:'Romie',Georgia,serif;--mono:'Space Mono',monospace;--body:'Hanken Grotesk',system-ui,sans-serif;}
  *{margin:0;padding:0;box-sizing:border-box;}
  body{margin:0;background:#0F0F0F;}
  .slide{width:1080px;height:1350px;background:var(--bg);color:var(--ink);font-family:var(--body);
    padding:70px 64px 56px;display:flex;flex-direction:column;position:relative;overflow:hidden;}
  .slide>*:not(.bloom):not(.grain){position:relative;z-index:2;}
  .bloom{position:absolute;width:820px;height:820px;right:-300px;top:-260px;opacity:.30;
    filter:blur(46px);pointer-events:none;z-index:0;}
  .slide:nth-of-type(even) .bloom{right:auto;left:-340px;top:auto;bottom:-300px;opacity:.20;}
  .grain{position:absolute;inset:0;pointer-events:none;z-index:1;opacity:.5;}
  .top{display:flex;justify-content:space-between;font-family:var(--mono);font-size:21px;
    letter-spacing:.14em;text-transform:uppercase;color:var(--hl);margin-bottom:30px;}
  .main{flex:1;display:flex;flex-direction:column;justify-content:center;}
  h1{font-family:var(--disp);font-weight:500;line-height:1.03;letter-spacing:-.01em;}
  .big{font-size:100px;} .lead{font-size:80px;} .mid{font-size:56px;}
  .slide.cover h1{font-size:100px;}
  .stat{font-family:var(--disp);font-size:150px;color:var(--hl);line-height:.92;display:block;}
  .slide.cover .stat{font-size:180px;}
  p{font-size:34px;line-height:1.45;color:var(--dim);margin-bottom:22px;}
  p b,p strong{color:var(--ink);font-weight:600;}
  .hl{color:var(--hl);}
  .spacer{height:30px;}
  .foot{display:flex;justify-content:space-between;align-items:flex-end;}
  .byline{display:flex;align-items:center;gap:16px;}
  .byline .pfp{width:72px;height:72px;object-fit:cover;border:1px solid var(--hl);padding:4px;}
  .byline .li{width:40px;height:40px;flex:none;}
  .byline .who{display:flex;flex-direction:column;line-height:1.2;}
  .byline .nm{font-family:var(--body);font-weight:600;font-size:27px;color:var(--ink);}
  .byline .org{font-family:var(--mono);font-size:18px;color:var(--hl);letter-spacing:.03em;}
  .stable{border-top:1px solid #ffffff26;margin:6px 0 24px;}
  .srow{display:flex;justify-content:space-between;align-items:baseline;gap:24px;
    padding:26px 0;border-bottom:1px solid #ffffff26;}
  .slab{font-size:34px;line-height:1.25;color:var(--dim);}
  .sval{font-family:var(--disp);font-size:72px;color:var(--hl);flex:none;line-height:1;}
  .panel{border:1px solid #ffffff26;border-radius:20px;padding:34px 32px;margin-bottom:26px;
    background:#ffffff08;}
  .plabel{font-family:var(--mono);font-size:19px;letter-spacing:.13em;text-transform:uppercase;
    color:var(--hl);margin-bottom:24px;}
  .bars{display:flex;flex-direction:column;gap:22px;}
  .brow{display:grid;grid-template-columns:250px 1fr auto;align-items:center;gap:20px;}
  .blab{font-size:27px;color:var(--dim);line-height:1.2;}
  .btrack{height:34px;background:#ffffff12;border-radius:4px;overflow:hidden;}
  .bfill{display:block;height:100%;background:var(--hl);border-radius:4px;}
  .bval{font-family:var(--disp);font-size:44px;color:var(--ink);line-height:1;}
  .ico{width:34px;height:34px;color:var(--hl);}
  .swipe{font-family:var(--mono);font-size:20px;color:#8a8580;letter-spacing:.14em;}
"""

CSS = (CSS.replace("@GOOGLE_IMPORT@", GOOGLE_IMPORT)
          .replace("@BG@", BG).replace("@INK@", INK).replace("@ACCENT@", ACCENT)
          .replace("@FONT_DISP@", FONT_DISP).replace("@FONT_BODY@", FONT_BODY)
          .replace("@FONT_MONO@", FONT_MONO))

if SKIN == "reach":
    _romie = os.path.join(WS, "assets", "fonts", "RomieTrial-Medium.ttf")
    CSS = (DARK_CSS.replace("@ROMIE@", "file://" + _romie).replace("@JEWEL@", "#22CCEE"))


# The percent branch comes FIRST and carries no \b. A word boundary cannot exist between
# "%" and a following space, both being non-word characters, so the old single-branch
# pattern matched "48" and dropped the sign on every percentage in the deck. That made
# percentages unit-less, which in turn made them look comparable to bare counts.
NUM_RE = re.compile(r"(\$?\d[\d,\.]*\s?%|\$?\d[\d,\.]*\s?(?:bn|billion|million|B|M|k|K|x)?\b|\$\d[\d,\.]*)")


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
    # The lookahead must include a DIGIT. Without it a sentence beginning with a numeral never
    # starts a new sentence, so "48% run hybrid. 35% have a consumption component. 18% charge
    # on outcomes." parsed as ONE sentence and the whole list collapsed to a single figure.
    # The creator's numeral law means sentences open with numbers constantly, so this was
    # silently flattening exactly the data pages that most needed splitting.
    parts = re.split(r"(?<=[.?!…])\s+(?=[A-Z0-9\"'‘“£$])", text)
    return [p.strip() for p in parts if p.strip()]


def group(sentences, per=2, cap=4):
    """Bundle sentences into <=cap slides of ~per sentences each."""
    if not sentences:
        return []
    n = max(1, min(cap, (len(sentences) + per - 1) // per))
    per = (len(sentences) + n - 1) // n
    return [sentences[i:i + per] for i in range(0, len(sentences), per)]


# ---- drawable elements ------------------------------------------------------
# Boxes, bars, a chart and icons, drawn from the design tokens rather than pasted in as
# assets. The renderer used to know exactly 4 shapes: a headline, a paragraph, a stat row and
# the byline avatar. That is why every deck read as text on a nice ground. These are the
# vocabulary, and they are driven by figures already parsed out of the script, so no new field
# has to be written for them to fire.

_UNIT = re.compile(r"(\$|%|x\b|£|€)", re.I)


def _unit_of(v):
    m = _UNIT.search(v)
    return m.group(1).lower() if m else ""


def _magnitude(v):
    """Comparable size of a figure string, scaling k/m/bn suffixes."""
    n = re.sub(r"[^\d.]", "", v)
    if not n:
        return 0.0
    try:
        f = float(n)
    except ValueError:
        return 0.0
    low = v.lower()
    if "bn" in low or "billion" in low:
        f *= 1e9
    elif "m" in low and "million" in low or low.rstrip().endswith("m"):
        f *= 1e6
    elif low.rstrip().endswith("k"):
        f *= 1e3
    return f


def chartable(sents):
    """The longest run of CONSECUTIVE sentences sharing one explicit unit, else None.

    Same unit is not the same as comparable. In one script "67%" is a price rise, "37%" is a
    plan to reprice, and "48% / 35% / 18%" are shares of one pie. Charting all five on one axis
    because they end in the same symbol asserts a relationship that is not there.

    Consecutiveness is the signal that survives. A writer listing comparable quantities puts
    them next to each other; a figure that belongs to a different argument has prose between
    it and the list.
    """
    best, cur, unit = [], [], None
    for x in sents:
        g = _numbered(x)
        u = _unit_of(g[0]) if g else None
        if g and u and u == unit:
            cur.append(g)
        elif g and u:
            if len(cur) > len(best):
                best = cur
            cur, unit = [g], u
        else:
            if len(cur) > len(best):
                best = cur
            cur, unit = [], None
    if len(cur) > len(best):
        best = cur
    return best if len(best) >= 3 else None


def bar_chart(pairs):
    """Horizontal bars when the figures share a unit and are worth comparing.

    Two or more values of the same unit ARE a comparison, and a comparison drawn is read in a
    glance where a comparison listed has to be computed. Falls back to None when the units are
    mixed, because a bar next to a bar implies they are the same kind of thing.
    """
    if len(pairs) < 2:
        return None
    units = {_unit_of(v) for v, _ in pairs}
    # An EXPLICIT shared unit, never an absent one. Bare numbers are not comparable just
    # because neither carries a symbol: "67" (a percentage rise), "150" (a survey sample) and
    # "12" (months) all read as unit-less and would have been drawn as three bars of one
    # quantity. A chart that puts unrelated figures on one axis does not merely look wrong,
    # it asserts something false, and it asserts it more confidently than the prose did.
    if len(units) != 1 or not next(iter(units)):
        return None
    mags = [_magnitude(v) for v, _ in pairs]
    if min(mags) <= 0 or max(mags) / min(mags) > 500:
        return None
    top = max(mags)
    rows = []
    for (v, l), m in zip(pairs, mags):
        pct = max(6.0, 100.0 * m / top)
        rows.append(f'<div class="brow"><span class="blab">{esc(l)}</span>'
                    f'<span class="btrack"><span class="bfill" style="width:{pct:.1f}%"></span></span>'
                    f'<span class="bval">{esc(v)}</span></div>')
    return f'<div class="bars">{"".join(rows)}</div>'


ICONS = {
    "up": '<path d="M4 20 L12 8 L20 20" />',
    "flag": '<path d="M6 21V4h12l-3 4 3 4H6" />',
    "warn": '<path d="M12 3 L22 20 H2 Z M12 10v4 M12 17v.5" />',
    "eye": '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3"/>',
}


def icon(name, cls="ico"):
    d = ICONS.get(name)
    if not d:
        return ""
    return (f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">{d}</svg>')


def panel(inner, label=""):
    """A bordered block. The system's cards put data inside a panel, never loose on the page."""
    head = f'<div class="plabel">{esc(label)}</div>' if label else ""
    return f'<div class="panel">{head}{inner}</div>'


def _numbered(sent):
    """(value, label) for a sentence built around one figure, else None.

    The label is the UNIT PHRASE that follows the number, not the sentence with the number
    cut out of it. Cutting leaves a hole: "The company is 20 months old" became "The company
    is months old", and "Roughly $108,000 of revenue per employee" became "Roughly of revenue
    per employee". Same defect as the cover headline, same fix. A stat row reads
    "20 / months old", so the words after the figure ARE the label.
    """
    ms = [m for m in NUM_RE.finditer(sent) if len(m.group(0)) >= 2]
    if not ms:
        return None
    m = max(ms, key=lambda x: len(x.group(0)))
    after = re.sub(r"^(of|in|a|an|the|per)\b\s*", "",
                   sent[m.end():].strip(" .,:;"), flags=re.I)
    # A comma ends the label. "across 35 markets, tuned to the local language" gave
    # "markets, tuned", which is half a label and half the next clause.
    after = re.split(r"[,;:]", after)[0]
    words = [w for w in re.split(r"\s+", after) if w]
    label = " ".join(words[:4]).strip(" .,:;")
    if len(label.split()) < 1:
        before = sent[:m.start()].strip(" .,:;")
        label = " ".join(before.split()[-4:])
    # Trim trailing function words. A label ending "revenue rate with about" is a sentence
    # fragment wearing a label's clothes, and it reads worse than the prose it replaced.
    for _ in range(3):
        label = re.sub(r"\s*\b(that|which|and|with|but|about|of|for|to|in|on|at|from|by|than|"
                       r"a|an|the|is|was|are)\b$", "", label, flags=re.I).strip(" .,:;")
    # A label that OPENS with a conjunction belongs to a sentence carrying two figures
    # ("usually runs 3 or 4 times that number"). Neither figure is the subject, so it is prose.
    if re.match(r"^(or|and|to|than)\b", label, flags=re.I):
        return None
    if not label or len(label) < 3 or len(label.split()) > 4:
        return None
    return m.group(0), label


def data_run(sents):
    """(start, end) of the longest run where most sentences carry a figure, else None.

    The run is found across the WHOLE body before chunking, because a stat table is a property
    of the argument, not of an arbitrary 2-sentence slice. Chunking first meant the decision
    was made on pairs and never saw the run.
    """
    flags = [bool(_numbered(x)) for x in sents]
    best = (0, 0)
    i = 0
    while i < len(flags):
        if not flags[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(flags) and (flags[j + 1] or (j + 2 < len(flags) and flags[j + 2])):
            j += 1
        # A ratio, not a hard count of exceptions. "At most 1 non-numeric line" failed the
        # first real data page by exactly one: the run held 4 figures across 6 sentences, with
        # "Do that division." and one two-number sentence sitting between them. Prose
        # interjections are normal inside a data run and they render under the table.
        span = j - i + 1
        hits = sum(flags[i:j + 1])
        if hits >= 3 and hits / span >= 0.6:
            if j - i > best[1] - best[0]:
                best = (i, j)
        i = j + 1
    return best if best[1] > best[0] else None


def stat_table(sents):
    """Label/value rows. The layout IS the argument on a data page."""
    rows, extra, seen = [], [], set()
    for x in sents:
        got = _numbered(x)
        if got and got[0] in seen:
            got = None            # the same figure twice is one row, not two
        if got:
            seen.add(got[0])
            n, l = got
            rows.append(f'<div class="srow"><span class="slab">{esc(l)}</span>'
                        f'<span class="sval">{esc(n)}</span></div>')
        else:
            extra.append(f'<p class="body">{hl(x)}</p>')
    return f'<div class="stable">{"".join(rows)}</div>{"".join(extra)}'


def deck_from_script(x):
    """Derive an ordered list of (kicker, html_body, cue) slides from a script."""
    facet = (x.get("facet") or "").strip()
    k_open = facet.replace("-", " ").title() if facet else PRIMARY_LABEL
    slides = []

    # 1) cover: text_hook as the punch, first number blown up if there is one
    hook = x.get("text_hook") or x.get("spoken_hook") or x.get("title") or ""
    # Lift the number into the display slot ONLY when the hook LEADS with it. Cutting a
    # number out of the middle and gluing the halves back together produces a hole where a
    # clause used to be: "Two AI studies disagree by 39 points." shipped as "Two AI studies
    # disagree by points", and "The market paid $5 billion." as "The market paid". Both went
    # to PDF on 2026-09-10 before anyone read the cover. A leading number is the only
    # position where removing it leaves something that still parses.
    m = NUM_RE.match(hook.lstrip())
    if m and len(m.group(0)) >= 3:
        rest = hook.lstrip()[m.end():].strip(" ?.-")
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
    # Pull the data run out as its own slide first, then prose-chunk what is left either side.
    run = data_run(body)
    segments = []
    if run:
        a, b = run
        if body[:a]:
            segments.append(("prose", body[:a]))
        segments.append(("stats", body[a:b + 1]))
        if body[b + 1:]:
            segments.append(("prose", body[b + 1:]))
    else:
        segments.append(("prose", body))
    for kind, seg in segments:
        if kind == "stats":
            # NB: the loop variable must not be `x`, which is this function's own parameter
            # holding the item. Shadowing it made deck_from_script crash on the next line that
            # touched the item, with a bare "'str' object has no attribute 'get'".
            prose, seen_v = [], set()
            for sent in seg:
                g = _numbered(sent)
                if g and g[0] not in seen_v:
                    seen_v.add(g[0])
                elif not g:
                    prose.append(sent)
            drawn = bar_chart(chartable(seg) or [])
            body_html = drawn or stat_table(seg)
            if drawn:
                body_html = panel(drawn, "the numbers") + "".join(
                    f'<p class="body">{hl(t)}</p>' for t in prose)
            # A blank kicker left interior headers empty while the cover, lesson and close all
            # had one, so the header flickered on and off as you swiped.
            slides.append((k_open, body_html, "swipe"))
            continue
        for chunk in group(seg, per=2, cap=3):
            slides.append((k_open, "".join(f'<p class="body">{hl(s)}</p>' for s in chunk), "swipe"))

    # n-1) the lesson: value line, eyebrowed
    val = x.get("value") or ""
    if val:
        # Strip a leading field label of any case. The old pattern only caught ALL CAPS, so
        # "Reframe: AI did not remove humans..." shipped with the internal label on the card.
        val = re.sub(r"^[A-Za-z][A-Za-z ]{2,20}:\s*", "", val).strip()
        slides.append(("The lesson",
                        f'<div class="label">Steal this</div><h1 class="lead">{hl(val)}</h1>',
                        "swipe"))

    # n) the close: cta if present, else a generic prompt
    cta = x.get("cta")
    if cta:
        close = f'<h1 class="mid">{hl(cta)}</h1>'
    else:
        # "Your move. Save this." is the stock CTA the creator's own gates ban, and it shipped
        # on every deck with no cta set. End on the payoff instead: the last line of the
        # script is the thing the deck was built to arrive at.
        tail = body[-1] if body else ""
        close = (f'<h1 class="mid">{hl(tail)}</h1>' if tail
                 else f'<h1 class="mid">{hl(hook)}</h1>')
    slides.append((k_open, close, "follow"))
    return slides


def render_deck(x):
    slides = deck_from_script(x)
    total = len(slides)
    sec = []
    for i, (kicker, body, cue) in enumerate(slides, 1):
        cue_html = ('<span class="swipe">Follow for more &rarr;</span>' if cue == "follow"
                    else '<span class="swipe">swipe &rarr;</span>')
        # Slide 1 is the only frame that competes in the feed, so it INVERTS: ink field,
        # paper type. Every deck this renderer has ever produced failed all 5 feed-floor
        # checks on its cover (2026-09-10: mean luminance 242 against a 200 ceiling, 94%
        # near-flat, accent under 1%), because a cream card with black type is beautiful
        # open and invisible at thumbnail size. visual_lint never caught it: it was handed
        # the PDF, could not read it, and crashed rather than failing. The interior slides
        # stay light, because those are read after the swipe, not scrolled past.
        cls = "slide cover" if i == 1 else "slide"
        skin_layers = ""
        if SKIN == "reach":
            (_g, _fid), _bloom = _skin_assets()
            if _bloom:
                skin_layers += f'<img class="bloom" src="{_bloom}" alt="">'
            if _fid:
                skin_layers += (f'<svg class="grain" viewBox="0 0 1080 1350" preserveAspectRatio="none">'
                                f'<rect width="1080" height="1350" filter="url(#{_fid})" '
                                f'fill="#ffffff" fill-opacity="0.30"/></svg>')
        sec.append(f"""<section class="{cls}">{skin_layers}
  <div class="top"><span class="kicker">{esc(kicker)}</span><span class="num">{i:02d} / {total:02d}</span></div>
  <div class="main">{body}</div>
  <div class="foot">{BYLINE}{cue_html}</div>
</section>""")
    head = f"<style>{CSS}</style>"
    if SKIN == "reach":
        (_g, _fid), _b = _skin_assets()
        if _g:
            head += f'\n<svg width="0" height="0" style="position:absolute"><defs>{_g}</defs></svg>'
    return head + "\n" + "\n".join(sec)


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

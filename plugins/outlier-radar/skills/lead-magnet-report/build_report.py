#!/usr/bin/env python3
"""Build a paginated lead-magnet report: one branded 4:5 document plus a print PDF.

Creator-agnostic. Nothing about this file assumes an industry, a brand, a colour or a
data source. It reads two JSON files and writes one HTML document:

    brand.json      who is publishing, and what it looks like
    findings.json   what was measured (see references/findings-schema.md)

    python3 build_report.py --dir <workspace>
    python3 build_report.py --dir <workspace> --pdf

The PDF pass drives headless Chrome, which is the only dependency beyond Python. The
document is 4:5 pages so it posts directly as a LinkedIn document, an Instagram carousel
or a slide deck, and prints to an 8 x 10 inch PDF one page per sheet.

WHY 4:5: it is the tallest aspect ratio the major feeds render without cropping, so it
buys the most screen height per swipe. Do not change it to 1:1 or 16:9 without also
re-checking every page for overflow.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
import html as _html

e = _html.escape

# ---------------------------------------------------------------- workspace
# One resolver for the whole plugin (Contract 2, 2026-09-09): yapcut_home.py in the sibling
# outlier-radar skill. realpath locates THIS file through any symlink and ../outlier-radar is
# the Radar skill inside the same plugin. The workspace itself is never located by resolving
# a symlink (that is the 2026-08 bug) and there is no skill-folder fallback.
_HERE = os.path.dirname(os.path.realpath(__file__))
_RADAR_SKILL = os.path.normpath(os.path.join(_HERE, "..", "outlier-radar"))
if not os.path.exists(os.path.join(_RADAR_SKILL, "yapcut_home.py")):
    sys.exit(f"yapcut_home.py not found at {_RADAR_SKILL}. lead-magnet-report ships beside "
             "outlier-radar in the same plugin; do not copy this skill out on its own.")
sys.path.insert(0, _RADAR_SKILL)
from yapcut_home import radar_home  # noqa: E402


def resolve_workspace(cli: str | None) -> pathlib.Path:
    """--dir when given, else yapcut_home's order: $YAPCUT_HOME, the legacy env keys, the cwd
    with a marker (brand.json counts), ~/outlier-radar. Exits 2 naming the places looked."""
    return radar_home(["--dir", cli] if cli else [])


# ---------------------------------------------------------------- palette

DEFAULTS = {
    # Two Google Fonts that pair without either being the obvious default. A serif with
    # real contrast for display, a mono for every number and label. Swap them in
    # brand.json; keep the ROLES (one display serif, one mono) or the pages lose their
    # register.
    "font_display": "Newsreader",
    "font_mono": "JetBrains Mono",
    "accent": "#3B82F6",
    "mode": "dark",
    "byline_name": "",
    "byline_org": "",
    "footer": "",
    "series_name": "The industry answer report",
    "avatar": "",          # optional path to a square image, relative to the workspace
    "cover_image": "",     # optional path to the cover photograph
}


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(t):
    return "#%02X%02X%02X" % tuple(max(0, min(255, round(v))) for v in t)


def _mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return _hex([ra[i] + (rb[i] - ra[i]) * t for i in range(3)])


def palette(accent: str, mode: str = "dark") -> dict:
    """Derive a whole page palette from ONE accent colour.

    Users give one hex. Everything else is arithmetic, so a rotated colour is the same
    document in a different key rather than a redesign. Deriving beats picking by eye:
    hand-picked neutrals drift apart across a series.
    """
    if mode == "dark":
        ink, ground = "#F6F4EF", "#07101F"
        return {
            "outer": _mix(accent, ground, 0.88),
            "panel": _mix(accent, ground, 0.82),
            "band": _mix(accent, ground, 0.42),
            "line": _mix(accent, ground, 0.66),
            "ink": ink,
            "dim": _mix(accent, ink, 0.55),
            "accent": accent,
            "tint": _mix(accent, ink, 0.42),
            "page": ground,
        }
    ink, ground = "#141D1A", "#FFFFFF"
    return {
        "outer": _mix(accent, ground, 0.94),
        "panel": ground,
        "band": _mix(accent, ground, 0.80),
        "line": _mix(accent, ground, 0.78),
        "ink": ink,
        "dim": _mix(accent, ink, 0.45),
        "accent": accent,
        "tint": _mix(accent, ink, 0.30),
        "page": _mix(accent, ground, 0.97),
    }


# ---------------------------------------------------------------- helpers

def data_uri(path: pathlib.Path) -> str:
    import base64
    ext = path.suffix.lower().lstrip(".")
    mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
            "webp": "image/webp", "svg": "image/svg+xml"}.get(ext, "application/octet-stream")
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode()


def fmt(v, unit=""):
    if isinstance(v, float):
        s = f"{v:,.2f}".rstrip("0").rstrip(".")
    else:
        s = f"{v:,}"
    return s + unit


class Doc:
    """Accumulates pages. Every page carries the byline last, which is also the
    overflow check: if the byline is missing from a rendered page, that page overflowed."""

    def __init__(self, brand, pal):
        self.b, self.p, self.pages = brand, pal, []

    # -- components ------------------------------------------------------
    def byline(self):
        b = self.b
        av = ""
        if b.get("_avatar_uri"):
            av = f'<img class="dot" src="{b["_avatar_uri"]}" alt="">'
        elif b.get("byline_name"):
            initials = "".join(w[0] for w in b["byline_name"].split()[:2]).upper()
            av = f'<span class="dot dot-txt">{e(initials)}</span>'
        who = e(b.get("byline_name", ""))
        org = f' &middot; {e(b["byline_org"])}' if b.get("byline_org") else ""
        return (f'<div class="byline">{av}<span><b>{who}</b>{org}</span>'
                f'<span class="pgno">{e(b.get("footer", ""))}</span></div>')

    def dl(self, items, rank=True):
        """label, bar, value. Ranked descending by default: a data list that is not in
        rank order reads as a mistake."""
        if rank:
            items = sorted(items, key=lambda r: -r[1])
        mx = max((v for _, v, _ in items), default=1) or 1
        out = []
        for k, v, label in items:
            faint = ' class="faint"' if str(label).startswith("~") else ""
            w = max(2, 100 * v / mx)
            out.append(f'<div{faint}><span class="k">{e(str(k))}</span>'
                       f'<span class="meter"><i style="width:{w:.0f}%"></i></span>'
                       f'<span class="v">{e(str(label).lstrip("~"))}</span></div>')
        return '<div class="dl">' + "".join(out) + "</div>"

    def dl2(self, items):
        """Two metrics on one row. Two four-row lists do not fit a page; one row
        carrying both does."""
        mx = max((v for _, v, _, _ in items), default=1) or 1
        out = []
        for k, v, a, b2 in items:
            w = max(2, 100 * v / mx)
            out.append(f'<div><span class="k">{e(str(k))}</span>'
                       f'<span class="meter"><i style="width:{w:.0f}%"></i></span>'
                       f'<span class="v">{e(str(a))}</span>'
                       f'<span class="v2">{e(str(b2))}</span></div>')
        return '<div class="dl">' + "".join(out) + "</div>"

    def rows(self, items):
        out = []
        for i, (title, subs) in enumerate(items, 1):
            s = "".join(f'<div class="sub"><span class="g">&#8627;</span>'
                        f'<span>{t}</span></div>' for t in subs)
            out.append(f'<div class="row"><span class="rnum">{i}</span>'
                       f'<div class="rbody"><div class="rtitle">{title}</div>{s}</div></div>')
        return '<div class="rows">' + "".join(out) + "</div>"

    def add(self, body, cls=""):
        self.pages.append((body, cls))


# ---------------------------------------------------------------- pages

def build_pages(d: Doc, F: dict) -> None:
    """Compose the document from whatever the findings file actually carries.

    Every block is conditional. A findings file with no engine split simply has no
    engine page, rather than a page of blanks. That is what makes one builder serve
    every industry.
    """
    b, p = d.b, d.p
    m = F["meta"]
    head = F.get("headline", {})
    series = e(b.get("series_name", "Report"))
    issue = m.get("issue", "01")

    # -- 01 cover: full-bleed object if supplied, otherwise type alone ----
    cover_img = ""
    if b.get("_cover_uri"):
        cover_img = (f'<img class="cover-bg" src="{b["_cover_uri"]}" alt="">'
                     f'<div class="cover-wash"></div>')
    measured = " ".join(x for x in [
        f'{fmt(m["questions"])} buyer questions.' if m.get("questions") else "",
        f'{fmt(m["answers"])} AI answers.' if m.get("answers") else "",
        f'{fmt(m["citations"])} citations' if m.get("citations") else "",
        f'across {fmt(m["cited_domains"])} domains.' if m.get("cited_domains") else "",
    ] if x)
    d.add(f'''{cover_img}<div class="inner cover-inner">
<h1 class="cover-title">{m["title_before"]}
<span class="em">{m["title_claim"]}</span>{m["title_after"]}</h1>
<div class="cover-eyebrow">{series} &middot; Issue {e(str(issue))}</div>
<div class="spacer"></div>
<div class="cover-foot">
  <div class="caption" style="margin-top:0">{e(measured)}</div>
  {d.byline()}
</div>''', cls="cover")

    # -- the anchor number ------------------------------------------------
    if head.get("anchor"):
        a = head["anchor"]
        d.add(f'''<div class="eyebrow">{e(a["label"])}</div>
<div class="spacer"></div>
<div class="figure">{e(a["value"])}</div>
<div class="unit" style="margin-top:2.2cqw">{e(a["unit"])}</div>
<div class="body" style="margin-top:3.4cqw">{a["body"]}</div>
<div class="spacer"></div>
<div class="caption">{e(a.get("caption", ""))}</div>
{d.byline()}''')

    # -- who wins -----------------------------------------------------
    if F.get("segments"):
        seg = F["segments"]
        top = F.get("top_outside", [])
        extra = ""
        if top:
            extra = (f'<div style="margin-top:3.4cqw"></div>'
                     f'<div class="eyebrow">{e(seg.get("extra_label", "The biggest wins"))}</div>'
                     f'<div style="margin-top:1.8cqw">'
                     + d.dl([(r["name"], r["value"], f'{r["value"]:.1f}%') for r in top[:3]],
                            rank=False) + '</div>')
        d.add(f'''<div class="eyebrow">{e(seg["eyebrow"])}</div>
<h2 style="margin-top:2.4cqw">{seg["headline"]}</h2>
<div style="margin-top:3.6cqw"></div>
{d.dl([(r["name"], r["value"], fmt(r["value"])) for r in seg["rows"]])}
{extra}
<div class="spacer"></div>
<div class="caption">{e(seg.get("caption", ""))}</div>
{d.byline()}''')

    # -- concentration band -------------------------------------------
    if F.get("concentration"):
        c = F["concentration"]
        segs = c["segments"]
        band = "".join(
            f'<span class="c{i+1}" style="flex:{s["value"]}">{e(s["short"])}</span>'
            for i, s in enumerate(segs))
        ends = ""
        if c.get("ends"):
            ends = '<div style="margin-top:3cqw" class="two">' + "".join(
                f'<div class="panel"><h3 class="phead">{e(x["label"])}</h3>'
                f'<div class="body">{x["body"]}</div></div>' for x in c["ends"]) + '</div>'
        d.add(f'''<div class="eyebrow">{e(c["eyebrow"])}</div>
<h2 style="margin-top:2.4cqw">{c["headline"]}</h2>
<div style="margin-top:3.4cqw"></div>
<div class="conc" style="height:16cqw">{band}</div>
<div style="margin-top:3cqw">
{d.dl([(s["name"], s["value"], fmt(s["value"])) for s in segs], rank=False)}
</div>
{ends}
<div class="spacer"></div>
<div class="caption">{e(c.get("caption", ""))}</div>
{d.byline()}''')

    # -- ranked tables (leaderboard, page types, sources, whatever) ----
    for t in F.get("tables", []):
        rank = t.get("rank", True)
        if t.get("rows") and len(t["rows"][0]) == 4:
            body = d.dl2([(r[0], r[1], r[2], r[3]) for r in t["rows"]])
        else:
            body = d.dl([(r[0], r[1], r[2]) for r in t["rows"]], rank=rank)
        colhead = ""
        if t.get("columns"):
            colhead = ('<div class="eyebrow colhead">'
                       + "".join(f"<span>{e(x)}</span>" for x in t["columns"])
                       + "</div>")
        anchor = ""
        if t.get("anchor"):
            anchor = (f'<div class="pair" style="margin-top:3.4cqw">'
                      f'<div class="figure-sm">{e(t["anchor"]["value"])}</div>'
                      f'<div class="lede">{t["anchor"]["body"]}</div></div>')
        d.add(f'''<div class="eyebrow">{e(t["eyebrow"])}</div>
<h2 style="margin-top:2.4cqw">{t["headline"]}</h2>
{anchor}
<div style="margin-top:{"1.6" if anchor else "3.2"}cqw"></div>
{colhead}{body}
<div class="spacer"></div>
<div class="caption">{t.get("caption", "")}</div>
{d.byline()}''')

    # -- the long-text list page, budgeted so it cannot overflow -------
    if F.get("question_list"):
        q = F["question_list"]
        budget = q.get("char_budget", 480)
        shown, used = [], 0
        for item in q["items"]:
            n = len(item["text"])
            if shown and used + n > budget:
                break
            shown.append(item)
            used += n
            if len(shown) >= q.get("max_rows", 6):
                break
        d.add(f'''<div class="eyebrow">{e(q["eyebrow"])}</div>
<h2 style="margin-top:2.4cqw">{q["headline"]}</h2>
<div style="margin-top:3cqw">
{d.rows([(e(i["text"]), [i["meta"]]) for i in shown])}
</div>
<div class="spacer"></div>
<div class="caption">{len(shown)} of {len(q["items"])} shown. {q.get("caption", "")}</div>
{d.byline()}''')

    # -- quad panels ---------------------------------------------------
    if F.get("quad"):
        qd = F["quad"]
        cells = "".join(
            f'<div class="panel"><h3>{e(c["label"])}</h3>'
            f'<div class="big">{e(c["value"])}</div>'
            f'<div class="sm">{e(c["primary"])}<br>'
            f'<span style="color:var(--accent)">{e(c["note"])}</span></div>'
            f'<div class="sm rule">{c["secondary"]}</div></div>' for c in qd["cells"])
        d.add(f'''<div class="eyebrow">{e(qd["eyebrow"])}</div>
<h2 style="margin-top:2.4cqw">{qd["headline"]}</h2>
<div class="quad" style="margin-top:3.2cqw">{cells}</div>
<div class="spacer"></div>
<div class="caption">{e(qd.get("caption", ""))}</div>
{d.byline()}''')

    # -- the gate: the only page that asks for anything ---------------
    g = F.get("gate")
    if g:
        nxt = ""
        if g.get("next"):
            nxt = (f'<div class="band" style="margin-top:3.4cqw">'
                   f'<span class="eyebrow">Up next</span>'
                   f'<span class="body">{e(g["next"])}</span></div>')
        d.add(f'''<div class="eyebrow">{e(g.get("eyebrow", "Next issue"))}</div>
<div class="spacer"></div>
<h2>{g["headline"]}</h2>
<div class="body" style="margin-top:3.4cqw">{g["body"]}</div>
{nxt}
<div class="spacer"></div>
<div class="caption">{g.get("method", "")}</div>
{d.byline()}''')


# ---------------------------------------------------------------- render

CSS = """
*{{box-sizing:border-box; margin:0; padding:0}}
body{{-webkit-print-color-adjust:exact; print-color-adjust:exact;
  background:{page}; color:{ink}; font-family:'{mono}',ui-monospace,monospace;
  min-height:100vh; display:flex; flex-direction:column; align-items:center;
  padding:18px 14px 96px}}
.stage{{width:100%; max-width:760px; display:flex; justify-content:center}}
.page{{position:relative; aspect-ratio:4/5; height:min(calc(100vh - 104px), 950px);
  width:auto; max-width:100%; background:{outer}; border:1px solid {line};
  overflow:hidden; display:none; container-type:size}}
.page.on{{display:block}}
@media (max-aspect-ratio:4/5){{.page{{height:auto; width:100%}}}}
.inner{{position:absolute; inset:2.4cqw 2.4cqw 2.4cqw 3.1cqw; display:flex;
  flex-direction:column; padding:4.2cqw 4.4cqw 2.6cqw; background:{panel};
  border:1px solid {line}}}
.cell{{position:absolute; top:4.2cqw; right:4.4cqw; display:grid;
  grid-template-columns:1.5cqw 1.5cqw; grid-template-rows:1.5cqw 1.5cqw}}
.cell i{{border:1px solid {line}}}
.cell i:nth-child(1),.cell i:nth-child(4){{background:{line}}}
.edge{{position:absolute; left:0; top:0; height:100%; width:.9%; background:{accent}}}
.eyebrow{{font-size:1.72cqw; letter-spacing:.26em; text-transform:uppercase; color:{tint}}}
.colhead{{display:flex; justify-content:space-between; margin-bottom:1.2cqw}}
h1,h2{{font-family:'{display}',Georgia,serif; font-weight:500; line-height:1.03;
  letter-spacing:-.015em}}
h2{{font-size:5.6cqw}}
.em{{color:{tint}; font-style:italic; font-weight:400}}
.body{{font-size:2.42cqw; line-height:1.62}}
.figure{{font-family:'{display}',Georgia,serif; font-weight:500; font-size:19cqw;
  line-height:.86; letter-spacing:-.03em}}
.figure-sm{{font-family:'{display}',Georgia,serif; font-weight:500; font-size:11cqw;
  line-height:.88; letter-spacing:-.03em}}
.pair{{display:flex; align-items:flex-end; gap:3.4cqw}}
.pair .lede{{flex:1; font-size:2.36cqw; line-height:1.55; color:{dim}; padding-bottom:.8cqw}}
.unit{{font-size:2.1cqw; letter-spacing:.2em; text-transform:uppercase; color:{tint}}}
.spacer{{flex:1}}
.panel{{background:{outer}; border:1px solid {line}; padding:3.4cqw 3.8cqw}}
.phead{{font-size:1.56cqw; letter-spacing:.2em; text-transform:uppercase; color:{tint};
  font-weight:400; margin-bottom:1.4cqw}}
.band{{background:{band}; padding:2.4cqw 3.2cqw; display:flex; gap:2.4cqw;
  align-items:baseline; flex-wrap:wrap}}
.caption{{background:{outer}; border:1px solid {line}; padding:2.2cqw 2.4cqw;
  font-size:2.06cqw; line-height:1.5; color:{dim}; margin-top:2.4cqw}}
.rows{{display:flex; flex-direction:column; gap:3.2cqw}}
.row{{display:flex; gap:2.2cqw; align-items:flex-start}}
.rnum{{font-family:'{display}',serif; font-size:3.5cqw; color:{tint}; line-height:1;
  min-width:3.6cqw; font-weight:500}}
.rbody{{flex:1; min-width:0}}
.rtitle{{font-size:2.78cqw; line-height:1.34; margin-bottom:1cqw}}
.sub{{font-size:2.24cqw; line-height:1.5; color:{dim}; display:flex; gap:1.2cqw}}
.sub .g{{color:{tint}}}
.dl{{display:flex; flex-direction:column}}
.dl div{{display:flex; align-items:baseline; gap:2.4cqw; padding:2.72cqw 0;
  border-bottom:1px solid {line}; font-size:2.66cqw}}
.dl div:last-child{{border-bottom:none}}
.dl .k{{flex:1; min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap}}
.dl .v{{font-variant-numeric:tabular-nums; color:{tint}}}
.dl .v2{{font-variant-numeric:tabular-nums; color:{dim}; font-size:2.16cqw;
  min-width:8.6cqw; text-align:right}}
.dl .faint .k,.dl .faint .v{{opacity:.5}}
.meter{{height:1cqw; background:{line}; width:22cqw; flex:none}}
.meter i{{display:block; height:100%; background:{accent}}}
.two{{display:grid; grid-template-columns:1fr 1fr; gap:3.4cqw}}
.quad{{display:grid; grid-template-columns:1fr 1fr; gap:2.6cqw}}
.quad .panel{{padding:3.6cqw 3.4cqw}}
.quad h3{{font-size:1.56cqw; letter-spacing:.2em; text-transform:uppercase; color:{tint};
  font-weight:400; margin-bottom:1.6cqw}}
.quad .big{{font-family:'{display}',Georgia,serif; font-size:4.6cqw; line-height:1;
  margin-bottom:.9cqw}}
.quad .sm{{font-size:2.06cqw; line-height:1.45; color:{dim}}}
.quad .sm.rule{{margin-top:1.4cqw; padding-top:1.4cqw; border-top:1px solid {line}}}
.conc{{display:flex; border:1px solid {line}}}
.conc span{{display:flex; align-items:center; justify-content:center; font-size:2.3cqw}}
.c1{{background:{accent}; color:{outer}}}
.c2{{background:{band}}}
.c3{{background:{outer}; color:{dim}}}
.byline{{display:flex; align-items:center; gap:2cqw; padding-top:2cqw; margin-top:1.6cqw;
  border-top:1px solid {line}; font-size:1.86cqw; color:{dim}}}
.dot{{width:4cqw; height:4cqw; border-radius:50%; flex:none; object-fit:cover;
  border:1px solid {line}}}
.dot-txt{{display:flex; align-items:center; justify-content:center; background:{band};
  color:{ink}; font-size:1.6cqw}}
.byline b{{color:{ink}; font-weight:400}}
.pgno{{margin-left:auto}}
.cover-inner{{inset:0 !important; background:none !important; border:none !important;
  padding:6cqw 6.4cqw 4.6cqw 7cqw !important; text-align:center; align-items:center}}
.page.cover .cell{{display:none}}
.cover-bg{{position:absolute; inset:0; width:100%; height:100%; object-fit:cover}}
.cover-wash{{position:absolute; inset:0; background:linear-gradient(180deg,
  rgba(7,16,31,.52) 0%, rgba(7,16,31,.44) 34%, rgba(7,16,31,.08) 52%,
  rgba(7,16,31,.10) 70%, rgba(7,16,31,.86) 92%, rgba(7,16,31,.96) 100%)}}
.cover-title{{font-family:'{display}',Georgia,serif; font-weight:500; font-size:7.4cqw;
  line-height:1.02; letter-spacing:-.02em; color:{ink}; max-width:21ch;
  text-wrap:balance; text-shadow:0 .25cqw 3.8cqw rgba(5,12,24,.85),
  0 .12cqw .5cqw rgba(5,12,24,.6)}}
.cover-eyebrow{{font-size:1.62cqw; letter-spacing:.3em; text-transform:uppercase;
  color:{tint}; margin-top:3.2cqw}}
.cover-foot{{width:100%; text-align:left; margin-top:auto}}
.nav{{position:fixed; bottom:0; left:0; right:0; background:{page};
  border-top:1px solid {line}; display:flex; align-items:center; justify-content:center;
  gap:16px; padding:12px}}
button{{font-family:'{mono}',monospace; font-size:12px; letter-spacing:.12em;
  text-transform:uppercase; background:transparent; color:{ink};
  border:1px solid {line}; padding:9px 16px; cursor:pointer}}
button:hover{{border-color:{accent}; color:{tint}}}
button:disabled{{opacity:.35; cursor:default}}
.count{{font-size:12px; letter-spacing:.14em; color:{dim}; font-variant-numeric:tabular-nums}}
.dots{{display:flex; gap:6px}}
.dots i{{width:7px; height:7px; background:{line}; cursor:pointer}}
.dots i.on{{background:{accent}}}
:focus-visible{{outline:2px solid {accent}; outline-offset:2px}}
@media (prefers-reduced-motion:reduce){{*{{transition:none!important}}}}
@page{{size:8in 10in; margin:0}}
@media print{{
  body{{padding:0; background:{outer}; display:block}} .nav{{display:none}}
  /* .stage MUST become block: it is flex on screen, and print turns every page
     display:block, so a flex stage lays all pages out side by side on one sheet. */
  .stage{{max-width:none; display:block}}
  .page{{display:block!important; break-after:page; border:none;
    width:8in; height:10in; max-width:none}}
}}
"""

NAV_JS = """
(function(){
  var pp=[].slice.call(document.querySelectorAll('.page')),
      dd=[].slice.call(document.querySelectorAll('#dots i')), i=0;
  function go(n){
    i=Math.max(0,Math.min(pp.length-1,n));
    pp.forEach(function(p,k){p.classList.toggle('on',k===i)});
    dd.forEach(function(d,k){d.classList.toggle('on',k===i)});
    document.getElementById('cur').textContent=i+1;
    document.getElementById('pv').disabled=(i===0);
    document.getElementById('nx').disabled=(i===pp.length-1);
  }
  document.getElementById('pv').onclick=function(){go(i-1)};
  document.getElementById('nx').onclick=function(){go(i+1)};
  dd.forEach(function(d){d.onclick=function(){go(+d.dataset.g-1)}});
  document.addEventListener('keydown',function(ev){
    if(ev.key==='ArrowRight'||ev.key===' ')go(i+1);
    if(ev.key==='ArrowLeft')go(i-1);
  });
  go(0);
})();
"""


def render(d: Doc, title: str) -> str:
    b, p = d.b, d.p
    css = CSS.format(display=b["font_display"], mono=b["font_mono"], **p)
    fam = "&family=".join(x.replace(" ", "+") + ":wght@400;500"
                          for x in (b["font_display"], b["font_mono"]))
    body = "".join(
        f'<section class="page {cls}" data-p="{i+1}"><div class="edge"></div>'
        + (inner if cls == "cover" else
           f'<div class="inner"><div class="cell"><i></i><i></i><i></i><i></i></div>{inner}</div>')
        + ("</div></section>" if cls == "cover" else "</section>")
        for i, (inner, cls) in enumerate(d.pages))
    dots = "".join(f'<i data-g="{i+1}"></i>' for i in range(len(d.pages)))
    return f"""<title>{e(title)}</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family={fam}&display=swap">
<style>{css}</style>
<div class="stage">{body}</div>
<div class="nav">
  <button id="pv" aria-label="Previous page">Prev</button>
  <span class="count"><span id="cur">1</span> / {len(d.pages)}</span>
  <div class="dots" id="dots">{dots}</div>
  <button id="nx" aria-label="Next page">Next</button>
</div>
<script>{NAV_JS}</script>
"""


def to_pdf(html_path: pathlib.Path, pdf_path: pathlib.Path) -> bool:
    chrome = os.environ.get("CHROME") or next(
        (c for c in [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
            shutil.which("google-chrome"), shutil.which("chromium"),
            shutil.which("chromium-browser"),
        ] if c and pathlib.Path(c).exists()), None)
    if not chrome:
        print("no Chrome found; skipping PDF. Set CHROME=/path/to/chrome", file=sys.stderr)
        return False
    subprocess.run([chrome, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    "--virtual-time-budget=15000", f"--print-to-pdf={pdf_path}",
                    str(html_path)], check=True, capture_output=True)
    return True


def check_overflow(pdf_path: pathlib.Path, needle: str) -> list[int]:
    """The byline is the last element on every page, so a page missing it overflowed.
    Cheapest reliable check there is; browser-measured heights are unreliable here
    because a paginated container query can report a zero-height page."""
    try:
        from pypdf import PdfReader
    except ImportError:
        return []
    if not needle:
        return []
    r = PdfReader(str(pdf_path))
    return [i for i, pg in enumerate(r.pages, 1)
            if needle not in (pg.extract_text() or "")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir")
    ap.add_argument("--findings", default="findings.json")
    ap.add_argument("--out", default="report")
    ap.add_argument("--pdf", action="store_true")
    a = ap.parse_args()

    ws = resolve_workspace(a.dir)
    bp, fp = ws / "brand.json", ws / a.findings
    if not fp.exists():
        sys.exit(f"no findings at {fp}. See references/findings-schema.md")

    brand = dict(DEFAULTS)
    if bp.exists():
        brand.update(json.load(open(bp)))
    else:
        print(f"no brand.json at {bp}; using neutral defaults "
              f"({brand['font_display']} + {brand['font_mono']})", file=sys.stderr)
    for key, slot in (("avatar", "_avatar_uri"), ("cover_image", "_cover_uri")):
        if brand.get(key):
            path = (ws / brand[key]) if not os.path.isabs(brand[key]) else pathlib.Path(brand[key])
            if path.exists():
                brand[slot] = data_uri(path)
            else:
                print(f"{key} not found at {path}; continuing without it", file=sys.stderr)

    F = json.load(open(fp))
    pal = palette(brand["accent"], brand.get("mode", "dark"))
    d = Doc(brand, pal)
    build_pages(d, F)

    out_dir = ws / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{a.out}.html"
    html_path.write_text(render(d, F["meta"].get("doc_title", "Report")))
    print(f"{html_path}  {len(d.pages)} pages")

    if a.pdf:
        pdf_path = out_dir / f"{a.out}.pdf"
        if to_pdf(html_path, pdf_path):
            bad = check_overflow(pdf_path, brand.get("footer", ""))
            print(f"{pdf_path}" + (f"  OVERFLOWING PAGES: {bad}" if bad else "  no overflow"))


if __name__ == "__main__":
    main()

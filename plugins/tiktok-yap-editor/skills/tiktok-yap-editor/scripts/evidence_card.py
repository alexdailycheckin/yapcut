#!/usr/bin/env python3
"""evidence_card.py: build the receipt cards that burn_pips.py composites.

Six card types, one geometry, all brand-typeset, all transparent PNG at the
locked <=972px receipt width so they drop straight into an _overlays.json
`{"type":"pip","file":...}` entry with no pipeline changes.

  capture   wrap a REAL page screenshot (from capture_gate.py, already cropped
            to the headline by DOM geometry) in the white card + source pill
  quote     typeset the real headline + dek + source + date. Use when the page
            refuses to be shot cleanly (bot wall, hard consent wall, paywall).
            Still a receipt: the words and the attribution are the page's own.
  stat      one figure, one label. The default for a number beat.
  bars      2-4 labelled bars. For "X vs Y" claims, which no screenshot shows well.
  timeline  dated ticks along a rule. For "this happened, then this" claims.
  chips     a row of short spec chips. For "2.8T params / MXFP4 / open weights".

Why not just screenshot everything: half the claims in a Radar episode are a
number or a comparison, and a news screenshot of a number is a wall of small
grey type that nobody reads on a phone. A typeset figure is legible in the
0.4s it is glanceable for. Screenshots stay the default where the page itself
is the evidence.

Hard rules kept: real sources only (nothing here invents a fact, every card
carries the source domain), text always wins over overlays (the caller passes
y/w and burn_pips honours cap_<out>.ass.meta.json), receipt ink stays inside
the card so platform chrome cannot clip it.

Usage:
  evidence_card.py capture  --src raw/x.png --domain pcgamer.com --date "29 Jul 2026" --out card.png
  evidence_card.py quote    --headline "..." [--dek "..."] --domain forbes.com --date "21 Sep 2025" --out card.png
  evidence_card.py stat     --value '$5T' --label "market cap, first ever" --domain cnbc.com --out card.png
  evidence_card.py bars     --domain gulfnews.com --label "Google pays Apple, per year" \
                            --bar "2022|20|\\$20B" --bar "2014|1|\\$1B" --out card.png
  evidence_card.py timeline --domain digiday.com --label "self-serve ads" \
                            --tick "Oct 2000|Google AdWords" --tick "2026|ChatGPT ads" --out card.png
  evidence_card.py chips    --domain huggingface.co --chip "2.8T params" --chip "MXFP4" --out card.png
"""
import argparse
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFont

CARD_W = 972                  # locked receipt width in the 1080x1920 frame
PAD = 30
RADIUS = 30
FONTS = pathlib.Path.home() / "Library" / "Fonts"

# alexmuresan.com brand. Tang is the spark, used on ONE element per card.
BONE = (255, 255, 251, 255)
INK = (35, 35, 35, 255)
TANG = (255, 90, 42, 255)
MUTE = (120, 120, 118, 255)
HAIR = (0, 0, 0, 38)


def font(name: str, size: int):
    """Brand faces, with a legible fallback rather than a crash: a missing font
    should degrade the card, not fail the build at 2am."""
    for cand in (FONTS / name, pathlib.Path("/System/Library/Fonts") / name):
        if cand.exists():
            return ImageFont.truetype(str(cand), size)
    for fb in ("/System/Library/Fonts/SFNS.ttf",
               "/System/Library/Fonts/Helvetica.ttc"):
        if pathlib.Path(fb).exists():
            return ImageFont.truetype(fb, size)
    return ImageFont.load_default()


def display(size):      # headline / figure face
    return font("BricolageGrotesque-ExtraBold.ttf", size)


def mono(size):         # labels, source pills, dates: 400, see tracked()
    return font("spacemono-400.ttf", size)


def mono_light(size):
    return font("spacemono-400.ttf", size)


def mono_bold(size):    # only where the glyphs are large enough to survive it
    return font("spacemono-700.ttf", size)


def tracked(d, xy, text, fnt, fill, sp=2.0):
    """Draw with letter-spacing, and return the advance.

    Space Mono BOLD draws W with the middle apex short of the cap line, so at
    label sizes (24px) an uppercase W reads as a cyrillic Sh: GULFNEWS.COM came
    out GULFNEШS.COM. Labels therefore use the 400 weight, tracked, which is
    also what the brand note specifies. libass gets this via \\fsp; PIL has no
    tracking, so advance per glyph by hand.
    """
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=fnt, fill=fill)
        x += d.textlength(ch, font=fnt) + sp
    return x - xy[0] - sp


def tracked_w(d, text, fnt, sp=2.0):
    return sum(d.textlength(c, font=fnt) + sp for c in text) - sp if text else 0


def wrap(draw, text, fnt, max_w):
    lines, cur = [], ""
    for word in (text or "").split():
        trial = f"{cur} {word}".strip()
        if draw.textlength(trial, font=fnt) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_lines(draw, text, max_w, size_hi, size_lo, max_lines, faceh=display):
    """Shrink until the text fits max_lines. Nothing on a receipt may clip:
    a headline cut mid-word reads as a broken build, not a source."""
    for size in range(size_hi, size_lo - 1, -2):
        f = faceh(size)
        ls = wrap(draw, text, f, max_w)
        if len(ls) <= max_lines:
            return f, ls
    f = faceh(size_lo)
    ls = wrap(draw, text, f, max_w)
    return f, ls[:max_lines]


def canvas(h):
    im = Image.new("RGBA", (CARD_W, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, CARD_W - 1, h - 1], RADIUS, fill=BONE,
                        outline=HAIR, width=2)
    return im, d


def pill(d, x, y, text, fill=INK, fg=BONE, size=24):
    f = mono_light(size)
    w = tracked_w(d, text, f)
    d.rounded_rectangle([x, y, x + w + 30, y + size + 14], (size + 14) // 2,
                        fill=fill)
    tracked(d, (x + 15, y + 5), text, f, fg)
    return size + 14


def source_strip(d, y, domain, date="", accent=False):
    """Domain pill plus optional date. Every card is attributable or it is not
    a receipt."""
    h = pill(d, PAD, y, (domain or "").upper(),
             fill=TANG if accent else INK, size=24)
    if date:
        f = mono_light(24)
        dw = tracked_w(d, date.upper(), f)
        tracked(d, (CARD_W - PAD - dw, y + 8), date.upper(), f, MUTE)
    return h


# --- card types ------------------------------------------------------------

def card_capture(a):
    """Real screenshot, already cropped to the headline block by DOM geometry.
    No band-finding, no undimming: if the capture needed either of those it
    should have been rejected upstream."""
    src = Image.open(a.src).convert("RGB")
    inner = CARD_W - 2 * PAD
    scale = inner / src.width
    src = src.resize((inner, max(1, int(src.height * scale))), Image.LANCZOS)
    if a.max_h and src.height > a.max_h:
        src = src.crop((0, 0, src.width, a.max_h))
    strip = 38
    im, d = canvas(src.height + 2 * PAD + strip)
    im.paste(src, (PAD, PAD))
    source_strip(d, src.height + PAD + 6, a.domain, a.date)
    return im


def card_quote(a):
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    inner = CARD_W - 2 * PAD
    hf, hl = fit_lines(probe, a.headline, inner, 62, 34, 5)
    lh = int(hf.size * 1.16)
    y = PAD + 4
    body = []
    if a.dek:
        df, dl = fit_lines(probe, a.dek, inner, 30, 22, 3, faceh=mono_light)
        body = [(df, dl, int(df.size * 1.42))]
    h = y + len(hl) * lh + 18
    for df, dl, dlh in body:
        h += len(dl) * dlh + 10
    if a.byline:
        h += 34
    h += 38 + PAD
    im, d = canvas(h)
    yy = y
    for ln in hl:
        d.text((PAD, yy), ln, font=hf, fill=INK)
        yy += lh
    yy += 14
    for df, dl, dlh in body:
        for ln in dl:
            d.text((PAD, yy), ln, font=df, fill=MUTE)
            yy += dlh
        yy += 8
    if a.byline:
        d.text((PAD, yy), a.byline.upper(), font=mono_light(22), fill=MUTE)
        yy += 30
    source_strip(d, h - PAD - 32, a.domain, a.date)
    return im


def card_stat(a):
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    inner = CARD_W - 2 * PAD
    vf = display(148)
    while probe.textlength(a.value, font=vf) > inner and vf.size > 60:
        vf = display(vf.size - 4)
    lf, ll = fit_lines(probe, a.label or "", inner, 34, 24, 2, faceh=mono)
    llh = int(lf.size * 1.4)
    h = PAD + int(vf.size * 1.12) + 12 + len(ll) * llh + 20 + 38 + PAD
    im, d = canvas(h)
    vw = probe.textlength(a.value, font=vf)
    d.text(((CARD_W - vw) / 2, PAD - 6), a.value, font=vf, fill=INK)
    yy = PAD + int(vf.size * 1.12) + 8
    for ln in ll:
        w = d.textlength(ln.upper(), font=lf)
        d.text(((CARD_W - w) / 2, yy), ln.upper(), font=lf, fill=MUTE)
        yy += llh
    source_strip(d, h - PAD - 32, a.domain, a.date, accent=True)
    return im


def card_bars(a):
    """Comparison bars. The first bar is the point, so it gets the tang."""
    rows = []
    for spec in a.bar:
        parts = (spec.split("|") + ["", "", ""])[:3]
        rows.append((parts[0], float(parts[1] or 0), parts[2] or parts[1]))
    top = max([v for _, v, _ in rows] + [1e-9])
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lf, ll = fit_lines(probe, a.label or "", CARD_W - 2 * PAD, 30, 22, 2, faceh=mono)
    barh, gap = 74, 26
    h = PAD + (len(ll) * 34 + 14 if ll else 0) + len(rows) * (barh + gap) + 20 + 38 + PAD
    im, d = canvas(h)
    yy = PAD
    for ln in ll:
        d.text((PAD, yy), ln.upper(), font=lf, fill=MUTE)
        yy += 34
    if ll:
        yy += 12
    track = CARD_W - 2 * PAD
    for i, (name, val, shown) in enumerate(rows):
        nf = mono(24)
        d.text((PAD, yy), name.upper(), font=nf, fill=MUTE)
        yy += 30
        # floor the bar at a readable stub: a 1-vs-20 comparison rendered at
        # true scale looks like a checkbox, not a bar, and the point of the
        # card is that the reader sees a bar
        w = max(46, int(track * (val / top)))
        col = TANG if i == 0 else (200, 200, 196, 255)
        d.rounded_rectangle([PAD, yy, PAD + track, yy + barh - 30], 8,
                            fill=(238, 238, 234, 255))
        d.rounded_rectangle([PAD, yy, PAD + w, yy + barh - 30], 8, fill=col)
        vf = display(34)
        vw = d.textlength(shown, font=vf)
        # keep the value legible: inside the bar when it fits, outside when not
        if w > vw + 34:
            d.text((PAD + w - vw - 16, yy + 2), shown, font=vf,
                   fill=BONE if i == 0 else INK)
        else:
            d.text((PAD + w + 14, yy + 2), shown, font=vf, fill=INK)
        yy += barh - 30 + gap
    source_strip(d, h - PAD - 32, a.domain, a.date)
    return im


def card_timeline(a):
    ticks = [(s.split("|") + ["", ""])[:2] for s in a.tick]
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lf, ll = fit_lines(probe, a.label or "", CARD_W - 2 * PAD, 30, 22, 2, faceh=mono)
    rowh = 96
    h = PAD + (len(ll) * 34 + 16 if ll else 0) + len(ticks) * rowh + 10 + 38 + PAD
    im, d = canvas(h)
    yy = PAD
    for ln in ll:
        d.text((PAD, yy), ln.upper(), font=lf, fill=MUTE)
        yy += 34
    if ll:
        yy += 16
    rail = PAD + 16
    d.line([rail, yy + 18, rail, yy + len(ticks) * rowh - 40], fill=HAIR, width=3)
    for i, (when, what) in enumerate(ticks):
        cy = yy + 18 + i * rowh
        col = TANG if i == len(ticks) - 1 else INK
        d.ellipse([rail - 9, cy - 9, rail + 9, cy + 9], fill=col)
        d.text((rail + 30, cy - 26), when.upper(), font=mono(24), fill=MUTE)
        wf, wl = fit_lines(probe, what, CARD_W - rail - 30 - PAD, 40, 26, 2)
        ty = cy + 2
        for ln in wl:
            d.text((rail + 30, ty), ln, font=wf, fill=INK)
            ty += int(wf.size * 1.12)
    source_strip(d, h - PAD - 32, a.domain, a.date)
    return im


def card_chips(a):
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    lf, ll = fit_lines(probe, a.label or "", CARD_W - 2 * PAD, 30, 22, 2, faceh=mono)
    cf = display(38)
    rows, cur, curw = [], [], 0
    avail = CARD_W - 2 * PAD
    for c in a.chip:
        w = probe.textlength(c, font=cf) + 44
        if cur and curw + w + 16 > avail:
            rows.append(cur)
            cur, curw = [], 0
        cur.append((c, w))
        curw += w + 16
    if cur:
        rows.append(cur)
    ch = 68
    h = PAD + (len(ll) * 34 + 14 if ll else 0) + len(rows) * (ch + 16) + 8 + 38 + PAD
    im, d = canvas(h)
    yy = PAD
    for ln in ll:
        d.text((PAD, yy), ln.upper(), font=lf, fill=MUTE)
        yy += 34
    if ll:
        yy += 12
    for ri, row in enumerate(rows):
        x = PAD
        for ci, (c, w) in enumerate(row):
            first = ri == 0 and ci == 0
            d.rounded_rectangle([x, yy, x + w, yy + ch], ch // 2,
                                fill=TANG if first else (240, 240, 236, 255),
                                outline=None if first else HAIR, width=2)
            tw = d.textlength(c, font=cf)
            d.text((x + (w - tw) / 2, yy + 12), c, font=cf,
                   fill=BONE if first else INK)
            x += w + 16
        yy += ch + 16
    source_strip(d, h - PAD - 32, a.domain, a.date)
    return im


BUILDERS = {"capture": card_capture, "quote": card_quote, "stat": card_stat,
            "bars": card_bars, "timeline": card_timeline, "chips": card_chips}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kind", choices=sorted(BUILDERS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--domain", default="")
    ap.add_argument("--date", default="")
    ap.add_argument("--src", help="capture: raw screenshot png")
    ap.add_argument("--max-h", type=int, default=560, dest="max_h",
                    help="capture: max card image height after scaling")
    ap.add_argument("--headline", default="")
    ap.add_argument("--dek", default="")
    ap.add_argument("--byline", default="")
    ap.add_argument("--value", default="")
    ap.add_argument("--label", default="")
    ap.add_argument("--bar", action="append", default=[],
                    help="bars: 'name|number|shown'")
    ap.add_argument("--tick", action="append", default=[],
                    help="timeline: 'when|what'")
    ap.add_argument("--chip", action="append", default=[], help="chips: text")
    a = ap.parse_args()

    need = {"capture": ["src"], "quote": ["headline"], "stat": ["value"],
            "bars": ["bar"], "timeline": ["tick"], "chips": ["chip"]}[a.kind]
    for n in need:
        if not getattr(a, n):
            sys.exit(f"{a.kind} needs --{n.replace('_', '-')}")

    im = BUILDERS[a.kind](a)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out)
    print(f"{a.kind}: {im.width}x{im.height} -> {out}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""DEPRECATED (2026-08-05): superseded by capture_gate.py.

This script REPAIRED broken captures (cropping above a cookie modal,
undimming the wash, sliding an ink-density band) and so produced
plausible-looking cards from pages that never rendered. One 7-video batch
shipped 21 junk receipts that way. Kept only so existing installs keep
running; do not point a new episode at it. Use capture_gate.py, which rejects
instead of repairing and clips to the headline by DOM geometry.

cards_from_raws.py: turn captured raw page screenshots into receipt cards.

A fixed top-of-page crop misses on most news sites: the headline
sits below the nav, and consent overlays grey-wash the page so looks_blank and
the flat crop both throw away usable captures. This finds the headline band by
ink density, undoes the consent dimming, and emits the locked white card.

Usage:
  python3 cards_from_raws.py --raw show/receipts/2026-08-02/raw \
      --out show/receipts/2026-08-02 [--only d-20260802-1] [--band 520]
  python3 cards_from_raws.py --raw <dir> --out <dir> --shot d-20260802-1_1 \
      --crop 0,240,1300,420       # explicit crop when the auto band is wrong

Every card still needs an eyeball pass: auto-crop cannot judge whether the
headline that landed is the one the beat needs.
"""
import argparse, json, pathlib, re, sys
from PIL import Image, ImageDraw, ImageFont, ImageStat, ImageOps

CARD_W = 972
PAD = 26
RADIUS = 28


def ink_rows(img, thresh=140):
    """per-row count of dark pixels: headline bands spike, chrome does not"""
    g = img.convert("L")
    w, h = g.size
    px = g.load()
    step = max(1, w // 260)
    return [sum(1 for x in range(0, w, step) if px[x, y] < thresh) for y in range(h)]


def text_rows(img, thresh=140):
    """Per-row score that rewards TYPE and punishes photography.

    A line of text inks a slice of the row and leaves the rest white; a
    photo or a dark hero banner inks nearly every pixel of every row. Raw
    ink density cannot tell them apart, which is how a receipt ends up being
    the article's illustration instead of its headline.
    """
    rows = ink_rows(img, thresh)
    n = max(1, img.width // max(1, img.width // 260))
    out = []
    for c in rows:
        frac = c / n
        out.append(c if 0.02 < frac < 0.55 else (-c if frac >= 0.75 else 0))
    return out


def modal_top(img, min_gap=30):
    """First row occupied by a consent modal, or None.

    Cookie walls are the single biggest source of junk receipts: they are the
    most text-dense thing on the page, so any "pick the texty region" rule
    walks straight into them. They are also easy to spot, being a bright
    centred panel sitting on a page the same overlay has dimmed. Everything
    from here down is off limits.
    """
    g = img.convert("L")
    w, h = g.size
    px = g.load()
    cl, cr = int(w * 0.34), int(w * 0.66)
    ml, mr = int(w * 0.02), int(w * 0.12)
    hits = 0
    for y in range(0, h, 4):
        centre = sum(px[x, y] for x in range(cl, cr, 6)) / len(range(cl, cr, 6))
        margin = sum(px[x, y] for x in range(ml, mr, 4)) / len(range(ml, mr, 4))
        # a real consent wall dims the WHOLE page behind it, so the margin has
        # to be genuinely dark. A white article column on a light grey page
        # also has a bright centre, and truncating those was the failure mode
        # of the first version of this check.
        if centre > 215 and margin < 165 and centre - margin > min_gap:
            hits += 1
            if hits >= 12:                      # ~48px of sustained panel
                return max(0, y - 12 * 4)
        else:
            hits = 0
    return None


def find_band(img, band_h, top_skip=90, bottom=None):
    """slide a band_h window over the page, keep the most TEXT-like one below the nav"""
    rows = text_rows(img)
    if bottom is not None:
        rows = rows[:max(top_skip + 40, bottom)]
    h = len(rows)
    band_h = min(band_h, h - top_skip)
    if band_h <= 0:
        return (0, min(h, band_h or h))
    run = sum(rows[top_skip:top_skip + band_h])
    best, best_y = run, top_skip
    for y in range(top_skip + 1, h - band_h):
        run += rows[y + band_h - 1] - rows[y - 1]
        if run > best:
            best, best_y = run, y
    # back off to a quiet row so we do not slice a line of type in half
    y0 = best_y
    for y in range(best_y, max(top_skip, best_y - 60), -1):
        if rows[y] <= 0:
            y0 = y
            break
    y1 = min(h, y0 + band_h)
    # a modal ceiling can land mid-line; back off to the last gap between lines
    # so the card never ends on a half-height row of type
    if bottom is not None and y1 >= len(rows) - 1:
        for y in range(y1 - 1, max(y0 + 40, y1 - 90), -1):
            if rows[y] <= 0:
                y1 = y + 1
                break
    return (y0, y1)


def undim(img):
    """consent overlays wash the page toward mid grey; stretch it back"""
    st = ImageStat.Stat(img.convert("L"))
    if st.stddev[0] < 1:
        return img
    return ImageOps.autocontrast(img, cutoff=(0.4, 0.2))


def tighten(img, thresh=150, pad=18):
    """Shrink-wrap the crop to the ink.

    A news page renders with big empty side margins, so a full-width band
    spends most of the card on whitespace and the headline lands tiny once
    it is scaled to the card. Cropping to the actual text bounding box means
    the same card width is all type, which is the whole point of a receipt
    the viewer has to read on a phone.
    """
    g = img.convert("L")
    w, h = g.size
    px = g.load()
    colink = [sum(1 for y in range(0, h, 2) if px[x, y] < thresh)
              for x in range(0, w, 2)]
    if not any(colink):
        return img

    # 1. pick the main text column. News pages put a sidebar of unrelated
    #    headlines and an ad slot beside the story; a gutter of blank columns
    #    separates them, so keep only the heaviest ink block.
    blocks, cur = [], None
    gutter = 0
    for i, c in enumerate(colink):
        if c > 0:
            if cur is None:
                cur = [i, i]
            else:
                cur[1] = i
            gutter = 0
        elif cur is not None:
            gutter += 1
            if gutter >= 7:                       # 14px of blank at step 2
                blocks.append(tuple(cur)); cur = None; gutter = 0
    if cur is not None:
        blocks.append(tuple(cur))

    def col_text_score(a, b):
        """rows inside this column band that look like lines of type"""
        span = max(1, (b - a + 1))
        s = 0
        for y in range(0, h, 2):
            c = sum(1 for x in range(a * 2, min(w, (b + 1) * 2), 2)
                    if px[x, y] < thresh)
            frac = c / span
            if 0.02 < frac < 0.6:
                s += c
            elif frac >= 0.8:
                s -= c
        return s

    blocks = [t for t in blocks if (t[1] - t[0]) * 2 >= 120]
    if blocks:
        a, b = max(blocks, key=lambda t: col_text_score(*t))
        x0, x1 = a * 2, min(w, (b + 1) * 2)
    else:
        x0, x1 = 0, w

    # 2. trim trailing page furniture (audio players, share rails, related
    #    strips) that sits below the story block behind a band of whitespace.
    rowink = [sum(1 for x in range(x0, x1, 2) if px[x, y] < thresh)
              for y in range(0, h, 2)]
    ys = [i for i, c in enumerate(rowink) if c > 0]
    if not ys:
        return img
    top = ys[0]
    end = ys[-1]
    blank = 0
    for i in range(top, len(rowink)):
        if rowink[i] == 0:
            blank += 1
            if blank >= 22 and (i - blank - top) * 2 >= 110:
                end = i - blank
                break
        else:
            blank = 0
    y0, y1 = top * 2, min(h, (end + 1) * 2)

    x0, x1 = max(0, x0 - pad), min(w, x1 + pad)
    y0, y1 = max(0, y0 - pad), min(h, y1 + pad)
    if x1 - x0 < 60 or y1 - y0 < 30:
        return img
    return img.crop((x0, y0, x1, y1))


def build_card(src_png, out_png, domain, band_h=520, crop=None, tight=True):
    src = Image.open(src_png).convert("RGB")
    if crop:
        x, y, w, h = crop
        src = src.crop((x, y, x + w, y + h))
    else:
        y0, y1 = find_band(src, band_h, bottom=modal_top(src))
        src = src.crop((0, y0, src.width, y1))
    src = undim(src)
    if tight:
        src = tighten(src)

    scale = (CARD_W - 2 * PAD) / src.width
    src = src.resize((CARD_W - 2 * PAD, max(1, int(src.height * scale))), Image.LANCZOS)

    pill_h = 44
    card_w, card_h = CARD_W, src.height + 2 * PAD + pill_h
    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, card_w - 1, card_h - 1], RADIUS,
                        fill=(255, 255, 255, 255), outline=(0, 0, 0, 40), width=2)
    card.paste(src, (PAD, PAD))
    try:
        font = ImageFont.truetype("/System/Library/Fonts/SFNSMono.ttf", 24)
    except OSError:
        font = ImageFont.load_default()
    label = domain.upper()
    tw = d.textlength(label, font=font)
    py = card_h - pill_h + 4
    d.rounded_rectangle([PAD, py, PAD + tw + 28, py + 32], 16, fill=(35, 35, 35, 255))
    d.text((PAD + 14, py + 4), label, font=font, fill=(255, 255, 251, 255))
    card.save(out_png)
    return {"w": card_w, "h": card_h,
            "blank": ImageStat.Stat(src.convert("L")).stddev[0] < 6.0}


def domain_for(shot_id, week_path):
    if not week_path:
        return ""
    try:
        wk = json.load(open(week_path))
    except OSError:
        return ""
    ep_id, _, n = shot_id.rpartition("_")
    for it in wk.get("distribution", []):
        if it["id"] != ep_id:
            continue
        for s in it.get("shot_list", []):
            if str(s.get("n", s.get("shot"))) == n:
                u = (s.get("url") or "")
                m = re.match(r"https?://([^/]+)", u)
                return m.group(1).replace("www.", "") if m else ""
    return ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--week", default=None, help="week json, for the source pill")
    ap.add_argument("--only", default=None, help="episode id prefix filter")
    ap.add_argument("--shot", default=None, help="single shot id, e.g. d-20260802-1_1")
    ap.add_argument("--band", type=int, default=520)
    ap.add_argument("--crop", default=None, help="x,y,w,h explicit crop (with --shot)")
    ap.add_argument("--no-tight", action="store_true",
                    help="keep the page margins instead of shrink-wrapping to the ink")
    a = ap.parse_args()

    raw = pathlib.Path(a.raw)
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    crop = tuple(int(v) for v in a.crop.split(",")) if a.crop else None

    shots = sorted(raw.glob("*.png"))
    if a.shot:
        shots = [p for p in shots if p.stem == a.shot]
    if a.only:
        shots = [p for p in shots if p.stem.startswith(a.only)]
    if not shots:
        sys.exit("no raw captures matched")

    n_ok = 0
    for p in shots:
        dom = domain_for(p.stem, a.week)
        meta = build_card(p, out / f"{p.stem}.png", dom, a.band, crop,
                          tight=not a.no_tight)
        state = "blank" if meta["blank"] else "ok"
        n_ok += state == "ok"
        print(f"{p.stem}: {state}  {meta['w']}x{meta['h']}  {dom}")
    print(f"\n{n_ok}/{len(shots)} cards built -> {out}")


if __name__ == "__main__":
    main()

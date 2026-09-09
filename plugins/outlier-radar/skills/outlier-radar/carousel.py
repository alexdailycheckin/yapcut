#!/usr/bin/env python3
# Moved from the linkedin-engine skill on 2026-09-09: the spec-driven carousel renderer
# ships with the plugin that owns LinkedIn visuals. Spec doctrine: references/linkedin-visuals.md.
"""Editorial carousel card renderer. Spec-driven, no per-project forks.

    python3 carousel.py <spec.json>

The spec names a photo per card and the copy that sits under it. Everything
about the look (canvas, palette, type scale, margins) has a default here and is
overridable per spec, so a set stays internally consistent by default and a
one-off restyle never means editing this file.

Two card types:
  cover  photo, stacked title with the payoff line in the accent, numbered
         steps in mono, accent rule, receipt footer.
  depth  photo, tracked mono eyebrow, accent rule, headline, body paragraphs.
  matrix a 2x2 figure in place of the photo, then the depth text block.
  table  a comparison table in place of the photo, then the depth text block.

Card N of a set uses the same photo block height as the cover, so the eyebrow on
every depth card lands on the cover's title baseline and the set reads as one
carousel when swiped.

Why the photo is extended rather than sat on a flat panel: a studio render has a
left-to-right vignette, so a flat cream block seams against it visibly. Instead
the render's own bottom edge is sampled, squeezed to 40px and back to kill
per-column noise (it tiles into vertical banding otherwise), then ramped a few
percent lighter as it recedes. The type ends up on real table.
"""

import json
import os
import sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps


# Font resolution (2026-09-09): no literal user paths in a shipped script. Search the
# usual directories for the family; a spec "fonts" block still overrides everything.
import os as _os
_FONT_DIRS = [_os.path.expanduser("~/Library/Fonts"), "/Library/Fonts", "/System/Library/Fonts",
              "/System/Library/Fonts/Supplemental", "/usr/share/fonts", "/usr/local/share/fonts",
              _os.path.expanduser("~/.local/share/fonts"), _os.path.expanduser("~/.fonts")]

def _find_font(candidates, env_key):
    if _os.environ.get(env_key) and _os.path.exists(_os.environ[env_key]):
        return _os.environ[env_key]
    for d in _FONT_DIRS:
        for name in candidates:
            p = _os.path.join(d, name)
            if _os.path.exists(p):
                return p
        if _os.path.isdir(d):
            low = {f.lower(): f for f in _os.listdir(d)}
            for name in candidates:
                if name.lower() in low:
                    return _os.path.join(d, low[name.lower()])
    raise SystemExit(f"carousel.py: no font found for {candidates[0]} in {_FONT_DIRS}; set {env_key} or fonts.* in the spec")

DEFAULTS = {
    "canvas": {"w": 1600, "h": 2000, "photo_h": 1200},
    # INVERTED BY DEFAULT (creator ruling, 2026-08-12). Card 1 of a carousel IS the feed surface,
    # and LinkedIn's feed page is #F4F2EE. A cream field measures a 4.9% edge delta
    # against it, against a 25% floor, so a cream cover does not read as a weak image,
    # it reads as no image. The ink field measures 81.2%. Same three brand tokens,
    # opposite weighting: ink is the ground, cream is the figure.
    # muted was #8A8478, chosen against cream, where it scored 1.84:1 and was
    # effectively invisible for footers, table heads and matrix axis labels.
    # #B8B0A4 on ink scores 3.97:1. To ship a cream set on purpose (an article hero,
    # or an interior card in a set whose frame 1 is already inverted), pin the palette
    # in the spec; see references/carousel-cards.md.
    "palette": {"bg": "#232323", "ink": "#FFFFFB", "accent": "#FF5A2A", "muted": "#B8B0A4"},
    "margin": 112,
    "min_bottom": 100,
    # Branding is SPEC-DRIVEN and defaults to none, so the public kit ships neutral
    # (the 2026-07-01 privacy rule). A branded install injects these from its own
    # config when it writes the spec. All three can be on at once (dual branding,
    # the creator 2026-08-14): brand_header draws a wordmark chip top-center on every card,
    # brand_author draws {"name", "org"} bottom-left, brand_mark draws bottom-right.
    # Reserve vertical room for the author block by raising min_bottom to ~180.
    "brand_header": None,
    "brand_author": None,
    "brand_mark": None,
    # Thin border frame inset from the card edge: {"inset": 56, "width": 3,
    # "color": "#22CBED"}. None = no frame.
    "frame": None,
    # Film-grain strength 0-30 (0 = off). ~10 reads as print texture at feed size.
    "grain": 0,
    # Vertical room reserved at the top for brand_header, so the chip never overlaps
    # a photo or a figure. The photo/figure region shrinks by the same amount, so the
    # text baseline every card shares is unchanged. 170 fits the default chip.
    "header_band": 0,
    # Accent tones cycled by numbered units (cover steps, and any card carrying a
    # "jewel" index). None = everything uses palette accent.
    "jewels": None,
    "fonts": {
        "sans": None,   # resolved by _find_font() at load: HelveticaNeue.ttc, then Helvetica, Arial
        "sans_bold_index": 1,
        "sans_regular_index": 0,
        "sans_medium_index": 10,
        "mono": None,   # resolved by _find_font(): spacemono-700.ttf / SpaceMono-Bold.ttf in the user font dirs
        # Optional display serif pair. When set, titles, headlines, step text and step
        # numbers render in the serif, and accent title lines render in the italic
        # (the Reach editorial look). When null, display type falls back to bold sans.
        "serif": None,
        "serif_italic": None,
    },
    # Scale raised ~30% on 2026-08-11 on the creator's note, twice: cards are read at thumb
    # distance in a feed, and the first pass was set for a page. Bigger type also caps
    # copy per card, which is the constraint working rather than a cost.
    "type": {
        "cover_title": 118,
        "cover_title_leading": 126,
        "cover_step": 60,
        "cover_step_leading": 85,
        "cover_num": 38,
        "cover_gap": 62,        # title block to steps; tighten when a series eyebrow is on
        "cover_eyebrow_gap": 30,
        "footer": 34,
        "eyebrow": 32,
        "eyebrow_track": 4,
        "headline": 88,
        "headline_leading": 102,
        "body": 48,
        "body_leading": 66,
        "para_gap": 32,
        "matrix_cell": 46,
        "matrix_axis": 30,
        "table_head": 30,
        "table_cell": 48,
        "brand_mark": 26,
        "header": 36,
        "footer_name": 30,
        "footer_org": 26,
    },
}


def merge(base, over):
    out = dict(base)
    for k, v in (over or {}).items():
        out[k] = merge(base[k], v) if isinstance(v, dict) and isinstance(base.get(k), dict) else v
    return out


def rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def tracked(d, xy, text, font, fill, track):
    """Draw text with extra letter spacing. PIL has no tracking of its own."""
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=font, fill=fill)
        x += d.textlength(ch, font=font) + track


def wrap(d, text, font, width):
    lines, line = [], ""
    for word in text.split():
        probe = f"{line} {word}".strip()
        if d.textlength(probe, font=font) <= width:
            line = probe
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def photo_block(path, w, photo_h, h, bg):
    """Photo full bleed at the top, its own bottom edge extended to fill below.

    COVER-CROP, never stretch (the creator, 2026-08-14: a 4:3 render squeezed into a wider
    block turned round pies oval). Scale to fill, crop the excess, bias the crop
    toward the top because the recipe keeps the object in the upper two thirds.
    """
    photo = ImageOps.fit(Image.open(path).convert("RGB"), (w, photo_h),
                         Image.LANCZOS, centering=(0.5, 0.42))
    out = Image.new("RGB", (w, h), bg)
    out.paste(photo, (0, 0))

    edge = photo.crop((0, photo_h - 6, w, photo_h)).resize((w, 1), Image.LANCZOS)
    edge = edge.resize((40, 1), Image.LANCZOS).resize((w, 1), Image.LANCZOS)
    fill = edge.resize((w, h - photo_h), Image.NEAREST).filter(ImageFilter.GaussianBlur(1.2))
    px, rows = fill.load(), h - photo_h
    for y in range(rows):
        k = 1.0 + 0.06 * (y / rows)
        # Ramp the extension toward the panel colour as it recedes, so a photo shot
        # on one ground still lands on the set's panel by the time the type starts.
        # Starts at 0 at the photo edge, so there is no seam to mask.
        a = 0.45 * (y / rows)
        for x in range(w):
            r, g, b = px[x, y]
            px[x, y] = (min(255, int(r * k * (1 - a) + bg[0] * a)),
                        min(255, int(g * k * (1 - a) + bg[1] * a)),
                        min(255, int(b * k * (1 - a) + bg[2] * a)))
    out.paste(fill, (0, photo_h))
    return out


def draw_matrix(d, m, cfg, top, height, fonts):
    """A 2x2 matrix drawn INTO THE PHOTO REGION, not below it.

    Deliberate: the set only reads as one carousel while every card's eyebrow lands on the
    cover's title baseline. An infographic card that pushed the text down would break the
    swipe rhythm, so a diagram gets exactly the space a photo would have had and the text
    block underneath is untouched.
    """
    c, p, t = cfg["canvas"], cfg["palette"], cfg["type"]
    ink, accent, muted = rgb(p["ink"]), rgb(p["accent"]), rgb(p["muted"])
    med, mono, reg = fonts["med"], fonts["mono"], fonts["reg"]
    M = cfg["margin"]

    side = min(c["w"] - 2 * M - 150, height - 190)
    x0 = M + 150
    y0 = top + 96
    mid_x, mid_y = x0 + side // 2, y0 + side // 2

    hi = tuple(m.get("highlight") or [])
    for r in (0, 1):
        for col in (0, 1):
            if (r, col) == hi:
                d.rectangle([x0 + col * side // 2, y0 + r * side // 2,
                             x0 + (col + 1) * side // 2, y0 + (r + 1) * side // 2],
                            fill=rgb(p.get("wash", "#F4EFE6")))
    d.rectangle([x0, y0, x0 + side, y0 + side], outline=ink, width=3)
    d.line([(mid_x, y0), (mid_x, y0 + side)], fill=ink, width=3)
    d.line([(x0, mid_y), (x0 + side, mid_y)], fill=ink, width=3)

    f_cell = med(t["matrix_cell"])
    pad = 26
    for r in (0, 1):
        for col in (0, 1):
            cell = m["cells"][r][col]
            lines = wrap(d, cell, f_cell, side // 2 - 2 * pad)
            # Centre the text block in its quadrant; top-hung cells read as
            # half-empty boxes (the 2026-08-14 spacing pass).
            block = len(lines) * (t["matrix_cell"] + 12)
            cx = x0 + col * side // 2 + pad
            cy = y0 + r * side // 2 + max(pad, (side // 2 - block) // 2)
            fill = accent if (r, col) == hi else ink
            for line in lines:
                d.text((cx, cy), line, font=f_cell, fill=fill)
                cy += t["matrix_cell"] + 12

    f_ax = mono(t["matrix_axis"])
    tracked(d, (x0, y0 + side + 26), m["x_label"].upper(), f_ax, muted, t["eyebrow_track"])
    xw = d.textlength(m["y_label"].upper(), font=f_ax) + t["eyebrow_track"] * len(m["y_label"])
    lab = Image.new("RGBA", (int(xw) + 8, t["matrix_axis"] + 16), (0, 0, 0, 0))
    tracked(ImageDraw.Draw(lab), (0, 0), m["y_label"].upper(), f_ax, muted, t["eyebrow_track"])
    return lab, (M - 30, y0), y0 + side + 26 + t["matrix_axis"]


def draw_table(d, tb, cfg, top, height, fonts):
    """A comparison table in the figure region. Same rhythm argument as draw_matrix.

    CENTRED VERTICALLY, which needs a measure pass first. Top-aligned, a four-row table
    ended around a third of the way down and left a slab of cream above the eyebrow that
    read as a mistake rather than as space. The row heights are not knowable in advance
    because every cell wraps, so this measures the wrapped lines, then draws.
    """
    c, p, t = cfg["canvas"], cfg["palette"], cfg["type"]
    ink, accent, muted = rgb(p["ink"]), rgb(p["accent"]), rgb(p["muted"])
    med, mono = fonts["med"], fonts["mono"]
    M = cfg["margin"]
    inner = c["w"] - 2 * M
    col_w = [int(inner * w) for w in tb.get("widths", [0.5, 0.5])]
    f_cell = med(t["table_cell"])
    line_h = t["table_cell"] + 12
    row_gap = 30

    wrapped, row_h = [], []
    for row in tb["rows"]:
        cells = [wrap(d, cell, f_cell, col_w[i] - 40) for i, cell in enumerate(row)]
        wrapped.append(cells)
        row_h.append(max(len(cl) for cl in cells) * line_h + row_gap)
    head_h = t["table_head"] + 34 + 34
    total = head_h + sum(row_h)

    y = top + max(0, (height - total) // 2) if tb.get("center", True) else top + 96
    x = M
    for i, head in enumerate(tb["head"]):
        tracked(d, (x, y), head.upper(), mono(t["table_head"]), muted, t["eyebrow_track"])
        x += col_w[i]
    y += t["table_head"] + 34
    d.line([(M, y), (M + inner, y)], fill=ink, width=3)
    y += 34

    hi = tb.get("highlight_row")
    for r, cells in enumerate(wrapped):
        x = M
        for i, lines in enumerate(cells):
            cy = y
            for line in lines:
                d.text((x, cy), line, font=f_cell, fill=accent if r == hi else ink)
                cy += line_h
            x += col_w[i]
        y += row_h[r]
        if r < len(wrapped) - 1:
            d.line([(M, y - 15), (M + inner, y - 15)], fill=rgb(p["muted"]), width=1)
    return y


def render(card, cfg, base_dir):
    c, p, t = cfg["canvas"], cfg["palette"], cfg["type"]
    f = cfg["fonts"]
    ink, accent, muted = rgb(p["ink"]), rgb(p["accent"]), rgb(p["muted"])
    M = cfg["margin"]
    inner = c["w"] - 2 * M

    sans = lambda s, i: ImageFont.truetype(f["sans"], s, index=i)
    bold = lambda s: sans(s, f["sans_bold_index"])
    reg = lambda s: sans(s, f["sans_regular_index"])
    med = lambda s: sans(s, f["sans_medium_index"])
    mono = lambda s: ImageFont.truetype(f["mono"], s)

    def display(s, italic=False):
        path = f.get("serif_italic") if italic else f.get("serif")
        if path:
            fnt = ImageFont.truetype(path, s)
            # Variable serifs (New York) default to hairline horizontals that vanish
            # on a dark field at display size; a named weight fixes the crossbars.
            var = f.get("serif_variation")
            if var:
                try:
                    fnt.set_variation_by_name(var)
                except Exception:
                    pass
            return fnt
        return bold(s)

    fonts = {"bold": bold, "reg": reg, "med": med, "mono": mono}

    jewels = cfg.get("jewels") or []

    def jewel(i):
        return rgb(jewels[i % len(jewels)]) if jewels else accent

    # A diagram card has no photo: the figure gets the photo block's space instead, so the
    # text below still starts on the cover's title baseline.
    band = cfg.get("header_band", 0)
    frame = cfg.get("frame") or {}
    fi = frame.get("inset", 56) if frame else 0
    panel = rgb(p["bg"])
    # LEAD-HUE MODE (creator ruling, 2026-08-14): when the frame carries a "band" colour, the
    # jewel tone leads the whole card: the margin ring is the band, the inside is the
    # panel, and photos sit inset so the ring stays visible, like the source deck's
    # event cards. Without "band", the old full-bleed layout is unchanged.
    banded = frame.get("band")
    img = Image.new("RGB", (c["w"], c["h"]), rgb(banded) if banded else panel)
    d = ImageDraw.Draw(img)
    if banded:
        d.rectangle([fi, fi, c["w"] - fi, c["h"] - fi], fill=panel)
    if card.get("photo"):
        px0 = fi if banded else 0
        top = band if band else px0
        pb = photo_block(f"{base_dir}/{card['photo']}", c["w"] - 2 * px0,
                         c["photo_h"] - top, c["h"] - top - (fi if banded else 0), panel)
        img.paste(pb, (px0, top))
        d = ImageDraw.Draw(img)
    else:
        if card.get("matrix"):
            lab, lab_at, _ = draw_matrix(d, card["matrix"], cfg, band, c["photo_h"] - band, fonts)
            img.paste(lab.rotate(90, expand=True), lab_at, lab.rotate(90, expand=True))
            d = ImageDraw.Draw(img)
        elif card.get("table"):
            draw_table(d, card["table"], cfg, band, c["photo_h"] - band, fonts)

    # Balance, don't pin (the creator, 2026-08-14: "spacing is a bit weird"). The old fixed
    # top_pad left short text blocks with dead bottoms. Measure the block, then centre
    # it between the figure and the footer band, clamped to a minimum gap so a full
    # card still reads top-anchored.
    def text_height():
        th = 0
        if card["type"] == "cover":
            if card.get("eyebrow"):
                th += t["eyebrow"] + t["cover_eyebrow_gap"]
            th += len(card["title"]) * t["cover_title_leading"] + t["cover_gap"]
            th += len(card["steps"]) * t["cover_step_leading"]
        else:
            th += 56 + 48
            th += len(wrap(d, card["headline"], display(t["headline"]), inner)) * t["headline_leading"] + 40
            f_b = reg(t["body"])
            for para in card["body"]:
                th += len(wrap(d, para, f_b, inner)) * t["body_leading"] + t["para_gap"]
        return th

    floor = c["h"] - max(cfg["min_bottom"], 150)
    avail = floor - c["photo_h"]
    y = c["photo_h"] + max(card.get("top_pad", 50), (avail - text_height()) // 2)

    if card["type"] == "cover":
        # Optional series eyebrow. A named recurring format compounds recognition, so the
        # name has to be ON the asset: the cover is the whole post for most of the feed,
        # and a series nobody can name accrues nothing from week to week.
        if card.get("eyebrow"):
            tracked(d, (M, y), card["eyebrow"], mono(t["eyebrow"]), accent, t["eyebrow_track"])
            y += t["eyebrow"] + t["cover_eyebrow_gap"]

        f_title = display(t["cover_title"])
        f_title_acc = display(t["cover_title"], italic=True)
        accent_from = card.get("title_accent_from", len(card["title"]) - 1)
        # A serif's hairline horizontals vanish at display size on a dark field, so
        # display lines get a 2px same-color stroke. No-op for the sans fallback.
        sw = 2 if f.get("serif") else 0
        for i, line in enumerate(card["title"]):
            if i >= accent_from:
                d.text((M, y), line, font=f_title_acc, fill=accent, stroke_width=sw, stroke_fill=accent)
            else:
                d.text((M, y), line, font=f_title, fill=ink, stroke_width=sw, stroke_fill=ink)
            y += t["cover_title_leading"]
        y += t["cover_gap"]

        f_num, f_step = display(t["cover_num"] + 12), display(t["cover_step"])
        for idx, (num, text) in enumerate(card["steps"]):
            col = jewel(idx)
            d.rectangle([M - 28, y + 6, M - 22, y + t["cover_step"] + 10], fill=col)
            d.text((M, y + 2), num, font=f_num, fill=col)
            d.text((M + 108, y), text, font=f_step, fill=ink)
            y += t["cover_step_leading"]

        if card.get("footer"):
            y += 26
            d.line([(M, y), (M + 96, y)], fill=accent, width=4)
            y += 30
            d.text((M, y), card["footer"], font=reg(t["footer"]), fill=muted)
            y += t["footer"]

    elif card["type"] in ("depth", "matrix", "table"):
        acc = jewel(card["jewel"]) if "jewel" in card else accent
        tracked(d, (M, y), card["eyebrow"], mono(t["eyebrow"]), acc, t["eyebrow_track"])
        y += 56  # clear the mono descenders or the rule reads as a strikethrough
        d.line([(M, y), (M + 84, y)], fill=acc, width=4)
        y += 48

        f_head = display(t["headline"])
        # Stroke rescues variable serifs whose hairlines vanish at display size; a
        # static display cut (Romie Medium) needs none, so specs set serif_stroke 0.
        sw = f.get("serif_stroke")
        if sw is None:
            sw = 1 if f.get("serif") else 0
        for line in wrap(d, card["headline"], f_head, inner):
            d.text((M, y), line, font=f_head, fill=ink, stroke_width=sw, stroke_fill=ink)
            y += t["headline_leading"]
        y += 40

        f_body = reg(t["body"])
        body_ink = rgb(p["body"]) if p.get("body") else ink
        for para in card["body"]:
            for line in wrap(d, para, f_body, inner):
                d.text((M, y), line, font=f_body, fill=body_ink)
                y += t["body_leading"]
            y += t["para_gap"]

    else:
        raise ValueError(f"unknown card type: {card['type']}")

    if frame:
        d.rectangle([fi, fi, c["w"] - fi, c["h"] - fi],
                    outline=rgb(frame.get("color", p["accent"])), width=frame.get("width", 3))

    if cfg.get("brand_header"):
        label = cfg["brand_header"]
        f_h = bold(t["header"])
        chip = t["header"] + 16
        wpx = d.textlength(label, font=f_h)
        x0 = (c["w"] - (chip + 18 + int(wpx))) // 2
        y0 = 96
        d.rounded_rectangle([x0, y0, x0 + chip, y0 + chip], radius=12,
                            fill=rgb("#0F0F0F"), outline=rgb("#3E3B38"), width=2)
        f_r = bold(t["header"] - 6)
        rw = d.textlength(label[0], font=f_r)
        d.text((x0 + (chip - int(rw)) // 2, y0 + 8), label[0], font=f_r, fill=ink)
        d.text((x0 + chip + 18, y0 + 7), label, font=f_h, fill=ink)

    # One shared footer baseline inside the frame: author left, mark right. Content
    # is kept clear of it by min_bottom (raise to ~160 when the footer is on).
    if cfg.get("brand_author"):
        a = cfg["brand_author"]
        f_a = mono(t["footer_name"])
        ay = c["h"] - 128
        ax = M
        if a.get("photo"):
            av = 72
            av_y = ay + t["footer_name"] // 2 - av // 2
            face = ImageOps.fit(Image.open(a["photo"]).convert("RGB"), (av, av),
                                Image.LANCZOS, centering=(0.5, 0.35))
            img.paste(face, (ax, av_y))
            d.rectangle([ax, av_y, ax + av, av_y + av], outline=accent, width=2)
            ax += av + 26
        d.text((ax, ay), a["name"], font=f_a, fill=ink)
        if a.get("org"):
            nx = ax + int(d.textlength(a["name"], font=f_a)) + 28
            d.text((nx, ay), a["org"], font=f_a, fill=accent)

    mark = cfg.get("brand_mark")
    if mark:
        f_mark = mono(t["brand_mark"])
        track = t["eyebrow_track"]
        wpx = d.textlength(mark, font=f_mark) + track * max(0, len(mark) - 1)
        tracked(d, (c["w"] - M - int(wpx), c["h"] - 126), mark, f_mark, muted, track)

    g = cfg.get("grain")
    if g:
        noise = Image.effect_noise((c["w"], c["h"]), 40).convert("L")
        img = Image.blend(img, Image.merge("RGB", (noise, noise, noise)), g / 255.0)

    out_path = f"{cfg.get('out_dir', base_dir)}/{card['out']}"
    img.save(out_path)

    slack = c["h"] - y
    flag = "  OVERFLOW" if slack < cfg["min_bottom"] else ""
    print(f"{card['out']}  {img.size}  bottom slack {slack}px{flag}")
    return slack >= cfg["min_bottom"]


def main():
    spec_path = sys.argv[1]
    spec = json.load(open(spec_path))
    base_dir = spec.get("base_dir") or os.path.dirname(os.path.abspath(spec_path))
    cfg = merge(DEFAULTS, {k: v for k, v in spec.items() if k in DEFAULTS or k == "out_dir"})
    f = cfg["fonts"]
    if not f.get("sans"):
        f["sans"] = _find_font(["HelveticaNeue.ttc", "Helvetica.ttc", "Arial Unicode.ttf", "Arial.ttf",
                                "DejaVuSans.ttf", "LiberationSans-Regular.ttf"], "CAROUSEL_FONT_SANS")
        if not f["sans"].lower().endswith(".ttc"):
            f["sans_bold_index"] = f["sans_regular_index"] = f["sans_medium_index"] = 0
    if not f.get("mono"):
        f["mono"] = _find_font(["spacemono-700.ttf", "SpaceMono-Bold.ttf", "SpaceMono-Regular.ttf",
                                "Menlo.ttc", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf"], "CAROUSEL_FONT_MONO")
    cfg.setdefault("out_dir", base_dir)

    # Render every card before judging, so one overflow does not hide the rest.
    results = [render(card, cfg, base_dir) for card in spec["cards"]]
    if not all(results):
        print("\nAt least one card overflows. Cut copy, do not shrink the type:")
        print("the set only reads as one carousel while the scale is shared.")
        sys.exit(1)


if __name__ == "__main__":
    main()

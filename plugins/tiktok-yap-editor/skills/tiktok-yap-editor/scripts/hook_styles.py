#!/usr/bin/env python3
"""Render a burned on-screen text hook as a transparent PNG, in one of three
styles. This is the richer, typography-driven alternative to the built-in ASS
hook (build_ass.py --hook): it overlays a 1080x1920 PNG on the cut for the hook
window (~0.15s to ~5s). Use it when you want the designed look; use the ASS hook
when you just want a clean one-liner burned inline with the captions.

Three styles (pick with --style):
  native   Looks typed in TikTok. SF NS Rounded Heavy, white + dark outline,
           balanced centred lines. Matches the platform caption font.
  minimal  Tight brand sans (brand-config caption_font, e.g. Bricolage Grotesque
           ExtraBold), a size hierarchy (big statement + smaller context line),
           NO outline, a subtle shadow only.
  branded  The editorial house style, font-contrast is the whole point:
           - SETUP line(s) big in a condensed display face (Anton), in the brand
             accent colour, uppercase, auto-shrunk to fit, up to 2 lines.
           - PAYOFF line in an italic serif (Hoefler Text Italic), white, and
             ALWAYS one line (auto-sized down to fit, never wrapped or clipped).
           - NO outline and NO drop shadow on anything.

Nothing ever clips: every line auto-shrinks to the safe width, and the payoff
auto-shrinks to stay on one line.

Usage:
  python3 hook_styles.py --style branded \
    --setup "SETUP LINE|OPTIONAL SECOND" --payoff "the tension underneath" \
    [--eyebrow POV] [--brand /path/brand-config.json] [--accent '#FF5A2A'] \
    --out hook.png
Then burn it over the cut for the hook window, e.g.:
  ffmpeg -i cut.mp4 -i hook.png -filter_complex \
    "[0][1]overlay=0:0:enable='between(t,0.15,5.2)'" -c:a copy out.mp4
"""
import argparse, json, os, re
from PIL import Image, ImageDraw, ImageFont

W, H = 1080, 1920
MARGIN = 56
MAXW = W - 2 * MARGIN

FONT_DIRS = [os.path.expanduser("~/Library/Fonts"), "/Library/Fonts",
             "/System/Library/Fonts", "/System/Library/Fonts/Supplemental",
             os.path.expanduser("~/.fonts"),
             os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts")]


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def find_font(name):
    """Best-effort resolve a font family name to a file path."""
    target = norm(name)
    best = None
    for d in FONT_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.lower().endswith((".ttf", ".otf", ".ttc")):
                continue
            stem = norm(os.path.splitext(fn)[0])
            if stem == target:
                return os.path.join(d, fn)
            if best is None and (target in stem or stem in target):
                best = os.path.join(d, fn)
    return best


def hex_rgba(h, a=255):
    h = (h or "").lstrip("#")
    if len(h) != 6:
        return (255, 90, 42, a)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def load(path, size, index=0, variation=None):
    f = ImageFont.truetype(path, size, index=index)
    if variation:
        try:
            f.set_variation_by_name(variation)
        except Exception:
            pass
    return f


def hoefler_italic_index(path):
    for i in range(12):
        try:
            if "italic" in ImageFont.truetype(path, 40, index=i).getname()[1].lower():
                return i
        except Exception:
            break
    return 2


def tw(f, t):
    return sum(f.getbbox(c)[2] for c in t) if t else 0


def fit(path, texts, maxw, start, floor, index=0, variation=None):
    s = start
    while s > floor:
        f = load(path, s, index, variation)
        if all(tw(f, t) <= maxw for t in texts):
            return f
        s -= 1
    return load(path, floor, index, variation)


def center(d, y, t, f, fill, stroke=0, stroke_fill=(0, 0, 0, 255), shadow=None):
    x = (W - tw(f, t)) // 2
    for c in t:
        if shadow:
            d.text((x + shadow[0], y + shadow[1]), c, font=f, fill=shadow[2])
        d.text((x, y), c, font=f, fill=fill,
                stroke_width=stroke, stroke_fill=stroke_fill)
        x += f.getbbox(c)[2]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--style", choices=["native", "minimal", "branded"], default="branded")
    ap.add_argument("--setup", required=True, help="big line(s), split with |")
    ap.add_argument("--payoff", default="", help="serif payoff / context line (one line)")
    ap.add_argument("--eyebrow", default="", help="small line above (e.g. POV)")
    ap.add_argument("--brand", default="", help="path to brand-config.json")
    ap.add_argument("--accent", default="", help="override accent hex, e.g. #FF5A2A")
    ap.add_argument("--out", default="hook.png")
    a = ap.parse_args()

    cfg = {}
    if a.brand and os.path.exists(a.brand):
        try:
            cfg = json.load(open(a.brand))
        except Exception:
            cfg = {}
    accent = hex_rgba(a.accent or cfg.get("accent_hex", "#FF5A2A"))
    white = hex_rgba(cfg.get("base_hex", "#FFFFFB"))
    ink = hex_rgba(cfg.get("ink_hex", "#0A0A0A"))
    brand_sans = cfg.get("caption_font", "Bricolage Grotesque ExtraBold")

    setup = [s for s in a.setup.split("|") if s.strip()]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    y = 230

    if a.style == "native":
        path = find_font("SF NS Rounded") or find_font("SFNSRounded") or find_font(brand_sans)
        f = fit(path, setup + ([a.payoff] if a.payoff else []), MAXW, 116, 56)
        step = int(f.size * 1.05)
        if a.eyebrow:
            center(d, y, a.eyebrow.upper(), load(path, int(f.size * 0.5)), white, stroke=6); y += int(f.size * 0.7)
        for ln in setup:
            center(d, y, ln, f, white, stroke=8, stroke_fill=ink); y += step
        if a.payoff:
            center(d, y + 6, a.payoff, f, white, stroke=8, stroke_fill=ink)

    elif a.style == "minimal":
        path = find_font(brand_sans) or find_font("Montserrat Black")
        big = fit(path, setup, MAXW, 122, 64)
        sh = (3, 3, (0, 0, 0, 90))
        if a.eyebrow:
            center(d, y, a.eyebrow.upper(), load(path, 46), white, shadow=sh); y += 70
        for ln in setup:
            center(d, y, ln, big, white, shadow=sh); y += int(big.size * 1.0)
        if a.payoff:
            sf = fit(path, [a.payoff], MAXW, int(big.size * 0.52), 30)
            center(d, y + 20, a.payoff, sf, white, shadow=sh)

    else:  # branded: Anton accent setup + Hoefler italic white payoff, no outline/shadow
        anton = find_font("Anton") or find_font(brand_sans)
        hoef = find_font("Hoefler Text") or find_font("Georgia") or find_font("Times New Roman")
        hi = hoefler_italic_index(hoef) if hoef and hoef.lower().endswith(".ttc") else 0
        big = fit(anton, setup, MAXW, 120, 60)
        step = int(big.size * 0.98)
        if a.eyebrow:
            center(d, y, a.eyebrow, load(hoef, 52, hi), white); y += int(52 * 1.5)
        for ln in setup:
            center(d, y, ln.upper(), big, accent); y += step
        if a.payoff:
            sf = fit(hoef, [a.payoff], MAXW, 64, 28, index=hi)  # ALWAYS one line
            center(d, y + 26, a.payoff, sf, white)

    img.save(a.out)
    print(f"wrote {a.out}  (style={a.style}, {len(setup)} setup line(s)"
          f"{', payoff' if a.payoff else ''})")


if __name__ == "__main__":
    main()

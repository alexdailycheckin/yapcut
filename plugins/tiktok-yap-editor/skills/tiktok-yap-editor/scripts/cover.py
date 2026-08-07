#!/usr/bin/env python3
"""Cover / thumbnail builder for a finished vertical video.

Two modes:

1) Contact sheet (pick the frame):
   python3 cover.py --video final.mp4 --contact-sheet --out .cover_cand [--interval 2]
   Extracts a candidate frame every N seconds so you (and Alex) can pick the
   strongest one: clear face, eyes open, good expression, no mid-blink/mid-word.

2) Build the cover:
   python3 cover.py --video final.mp4 --frame 34 --title "How does Apple sell?" \
     --kicker "How whatever sells" --out cover.jpg [--no-text] [--yt]

Design:
- Vertical cover is 1080x1920. The Instagram grid crops covers to the CENTRE
  1080x1080 square (y 420..1500), so the title and the face must both live inside
  that square. The title cannot just move above his head to stay off his face.
- **No scrim.** The default `clean` style puts bone type straight onto the black
  t-shirt under the chin, which is the darkest thing inside that square, with a
  modest ink stroke to carry it over the camera or a hand. Sentence case, left
  aligned, one tang rule under the line. Alex killed the old full-width blurred
  band on 2026-08-07: it was muddy, it dulled the frame, and at the old default
  y it sat across his eyes and mouth. `--style scrim` still reaches it.
- Placement is measured, not fixed: `best_title_y` slides the block down the
  frame and picks the y with the lowest mean luma plus a heavy penalty on bright
  pixels, because he reframes between takes and the silver camera drifts. Pass
  `--title-y` to override or `--no-auto-y` to fall back to the constant.
- Title text for a show episode is the franchise question, not a claim:
  "How does X sell?" Long subjects auto-wrap to two balanced lines.
- --yt also exports a 1280x720 thumbnail (subject scaled onto a blurred fill of
  the same frame) for YouTube repurposes.

Build covers from the caption-free cut (`full_<name>.mp4`), never the delivered
file, or you bake a caption word or an evidence card into the thumbnail.

Pick a frame with eye contact and an expressive (not neutral) face: it lifts CTR.
The auto placement optimises legibility only, so it cannot tell a blink from a
smile; eyeball the frame before shipping.
"""
import argparse, os, subprocess, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1920
FONT_CANDIDATES = [
    os.path.expanduser("~/Library/Fonts/BricolageGrotesque-ExtraBold.ttf"),
    os.path.expanduser("~/Library/Fonts/Montserrat-Black.ttf"),
    "/System/Library/Fonts/Supplemental/Arial Black.ttf",
]


def font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def grab(video, t, out):
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-ss", str(t), "-i", video,
                    "-frames:v", "1", out, "-hide_banner", "-loglevel", "error"], check=True)


def duration(video):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "default=nw=1:nk=1", video], capture_output=True, text=True).stdout
    return float(o.strip())


def contact_sheet(video, out, interval):
    os.makedirs(out, exist_ok=True)
    dur = duration(video)
    t = 0.5
    while t < dur:
        grab(video, t, os.path.join(out, f"f_{t:05.1f}.jpg"))
        t += interval
    print(f"candidates in {out}/ (every {interval}s up to {dur:.1f}s)")


BONE = (255, 255, 251, 255)
INK = (35, 35, 35, 255)
TANG = (255, 90, 42, 255)


def mono(size):
    p = os.path.expanduser("~/Library/Fonts/spacemono-400.ttf")
    if os.path.exists(p):
        return ImageFont.truetype(p, size)
    return font(size)


def draw_title(img, title, title_y):
    """LEGACY 'scrim' style, kept only for old calls. Alex killed it 2026-08-07:
    the full-width blurred band was muddy, it dulled the whole frame, and at the
    default title_y it sat straight across his eyes and mouth, which breaks the
    standing rule that burned text never covers the face. Use draw_title_clean."""
    dr = ImageDraw.Draw(img)
    lines = [l for l in title.split("|") if l]
    fs = 96
    f = font(fs)
    # fit width
    def wide(ls, ff):
        return max(ff.getbbox(l.upper(), stroke_width=10)[2] for l in ls)
    while wide(lines, f) > (940 - 140) and fs > 48:
        fs -= 4; f = font(fs)
    # soft dark scrim band behind the text for legibility
    lh = f.getbbox("Ay", stroke_width=10)[3] + 18
    band_h = lh * len(lines) + 60
    scrim = Image.new("RGBA", (W, band_h), (0, 0, 0, 0))
    sd = ImageDraw.Draw(scrim)
    sd.rectangle([0, 0, W, band_h], fill=(0, 0, 0, 110))
    scrim = scrim.filter(ImageFilter.GaussianBlur(30))
    img.alpha_composite(scrim, (0, max(0, title_y - 30)))
    y = title_y
    for l in lines:
        t = l.upper()
        bb = f.getbbox(t, stroke_width=10); lw = bb[2] - bb[0]
        dr.text(((W - lw) / 2, y), t, font=f, fill=(255, 255, 255, 255),
                stroke_width=10, stroke_fill=(0, 0, 0, 255))
        y += lh


def best_title_y(img, block=300, side=140, lo=880, hi=1420):
    """Slide the title block down the frame and return the y where it reads best.

    A fixed y does not survive real footage: he reframes between takes, so a
    hardcoded 1030 lands on the shirt in one clip and across the collar in the
    next, and the silver camera drifts through the band. Cost is mean luma plus a
    heavy penalty on bright pixels, which is what actually kills bone type: the
    camera body and a lit hand, not the average.
    """
    px = img.convert("L").load()
    w, h = img.size
    hi = min(hi, h - block)

    def cost(y):
        tot = n = brt = 0
        for yy in range(y, y + block, 6):
            for xx in range(side, w - side, 10):
                v = px[xx, yy]
                tot += v
                n += 1
                if v > 140:
                    brt += 1
        return (tot / n) / 255.0 + 2.4 * (brt / n)

    return min(range(lo, hi + 1, 10), key=cost)


def _wrap_two(dr, text, fnt, max_w):
    """Balance a too-long title over two lines at the nearest word break."""
    words = text.split()
    if len(words) < 2:
        return [text]
    best, score = None, None
    for i in range(1, len(words)):
        a, b = " ".join(words[:i]), " ".join(words[i:])
        wa, wb = dr.textlength(a, font=fnt), dr.textlength(b, font=fnt)
        if max(wa, wb) > max_w:
            continue
        s = abs(wa - wb)
        if score is None or s < score:
            best, score = [a, b], s
    return best or [text]


def draw_title_clean(img, title, kicker="", title_y=1030, side=140):
    """The default cover treatment.

    No background plate at all. Instagram crops the grid thumbnail to the CENTRE
    1080x1080 (y 420..1500), so the title cannot simply move above his head; but
    inside that square his black t-shirt just under the chin is the darkest thing
    in frame, so bone type sits on it with no scrim needed and the photograph is
    left intact. A modest ink stroke carries it over the camera or a hand when
    one drifts into the zone, matching the caption style rather than the old
    10px slab. One tang rule under the line is the brand spark.

    Left-aligned and sentence case: the site's convention, not all-caps.
    """
    dr = ImageDraw.Draw(img)
    max_w = W - side * 2
    fs = 128
    f = font(fs)
    lines = [title]
    while dr.textlength(title, font=f) > max_w and fs > 78:
        fs -= 2
        f = font(fs)
    if dr.textlength(title, font=f) > max_w:
        # still too wide at the floor: go to two balanced lines and refit
        fs = 116
        f = font(fs)
        while fs > 62:
            cand = _wrap_two(dr, title, f, max_w)
            if len(cand) == 2 and max(dr.textlength(l, font=f) for l in cand) <= max_w:
                lines = cand
                break
            fs -= 2
            f = font(fs)
        else:
            lines = _wrap_two(dr, title, f, max_w)

    y = title_y
    if kicker:
        kf = mono(38)
        x = side
        for ch in kicker.upper():
            dr.text((x, y), ch, font=kf, fill=(236, 233, 227, 255),
                    stroke_width=3, stroke_fill=(0, 0, 0, 190))
            x += dr.textlength(ch, font=kf) + 3.0
        y += 58

    lh = int(fs * 1.06)
    widest = 0
    for l in lines:
        dr.text((side, y), l, font=f, fill=BONE, stroke_width=4,
                stroke_fill=(0, 0, 0, 205))
        widest = max(widest, dr.textlength(l, font=f))
        y += lh
    rule_w = int(min(widest, max_w))
    dr.rounded_rectangle([side, y + 6, side + rule_w, y + 15], 5, fill=TANG)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video")
    ap.add_argument("--image", help="use a still (already 1080x1920, caption-free) instead of grabbing from --video")
    ap.add_argument("--contact-sheet", action="store_true")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--frame", type=float)
    ap.add_argument("--title", default="")
    ap.add_argument("--kicker", default="",
                    help="small tracked mono line above the title (e.g. the show name)")
    ap.add_argument("--style", choices=["clean", "scrim"], default="clean",
                    help="clean = no plate, bone type on the shirt (default). "
                         "scrim = the retired full-width band.")
    ap.add_argument("--no-text", action="store_true")
    ap.add_argument("--title-y", type=int, default=None,
                    help="default: auto for clean (see --no-auto-y), 520 for scrim")
    ap.add_argument("--no-auto-y", action="store_true",
                    help="clean style: skip the automatic placement scan")
    ap.add_argument("--yt", action="store_true")
    ap.add_argument("--out", default="cover.jpg")
    a = ap.parse_args()

    if a.contact_sheet:
        contact_sheet(a.video, a.out, a.interval)
        return
    if a.frame is None and not a.image:
        raise SystemExit("give --frame T (use --contact-sheet first to pick) or --image")

    with tempfile.TemporaryDirectory() as td:
        if a.image:
            raw = a.image
        else:
            raw = os.path.join(td, "f.png"); grab(a.video, a.frame, raw)
        img = Image.open(raw).convert("RGBA")
        if img.size != (W, H):
            img = img.resize((W, H))
        if a.title and not a.no_text:
            if a.title_y is not None:
                ty = a.title_y
            elif a.style == "clean" and not a.no_auto_y:
                ty = best_title_y(img)
                print(f"  auto title-y {ty}")
            else:
                ty = 1030 if a.style == "clean" else 520
            if a.style == "clean":
                draw_title_clean(img, a.title, a.kicker, ty)
            else:
                draw_title(img, a.title, ty)
        img.convert("RGB").save(a.out, quality=92)
        print(f"wrote {a.out}  (frame {a.frame}s)")

        if a.yt:
            # 1280x720: blurred fill of the frame + the subject scaled to fit height
            bg = img.convert("RGB").resize((1280, 1280)).filter(ImageFilter.GaussianBlur(40))
            bg = bg.crop((0, 280, 1280, 1000))  # centre 16:9 band
            scale = 720 / H; fw = int(W * scale)
            fg = img.convert("RGB").resize((fw, 720))
            bg.paste(fg, ((1280 - fw) // 2, 0))
            ytout = os.path.splitext(a.out)[0] + "_yt.jpg"
            bg.save(ytout, quality=92)
            print(f"wrote {ytout}  (1280x720)")


if __name__ == "__main__":
    main()

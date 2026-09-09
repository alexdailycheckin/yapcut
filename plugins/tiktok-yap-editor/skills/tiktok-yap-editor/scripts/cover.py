#!/usr/bin/env python3
"""Cover / thumbnail builder for a finished vertical video.

Two modes:

1) Contact sheet (pick the frame):
   python3 cover.py --video final.mp4 --contact-sheet --out .cover_cand [--interval 2]
   Extracts a candidate frame every N seconds so you (and the creator) can pick the
   strongest one: clear face, eyes open, good expression, no mid-blink/mid-word.

2) Build the cover:
   python3 cover.py --video final.mp4 --frame 34 --title "How does Apple sell?" \
     [--kicker "How whatever sells"] --out cover.jpg [--no-text] [--yt] [--brand cfg]
   or, for a show episode, let the series block in brand-config shape it:
   python3 cover.py --video final.mp4 --frame 34 --subject Apple --out cover.jpg

Series identity comes from brand-config `series` {name, question_template,
mark_png, pillars} (yaplib.brand): --kicker defaults to series.name, --subject
fills question_template ("How does {subject} sell?"), and the series mark is
drawn under the accent rule ONLY when mark_png exists (relative paths resolve
against <workspace>/assets/); room is reserved for it only then. Before this
the kicker was a per-run string and the mark came from a script that lives only
in one private workspace, while every cover reserved 166px for it.

Design:
- Vertical cover is 1080x1920. The Instagram grid crops covers to the CENTRE
  1080x1080 square (y 420..1500), so the title and the face must both live inside
  that square. The title cannot just move above his head to stay off his face.
- **No scrim.** The default `clean` style puts bone type straight onto the black
  t-shirt under the chin, which is the darkest thing inside that square, with a
  modest ink stroke to carry it over the camera or a hand. Sentence case, left
  aligned, one brand-accent rule under the line. the creator killed the old full-width blurred
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
import argparse, json, os, sys, tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import ass as yass  # noqa: E402
from yaplib import brand, fonts, media  # noqa: E402
from yaplib.home import radar_home  # noqa: E402

W, H = media.W, media.H
IG_BOTTOM = 1500          # the Instagram grid crop; cover text must finish above it
MARK_GAP, MARK_H = 34, 132   # room under the rule for the series mark, when there is one

# Faces are resolved by FAMILY from brand-config (caption_font for the title,
# label_font for the kicker) in main() via configure(); these are the fallbacks
# for a call with no brand file at all.
_FACES = {"title": None, "mono": None}


def configure(cfg):
    _FACES["title"] = fonts.first_font([(cfg.get("caption_font"), None), ("Montserrat Black", None),
                                        ("Arial Black", None), ("Helvetica", None)])
    _FACES["mono"] = fonts.first_font([(cfg.get("label_font"), "400"), (cfg.get("label_font"), None),
                                       ("Space Mono", "400"), ("Menlo", None), ("DejaVu Sans Mono", None)])


def font(size):
    p = _FACES["title"]
    return ImageFont.truetype(p, size) if p else ImageFont.load_default()


def grab(video, t, out):
    media.ffmpeg(["-ss", str(t), "-i", video, "-frames:v", "1", out], what="ffmpeg frame grab")


def duration(video):
    return media.probe_duration(video)


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

# The accent under the title. This used to be a hardcoded tangerine, which
# silently outvoted brand-config: a creator who set accent_hex still got the creator's
# orange rule on every cover. It is now the brand's accent, resolved in main()
# from brand-config.json (or --accent), with the old constant as the fallback so
# a call with no brand file behaves exactly as before.
TANG = (255, 90, 42, 255)


def hex_rgba(h, a=255):
    return yass.hex_to_rgba(h, a)


def mono(size):
    p = _FACES["mono"]
    return ImageFont.truetype(p, size) if p else font(size)


def resolve_mark(cfg, home):
    """Absolute path of the series mark PNG, or None when it does not exist.
    Relative paths resolve against <workspace>/assets/."""
    m = (cfg.get("series") or {}).get("mark_png") or ""
    if not m:
        return None
    if not os.path.isabs(m):
        m = os.path.join(str(home), "assets", m) if home else os.path.abspath(m)
    return m if os.path.isfile(m) else None


def draw_title(img, title, title_y):
    """LEGACY 'scrim' style, kept only for old calls. the creator killed it 2026-08-07:
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
    rgb = img.convert("RGB").load()
    w, h = img.size
    hi = min(hi, h - block)
    if hi < lo:
        return max(0, hi)

    def skin(r, g, b):
        """Classic skin-tone rule. Luma alone cannot keep type off the face: on a
        WHITE t-shirt the shirt is the brightest thing in frame, so the darkest
        band the old cost could find was his own face, and a 128pt title landed
        across the mouth. Hue separates them where value does not: skin runs
        R > G > B with real spread, the wall and the shirt sit near-neutral."""
        return (r > 95 and g > 40 and b > 20 and r > g and r > b
                and max(r, g, b) - min(r, g, b) > 15)

    def cost(y):
        tot = n = brt = skn = 0
        for yy in range(y, y + block, 6):
            for xx in range(side, w - side, 10):
                v = px[xx, yy]
                tot += v
                n += 1
                if v > 140:
                    brt += 1
                if skin(*rgb[xx, yy]):
                    skn += 1
        return (tot / n) / 255.0 + 2.4 * (brt / n) + 3.2 * (skn / n)

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


def _wrap_n(dr, text, fnt, max_w, n):
    """Split text over exactly n lines as evenly as possible, or None if it
    cannot be done inside max_w.

    Minimum-raggedness DP over the word breaks. A greedy fill cannot do this
    job: filling to a running target leaves the whole remainder on the last
    line, which is how a 3-line attempt reported "impossible" at every size
    while an obvious even split existed."""
    words = text.split()
    if n == 1:
        return [text] if dr.textlength(text, font=fnt) <= max_w else None
    if len(words) < n:
        return None
    m = len(words)
    w = [[None] * (m + 1) for _ in range(m)]
    for i in range(m):
        for j in range(i + 1, m + 1):
            wid = dr.textlength(" ".join(words[i:j]), font=fnt)
            w[i][j] = wid if wid <= max_w else None
    INF = float("inf")
    dp = [[INF] * (n + 1) for _ in range(m + 1)]
    back = [[None] * (n + 1) for _ in range(m + 1)]
    dp[0][0] = 0.0
    for k in range(1, n + 1):
        for j in range(1, m + 1):
            for i in range(k - 1, j):
                if dp[i][k - 1] == INF or w[i][j] is None:
                    continue
                c = dp[i][k - 1] + (max_w - w[i][j]) ** 2
                if c < dp[j][k]:
                    dp[j][k] = c
                    back[j][k] = i
    if dp[m][n] == INF:
        return None
    lines, j = [], m
    for k in range(n, 0, -1):
        i = back[j][k]
        lines.append(" ".join(words[i:j]))
        j = i
    return lines[::-1]


# Below this, two big lines read better than one small line. the creator's call
# 2026-08-31, after a batch shipped with "How does Tesla sell?" at 78 on one
# line next to "How does MrBeast sell?" at 116 on two: the old loop exhausted
# every one-line size before it ever tried wrapping, so the SHORTEST titles
# came out smallest. TARGET is the size that batch's biggest cover landed on,
# and it is now the floor the fitter aims at, adding lines to reach it.
TITLE_TARGET = 116
# Ceiling as well as a target: the set should read as ONE set, and a 128pt
# Tesla next to a 114pt Pop Mart does not. 120 is what the biggest cover in the
# 08-30 batch landed on, which is the size the creator pointed at. It also keeps the
# block short enough to sit under the chin once the mark's room is reserved.
TITLE_MAX = 120
MAX_TITLE_LINES = 3
# An extra line has to EARN itself. Without this, "How does Pop Mart sell?"
# takes 3 lines to gain 14pt and reads "How / does Pop / Mart sell?", which is
# worse than 2 lines at 114 however much taller the type is. A break mid-phrase
# costs more than a small size gain.
LINE_GAIN = 1.20


def fit_title(dr, title, max_w):
    """Return (font, lines): the biggest type that fits, lines added as needed.

    Walks 1..MAX_TITLE_LINES, keeping the largest size each arrangement allows,
    and only takes a taller-line-count option when it is LINE_GAIN bigger than
    the best fewer-line option. Stops as soon as TITLE_TARGET is reached."""
    best = None                       # (fs, font, lines)
    for n in range(1, MAX_TITLE_LINES + 1):
        fs = TITLE_MAX
        while fs >= 62:
            f = font(fs)
            cand = _wrap_n(dr, title, f, max_w, n)
            if cand:
                if best is None or fs >= best[0] * LINE_GAIN:
                    best = (fs, f, cand)
                break
            fs -= 2
        if best and best[0] >= TITLE_TARGET:
            break
    if best:
        return best[1], best[2]
    f = font(62)
    return f, _wrap_two(dr, title, f, max_w)


def title_block_height(dr, title, kicker, side=140):
    """Rendered height of the kicker + title + accent rule block, so a caller
    can place it without running off the Instagram grid crop."""
    f, lines = fit_title(dr, title, W - side * 2)
    h = (58 if kicker else 0) + int(f.size * 1.06) * len(lines) + 15
    return h


def draw_title_clean(img, title, kicker="", title_y=1030, side=140, mark=None):
    """The default cover treatment.

    No background plate at all. Instagram crops the grid thumbnail to the CENTRE
    1080x1080 (y 420..1500), so the title cannot simply move above his head; but
    inside that square his black t-shirt just under the chin is the darkest thing
    in frame, so bone type sits on it with no scrim needed and the photograph is
    left intact. A modest ink stroke carries it over the camera or a hand when
    one drifts into the zone, matching the caption style rather than the old
    10px slab. One rule under the line, in the brand accent, is the spark.

    Left-aligned and sentence case: the site's convention, not all-caps.
    """
    dr = ImageDraw.Draw(img)
    max_w = W - side * 2
    f, lines = fit_title(dr, title, max_w)
    fs = f.size

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
    if mark:
        # the series mark, MARK_GAP under the rule, MARK_H tall, left-aligned
        # with the type. Only drawn when the PNG exists (resolve_mark).
        m = Image.open(mark).convert("RGBA")
        scale = MARK_H / m.height
        m = m.resize((max(1, int(m.width * scale)), MARK_H), Image.LANCZOS)
        img.alpha_composite(m, (side, y + 15 + MARK_GAP))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video")
    ap.add_argument("--image", help="use a still (already 1080x1920, caption-free) instead of grabbing from --video")
    ap.add_argument("--contact-sheet", action="store_true")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--frame", type=float)
    ap.add_argument("--title", default="")
    ap.add_argument("--subject", default="",
                    help="episode subject; the title becomes brand-config series.question_template "
                         "with {subject} filled (e.g. 'How does Apple sell?')")
    ap.add_argument("--kicker", default=None,
                    help="small tracked mono line above the title (default: brand-config series.name)")
    ap.add_argument("--style", choices=["clean", "scrim"], default="clean",
                    help="clean = no plate, bone type on the shirt (default). "
                         "scrim = the retired full-width band.")
    ap.add_argument("--no-text", action="store_true")
    ap.add_argument("--title-y", type=int, default=None,
                    help="default: auto for clean (see --no-auto-y), 520 for scrim")
    ap.add_argument("--no-mark-room", action="store_true",
                    help="do not reserve space under the rule for the series mark even "
                         "when brand-config series.mark_png exists")
    ap.add_argument("--no-auto-y", action="store_true",
                    help="clean style: skip the automatic placement scan")
    ap.add_argument("--yt", action="store_true")
    ap.add_argument("--brand", default="",
                    help="explicit brand-config.json (default: yaplib.brand resolution: "
                         "the video's .yap_build, then the workspace, then the shipped default)")
    ap.add_argument("--accent", default="",
                    help="override the accent rule colour, e.g. '#E8232F'")
    ap.add_argument("--out", default="cover.jpg")
    a = ap.parse_args()

    global TANG
    src_dir = os.path.dirname(os.path.abspath(a.video or a.image or a.out))
    home = radar_home(argv=[], required=False)
    cfg = brand.load(a.brand or None, workdir=src_dir, home_dir=home)
    configure(cfg)
    series = cfg.get("series") or {}
    accent = a.accent or ("" if yass.is_none(cfg.get("accent_hex")) else cfg.get("accent_hex"))
    if accent:
        TANG = hex_rgba(accent)
    if a.kicker is None:
        a.kicker = series.get("name") or ""
    if not a.title and a.subject:
        tpl = series.get("question_template") or "How does {subject} sell?"
        a.title = tpl.replace("{subject}", a.subject)
    mark = None if a.no_mark_room else resolve_mark(cfg, home)
    if (series.get("mark_png") and not mark and not a.no_mark_room):
        print(f"  series.mark_png set but not found ({series.get('mark_png')}); no mark, no room reserved")

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
                # The scan must know the REAL block height. It used to assume a
                # fixed 300px, so a two-line title placed near the bottom of the
                # search range ran past the Instagram grid crop: that is how
                # "How does Pop Mart sell?" shipped with its question below the
                # square entirely. reserve keeps room under the rule for the
                # series mark, and only when there is one to draw.
                dr0 = ImageDraw.Draw(img)
                blk = title_block_height(dr0, a.title, a.kicker)
                reserve = (MARK_GAP + MARK_H) if mark else 0
                hi = IG_BOTTOM - blk - reserve
                ty = best_title_y(img, block=blk, lo=min(880, hi), hi=hi)
                print(f"  auto title-y {ty}  (block {blk}px, ends {ty + blk})")
            else:
                ty = 1030 if a.style == "clean" else 520
            if a.style == "clean":
                draw_title_clean(img, a.title, a.kicker, ty, mark=mark)
            else:
                draw_title(img, a.title, ty)
        img.convert("RGB").save(a.out, quality=92)
        print(f"wrote {a.out}  (frame {a.frame}s)")
        # sidecar for finalize.sh: the edit record carries cover {frame_t, path}
        json.dump({"frame_t": a.frame, "video": a.video, "image": a.image, "title": a.title,
                   "kicker": a.kicker, "mark": mark, "brand": cfg.get("_path")},
                  open(a.out + ".meta.json", "w"), indent=1)

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

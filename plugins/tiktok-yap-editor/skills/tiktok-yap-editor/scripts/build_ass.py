#!/usr/bin/env python3
"""Generate a styled .ass caption file from whisper -dtw word-level JSON.

This is the libass-era replacement for caption_frames.py. Instead of rendering
one transparent PNG per frame and compositing with overlay, we emit a single
.ass subtitle file and burn it in one ffmpeg pass (see compose_ass.sh). It is
far faster (no per-frame PNGs), less code, and easy to restyle.

It needs an ffmpeg built WITH libass (the `ass`/`subtitles` filter). The default
Homebrew `ffmpeg` bottle does NOT have it; install `ffmpeg-full` and link it
(`brew install ffmpeg-full && brew link --overwrite --force ffmpeg-full`).
preflight.py asserts this. If you are on a crippled ffmpeg, fall back to
caption_frames.py + compose.sh.

Caption behaviour matches the proven house style: a STABLE phrase block (default
3 words) with the currently-spoken word emphasised (karaoke). "Emphasis" depends
on the preset: minimal scales the active word only (clean, on-brand default),
bold/native also recolour it.

PRESETS (pick with --preset, default minimal):
  minimal  Dynamic Minimalism, Alex's default. Montserrat, white, NO neon, the
           active word just scales up. Reads premium, structure stays invisible.
  bold     Hormozi-style for YouTube long-form repurpose. Anton, ALL CAPS, neon
           yellow active word, thick stroke, big pop. Use OFF the main feed.
  native   TikTok-native. Montserrat, sentence case, white + soft shadow, a
           subtle accent on the active word.

Input is whisper -oj -ml 1 -sow -dtw word JSON (transcription[].offsets.from/to
in ms, .text). Optional corrections JSON fixes transcriber slips without
re-running audio:  {"drop": [110,111], "fix": {"117": "Be", "122": "They"}}

Usage:
  python3 build_ass.py --words words.json --out captions.ass \
    [--preset minimal|bold|native] \
    [--hook "YOUR HOOK LINE|SECOND LINE"] [--corrections corr.json] \
    [--accent '#FFDE00'] [--font 'Montserrat'] [--caps on|off] \
    [--cap-y 1320] [--hook-y 640] [--group 3] [--active-scale 113]

Notes on ASS:
  - Colours are &HBBGGRR (NOT RGB) with inverted alpha. hex_to_ass() handles it.
  - Coordinates run from top-left of a 1080x1920 PlayRes canvas.
  - We anchor every line middle-centre (\\an5) and \\pos it, so scaling a single
    word keeps the line centred.
"""
import argparse, json, os, re, sys

W, H = 1080, 1920

# preset -> style defaults. accent=None means "no colour, scale only".
PRESETS = {
    "minimal": dict(font="Montserrat Black", bold=False, base="#FFFFFF",
                    outline="#000000", outline_px=7, shadow_px=1,
                    accent=None, caps=True, active_scale=116,
                    cap_size=90, cap_y=1320, hook_size=120, hook_y=640,
                    hook_accent=False, spacing=0),
    "bold": dict(font="Anton", bold=True, base="#FFFFFF",
                 outline="#000000", outline_px=9, shadow_px=0,
                 accent="#FFDE00", caps=True, active_scale=122,
                 cap_size=96, cap_y=1300, hook_size=132, hook_y=620,
                 hook_accent=True, spacing=1),
    "native": dict(font="Montserrat Black", bold=False, base="#FFFFFF",
                   outline="#000000", outline_px=7, shadow_px=2,
                   accent="#FFD23F", caps=False, active_scale=110,
                   cap_size=82, cap_y=1340, hook_size=116, hook_y=650,
                   hook_accent=False, spacing=0),
}


def hex_to_ass(h):
    """#RRGGBB -> &H00BBGGRR (opaque)."""
    h = h.lstrip("#")
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}".upper()


def cs(t):
    """seconds -> H:MM:SS.cc (centiseconds), ASS time format."""
    if t < 0:
        t = 0
    h = int(t // 3600); m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


# --- hook auto-fit: the on-screen hook must NEVER run off the edge ----------
# Burned text hooks are author-written (~6 words) and were repeatedly getting
# clipped because ASS WrapStyle 2 does no auto-wrapping and a heavy display
# font overflows 1080px after ~3-4 words. We measure the real rendered width
# with the actual font file (Pillow) and wrap + shrink until the hook fits
# inside a title-safe width. Degrades to a char-width estimate if Pillow or the
# font file is unavailable, so it still wraps (never silently clips).
_FONT_DIRS = [
    os.path.expanduser("~/Library/Fonts"), "/Library/Fonts",
    "/System/Library/Fonts", "/System/Library/Fonts/Supplemental",
    os.path.expanduser("~/.fonts"), "/usr/share/fonts", "/usr/local/share/fonts",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "fonts"),
]


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def resolve_font_file(name):
    """Best-effort map an ASS font name -> a .ttf/.otf path on disk."""
    target = _norm(name)
    best = None
    for d in _FONT_DIRS:
        if not os.path.isdir(d):
            continue
        for fn in os.listdir(d):
            if not fn.lower().endswith((".ttf", ".otf", ".ttc")):
                continue
            stem = _norm(os.path.splitext(fn)[0])
            if stem == target:
                return os.path.join(d, fn)
            if best is None and (target in stem or stem in target):
                best = os.path.join(d, fn)
    return best


def _measurer(font_name, spacing_px):
    """Return measure(text, size)->px. Uses Pillow if possible, else estimate."""
    path = resolve_font_file(font_name)
    try:
        from PIL import ImageFont  # noqa
        cache = {}

        def measure(text, size):
            if not text:
                return 0.0
            f = cache.get(size)
            if f is None:
                f = ImageFont.truetype(path, size) if path else ImageFont.load_default()
                cache[size] = f
            try:
                w = f.getlength(text)
            except Exception:
                w = f.getbbox(text)[2]
            return w + spacing_px * max(0, len(text) - 1)
        if path:
            return measure
    except Exception:
        pass
    # fallback: heavy display fonts run ~0.62 * size per glyph (caps a touch wider)
    def measure(text, size):
        return len(text) * (0.62 * size + spacing_px)
    return measure


def fit_hook(hlines, font_name, caps, spacing_px, base_size,
             safe_w, max_lines, min_size):
    """Wrap + shrink author hook lines so the widest fits in safe_w.

    hlines: author segments (already split on '|'); each is a HARD break we
    keep, but we may wrap a long segment further. Returns (lines, size)."""
    measure = _measurer(font_name, spacing_px)
    segs = [(l.upper() if caps else l).strip() for l in hlines if l.strip()]
    if not segs:
        return [], base_size

    def wrap_at(size):
        lines = []
        for seg in segs:
            cur = ""
            for word in seg.split():
                trial = (cur + " " + word).strip()
                if not cur or measure(trial, size) <= safe_w:
                    cur = trial
                else:
                    lines.append(cur); cur = word
            if cur:
                lines.append(cur)
        return lines

    size = base_size
    while size >= min_size:
        lines = wrap_at(size)
        widest = max((measure(l, size) for l in lines), default=0)
        if widest <= safe_w and len(lines) <= max_lines:
            return lines, size
        size -= 4
    # floor: best effort at min_size (still wrapped, so worst case it shrank)
    return wrap_at(min_size), min_size


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", required=True)
    ap.add_argument("--out", default="captions.ass")
    ap.add_argument("--preset", choices=list(PRESETS), default="minimal")
    ap.add_argument("--hook", default="")
    ap.add_argument("--corrections", default="")
    ap.add_argument("--accent", default=None, help="override active-word colour, e.g. '#FFDE00' or 'none'")
    ap.add_argument("--font", default=None)
    ap.add_argument("--caps", choices=["on", "off"], default=None)
    ap.add_argument("--cap-y", type=int, default=None)
    ap.add_argument("--hook-y", type=int, default=None)
    ap.add_argument("--group", type=int, default=3)
    ap.add_argument("--active-scale", type=int, default=None)
    ap.add_argument("--hook-secs", type=float, default=2.5)
    ap.add_argument("--hook-anim", choices=["none", "typewriter"], default="none",
                    help="typewriter = reveal the hook character-by-character with a cursor")
    ap.add_argument("--hook-spark", default="",
                    help="word in the hook to colour in the accent on the held frame")
    ap.add_argument("--overlays", default="",
                    help="JSON list of {type:source|counter,...} extra timed overlays")
    ap.add_argument("--accent-hex", default="",
                    help="brand accent colour for hook spark + counter, even when "
                         "the caption highlight is scale-only (--accent none)")
    ap.add_argument("--hook-safe-frac", type=float, default=0.90,
                    help="fraction of the 1080px width the hook may occupy before it "
                         "is wrapped/shrunk. The hook is NEVER allowed past this.")
    ap.add_argument("--hook-max-lines", type=int, default=3,
                    help="max hook lines; shrink the font rather than overflow this.")
    ap.add_argument("--hook-min-size", type=int, default=54,
                    help="floor for hook auto-shrink (px).")
    a = ap.parse_args()

    p = dict(PRESETS[a.preset])
    if a.font: p["font"] = a.font
    if a.caps: p["caps"] = (a.caps == "on")
    if a.cap_y is not None: p["cap_y"] = a.cap_y
    if a.hook_y is not None: p["hook_y"] = a.hook_y
    if a.active_scale is not None: p["active_scale"] = a.active_scale
    if a.accent is not None:
        p["accent"] = None if a.accent.lower() in ("none", "off", "") else a.accent

    d = json.load(open(a.words))
    words = [[s["offsets"]["from"] / 1000.0, s["offsets"]["to"] / 1000.0, s["text"].strip()]
             for s in d["transcription"] if s["text"].strip()]
    if not words:
        sys.exit("no words in transcript")

    if a.corrections:
        c = json.load(open(a.corrections)); drop = set(c.get("drop", []))
        fix = {int(k): v for k, v in c.get("fix", {}).items()}
        words = [[w[0], w[1], fix.get(i, w[2])] for i, w in enumerate(words) if i not in drop]

    eos = lambda t: t.rstrip()[-1:] in ".?!"
    def disp(t):
        t = re.sub(r"[,;:]+$", "", t)            # strip trailing soft punctuation
        t = re.sub(r"[.!?]+$", "", t)            # keep it clean on screen
        t = t.replace("{", "(").replace("}", ")")  # ASS-safe
        return t.upper() if p["caps"] else t

    # stable phrase groups (same logic as caption_frames.py)
    groups, cur = [], []
    for w in words:
        cur.append(w)
        if len(cur) >= a.group or eos(w[2]):
            groups.append(cur); cur = []
    if cur: groups.append(cur)

    base_ass = hex_to_ass(p["base"])
    accent_ass = hex_to_ass(p["accent"]) if p["accent"] else base_ass
    out_ass = hex_to_ass(p["outline"])
    # spark/counter accent: explicit --accent-hex wins, else the caption accent
    spark_ass = hex_to_ass(a.accent_hex) if a.accent_hex else accent_ass
    SC = p["active_scale"]

    # --- build dialogue lines: one per active word so the highlight moves ---
    events = []

    def line_text(toks, active):
        parts = []
        for i, t in enumerate(toks):
            if i == active:
                if p["accent"]:
                    parts.append(f"{{\\fscx{SC}\\fscy{SC}\\1c{accent_ass}}}{t}{{\\fscx100\\fscy100\\1c{base_ass}}}")
                else:
                    parts.append(f"{{\\fscx{SC}\\fscy{SC}}}{t}{{\\fscx100\\fscy100}}")
            else:
                parts.append(t)
        body = " ".join(parts)
        return f"{{\\an5\\pos({W // 2},{p['cap_y']})}}{body}"

    for gi, g in enumerate(groups):
        gend = groups[gi + 1][0][0] if gi + 1 < len(groups) else g[-1][1] + 0.30
        toks = [disp(w[2]) for w in g]
        for k in range(len(g)):
            st = g[k][0]
            en = g[k + 1][0] if k + 1 < len(g) else gend
            if en <= st:
                en = st + 0.08
            events.append((st, en, "Cap", line_text(toks, k)))

    # --- hook line (upper-middle) ---
    if a.hook:
        hlines = [s for s in a.hook.split("|") if s]
        if hlines:
            # NEVER let the hook clip: measure with the real font and wrap +
            # shrink until the widest line fits a title-safe width. Author '|'
            # breaks are kept as hard breaks; we only ADD breaks / shrink.
            safe_w = a.hook_safe_frac * W
            disp_lines, fit_size = fit_hook(
                hlines, p["font"], p["caps"], p["spacing"],
                p["hook_size"], safe_w, a.hook_max_lines, a.hook_min_size)
            if fit_size != p["hook_size"]:
                print(f"  hook auto-fit: {p['hook_size']}px -> {fit_size}px, "
                      f"{len(disp_lines)} line(s) (safe width {int(safe_w)}px)")
            p["hook_size"] = fit_size
            full = "\\N".join(disp_lines)
            hk_col = accent_ass if p["hook_accent"] else base_ass
            pos = f"\\an5\\pos({W // 2},{p['hook_y']})"

            def spark(text):
                """Colour the spark word in the accent on the held hook."""
                if not a.hook_spark:
                    return text
                wd = a.hook_spark.upper() if p["caps"] else a.hook_spark
                return text.replace(wd, f"{{\\1c{spark_ass}}}{wd}{{\\1c{hk_col}}}", 1)

            if a.hook_anim == "typewriter":
                # reveal unit-by-unit (a "\\N" line break counts as one unit)
                units, i = [], 0
                while i < len(full):
                    if full[i:i + 2] == "\\N":
                        units.append("\\N"); i += 2
                    else:
                        units.append(full[i]); i += 1
                type_dur = min(1.1, a.hook_secs * 0.55)
                step = type_dur / max(1, len(units))
                for k in range(1, len(units) + 1):
                    sub = "".join(units[:k])
                    cursor = "" if k == len(units) else "▌"  # ▌
                    st = (k - 1) * step
                    en = k * step if k < len(units) else type_dur
                    events.append((st, en + 0.001, "Hook",
                                   f"{{{pos}\\1c{hk_col}}}{sub}{cursor}"))
                # held full hook (with spark), fades out
                events.append((type_dur, a.hook_secs, "Hook",
                               f"{{{pos}\\1c{hk_col}\\fad(0,250)}}{spark(full)}"))
            else:
                events.append((0.0, a.hook_secs, "Hook",
                               f"{{{pos}\\1c{hk_col}\\fad(150,250)}}{spark(full)}"))

    # --- optional extra overlays: source lower-thirds + number count-ups ---
    if a.overlays:
        for o in json.load(open(a.overlays)):
            ot = o.get("type")
            if ot == "source":
                txt = o["text"].replace("{", "(").replace("}", ")")
                events.append((o["start"], o["end"], "Cap",
                               f"{{\\an1\\pos(48,1500)\\fn Space Mono\\fs34\\bord5\\shad2"
                               f"\\1c{base_ass}\\3c{out_ass}\\fad(150,150)}}{txt}"))
            elif ot == "counter":
                y = o.get("y", 540)
                target = int(re.sub(r"[^0-9]", "", str(o["value"])) or 0)
                steps = 12
                cdur = min(0.9, (o["end"] - o["start"]) * 0.5)
                for s in range(steps):
                    val = f"{int(target * s / steps):,}"
                    st = o["start"] + (s / steps) * cdur
                    en = o["start"] + ((s + 1) / steps) * cdur
                    events.append((st, en, "Cap",
                                   f"{{\\an5\\pos({W // 2},{y})\\fn {p['font']}\\fs118\\bord10\\shad3"
                                   f"\\1c{spark_ass}\\3c{out_ass}\\4c&H00000000}}{val}"))
                events.append((o["start"] + cdur, o["end"], "Cap",
                               f"{{\\an5\\pos({W // 2},{y})\\fn {p['font']}\\fs118\\bord10\\shad3"
                               f"\\1c{spark_ass}\\3c{out_ass}\\4c&H00000000\\fad(0,150)}}{o['value']}"))
                if o.get("label"):
                    events.append((o["start"], o["end"], "Cap",
                                   f"{{\\an5\\pos({W // 2},{y + 92})\\fn Space Mono\\fs32\\fsp2"
                                   f"\\bord4\\1c{base_ass}\\3c{out_ass}\\fad(150,150)}}{o['label']}"))

    events.sort(key=lambda e: e[0])

    bold = "-1" if p["bold"] else "0"
    # V4+ style fields: see header. BorderStyle 1 = outline+shadow.
    style_fmt = ("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                 "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                 "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                 "Alignment, MarginL, MarginR, MarginV, Encoding")
    cap_style = (f"Style: Cap,{p['font']},{p['cap_size']},{base_ass},{base_ass},"
                 f"{out_ass},&H64000000,{bold},0,0,0,100,100,{p['spacing']},0,1,"
                 f"{p['outline_px']},{p['shadow_px']},5,90,90,0,0")
    hook_style = (f"Style: Hook,{p['font']},{p['hook_size']},{base_ass},{base_ass},"
                  f"{out_ass},&H64000000,{bold},0,0,0,100,100,{p['spacing']},0,1,"
                  f"{p['outline_px'] + 1},{p['shadow_px']},5,80,80,0,0")

    lines = []
    lines.append("[Script Info]")
    lines.append("ScriptType: v4.00+")
    lines.append("WrapStyle: 2")
    lines.append("ScaledBorderAndShadow: yes")
    lines.append(f"PlayResX: {W}")
    lines.append(f"PlayResY: {H}")
    lines.append("")
    lines.append("[V4+ Styles]")
    lines.append(style_fmt)
    lines.append(cap_style)
    lines.append(hook_style)
    lines.append("")
    lines.append("[Events]")
    lines.append("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text")
    for st, en, style, txt in events:
        lines.append(f"Dialogue: 0,{cs(st)},{cs(en)},{style},,0,0,0,,{txt}")

    open(a.out, "w").write("\n".join(lines) + "\n")
    print(f"wrote {a.out}  (preset={a.preset}, font={p['font']}, "
          f"accent={p['accent'] or 'scale-only'}, {len(groups)} phrase-groups, "
          f"{len(events)} events)")


if __name__ == "__main__":
    main()

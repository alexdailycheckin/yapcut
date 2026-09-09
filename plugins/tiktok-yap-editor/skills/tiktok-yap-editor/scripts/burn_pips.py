#!/usr/bin/env python3
"""Burn image PiP overlays (logos, article/headline screenshots) onto a finished
clip. libass cannot composite raster images, so build_ass only handles the text
overlays (source tags, number counters); the `pip` entries in the overlays JSON
are burned here instead. yapfull calls this after compose so PiPs are automatic.

Overlays JSON entry:
  {"type":"pip","file":"evidence/chip_arc.png","start":5.6,"end":8.6,"w":300,"y":470}
- file: path (relative to --workdir, or absolute) of a REAL screenshot/logo PNG.
- start/end: seconds on the finished timeline.
- w: rendered width in px (default 720). Height auto (aspect kept).
- y: top edge y in px (default 1400: UNDER the caption line at ~1320, never over
     the face). Horizontally centered. Rolling number counters go ABOVE the
     caption (build_ass, ~1150); logos/screenshots go BELOW it (here).

TEXT COLLISION RULE (hard, added after the Jul 26 batch burned logos straight
over the hook): PiPs are composited ON TOP of the already-burned captions, so
any geometric overlap HIDES text. Every pip is checked against the geometry
sidecar build_ass writes (cap_<out>.ass.meta.json, passed as --meta):
- a pip on screen during the hook window is auto-fitted (moved/shrunk) into the
  band ABOVE the hook block; if it cannot fit there it goes under the captions.
- no pip may ever cross the caption band; offenders are shrunk to clear it.
Requested y/w are treated as suggestions; text always wins.

Real screenshots/logos only (no AI), per the skill's hard rule. Exit 0 always;
if there are no pip entries it just copies the stream through.

Usage: burn_pips.py --video in.mp4 --overlays x_overlays.json --workdir WD
                    --out out.mp4 [--meta cap_x.ass.meta.json]
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import media  # noqa: E402

TOP_MARGIN = 60          # stay clear of the platform UI at the very top
PAD = 20                 # min gap between a pip and any text block
BOTTOM_LIMIT = 1880      # never off the bottom edge

def img_size(path):
    return media.image_size(path)

def fit_pip(p, iw, ih, meta):
    """Return (w, y) honouring the text-collision rule. Never lets the pip
    cover the hook (while it is up) or the caption band."""
    w = int(p.get("w", 720)); y = int(p.get("y", 1400))
    ar = ih / iw
    h = int(w * ar)
    hook = (meta or {}).get("hook")
    cap = (meta or {}).get("caption_band") or {"top": 1220, "bottom": 1420}
    s = float(p["start"])

    def log(msg):
        print(f"burn_pips: {os.path.basename(p['file'])}: {msg}")

    # 1) hook window: the pip must live entirely ABOVE the hook block
    if hook and s < hook["secs"] and y + h > hook["top"] - PAD and y < hook["bottom"] + PAD:
        band_h = hook["top"] - PAD - TOP_MARGIN
        if band_h >= 90:
            if h > band_h:
                w = max(1, int(w * band_h / h)); h = int(w * ar)
                log(f"shrunk to {w}px wide to fit above the hook")
            ny = hook["top"] - PAD - h
            log(f"on screen during the hook: y {p.get('y')} -> {ny} (above hook band "
                f"{hook['top']}-{hook['bottom']})")
            y = ny
        else:
            y = cap["bottom"] + PAD
            log(f"no room above the hook; moved under the captions (y={y})")

    # 2) caption band: always on screen; a pip may sit fully above or fully below
    if y < cap["top"] and y + h > cap["top"] - PAD:
        nh = cap["top"] - PAD - y
        if nh >= 90:
            w = max(1, int(w * nh / h)); h = int(w * ar)
            log(f"shrunk to {w}px wide to clear the caption line")
        else:
            y = cap["bottom"] + PAD
            log(f"moved under the captions (y={y})")
    if cap["top"] <= y <= cap["bottom"]:
        y = cap["bottom"] + PAD
        log(f"sat inside the caption band; moved to y={y}")

    # 3) frame bottom
    if y + h > BOTTOM_LIMIT:
        nh = BOTTOM_LIMIT - y
        w = max(1, int(w * nh / h)); h = int(w * ar)
        log(f"shrunk to {w}px wide to stay on screen")
    return w, y

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--overlays", required=True)
    ap.add_argument("--workdir", default=".")
    ap.add_argument("--out", required=True)
    ap.add_argument("--meta", default="",
                    help="geometry sidecar from build_ass (cap_<out>.ass.meta.json); "
                         "enables the text-collision guard")
    a = ap.parse_args()

    if not os.path.exists(a.overlays):
        print("burn_pips: no overlays file, skipping"); return
    pips = [o for o in json.load(open(a.overlays)) if o.get("type") == "pip"]
    if not pips:
        print("burn_pips: no pip entries, skipping")
        return
    meta = None
    if a.meta and os.path.exists(a.meta):
        meta = json.load(open(a.meta))
    else:
        print("burn_pips: WARNING no geometry sidecar; text-collision guard is "
              "running on default caption geometry only")

    inputs = ["-i", a.video]
    parts, last = [], "0:v"
    for i, p in enumerate(pips):
        f = p.get("file")
        if not f:
            print("burn_pips: pip entry without 'file' (coverage-only log), skipping")
            continue
        if not os.path.isabs(f):
            f = os.path.join(a.workdir, f)
        if not os.path.exists(f):
            print(f"burn_pips: MISSING {f}, skipping that pip"); continue
        iw, ih = img_size(f)
        w, y = fit_pip(p, iw, ih, meta)
        inputs += ["-i", f]
        idx = len([x for x in inputs if x == "-i"]) - 1  # this image's input index
        s = float(p["start"]); e = float(p["end"])
        parts.append(f"[{idx}:v]scale={w}:-1[p{i}]")
        out = f"o{i}"
        parts.append(
            f"[{last}][p{i}]overlay=(W-w)/2:{y}:enable='between(t,{s},{e})'[{out}]")
        last = out
    if last == "0:v":
        print("burn_pips: no valid pips, skipping"); return

    fc = ";".join(parts)
    # the final label needs a stable name for -map
    fc = fc.rsplit(f"[{last}]", 1)[0] + "[vout]"
    cmd = ["ffmpeg", "-nostdin", "-y", *inputs, "-filter_complex", fc,
           "-map", "[vout]", "-map", "0:a?", "-c:a", "copy",
           "-c:v", "libx264", "-preset", "medium", "-crf", "16",
           "-pix_fmt", "yuv420p", a.out,
           "-hide_banner", "-loglevel", "error"]
    media.run(cmd, what="ffmpeg pip burn")
    print(f"burn_pips: {len([p for p in pips])} pip(s) burned -> {a.out}")

if __name__ == "__main__":
    main()

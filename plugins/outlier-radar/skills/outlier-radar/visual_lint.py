#!/usr/bin/env python3
"""Machine gate for Outlier Radar feed assets.

A LinkedIn feed asset has to survive two things a pretty render does not care about:
the page it sits on, and a 1.7-second glance. This checks the first, which is the part
a machine can actually measure.

Added 2026-08-11 after the 08-10 slate shipped a cream-on-cream still life measuring
5.9% edge delta against LinkedIn's own #F4F2EE feed background. It was a genuinely
handsome image that in-feed read as no image at all.

Usage:
    python3 visual_lint.py render.png [more.png ...]
    python3 visual_lint.py --dir path/to/renders
    python3 visual_lint.py --accent "#FEA3B4" render.png    # grade THIS accent, not the warm default

--accent (3.11.1): the coverage floor used to count warm red and orange pixels by a fixed
rule, so a cover rendered in the creator's current palette failed at 0.0% while looking
right. The floor now runs ONLY against an accent the asset declares: radar_gate.py passes
`visual.accent` from the week file per render. No declaration, no accent floor; the four
legibility floors always run.

Exit codes (Contract 1, 2026-09-09): 0 every asset clears the floor, 2 any asset fails,
1 when there was nothing to measure or Pillow is missing (an onboarding state, not a
defect). NOTE --dir here means a directory OF RENDERS, not the workspace; radar_gate.py
passes explicit paths.
"""
import sys
import os
import glob

try:
    from PIL import Image
except ImportError:
    sys.exit("visual_lint needs Pillow: pip3 install Pillow")

# LinkedIn's feed background. The asset has to have an edge against THIS, not white.
FEED_BG_LUM = 240.3          # luminance of #F4F2EE

# Floors. See the-show.md, "Feed-asset physics".
MAX_MEAN_LUM = 200.0         # brighter than this and it dissolves into the page
MIN_RMS = 55.0               # below this there is no internal contrast to catch an eye
MIN_EDGE_DELTA_PCT = 25.0    # separation from the feed background
MIN_ACCENT_PCT = 4.0         # opt-in via --accent: the declared accent has to be present
MAX_FLAT_PCT = 55.0          # share of frame allowed to sit in one near-flat band
ACCENT = None                # (r, g, b) from --accent; None keeps the warm-pixel rule
ACCENT_DIST = 70.0           # colour distance that still counts as the accent


def parse_hex(h):
    h = h.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def luminance(p):
    r, g, b = p[0], p[1], p[2]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def measure(path):
    im = Image.open(path).convert("RGB")
    # Downscale for speed; contrast statistics survive it fine.
    if im.width > 900:
        im = im.resize((900, int(im.height * 900 / im.width)), Image.LANCZOS)
    px = list(im.getdata())
    n = len(px)

    lums = [luminance(p) for p in px]
    mean = sum(lums) / n
    rms = (sum((l - mean) ** 2 for l in lums) / n) ** 0.5
    flat = sum(1 for l in lums if l > 225) / n * 100
    accent = None
    if ACCENT:
        ar, ag, ab = ACCENT
        accent = sum(1 for (r, g, b) in px
                     if ((r - ar) ** 2 + (g - ag) ** 2 + (b - ab) ** 2) ** 0.5 <= ACCENT_DIST) / n * 100
    edge = abs(FEED_BG_LUM - mean) / 255 * 100

    checks = [
        ("mean luminance", mean, MAX_MEAN_LUM, mean <= MAX_MEAN_LUM, "<="),
        ("RMS contrast", rms, MIN_RMS, rms >= MIN_RMS, ">="),
        ("edge vs feed bg %", edge, MIN_EDGE_DELTA_PCT, edge >= MIN_EDGE_DELTA_PCT, ">="),
        ("near-flat frame %", flat, MAX_FLAT_PCT, flat <= MAX_FLAT_PCT, "<="),
    ]
    if accent is not None:
        # opt-in: the accent floor runs only against an accent the asset declared
        checks.insert(3, ("accent coverage %", accent, MIN_ACCENT_PCT, accent >= MIN_ACCENT_PCT, ">="))
    return checks, all(c[3] for c in checks)


def main(argv):
    global ACCENT
    args = argv[1:]
    if "--accent" in args:
        i = args.index("--accent")
        try:
            ACCENT = parse_hex(args[i + 1])
        except (IndexError, ValueError):
            sys.exit("--accent needs a hex colour like #FEA3B4")
        del args[i:i + 2]
    if not args:
        sys.exit(__doc__)

    if args[0] == "--dir":
        if len(args) < 2:
            sys.exit("--dir needs a path")
        paths = sorted(
            p for ext in ("png", "jpg", "jpeg", "webp")
            for p in glob.glob(os.path.join(args[1], f"*.{ext}"))
        )
    else:
        paths = args

    if not paths:
        print("no images found")
        return 1

    failed = []
    for path in paths:
        checks, ok = measure(path)
        print(f"\n{'PASS' if ok else 'FAIL'}  {os.path.basename(path)}")
        for name, value, floor, passed, op in checks:
            mark = "ok  " if passed else "FAIL"
            print(f"  {mark} {name:<20} {value:7.1f}   needs {op} {floor}")
        if not ok:
            failed.append(path)

    print()
    if failed:
        print(f"{len(failed)} of {len(paths)} assets fail the feed floor:")
        for p in failed:
            print(f"  {os.path.basename(p)}")
        print("\nUsual fix: the field is too light. Invert it: run your dark ink or your")
        print("accent as the FIELD and your paper tone as the type. Same brand tokens,")
        print("opposite weighting. A light object on a dark field clears the floor.")
        print(f"visual_lint: {len(failed)} fail -> rc 2")
        return 2

    print(f"all {len(paths)} assets clear the feed floor")
    print("visual_lint: 0 fail -> rc 0")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

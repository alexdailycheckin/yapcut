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

Exit code 1 if any asset fails, so it can gate a build.
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
MIN_ACCENT_PCT = 4.0         # the accent has to be present, not a garnish
MAX_FLAT_PCT = 55.0          # share of frame allowed to sit in one near-flat band


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
    accent = sum(1 for (r, g, b) in px if r > 180 and r - b > 80 and g < 180) / n * 100
    edge = abs(FEED_BG_LUM - mean) / 255 * 100

    checks = [
        ("mean luminance", mean, MAX_MEAN_LUM, mean <= MAX_MEAN_LUM, "<="),
        ("RMS contrast", rms, MIN_RMS, rms >= MIN_RMS, ">="),
        ("edge vs feed bg %", edge, MIN_EDGE_DELTA_PCT, edge >= MIN_EDGE_DELTA_PCT, ">="),
        ("accent coverage %", accent, MIN_ACCENT_PCT, accent >= MIN_ACCENT_PCT, ">="),
        ("near-flat frame %", flat, MAX_FLAT_PCT, flat <= MAX_FLAT_PCT, "<="),
    ]
    return checks, all(c[3] for c in checks)


def main(argv):
    args = argv[1:]
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
        sys.exit("no images found")

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
        return 1

    print(f"all {len(paths)} assets clear the feed floor")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

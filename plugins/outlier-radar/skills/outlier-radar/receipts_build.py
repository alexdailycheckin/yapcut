#!/usr/bin/env python3
"""DEPRECATED (2026-08-05): superseded by capture_gate.py.

This script REPAIRED broken captures (cropping above a cookie modal,
undimming the wash, sliding an ink-density band) and so produced
plausible-looking cards from pages that never rendered. One 7-video batch
shipped 21 junk receipts that way. Kept only so existing installs keep
running; do not point a new episode at it. Use capture_gate.py, which rejects
instead of repairing and clips to the headline by DOM geometry.

receipts_build.py: turn an episode's shot list into styled on-screen receipt cards.

The bridge between the show's week JSON (shot_list per episode: URL + what to frame)
and the yap editor's evidence-insert layer (white-card receipts in the top third,
pip_coverage). For each shot:

  1. CAPTURE: headless Chrome screenshot of the URL (top of page, 1300px wide).
     If a manual capture exists at <out>/manual/<episode>_<shot>.png it wins
     (paywalls, cookie walls, logged-in views: grab those by hand or with the
     browser agent, drop them in manual/, rerun).
  2. STYLE: crop, scale to the locked receipt width (<=972px), white rounded
     card pad, hairline border, source pill with the domain.
  3. MANIFEST: <out>/receipts_manifest.json with per-shot status
     (captured | manual | needs_manual) + suggested overlay timing parsed from
     the episode's beat map, in the editor's overlays-JSON shape.

Usage:
  python3 scripts/receipts_build.py --week weeks/2026-08-01.json \
      [--episode d-20260801-2] [--out show/receipts/2026-08-01] [--crop-h 620]

Verify every card by eye before burning: auto-capture cannot judge whether the
headline landed in frame. Cards flagged needs_manual MUST be replaced by hand.
"""
import argparse, json, os, pathlib, re, subprocess, sys, tempfile
from urllib.parse import urlparse

try:
    from PIL import Image, ImageDraw, ImageFont, ImageStat
except ImportError:
    sys.exit("Pillow required: pip3 install Pillow")

CHROME = os.environ.get(
    "CHROME_BIN", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
CARD_W = 972          # locked receipt max width in the 1080x1920 frame
PAD = 26              # white card padding
RADIUS = 28
CAP_W, CAP_H = 1300, 1700   # capture viewport
# Placement: TOP THIRD. Frame the talking head low and shoot with headroom for
# the card. A bottom band (y1440-1650) collides with the caption line, never use it.
TOP_THIRD_Y = 150
Y_BAND = "140-190 top third (locked; burn_pips collision guard may re-place)"


def capture(url: str, dest: pathlib.Path, timeout=60) -> bool:
    with tempfile.TemporaryDirectory() as td:
        cmd = [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars",
               f"--user-agent={UA}", f"--window-size={CAP_W},{CAP_H}",
               f"--screenshot={dest}", "--virtual-time-budget=9000",
               f"--user-data-dir={td}", "--no-first-run", url]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return False
    return dest.exists() and dest.stat().st_size > 8000


def looks_blank(img: Image.Image) -> bool:
    g = img.convert("L").resize((64, 64))
    return ImageStat.Stat(g).stddev[0] < 6.0


def rounded_card(shot_png: pathlib.Path, out_png: pathlib.Path, domain: str,
                 crop_h: int) -> dict:
    src = Image.open(shot_png).convert("RGB")
    src = src.crop((0, 0, src.width, min(crop_h, src.height)))
    scale = (CARD_W - 2 * PAD) / src.width
    src = src.resize((CARD_W - 2 * PAD, int(src.height * scale)), Image.LANCZOS)

    pill_h = 44
    card_w, card_h = CARD_W, src.height + 2 * PAD + pill_h
    card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(card)
    d.rounded_rectangle([0, 0, card_w - 1, card_h - 1], RADIUS,
                        fill=(255, 255, 255, 255), outline=(0, 0, 0, 40), width=2)
    card.paste(src, (PAD, PAD))

    # source pill: domain bottom-left
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
    return {"w": card_w, "h": card_h, "blank": looks_blank(src)}


def beat_seconds(directions: str, shot_id: str, beat: str = ""):
    """Start second for a shot. The slate writes windows as '0-4s' / '22-38s',
    first on the shot's own beat label, then in the episode directions."""
    for text in (beat, ""):
        m = re.search(r"(\d+)\s*-\s*(\d+)\s*s", text)
        if m:
            return float(m.group(1))
    for line in directions.splitlines():
        if beat and line.strip().startswith(beat.split(".")[0].strip()):
            m = re.search(r"(\d+)\s*-\s*(\d+)\s*s", line)
            if m:
                return float(m.group(1))
        if re.search(rf"\b{re.escape(str(shot_id))}\b", line):
            m = re.search(r"(\d+):(\d\d)", line)
            if m:
                return float(int(m.group(1)) * 60 + int(m.group(2)))
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True)
    ap.add_argument("--episode", help="one episode id; default = all")
    ap.add_argument("--out", default=None)
    ap.add_argument("--crop-h", type=int, default=620,
                    help="pixels of page top kept before scaling (default 620)")
    ap.add_argument("--hold", type=float, default=3.2,
                    help="default overlay hold seconds (default 3.2)")
    args = ap.parse_args()

    week = json.load(open(args.week))
    date = week["week"]
    out = pathlib.Path(args.out or f"show/receipts/{date}")
    (out / "raw").mkdir(parents=True, exist_ok=True)
    (out / "manual").mkdir(exist_ok=True)

    manifest = []
    for it in week.get("distribution", []):
        if args.episode and it["id"] != args.episode:
            continue
        for shot in it.get("shot_list", []):
            # slate schema drifted: early weeks wrote shot/what, the show
            # skeleton writes n/shoot. Accept both rather than crash.
            sid = shot.get("shot", shot.get("n", shot.get("id")))
            url = (shot.get("url") or "").strip()
            what = shot.get("what") or shot.get("shoot") or ""
            beat = shot.get("beat", "")
            base = f"{it['id']}_{sid}"
            if not url:
                # face-only beat, nothing to capture
                print(f"{base}: no_artifact (face only)")
                continue
            if not url.startswith("http"):
                # e.g. "device screenshot": the creator shoots it, cannot be headless
                print(f"{base}: needs_manual ({url})")
                manifest.append({
                    "type": "pip", "episode": it["id"], "shot": sid, "url": url,
                    "what": what, "file": str(out / f"{base}.png"),
                    "status": "needs_manual",
                    "start": beat_seconds(it.get("directions", ""), sid, beat),
                    "end": None, "y_band": Y_BAND,
                })
                continue
            raw = out / "raw" / f"{base}.png"
            card = out / f"{base}.png"
            manual = out / "manual" / f"{base}.png"
            status = "captured"
            if manual.exists():
                raw, status = manual, "manual"
            elif not raw.exists():
                if not capture(url, raw):
                    status = "needs_manual"
            if status != "needs_manual":
                meta = rounded_card(raw, card, urlparse(url).netloc.replace("www.", ""),
                                    args.crop_h)
                if meta["blank"]:
                    status = "needs_manual"
            t0 = beat_seconds(it.get("directions", ""), sid, beat)
            manifest.append({
                "type": "pip", "episode": it["id"], "shot": sid, "url": url,
                "what": what, "file": str(card),
                "status": status,
                "start": t0, "end": (t0 + args.hold) if t0 is not None else None,
                "y": TOP_THIRD_Y, "y_band": Y_BAND,
            })
            print(f"{base}: {status}" + (f" @ {t0}s" if t0 is not None else ""))

    mpath = out / "receipts_manifest.json"
    mpath.write_text(json.dumps(manifest, indent=2))
    need = [m for m in manifest if m["status"] == "needs_manual"]
    print(f"\n{len(manifest)} shots -> {mpath}")
    if need:
        print(f"{len(need)} need a manual capture in {out/'manual'}/ then rerun:")
        for m in need:
            print(f"  {m['episode']}_{m['shot']}.png  <- {m['url']}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Retention gate: find visual-event gaps in a finished cut.

A visual event is anything that changes the frame: a hard cut or big frame
change (ffmpeg scene detection), or an overlay window you pass in (hook,
counter, source tag, PiP evidence insert). The gate flags:
  1. any stretch longer than --max-gap seconds with NO visual event
     (that stretch is where people scroll away),
  2. no event inside the re-hook window (0.3s .. --first): seconds 2-5 must
     raise the stakes visually, not just verbally.

Usage:
  python3 retention_check.py --video final.mp4 \
      [--overlays .yap_build/clip_overlays.json] [--hook-end 5.2] \
      [--max-gap 5.0] [--first 3.5] [--scene 0.10]

Exit codes: 0 = clean, 2 = gate failed (build-gating, like stutter_check).
Tuning: the alternating static crop reads as a small change; if real cuts are
missed lower --scene toward 0.06, if caption words register as cuts raise it.
"""
import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path


def probe_duration(video: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=noprint_wrappers=1:nokey=1", video],
        capture_output=True, text=True, check=True)
    return float(out.stdout.strip())


def scene_events(video: str, threshold: float) -> list:
    """Timestamps where the frame changes hard (cuts, punch-ins, PiP pops)."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
        meta_path = tf.name
    vf = f"select='gt(scene,{threshold})',metadata=print:file={meta_path}"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-i", video, "-vf", vf, "-an", "-f", "null", "-"],
        capture_output=True, text=True)
    times = []
    for line in Path(meta_path).read_text().splitlines():
        m = re.search(r"pts_time:([0-9.]+)", line)
        if m:
            times.append(float(m.group(1)))
    Path(meta_path).unlink(missing_ok=True)
    return times


def overlay_events(overlays_path: str) -> list:
    """Overlay starts AND ends both change the frame, count both."""
    items = json.loads(Path(overlays_path).read_text())
    times = []
    for it in items:
        for key in ("start", "end"):
            v = it.get(key)
            if isinstance(v, (int, float)):
                times.append(float(v))
    return times


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--overlays", help="overlays.json (source tags, counters, pip)")
    ap.add_argument("--hook-end", type=float, default=5.2,
                    help="when the burned hook disappears (that is an event)")
    ap.add_argument("--max-gap", type=float, default=5.0,
                    help="longest allowed stretch with no visual event")
    ap.add_argument("--first", type=float, default=3.5,
                    help="re-hook window: need an event between 0.3s and this")
    ap.add_argument("--scene", type=float, default=0.10,
                    help="ffmpeg scene-change threshold")
    args = ap.parse_args()

    dur = probe_duration(args.video)
    events = scene_events(args.video, args.scene)
    events.append(args.hook_end)
    if args.overlays and Path(args.overlays).exists():
        events += overlay_events(args.overlays)
    events = sorted(t for t in set(round(e, 2) for e in events) if 0 < t < dur)

    print(f"video: {args.video}")
    print(f"duration: {dur:.1f}s, visual events: {len(events)} "
          f"({len(events) / dur * 60:.1f}/min)")

    failed = False

    # Re-hook window: something must change on screen in seconds ~2-4.
    rehook = [t for t in events if 0.3 <= t <= args.first]
    if rehook:
        print(f"re-hook: OK (event at {rehook[0]:.1f}s)")
    else:
        failed = True
        print(f"re-hook: FAIL, nothing changes on screen before {args.first}s. "
              "Add a cut, punch-in, or text pop in seconds 2-4.")

    # Static stretches.
    marks = [0.0] + events + [dur]
    gaps = []
    for a, b in zip(marks, marks[1:]):
        if b - a > args.max_gap:
            gaps.append((a, b))
    if gaps:
        failed = True
        for a, b in gaps:
            print(f"static stretch: {a:.1f}s -> {b:.1f}s ({b - a:.1f}s). "
                  "Add a text pop, counter, PiP evidence insert, or punch-in here.")
        longest = max(gaps, key=lambda g: g[1] - g[0])
        print(f"longest static stretch: {longest[1] - longest[0]:.1f}s "
              f"at {longest[0]:.1f}s. That is where people leave.")
    else:
        print(f"pattern-interrupt budget: OK (no stretch over {args.max_gap:.0f}s)")

    return 2 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

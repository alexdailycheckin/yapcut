#!/usr/bin/env python3
"""Retention gate: find visual-event gaps in a finished cut.

A visual event is anything that changes the frame: a hard cut or big frame
change (ffmpeg scene detection), or an overlay window you pass in (hook,
counter, source tag, PiP evidence insert). The gate flags:
  1. any stretch longer than --max-gap seconds with NO visual event
     (that stretch is where people scroll away),
  2. no event inside the re-hook window (0.3s .. --first): seconds 2-5 must
     raise the stakes visually, not just verbally.

JOINS ARE NOT EVENTS (2026-09-09). The cutter's own pause-cuts, plus the
1.00/1.06 crop toggle at each of them, register as scene changes, and on the
shipped aug 24 / aug 30 files 69 to 86 percent of counted events sat at joins.
A 56s talking head with 16 pause-cuts passed the budget with zero deliberate
events. Pass --keeps (the keeps_full_<out>.json yapcut writes) and every scene
event within --join-tol of a join is discarded before counting; the gate then
measures what the EDITOR put on screen, not what the cutter removed.

Usage:
  python3 retention_check.py --video final.mp4 \
      [--overlays .yap_build/clip_overlays.json] [--hook-end 5.2] \
      [--keeps .yap_build/keeps_full_clip.json] [--join-tol 0.2] \
      [--max-gap 5.0] [--first 3.5] [--scene 0.10]

Exit codes: 0 = clean, 2 = gate failed (build-gating, like stutter_check).
Tuning: if real cuts are missed lower --scene toward 0.06, if caption words
register as cuts raise it.
"""
import argparse
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import media  # noqa: E402


def scene_events(video: str, threshold: float) -> list:
    """Timestamps where the frame changes hard (cuts, punch-ins, PiP pops)."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tf:
        meta_path = tf.name
    vf = f"select='gt(scene,{threshold})',metadata=print:file={meta_path}"
    media.run(["ffmpeg", "-nostdin", "-hide_banner", "-i", video, "-vf", vf,
               "-an", "-f", "null", "-"], what="ffmpeg scene detection")
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


def join_times(keeps_path: str) -> list:
    """Cumulative join positions on the OUTPUT timeline from a keeps json."""
    keeps = json.loads(Path(keeps_path).read_text())
    joins, t = [], 0.0
    for k in keeps[:-1]:
        t += float(k["b"]) - float(k["a"])
        joins.append(t)
    return joins


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--overlays", help="overlays.json (source tags, counters, pip)")
    ap.add_argument("--keeps", help="keeps_full_<out>.json from yapcut: scene events at its "
                    "joins are the cutter's, not the editor's, and are discarded")
    ap.add_argument("--join-tol", type=float, default=0.2,
                    help="a scene event within this many seconds of a join is a join")
    ap.add_argument("--hook-end", type=float, default=5.2,
                    help="when the burned hook disappears (that is an event)")
    ap.add_argument("--max-gap", type=float, default=5.0,
                    help="longest allowed stretch with no visual event")
    ap.add_argument("--first", type=float, default=3.5,
                    help="re-hook window: need an event between 0.3s and this")
    ap.add_argument("--scene", type=float, default=0.10,
                    help="ffmpeg scene-change threshold")
    args = ap.parse_args()

    dur = media.probe_duration(args.video)
    scenes = scene_events(args.video, args.scene)
    discarded = 0
    if args.keeps and Path(args.keeps).exists():
        joins = join_times(args.keeps)
        kept = [t for t in scenes if not any(abs(t - j) <= args.join_tol for j in joins)]
        discarded = len(scenes) - len(kept)
        scenes = kept
        print(f"joins: {len(joins)} from {Path(args.keeps).name}; "
              f"{discarded} scene event(s) discarded as joins (within {args.join_tol}s)")
    events = list(scenes)
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

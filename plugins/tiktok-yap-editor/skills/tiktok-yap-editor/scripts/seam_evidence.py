#!/usr/bin/env python3
"""Decide whether seam_qa's failures on this clip are real, or a gated mic.

seam_qa treats anything under -65dB near a join as a splice dropout, on the
reasonable assumption that room tone never reaches digital silence. Plenty of
mics break that assumption: with a noise gate or a very quiet room the pause
between two words IS silence, so every join trips the gate and a clean edit
looks broken. Turning the gate off on a hunch is how a real dropout ships, so
measure instead. Two numbers separate a harmless inter-word beat from a defect:

  1. DURATION of the sub-65dB run. Speech rhythm leaves short gaps; the cutter
     only removes pauses from 550ms up, and a spoken list needs a beat between
     items. Under ~150ms is rhythm, not dead air.
  2. A STEP CLICK at the join. A bad splice joins two samples with a jump, which
     reads as a click. Compare the largest sample-to-sample delta at each join
     against the file's own 99.9th percentile: a real click stands far above it.

Exit 0 (override justified) only when every flagged join is short AND click-free.
Exit 1 means at least one join looks like a genuine defect: fix the cut.

Usage:
  seam_evidence.py <final.mp4> <keeps_full_<slug>.json> [--hole-db -65]
                   [--max-run-ms 150] [--click-factor 1.5]

Then, and only then:  YAP_ALLOW_SEAM=1 yapfull.sh ...
"""
import argparse
import json
import math
import os
import statistics
import struct
import subprocess
import sys
import tempfile
import wave


def load_pcm(video, rate=48000):
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-i", video, "-ar", str(rate),
                    "-ac", "1", "-c:a", "pcm_s16le", tmp.name,
                    "-hide_banner", "-loglevel", "error"], check=True)
    w = wave.open(tmp.name, "rb")
    fr = w.getframerate()
    sm = struct.unpack(f"<{w.getnframes()}h", w.readframes(w.getnframes()))
    w.close()
    os.unlink(tmp.name)
    return sm, fr


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("keeps")
    ap.add_argument("--hole-db", type=float, default=-65.0)
    ap.add_argument("--max-run-ms", type=float, default=150.0)
    ap.add_argument("--click-factor", type=float, default=1.5)
    ap.add_argument("--span", type=float, default=0.35)
    a = ap.parse_args()

    sm, fr = load_pcm(a.video)
    keeps = json.load(open(a.keeps))
    joins, t = [], 0.0
    for k in keeps[:-1]:
        t += k["b"] - k["a"]
        joins.append(t)
    if not joins:
        print("no joins in this cut, nothing to measure")
        return

    # the file's own dynamics set the click bar, so a loud clip is not penalised
    diffs = [abs(sm[i + 1] - sm[i]) for i in range(0, len(sm) - 1, 9)]
    base = statistics.quantiles(diffs, n=1000)[998]

    def frames_db(t0, t1, win=0.01):
        a0, b0 = int(t0 * fr), int(t1 * fr)
        step = max(1, int(win * fr))
        out = []
        for i in range(max(0, a0), min(len(sm), b0) - step, step):
            c = sm[i:i + step]
            r = math.sqrt(sum(x * x for x in c) / len(c)) / 32768.0
            out.append(20 * math.log10(r) if r > 0 else -99.0)
        return out

    worst_run = worst_step = 0.0
    bad = []
    for j, tt in enumerate(joins):
        run = cur = 0
        for d in frames_db(tt - a.span, tt + a.span):
            cur = cur + 1 if d <= a.hole_db else 0
            run = max(run, cur)
        run_ms = run * 10
        lo, hi = int((tt - 0.012) * fr), int((tt + 0.012) * fr)
        step = max(abs(sm[i + 1] - sm[i])
                   for i in range(max(0, lo), min(hi, len(sm) - 1)))
        worst_run = max(worst_run, run_ms)
        worst_step = max(worst_step, step)
        if run_ms > a.max_run_ms or step > base * a.click_factor:
            bad.append((j, tt, run_ms, step))

    print(f"{os.path.basename(a.video)}: {len(joins)} joins measured")
    print(f"  file 99.9pct sample step : {base:.0f}")
    print(f"  worst sub{a.hole_db:.0f}dB run       : {worst_run:.0f}ms "
          f"(limit {a.max_run_ms:.0f}ms)")
    print(f"  worst step at any join   : {worst_step:.0f} "
          f"(limit {base * a.click_factor:.0f})")
    if bad:
        print("  VERDICT: do NOT override, these look like real defects:")
        for j, tt, run_ms, step in bad:
            print(f"    join{j} @{tt:7.2f}s  run {run_ms:.0f}ms  step {step:.0f}")
        sys.exit(1)
    print("  VERDICT: inter-word beats only, no clicks -> YAP_ALLOW_SEAM=1 is honest")


if __name__ == "__main__":
    main()

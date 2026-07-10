#!/usr/bin/env python3
"""Repetition gate that cannot be fooled by its own transcript.

Whisper transcribing a WHOLE video sometimes collapses a repeated line into
one ("Then read the post history... then read the post history..." came back
as a single sentence), so a transcript-based stutter check is blind to exactly
the defect it exists to catch. Short-window whisper stays literal.

This scans the video's audio in overlapping windows (default 30s / 15s hop),
word-transcribes each window fresh, runs stutter_check's detector per window,
and aggregates flags on the video timeline. Repeats up to ~15s apart land
inside at least one window together.

Usage: restart_scan.py --video cut.mp4 [--win 30] [--hop 15]
Exit: 0 clean, 1 MEDIUM-only (review in the line audit), 2 HIGH (gate fails).
"""
import argparse, json, os, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from stutter_check import find_flags, norm

MODEL = os.environ.get("WHISPER_MODEL",
                       os.path.expanduser("~/.whisper-models/ggml-small.en.bin"))

def window_tokens(video, t0, t1, tmpdir):
    base = os.path.join(tmpdir, f"w_{int(t0*1000)}")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-ss", f"{t0:.2f}", "-to", f"{t1:.2f}",
                    "-i", video, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                    base + ".wav", "-hide_banner", "-loglevel", "error"], check=True)
    subprocess.run(["whisper-cli", "-m", MODEL, "-f", base + ".wav", "-ml", "1",
                    "-sow", "-dtw", "small.en", "-oj", "-of", base],
                   capture_output=True, check=True)
    out = []
    for s in json.load(open(base + ".json"))["transcription"]:
        t = s["text"].strip()
        if not t or t.startswith("["):
            continue
        out.append((s["offsets"]["from"] / 1000.0 + t0,
                    s["offsets"]["to"] / 1000.0 + t0, t, norm(t)))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--win", type=float, default=30.0)
    ap.add_argument("--hop", type=float, default=15.0)
    a = ap.parse_args()
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                "format=duration", "-of", "csv=p=0", a.video],
                               capture_output=True, text=True).stdout)
    found = []   # (t0, t1, kind, conf, text)
    with tempfile.TemporaryDirectory() as td:
        t = 0.0
        while t < dur - 1.0:
            w = window_tokens(a.video, t, min(dur, t + a.win), td)
            for (_i, _j, kind, conf, text, t0, t1) in find_flags(w):
                # dedupe across overlapping windows by time+text
                if any(abs(t0 - f[0]) < 0.8 and norm(text)[:24] == norm(f[4])[:24]
                       for f in found):
                    continue
                found.append((t0, t1, kind, conf, text))
            t += a.hop
    if not found:
        print("clean: no repetition found in windowed scan")
        return
    found.sort()
    print(f"windowed scan found {len(found)} repetition span(s) "
          f"({sum(1 for f in found if f[3]=='HIGH')} HIGH):")
    for t0, t1, kind, conf, text in found:
        print(f"  [{conf:6}] {t0:6.2f}-{t1:6.2f}s  {kind:24} | \"{text}\"")
    sys.exit(2 if any(f[3] == "HIGH" for f in found) else 1)

if __name__ == "__main__":
    main()

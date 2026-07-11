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
import argparse, json, math, os, struct, subprocess, sys, tempfile, wave

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

def has_double_take_dip(video, t0, t1, tmpdir):
    """The acoustic signature of a restart: a >=0.22s quiet dip inside the
    flagged span (attempt 1 - pause - attempt 2). Roam's true restart never
    reproduced in ANY tight transcription (whisper collapsed it down to 5s
    windows) and was confirmed by exactly this envelope shape."""
    wav = os.path.join(tmpdir, f"dip_{int(t0*1000)}.wav")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-ss", f"{max(0,t0-0.2):.2f}",
                    "-to", f"{t1+0.6:.2f}", "-i", video, "-ar", "16000", "-ac", "1",
                    wav, "-hide_banner", "-loglevel", "error"], check=True)
    w = wave.open(wav, "rb"); fr = w.getframerate()
    sm = struct.unpack(f"<{w.getnframes()}h", w.readframes(w.getnframes())); w.close()
    win, hop = int(0.030 * fr), int(0.010 * fr)
    dbs = []
    for i in range(0, len(sm) - win, hop):
        c = sm[i:i + win]
        r = math.sqrt(sum(x * x for x in c) / len(c)) / 32768.0
        dbs.append(20 * math.log10(r) if r > 0 else -99.0)
    run = best = 0
    for i in range(len(dbs)):
        lo, hi = max(0, i - 2), min(len(dbs), i + 3)
        v = sorted(dbs[lo:hi])[(hi - lo) // 2]
        run = run + 1 if v < -28.0 else 0
        best = max(best, run)
    return best * hop / fr >= 0.22


def verify_flag(video, t0, t1, text, tmpdir):
    """A HIGH flag must be corroborated before it can fail a build. Two
    independent paths: (a) it reproduces in a tight re-transcription (the most
    literal whisper we can get), or (b) the audio envelope shows the
    double-take dip inside the span. Artifacts (token-splitting over
    continuous speech) fail both; true repeats pass at least one."""
    lo = max(0.0, t0 - 2.0)
    w = window_tokens(video, lo, t1 + 2.5, tmpdir)
    for (_i, _j, _k, conf, text2, s0, _s1) in find_flags(w):
        if conf == "HIGH" and abs(s0 - t0) < 1.2 and norm(text2)[:16] == norm(text)[:16]:
            return True
    return has_double_take_dip(video, t0, t1, tmpdir)


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
        # HIGH must reproduce in a tight re-transcription or it is demoted
        verified = []
        for t0, t1, kind, conf, text in found:
            if conf == "HIGH" and not verify_flag(a.video, t0, t1, text, td):
                conf = "MEDIUM"
                kind += " (unverified)"
            verified.append((t0, t1, kind, conf, text))
        found = verified
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

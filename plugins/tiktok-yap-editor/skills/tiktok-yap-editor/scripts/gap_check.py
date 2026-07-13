#!/usr/bin/env python3
"""Dead-air gate: measure the pauses that actually SURVIVED the cut.

Why this exists: silence detection cannot prove a cut is tight. Room tone sits
above any -dB threshold (a fan/AC take reports zero silence while holding a
1.3s hole), so the only honest measure is the transcript: the gap between one
spoken word ending and the next beginning. Run it on the CUT's word JSON
(yapfull step 2 already produces it). If this gate fails, the cut stage never
saw the pauses; that is the noisy-take symptom, see SKILL.md 6b: measure the
real floor, raise --silence-db, re-cut.

IMPORTANT: this gate transcribes the video ITSELF (whisper -ml 1, punctuation
as separate tokens). The pipeline's caption transcription uses -sow, which
glues punctuation to the word so the token's span swallows the very pause we
are hunting; measured on that JSON the roam 1.3s hole reads as zero gap.
Punct-separate tokens park pause time inside '.' tiles, which we skip, so the
hole shows up between speech tokens.

Usage:
  python3 gap_check.py --video cut.mp4 [--words no_sow_words.json] \
      [--fail 0.8] [--warn 0.6] [--lead 0.8] [--allow "6.9,41.2"]

--allow: comma-separated timestamps (s) of deliberate beats to permit (+/-0.3s).
Exit codes: 0 clean, 1 warnings only, 2 dead air found (build-gating).
"""
import argparse
import json
import os
import re
import subprocess
import sys
import tempfile


def transcribe_punct_separate(video: str) -> str:
    """16k mono extract + whisper -ml 1 (NO -sow): punct tokens stay separate."""
    model = os.environ.get("WHISPER_MODEL",
                           os.path.expanduser("~/.whisper-models/ggml-small.en.bin"))
    td = tempfile.mkdtemp(prefix="gapchk_")
    wav = os.path.join(td, "a.wav")
    out = os.path.join(td, "w")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-i", video, "-ar", "16000",
                    "-ac", "1", "-c:a", "pcm_s16le", wav,
                    "-hide_banner", "-loglevel", "error"], check=True)
    subprocess.run(["whisper-cli", "-m", model, "-f", wav, "-ml", "1",
                    "-oj", "-of", out], check=True,
                   capture_output=True, text=True)
    return out + ".json"


def speech_tokens(words_json: str) -> list:
    """(start, end, text) for real spoken tokens; punctuation tiles are skipped
    so their span counts as gap (whisper parks pause time inside '.' tokens)."""
    d = json.load(open(words_json))
    toks = []
    for s in d.get("transcription", []):
        t = s.get("text", "").strip()
        if not re.search(r"[A-Za-z0-9]", t) or re.match(r"^[\[(].*[\])]$", t):
            continue
        o = s["offsets"]
        toks.append((o["from"] / 1000.0, o["to"] / 1000.0, t))
    return toks


def probe_duration(video: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "csv=p=0", video], capture_output=True, text=True)
    try:
        return float(out.stdout.strip())
    except ValueError:
        return 0.0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--words", help="pre-made PUNCT-SEPARATE word json (no -sow); "
                    "omit to let the gate transcribe the video itself")
    ap.add_argument("--fail", type=float, default=0.8,
                    help="a surviving gap this long is dead air (exit 2)")
    ap.add_argument("--warn", type=float, default=0.6,
                    help="gaps between warn and fail are printed for the ear pass")
    ap.add_argument("--lead", type=float, default=0.8,
                    help="max silence before the first word (cold-open rule)")
    ap.add_argument("--allow", default="",
                    help="comma-separated gap timestamps to permit (+/-0.3s)")
    a = ap.parse_args()

    allow = [float(x) for x in a.allow.split(",") if x.strip()]
    words_json = a.words or transcribe_punct_separate(a.video)
    toks = speech_tokens(words_json)
    if not toks:
        print("gap_check: no speech found, refusing to pass silence")
        return 2

    fails, warns = [], []

    lead = toks[0][0]
    if lead > a.lead:
        fails.append((0.0, lead, "<start>", toks[0][2]))

    for (s1, e1, t1), (s2, e2, t2) in zip(toks, toks[1:]):
        g = s2 - e1
        if g < a.warn:
            continue
        if any(abs(e1 - t) <= 0.3 for t in allow):
            print(f"  allowed beat: {g:.2f}s @ {e1:.2f}s  (...{t1} | {t2}...)")
            continue
        (fails if g >= a.fail else warns).append((e1, s2, t1, t2))

    dur = probe_duration(a.video)
    tail = dur - toks[-1][1]
    if dur and tail > 1.2:
        warns.append((toks[-1][1], dur, toks[-1][2], "<end>"))

    for e1, s2, t1, t2 in warns:
        print(f"  warn: {s2 - e1:.2f}s gap @ {e1:.2f}s  (...{t1} | {t2}...)")
    for e1, s2, t1, t2 in fails:
        print(f"  DEAD AIR: {s2 - e1:.2f}s @ {e1:.2f}s  (...{t1} | {t2}...)")

    if fails:
        print(f"gap_check: {len(fails)} dead-air gap(s) survived the cut. "
              "The cut never saw them: measure the real pause floor, raise "
              "--silence-db (see SKILL.md 6b), re-cut. Deliberate beat? --allow <t>.")
        return 2
    if warns:
        print(f"gap_check: {len(warns)} borderline gap(s), listen before shipping")
        return 1
    print(f"gap_check: clean ({len(toks)} words, no gap >= {a.warn}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

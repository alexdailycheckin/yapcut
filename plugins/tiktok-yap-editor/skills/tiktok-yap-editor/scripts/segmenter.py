#!/usr/bin/env python3
"""List silence-delimited speech runs of a source with accurate boundaries +
per-run transcript, so restart duplicates are visible and pickable.

Whisper word-times DRIFT and are unreliable for cutting; run boundaries here come
from silencedetect (audio energy = reliable), and each run is transcribed
directly so you can SEE which take/pass to keep on a restart-heavy clip.

Usage: segmenter.py <src.MOV> [--workdir DIR] [--silence-db -42] [--d 0.32]
Prints: idx  start-end  text   (pick the clean runs -> keep_whole clauses)
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import media  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("src")
ap.add_argument("--workdir", default=None)
ap.add_argument("--silence-db", default="-42")
ap.add_argument("--d", default="0.32")
a = ap.parse_args()

src = a.src
WD = a.workdir or os.path.join(os.path.dirname(os.path.abspath(src)), ".yap_build")
os.makedirs(os.path.join(WD, "audio"), exist_ok=True)
MODEL = os.environ.get("WHISPER_MODEL",
                       os.path.expanduser("~/.whisper-models/ggml-small.en.bin"))
base = os.path.splitext(os.path.basename(src))[0]
wav = f"{WD}/audio/{base}.wav"
if not os.path.exists(wav):
    media.ffmpeg(["-i", src, "-ar", "16000", "-ac", "1", wav], what="ffmpeg wav extract")
dur = media.probe_duration(wav)
r = media.run(["ffmpeg", "-nostdin", "-i", wav, "-af",
               f"silencedetect=noise={a.silence_db}dB:d={a.d}", "-f", "null", "-"],
              what="ffmpeg silencedetect").stderr
sil = []; st = None
for l in r.splitlines():
    m = re.search(r"silence_start:\s*([\d.]+)", l)
    if m: st = float(m.group(1))
    m = re.search(r"silence_end:\s*([\d.]+)", l)
    if m and st is not None: sil.append((st, float(m.group(1)))); st = None
runs = []; cur = 0.0
for s, e in sil:
    if s > cur: runs.append((cur, s))
    cur = e
if cur < dur: runs.append((cur, dur))
tmp = f"{WD}/audio/_seg.wav"
for i, (s, e) in enumerate(runs):
    if e - s < 0.30: continue
    media.ffmpeg(["-ss", f"{s:.2f}", "-to", f"{e:.2f}", "-i", wav, tmp], what="ffmpeg run extract")
    media.run(["whisper-cli", "-m", MODEL, "-f", tmp, "-oj", "-of", f"{WD}/audio/_seg"],
              what="whisper-cli")
    j = json.load(open(f"{WD}/audio/_seg.json"))
    txt = " ".join(t["text"].strip() for t in j["transcription"]).strip()
    print(f"{i}\t{s:.2f}-{e:.2f}\t{txt}")

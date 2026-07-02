#!/usr/bin/env python3
"""Layer a music bed (ducked under the voice) + timed SFX hits onto a video's
existing audio. Video stream is copied; only audio is rebuilt. Works for both
modes: talking-head (whoosh on cuts, impact on hook) and VO storytelling
(music bed + cut whooshes under the voiceover).

Usage:
  sfxmix.py --in clip.mp4 --sfx sfx.json --out clip_sfx.mp4

sfx.json:
{
  "music": {"file": "bed_calm", "gain_db": -20, "duck": true},
  "hits": [
    {"sfx": "whoosh", "at": 0.0,  "gain_db": -8},
    {"sfx": "impact", "at": 1.15, "gain_db": -4},
    {"sfx": "ding",   "at": 9.30, "gain_db": -10}
  ]
}
- file/sfx: a pack name (-> assets/sfx/<name>.wav) OR an absolute path (BYO music/sfx).
- music.duck: sidechain-duck the bed whenever the voice is talking (default true).
- gain_db on the bed is its resting level under speech; hits are one-shot at `at` seconds.
Pack lives at <skill>/assets/sfx/ (run gen_sfx.py once to build it).
"""
import argparse, json, os, subprocess

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PACK = os.path.join(SKILL, "assets", "sfx")

def resolve(name):
    if os.path.isabs(name) or os.path.exists(name):
        return name
    for ext in (".wav", ".mp3", ".m4a", ".aac", ""):
        p = os.path.join(PACK, name + ext)
        if os.path.exists(p):
            return p
    raise SystemExit(f"sfx not found: {name} (looked in {PACK})")

def has_audio(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=index", "-of", "csv=p=0", path],
                       capture_output=True, text=True).stdout.strip()
    return bool(r)

def duration(path):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                 "format=duration", "-of", "csv=p=0", path],
                                capture_output=True, text=True).stdout)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--sfx", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    spec = json.load(open(a.sfx))
    music = spec.get("music")
    hits = spec.get("hits", [])
    voice = has_audio(a.inp)
    vdur = duration(a.inp)

    inputs = ["-i", a.inp]               # input 0 = video
    idx = 1
    parts, mixlabels = [], []

    # voice (split only when a ducked music bed will consume the [key] leg;
    # an unconsumed asplit output is a filtergraph error)
    need_key = bool(music) and music.get("duck", True) and voice
    if voice:
        if need_key:
            parts.append("[0:a]asplit=2[voc][key]")
        else:
            parts.append("[0:a]anull[voc]")
        mixlabels.append("[voc]")
    else:
        # silent video: synth a silent base so amix always has a member
        parts.append("anullsrc=channel_layout=stereo:sample_rate=48000[voc]")
        mixlabels.append("[voc]")

    # music bed (looped to fill, gain, optional sidechain duck under the voice)
    if music:
        mfile = resolve(music.get("file", "bed_calm"))
        inputs[:0] = []  # keep order: append
        inputs += ["-stream_loop", "-1", "-i", mfile]
        mi = idx; idx += 1
        g = music.get("gain_db", -20)
        parts.append(f"[{mi}:a]volume={g}dB[mraw]")
        if music.get("duck", True) and voice:
            parts.append("[mraw][key]sidechaincompress=threshold=0.03:ratio=8:"
                         "attack=20:release=300:makeup=1[mbed]")
        else:
            parts.append("[mraw]anull[mbed]")
        mixlabels.append("[mbed]")

    # one-shot SFX hits
    for n, h in enumerate(hits):
        hf = resolve(h.get("sfx", h.get("file")))
        inputs += ["-i", hf]
        hi = idx; idx += 1
        ms = int(round(float(h.get("at", 0)) * 1000))
        g = h.get("gain_db", -6)
        parts.append(f"[{hi}:a]adelay={ms}|{ms},volume={g}dB[h{n}]")
        mixlabels.append(f"[h{n}]")

    n_in = len(mixlabels)
    # normalize=0 keeps levels we set; final compose loudnorms anyway. alimiter
    # guards against clipping when hits stack on the voice.
    parts.append("".join(mixlabels) +
                 f"amix=inputs={n_in}:duration=first:normalize=0,"
                 "alimiter=limit=0.95[mix]")
    fc = ";".join(parts)

    # bound to the video's real duration: looped music + short hit inputs make
    # -shortest unreliable, so we cut explicitly instead.
    cmd = ["ffmpeg", "-nostdin", "-y"] + inputs + [
        "-filter_complex", fc, "-map", "0:v", "-map", "[mix]",
        "-c:v", "copy", "-c:a", "aac", "-ar", "48000", "-ac", "2", "-b:a", "192k",
        "-t", f"{vdur:.3f}", a.out, "-hide_banner", "-loglevel", "error"]
    subprocess.run(cmd, check=True)
    print(f"sfx mixed ({n_in - 1} layer(s)) -> {a.out}")

if __name__ == "__main__":
    main()

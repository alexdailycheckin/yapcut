#!/usr/bin/env python3
"""Synthesize a royalty-free SFX + music-bed pack with ffmpeg (no downloads, no
licensing, fully CC0 because it is generated tone/noise). Writes 48k stereo WAVs
into assets/sfx/ so sfxmix.py can layer them.

Run once (or after editing):  python3 scripts/gen_sfx.py
Force overwrite:              python3 scripts/gen_sfx.py --force
Pack lives at: <skill>/assets/sfx/
"""
import argparse, math, os, subprocess

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(SKILL, "assets", "sfx")

def ff(src_filter, out, dur, post="", sr=48000):
    """Render an lavfi audio graph to a 48k stereo wav."""
    af = f"{src_filter}" + (f",{post}" if post else "")
    cmd = ["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i", f"{af}",
           "-t", f"{dur}", "-ar", str(sr), "-ac", "2",
           "-c:a", "pcm_s16le", out, "-hide_banner", "-loglevel", "error"]
    subprocess.run(cmd, check=True)

def chirp(f0, f1, T):
    """aevalsrc expression for a linear frequency sweep f0->f1 over T seconds."""
    k = (f1 - f0) / (2.0 * T)
    return f"aevalsrc='sin(2*PI*({f0}*t + {k}*t*t))':d={T}:s=48000"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    os.makedirs(OUT, exist_ok=True)

    def need(name):
        p = os.path.join(OUT, name)
        return p if (a.force or not os.path.exists(p)) else None

    # --- whoosh: shaped noise swell, good on a hard cut / text-hook entrance ---
    if (p := need("whoosh.wav")):
        ff("anoisesrc=d=0.45:c=pink:a=0.7", p, 0.45,
           post="highpass=f=300,lowpass=f=6000,afade=t=in:st=0:d=0.18:curve=ipar,"
                "afade=t=out:st=0.22:d=0.23,volume=0.8")

    # --- impact / boom: low body + transient, lands the hook word ---
    if (p := need("impact.wav")):
        ff("sine=frequency=64:duration=0.4", p, 0.4,
           post="afade=t=out:st=0.04:d=0.34:curve=exp,volume=1.4")

    # --- riser: rising sweep into a turn / reveal (~1.4s) ---
    if (p := need("riser.wav")):
        ff(chirp(180, 1400, 1.4), p, 1.4,
           post="lowpass=f=4000,afade=t=in:st=0:d=1.2,afade=t=out:st=1.25:d=0.15,volume=0.5")

    # --- ding: bright two-tone confirm, for a stat count-up / list item ---
    if (p := need("ding.wav")):
        # mix two sine partials, fast exp decay
        graph = ("sine=frequency=988:duration=0.6[a];"
                 "sine=frequency=1319:duration=0.6[b];"
                 "[a][b]amix=inputs=2,afade=t=out:st=0.05:d=0.55:curve=exp,volume=0.6")
        cmd = ["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i", graph,
               "-t", "0.6", "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le",
               p, "-hide_banner", "-loglevel", "error"]
        subprocess.run(cmd, check=True)

    # --- click / pop: tiny transient for a caption snap / quick beat ---
    if (p := need("click.wav")):
        ff("sine=frequency=1500:duration=0.05", p, 0.05,
           post="afade=t=out:st=0.005:d=0.045:curve=exp,volume=0.5")

    # --- swish (softer, shorter whoosh) for subtle b-roll cuts ---
    if (p := need("swish.wav")):
        ff("anoisesrc=d=0.25:c=white:a=0.5", p, 0.25,
           post="bandpass=f=2500:width_type=h:w=2500,afade=t=in:st=0:d=0.1,"
                "afade=t=out:st=0.12:d=0.13,volume=0.5")

    # --- ambient pad beds (loopable, sit UNDER the VO): two moods ---
    # encoded as AAC m4a (20s stereo) so the pack stays small + committable;
    # one-shots above stay WAV for clean transients.
    if (p := need("bed_calm.m4a")):
        # Cmaj-ish drone: C3 G3 E4 with slow tremolo + echo tail
        graph = ("sine=frequency=130.81:duration=20[a];"
                 "sine=frequency=196.00:duration=20[b];"
                 "sine=frequency=329.63:duration=20[c];"
                 "[a][b][c]amix=inputs=3,"
                 "tremolo=f=0.15:d=0.3,aecho=0.8:0.85:600:0.35,"
                 "lowpass=f=3000,afade=t=in:st=0:d=2,afade=t=out:st=18:d=2,volume=0.5")
        cmd = ["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i", graph,
               "-t", "20", "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "128k",
               p, "-hide_banner", "-loglevel", "error"]
        subprocess.run(cmd, check=True)

    if (p := need("bed_drive.m4a")):
        # darker, more momentum: A2 E3 A3 with faster tremolo pulse
        graph = ("sine=frequency=110.00:duration=20[a];"
                 "sine=frequency=164.81:duration=20[b];"
                 "sine=frequency=220.00:duration=20[c];"
                 "[a][b][c]amix=inputs=3,"
                 "tremolo=f=2.0:d=0.5,aecho=0.8:0.88:330:0.3,"
                 "lowpass=f=2600,afade=t=in:st=0:d=1.5,afade=t=out:st=18:d=2,volume=0.45")
        cmd = ["ffmpeg", "-nostdin", "-y", "-f", "lavfi", "-i", graph,
               "-t", "20", "-ar", "48000", "-ac", "2", "-c:a", "aac", "-b:a", "128k",
               p, "-hide_banner", "-loglevel", "error"]
        subprocess.run(cmd, check=True)

    print("SFX pack ->", OUT)
    for f in sorted(os.listdir(OUT)):
        full = os.path.join(OUT, f)
        d = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration", "-of", "csv=p=0", full],
                           capture_output=True, text=True).stdout.strip()
        print(f"  {f:16s} {d}s")

if __name__ == "__main__":
    main()

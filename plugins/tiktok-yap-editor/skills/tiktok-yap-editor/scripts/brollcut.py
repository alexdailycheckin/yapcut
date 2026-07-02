#!/usr/bin/env python3
"""VO-to-picture assembler (storytelling / day-in-the-life mode). The INVERSE of
yapcut: instead of cutting footage to the words spoken, it locks PICTURE to a
beat script at attention-tuned lengths, so the voiceover can be recorded later
and dropped in (vo_lay.py) in sync.

Each beat plays a chosen clip for a target duration. Output:
  - picture.mp4   : the picture-locked vertical timeline (1080x1920, CFR 30)
  - <out>.timeline.json : per-beat assembled-timeline times (drives the VO guide,
                          captions sync, and sfx hit placement)

Usage:
  brollcut.py --beats beats.json --workdir .yap_build --out .yap_build/picture.mp4

beats.json (ordered):
[
  {"src":"/abs/IMG_1.MOV","start":2.0,"target_dur":2.2,"role":"hook","text":"VO line","push":true},
  {"src":"/abs/IMG_2.MOV","start":11.0,"end":14.0,"role":"beat","text":"next line"},
  {"src":"/abs/IMG_3.MOV","start":0.0,"target_dur":3.0,"role":"button","text":"close","gain_db":-30}
]
- target_dur OR end sets the play length (pacing). Keep hooks short (1.5-2.5s),
  let later beats breathe (3-4s).
- push:true adds a slow 12% push-in for visual life on a near-static shot.
- gain_db trims that clip's natural audio (VO replaces it later; default keep low).
- text is the VO line for that beat; carried into the timeline for the guide.
"""
import argparse, json, os, subprocess

def has_audio(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a",
                        "-show_entries", "stream=index", "-of", "csv=p=0", path],
                       capture_output=True, text=True).stdout.strip()
    return bool(r)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--beats", required=True)
    ap.add_argument("--workdir", default=".yap_build")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--natural-gain", type=float, default=-24.0,
                    help="default trim on each clip's natural audio (VO leads later)")
    a = ap.parse_args()

    wd = a.workdir
    outbase = os.path.splitext(os.path.basename(a.out))[0]
    segdir = f"{wd}/broll_{outbase}"
    os.makedirs(segdir, exist_ok=True)
    beats = json.load(open(a.beats))

    concat = f"{wd}/bconcat_{outbase}.txt"
    open(concat, "w").close()
    timeline = []
    t = 0.0
    for i, b in enumerate(beats):
        src = b["src"]
        s = float(b.get("start", 0.0))
        dur = (float(b["end"]) - s) if "end" in b else float(b.get("target_dur", 3.0))
        e = s + dur
        gain = float(b.get("gain_db", a.natural_gain))
        o = f"{segdir}/bc_{i:03d}.mp4"

        # fill the vertical frame, then (optional) slow push-in for life
        vf = ("scale=1080:1920:force_original_aspect_ratio=increase,"
              "crop=1080:1920,setsar=1,fps=%d" % a.fps)
        if b.get("push"):
            vf += (",zoompan=z='min(1.0+0.0009*on,1.12)':d=1:"
                   "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=%d" % a.fps)

        cmd = ["ffmpeg", "-nostdin", "-y", "-ss", f"{s:.3f}", "-to", f"{e:.3f}",
               "-i", src]
        if has_audio(src):
            af = f"volume={gain}dB"
            cmd += ["-vf", vf, "-af", af]
        else:
            # synth silent track so every segment has identical audio params
            cmd += ["-f", "lavfi", "-t", f"{dur:.3f}",
                    "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                    "-vf", vf, "-map", "0:v", "-map", "1:a"]
        cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-ac", "2",
                "-b:a", "192k", "-video_track_timescale", "30000",
                o, "-hide_banner", "-loglevel", "error"]
        subprocess.run(cmd, check=True)

        # real encoded duration (push/fps rounding can shift it a touch)
        real = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                     "format=duration", "-of", "csv=p=0", o],
                                    capture_output=True, text=True).stdout)
        timeline.append({"idx": i, "role": b.get("role", "beat"),
                         "text": b.get("text", ""), "src": src,
                         "t_start": round(t, 3), "t_end": round(t + real, 3),
                         "dur": round(real, 3)})
        t += real
        open(concat, "a").write(f"file '{os.path.abspath(o)}'\n")

    subprocess.run(["ffmpeg", "-nostdin", "-y", "-f", "concat", "-safe", "0",
                    "-i", concat, "-c", "copy", a.out,
                    "-hide_banner", "-loglevel", "error"], check=True)
    tlpath = f"{wd}/{outbase}.timeline.json"
    json.dump(timeline, open(tlpath, "w"), indent=2)
    print(f"{len(beats)} beats -> {a.out}  ({t:.2f}s)")
    print(f"timeline -> {tlpath}")

if __name__ == "__main__":
    main()

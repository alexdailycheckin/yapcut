#!/usr/bin/env python3
"""Record-to-picture guide. Burns each beat's VO line over the picture-locked
timeline (from brollcut), with a 3s countdown leader, so the creator plays this
back and reads the voiceover IN SYNC. What they record then drops straight onto
picture.mp4 (vo_lay step) because the timing already matches.

Usage:
  vo_guide.py --picture picture.mp4 --timeline picture.timeline.json \
              --out guide.mp4 [--font "Bricolage Grotesque"] [--lead 3.0]
"""
import argparse, json, os, subprocess

def ass_time(x):
    h = int(x // 3600); x -= h * 3600
    m = int(x // 60); s = x - m * 60
    return f"{h:d}:{m:02d}:{s:05.2f}"

def esc(t):
    return t.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", r"\N")

def wrap(t, n=30):
    out, line = [], ""
    for w in t.split():
        if len(line) + len(w) + 1 > n:
            out.append(line); line = w
        else:
            line = (line + " " + w).strip()
    if line: out.append(line)
    return r"\N".join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--picture", required=True)
    ap.add_argument("--timeline", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--font", default="Bricolage Grotesque")
    ap.add_argument("--lead", type=float, default=3.0)
    a = ap.parse_args()

    tl = json.load(open(a.timeline))
    n = len(tl)
    wd = os.path.dirname(os.path.abspath(a.out)) or "."
    ass = os.path.join(wd, "_voguide.ass")

    head = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Read,{a.font},58,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,4,0,5,80,80,0,1
Style: Tag,{a.font},34,&H0000E5FF,&H00000000,&H64000000,1,0,0,0,100,100,2,0,1,3,0,8,60,60,90,1
Style: Idx,{a.font},30,&H00CCCCCC,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,3,0,2,60,60,80,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    ev = []
    L = a.lead
    # countdown leader
    for k, sec in enumerate([3, 2, 1]):
        st, en = k * (L / 3.0), (k + 1) * (L / 3.0)
        ev.append(f"Dialogue: 0,{ass_time(st)},{ass_time(en)},Read,,0,0,0,,"
                  f"{{\\an5\\fs220}}{sec}")
    ev.append(f"Dialogue: 0,{ass_time(0)},{ass_time(L)},Tag,,0,0,0,,GET READY TO READ")
    # per-beat VO lines (offset by leader)
    for b in tl:
        st = ass_time(b["t_start"] + L)
        en = ass_time(b["t_end"] + L)
        txt = wrap(esc(b.get("text", "") or "[no line]"))
        ev.append(f"Dialogue: 0,{st},{en},Read,,0,0,0,,{txt}")
        ev.append(f"Dialogue: 0,{st},{en},Tag,,0,0,0,,{esc(b.get('role','beat')).upper()}")
        ev.append(f"Dialogue: 0,{st},{en},Idx,,0,0,0,,{b['idx']+1}/{n}")
    open(ass, "w").write(head + "\n".join(ev) + "\n")

    # 3s black leader, then the picture; burn the guide .ass over the whole thing
    lead_clip = os.path.join(wd, "_lead.mp4")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-f", "lavfi",
                    "-i", f"color=c=black:s=1080x1920:r=30:d={a.lead}",
                    "-f", "lavfi", "-t", f"{a.lead}",
                    "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "18",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-ac", "2",
                    "-b:a", "192k", "-video_track_timescale", "30000",
                    lead_clip, "-hide_banner", "-loglevel", "error"], check=True)
    cat = os.path.join(wd, "_guidecat.txt")
    with open(cat, "w") as f:
        f.write(f"file '{os.path.abspath(lead_clip)}'\n")
        f.write(f"file '{os.path.abspath(a.picture)}'\n")
    base = os.path.join(wd, "_guidebase.mp4")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-f", "concat", "-safe", "0",
                    "-i", cat, "-c", "copy", base,
                    "-hide_banner", "-loglevel", "error"], check=True)
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-i", base,
                    "-vf", f"ass={ass}", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-pix_fmt", "yuv420p", "-c:a", "copy",
                    a.out, "-hide_banner", "-loglevel", "error"], check=True)
    print(f"guide -> {a.out}  (leader {a.lead}s + {n} beats)")

if __name__ == "__main__":
    main()

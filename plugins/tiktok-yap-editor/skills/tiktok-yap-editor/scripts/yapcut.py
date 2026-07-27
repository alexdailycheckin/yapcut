#!/usr/bin/env python3
"""Single-pass yap cutter: clause selection + dead-air removal + tight tails,
all in ONE clean CFR 30fps encode. Replaces cut.py + auto-editor (whose VFR
output caused 1-frame black flashes at every jump cut).

Cut-placement rules (v2 "perfect cuts" pass, 2026-07-09):
- Only pauses >= --min-gap (0.55) become jump cuts. Shorter pauses are speech
  cadence: cutting them saves ~0.2-0.4s but costs a visible pose-jump + crop
  toggle every couple of seconds (machine-gun cutting).
- No kept segment shorter than --min-seg (0.45): a 4-10 frame segment between
  two cuts reads as a glitch/flash. Sub-min-seg runs are bridged into the
  nearer neighbour (the gap is kept) when that gap is <= --bridge-max (0.75);
  bridge-max is deliberately tight so bridging can never re-include a long
  dead-air pause. A cut that removes < --min-cut (0.25) is not worth its
  visual jump and is merged away (the small gap stays).
- Pauses are detected on a median-smoothed RMS envelope, not an instantaneous
  level gate: a single mouth click inside a 1.5s pause spikes above the
  threshold and splits it into sub-min-gap chunks, hiding real dead air from
  the cutter (found on the Jun 29/Jul 5 batch: a 2s on-screen gap survived).
- The level gate marks "silence" while trailing consonants are still decaying
  below the threshold, so pads are decay-aware: --padr 0.12 / --padl 0.10
  (the old 0.04/0.08 shaved word edges at every cut).
- No transcript-based snapping: whisper -ml 1 -sow DTW tokens tile the whole
  timeline (a token's span runs to the next token's start), so "don't cut
  inside a word" degenerates to "pad every cut". Level-based boundaries with
  the decay pads above were energy-verified to clip nothing audible.

- Segment audio is PCM with 4ms edge fades and the concatenated audio gets ONE
  continuous AAC encode: per-segment AAC + concat -c copy inserted a ~20-40ms
  priming hole at every join, audible as a blip wherever room tone is hot.
- Tight trailing pad (PADR) still removes the look-down-at-script frames.
- Multi-source: each clause carries its own "src", so the shared CTA clip
  can be appended in the same pass for any content clip.
- Per-clause "protect_tail": true keeps a quiet final word (no tail trim).

Usage: yapcut.py --clauses c.json --workdir D --out OUT.mp4
       [--silence-db -42] [--padr 0.12] [--padl 0.10] [--min-gap 0.55]
       [--min-seg 0.45] [--bridge-max 0.75] [--min-cut 0.25] [--d 0.10]
Writes <workdir>/keeps_<out>.json (final cut points) for the QA seam audit.
clauses: [{"src":"/abs.MOV","start":6.5,"end":16.6,"label":"hook",
           "protect_tail":false}, ...]
"""
import argparse, json, math, os, shutil, struct, subprocess, wave as wavmod

def silences(wav, thr, d):
    # Pause detection on a median-smoothed RMS envelope, NOT an instantaneous
    # gate (ffmpeg silencedetect): a single mouth click in a 1.5s pause spikes
    # above the threshold and splits it into sub-min-gap chunks, hiding a real
    # gap from the cutter. 30ms windows / 10ms hop; 5-tap median absorbs clicks.
    w=wavmod.open(wav,"rb"); fr=w.getframerate()
    raw=w.readframes(w.getnframes()); w.close()
    sm=struct.unpack(f"<{len(raw)//2}h",raw)
    win=int(0.030*fr); hop=int(0.010*fr)
    dbs=[]
    for i in range(0,len(sm)-win,hop):
        c=sm[i:i+win]
        r=math.sqrt(sum(x*x for x in c)/len(c))/32768.0
        dbs.append(20*math.log10(r) if r>0 else -99.0)
    sil=[]; st=None
    for i in range(len(dbs)):
        lo=max(0,i-2); hi=min(len(dbs),i+3)
        v=sorted(dbs[lo:hi])[(hi-lo)//2]
        t=i*hop/fr
        if v<thr:
            if st is None: st=t
        elif st is not None:
            if t-st>=d: sil.append((st,t))
            st=None
    t=len(dbs)*hop/fr
    if st is not None and t-st>=d: sil.append((st,t))
    return sil

def estimate_floor(wav):
    # Estimate the room-tone / pause floor of a take as a low percentile of the
    # RMS envelope (same windows as silences()), ignoring digital-silence padding.
    # Used by --auto-floor: on a noisy take the floor sits ABOVE the fixed -42dB
    # gate, so nothing ever reads as silence and no beat gets cut; raising the
    # gate above the measured floor makes the cutter fire on those takes.
    w=wavmod.open(wav,"rb"); fr=w.getframerate()
    raw=w.readframes(w.getnframes()); w.close()
    sm=struct.unpack(f"<{len(raw)//2}h",raw)
    win=int(0.030*fr); hop=int(0.010*fr); dbs=[]
    for i in range(0,len(sm)-win,hop):
        c=sm[i:i+win]
        r=math.sqrt(sum(x*x for x in c)/len(c))/32768.0
        if r>0:
            db=20*math.log10(r)
            if db>-70: dbs.append(db)   # drop digital-silence padding
    if not dbs: return -60.0
    dbs.sort()
    return dbs[int(0.20*len(dbs))]   # 20th percentile ~ the pause floor

def head_onset(wav, seg_start, seg_end, thr, min_sustain=0.15):
    # First time the smoothed RMS sustains above `thr` for >= min_sustain within
    # [seg_start, seg_end]. Used by --head-trim to skip a settling / room-tone
    # lead-in that sits ABOVE the silence gate (so silences() never cut it) but
    # comes before the first real word: whisper front-loads the first token onto
    # it, loudnorm amplifies it, and it reads as "a pause before he says anything".
    w=wavmod.open(wav,"rb"); fr=w.getframerate()
    raw=w.readframes(w.getnframes()); w.close()
    sm=struct.unpack(f"<{len(raw)//2}h",raw)
    win=int(0.030*fr); hop=int(0.010*fr)
    a=max(0,int(seg_start*fr)); b=min(len(sm),int(seg_end*fr))
    need=max(1,int(min_sustain/0.010)); run=0
    for i in range(a,b-win,hop):
        c=sm[i:i+win]
        r=math.sqrt(sum(x*x for x in c)/len(c))/32768.0
        db=20*math.log10(r) if r>0 else -99.0
        if db>=thr:
            run+=1
            if run>=need: return (i-(need-1)*hop)/fr
        else: run=0
    return seg_start

def speech_in(sil, cs, ce):
    pts=[(s,e) for s,e in sil if e>cs and s<ce]; sp=[]; cur=cs
    for s,e in pts:
        s=max(cs,s); e=min(ce,e)
        if s>cur: sp.append((cur,s))
        cur=max(cur,e)
    if cur<ce: sp.append((cur,ce))
    return sp

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--clauses",required=True)
    ap.add_argument("--workdir",default=".yap_build")
    ap.add_argument("--out",required=True)
    ap.add_argument("--silence-db",type=float,default=-42.0)
    ap.add_argument("--padl",type=float,default=0.10)
    ap.add_argument("--padr",type=float,default=0.12)
    ap.add_argument("--min-gap",type=float,default=0.55)
    ap.add_argument("--min-seg",type=float,default=0.45)
    ap.add_argument("--bridge-max",type=float,default=0.75)
    ap.add_argument("--d",type=float,default=0.10)
    ap.add_argument("--min-keep",type=float,default=0.10)
    ap.add_argument("--min-cut",type=float,default=0.25)
    ap.add_argument("--auto-floor",action="store_true",
        help="measure each take's noise floor and raise the silence gate above "
             "it (needed for noisy/teleprompter takes where the room tone sits "
             "above the fixed gate, so no beat ever gets cut). Never lowers the "
             "gate below --silence-db, and is capped so it cannot eat speech.")
    ap.add_argument("--floor-margin",type=float,default=2.0,
        help="dB above the measured floor to set the gate when --auto-floor "
             "(2.0 reproduces the hand-tuned gate that shipped the arc take)")
    ap.add_argument("--head-trim",action="store_true",
        help="drop a settling/room-tone lead-in before the first spoken word "
             "(first clause only). Only trims a 0.3-2.5s lead so it never eats a "
             "genuinely quick start; needs the floor (implies auto-floor's estimate).")
    ap.add_argument("--head-margin",type=float,default=8.0,
        help="dB above the measured floor that counts as confident speech for --head-trim")
    a=ap.parse_args()

    wd=a.workdir; os.makedirs(f"{wd}/audio",exist_ok=True)
    outbase=os.path.splitext(os.path.basename(a.out))[0]   # parallel-safe scratch
    segdir=f"{wd}/segs_{outbase}"; os.makedirs(segdir,exist_ok=True)
    clauses=json.load(open(a.clauses))
    srcs={c["src"] for c in clauses}

    SIL={}; FLOOR={}; WAVP={}
    for src in srcs:
        wav=f"{wd}/audio/{os.path.splitext(os.path.basename(src))[0]}.wav"
        if not os.path.exists(wav):
            subprocess.run(["ffmpeg","-nostdin","-y","-i",src,"-ar","16000","-ac","1",
                wav,"-hide_banner","-loglevel","error"],check=True)
        WAVP[src]=wav
        fl=estimate_floor(wav) if (a.auto_floor or a.head_trim) else None
        FLOOR[src]=fl
        thr=a.silence_db
        if a.auto_floor and fl is not None:
            thr=min(-22.0, max(a.silence_db, fl+a.floor_margin))   # never below default, capped so it can't eat speech
            print(f"auto-floor: {os.path.basename(src)} floor ~{fl:.1f}dB -> silence gate {thr:.1f}dB")
        SIL[src]=silences(wav,thr,a.d)

    keeps=[]   # (src, a, b, gain_db)
    for ci,c in enumerate(clauses):
        src,cs,ce=c["src"],float(c["start"]),float(c["end"])
        protect=bool(c.get("protect_tail",False))
        g=float(c.get("gain_db",0))
        if c.get("keep_whole",False):        # no silence processing; keep as-is
            keeps.append((src,max(0,cs-a.padl),ce,g)); continue
        sp=speech_in(SIL[src],cs,ce)
        if not sp:
            keeps.append((src,max(0,cs-a.padl),ce,g)); continue
        # merge runs separated by < min-gap (keep natural cadence pauses)
        runs=[]; s0,e0=sp[0]
        for s,e in sp[1:]:
            if s-e0>a.min_gap: runs.append((s0,e0)); s0=s
            e0=e
        runs.append((s0,e0))
        # head-trim: on the very first clause, drop a settling/room-tone lead-in
        # that sits above the silence gate but before the first real word.
        if a.head_trim and ci==0 and runs and FLOOR.get(src) is not None:
            onset=head_onset(WAVP[src], runs[0][0], runs[0][1], FLOOR[src]+a.head_margin)
            drop=onset-runs[0][0]
            if 0.3<drop<2.5:
                print(f"head-trim: dropped {drop:.2f}s settling lead-in before first word")
                runs[0]=(onset,runs[0][1])
        # bridge glitch-length runs into the nearer neighbour (gap kept):
        # a < min-seg segment between two jump cuts reads as a flash frame.
        changed=True
        while changed and len(runs)>1:
            changed=False
            for i,(s,e) in enumerate(runs):
                if e-s>=a.min_seg: continue
                gl=s-runs[i-1][1] if i>0 else None
                gr=runs[i+1][0]-e if i<len(runs)-1 else None
                if gl is not None and gl<=a.bridge_max and (gr is None or gl<=gr):
                    runs[i-1]=(runs[i-1][0],e)
                elif gr is not None and gr<=a.bridge_max:
                    runs[i+1]=(s,runs[i+1][1])
                else: continue
                del runs[i]; changed=True; break
        for i,(s,e) in enumerate(runs):
            A=max(cs,s-a.padl)
            last = (i==len(runs)-1)
            if last and protect:
                B=ce                          # keep quiet trailing word
            else:
                B=min(ce, e+a.padr)           # tight tail -> no look-down
            keeps.append((src,A,B,g))
    # a cut that removes < min-cut is not worth its visual jump: merge that
    # join away (the tiny gap stays). Forward-adjacent only (prevB-A <= 1.0),
    # so a reordered clause that jumps BACK in the source is never swallowed.
    merged=[]
    for src,A,B,g in keeps:
        if merged and merged[-1][0]==src and merged[-1][3]==g \
           and A<=merged[-1][2]+a.min_cut and merged[-1][2]-A<=1.0:
            if B>merged[-1][2]: merged[-1]=(src,merged[-1][1],B,g)
            continue
        merged.append((src,A,B,g))
    keeps=[(s,A,B,g) for s,A,B,g in merged if B-A>=a.min_keep]
    with open(f"{wd}/keeps_{outbase}.json","w") as f:   # QA: real cut points
        json.dump([{"src":s,"a":round(A,3),"b":round(B,3)} for s,A,B,g in keeps],f,indent=1)

    concat_v=f"{wd}/concat_{outbase}.txt"; open(concat_v,"w").close()
    concat_a=f"{wd}/concata_{outbase}.txt"; open(concat_a,"w").close()
    # alternating STATIC crop (hard cut, no animation) masks pose-match jump-cut
    # stutter: every consecutive segment toggles scale so a cut always changes framing.
    ALT=[1.00,1.06]
    # DRIFT GUARD: the fps=30 filter emits floor(dur*30)+1 frames per segment
    # (+0.5 frame per cut on average) while the PCM audio is cut sample-exact,
    # so the picture gains ~16ms on the voice AT EVERY JOIN (measured +0.25-0.77s
    # by the end on the Jul 12 / Jul 26 batches). setpts renumbering later cannot
    # remove real excess frames. Fix: pace every segment's frame count against
    # the CUMULATIVE audio clock - segment i must end video at round(T_audio*30)
    # total frames - so per-join error is bounded at half a frame forever and
    # can never accumulate. tpad clones headroom frames; -frames:v cuts exact.
    #
    # Video and audio are cut to SEPARATE per-segment files and concatenated as
    # separate streams: in a muxed segment concat the demuxer offsets each next
    # segment by ONE stream's duration, so whenever a paced video track ran
    # shorter than its audio the join CLIPPED audio (measured -0.116s / 19
    # segments). Separate concats keep video = sum(nfr) and audio sample-exact.
    t_audio=0.0; f_video=0
    for i,(src,s,e,gain) in enumerate(keeps):
        ov=f"{segdir}/yc_{i:03d}.mov"; oa=f"{segdir}/ya_{i:03d}.wav"
        # PCM segment audio + 4ms edge fades: per-segment AAC concatenated with
        # -c copy inserts a ~20-40ms priming hole (audible blip) at every join,
        # and un-faded splices leave step clicks. PCM has no priming; the audio
        # gets ONE continuous AAC encode after the concat.
        dur=e-s
        t_audio+=dur
        nfr=max(1,round(t_audio*30)-f_video)   # frames this segment owes the grid
        f_video+=nfr
        af=((f"volume={gain}dB," if gain else "")
            +f"afade=t=in:st=0:d=0.004,afade=t=out:st={max(0.0,dur-0.004):.4f}:d=0.004")
        z=ALT[i%len(ALT)]; W=round(1080*z); H=round(1920*z)
        if W%2: W+=1
        if H%2: H+=1
        vf=(f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,setsar=1,fps=30,"
            f"tpad=stop_mode=clone:stop_duration=0.3")
        # -ss/-to (not -t): input -t measures from the packet where reading
        # starts, not from the seek point, and shaves ~5-10ms of AUDIO per
        # segment. -to is sample-exact.
        subprocess.run(["ffmpeg","-nostdin","-y","-ss",f"{s:.3f}","-to",f"{e:.3f}",
            "-i",src,
            "-map","0:v","-vf",vf,"-frames:v",str(nfr),
            "-c:v","libx264","-preset","veryfast","-crf","18","-pix_fmt","yuv420p",
            "-video_track_timescale","30000","-an",ov,
            "-map","0:a","-af",af,"-c:a","pcm_s16le","-ar","48000","-ac","2","-vn",oa,
            "-hide_banner","-loglevel","error"],check=True)
        open(concat_v,"a").write(f"file '{os.path.abspath(ov)}'\n")
        open(concat_a,"a").write(f"file '{os.path.abspath(oa)}'\n")

    tmpv=f"{wd}/cc_{outbase}.mov"; tmpa=f"{wd}/cc_{outbase}.wav"
    subprocess.run(["ffmpeg","-nostdin","-y","-f","concat","-safe","0","-i",concat_v,
        "-c","copy",tmpv,"-hide_banner","-loglevel","error"],check=True)
    subprocess.run(["ffmpeg","-nostdin","-y","-f","concat","-safe","0","-i",concat_a,
        "-c","copy",tmpa,"-hide_banner","-loglevel","error"],check=True)
    # The concat demuxer + -c copy leaves a small timestamp gap at every segment
    # join; renumber the video onto a gapless 30fps grid (setpts=N/(30*TB)) so
    # every frame lands at frame#/30 and locks to the gapless PCM->AAC audio.
    # Never -c:v copy here.
    subprocess.run(["ffmpeg","-nostdin","-y","-i",tmpv,"-i",tmpa,
        "-map","0:v","-map","1:a",
        "-vf","setpts=N/(30*TB),setsar=1","-r","30","-vsync","cfr",
        "-video_track_timescale","30000",
        "-c:v","libx264","-preset","veryfast","-crf","18","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","192k",a.out,"-hide_banner","-loglevel","error"],check=True)
    os.remove(tmpv); os.remove(tmpa)
    shutil.rmtree(segdir,ignore_errors=True)   # segments are spent once concatenated
    dur=float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration",
        "-of","csv=p=0",a.out],capture_output=True,text=True).stdout)
    # DRIFT GATE: video and audio stream lengths must match. Any excess picture
    # means the per-segment frame pacing failed and lips will slide off the voice.
    sd={}
    for ln in subprocess.run(["ffprobe","-v","error","-show_entries",
            "stream=codec_type,duration","-of","csv=p=0",a.out],
            capture_output=True,text=True).stdout.strip().splitlines():
        typ,d=ln.split(",")[0],ln.split(",")[1]
        sd[typ]=float(d)
    drift=sd.get("video",0)-sd.get("audio",0)
    print(f"{len(keeps)} segments -> {a.out}  ({dur:.2f}s, video-audio drift {drift:+.3f}s)")
    if abs(drift)>0.067:   # 2 frames; AAC edge padding accounts for < 1
        raise SystemExit(f"DRIFT GATE FAILED: picture is {drift:+.3f}s vs voice "
            f"(limit 0.067s). Do not ship; the cut stage is broken.")

if __name__=="__main__":
    main()

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
import argparse, json, math, os, shutil, struct, subprocess, sys, wave as wavmod

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import media  # noqa: E402

HOP=0.010   # envelope hop, seconds

def envelope(wav):
    # Median-smoothed RMS envelope in dB: 30ms windows, 10ms hop, 5-tap median.
    # Computed ONCE per source and reused by silences(), estimate_floor(),
    # head_onset() and audible_edge() - they all want the same series, and this
    # per-sample loop is the expensive part of a cut.
    w=wavmod.open(wav,"rb"); fr=w.getframerate()
    raw=w.readframes(w.getnframes()); w.close()
    sm=struct.unpack(f"<{len(raw)//2}h",raw)
    win=int(0.030*fr); hop=int(HOP*fr)
    raw_db=[]
    for i in range(0,len(sm)-win,hop):
        c=sm[i:i+win]
        r=math.sqrt(sum(x*x for x in c)/len(c))/32768.0
        raw_db.append(20*math.log10(r) if r>0 else -99.0)
    n=len(raw_db)
    return [sorted(raw_db[max(0,i-2):min(n,i+3)])[(min(n,i+3)-max(0,i-2))//2]
            for i in range(n)]

def silences(dbs, thr, d):
    # Pause detection on the median-smoothed envelope, NOT an instantaneous gate
    # (ffmpeg silencedetect): a single mouth click inside a 1.5s pause spikes
    # above the threshold and splits it into sub-min-gap chunks, hiding real dead
    # air from the cutter (Jun 29/Jul 5 batch: a 2s on-screen gap survived).
    sil=[]; st=None
    for i,v in enumerate(dbs):
        t=i*HOP
        if v<thr:
            if st is None: st=t
        elif st is not None:
            if t-st>=d: sil.append((st,t))
            st=None
    t=len(dbs)*HOP
    if st is not None and t-st>=d: sil.append((st,t))
    return sil

def estimate_floor(dbs):
    # Room-tone / pause floor of a take: a low percentile of the envelope,
    # ignoring digital-silence padding. Used by --auto-floor (on a noisy take the
    # floor sits ABOVE the fixed -42dB gate, so nothing ever reads as silence and
    # no beat gets cut) and by audible_edge() as the "still audible" reference.
    vals=sorted(db for db in dbs if db>-70)
    if not vals: return -60.0
    return vals[int(0.20*len(vals))]   # 20th percentile ~ the pause floor

def audible_edge(dbs, t, direction, thr, max_travel, stop_at=None, gap_tol=0.09):
    """Walk the envelope from `t` in `direction` (+1 forward, -1 back) and return
    where the sound genuinely stops or starts, tolerating a stop consonant's
    silent closure on the way.

    Why this exists (2026-08-27, after the creator flagged clipped words that "only
    happen on some words"): the speech gate is a LEVEL gate, so it fires while a
    word is still clearly audible whenever that word ends in a low-energy
    phoneme. Measured over the 08-24 batch, 5 of 78 joins cut into a live tail by
    up to 0.19s and EVERY one was a word ending in an unvoiced stop or a nasal:
    "landlord", "them", "it", "entertainment", "headcount". Words ending in a
    vowel or a voiced consonant never clipped, which is exactly why the defect
    looked random. A fixed trailing pad cannot fix it, because the pad a word
    needs depends on how its own last phoneme decays, so measure it per boundary.

    `thr` sits near the take's floor, well BELOW the speech gate, so the walk
    follows the decay itself instead of the gate crossing. `max_travel` caps it
    so it can never re-include dead air, and `stop_at` keeps it out of the
    neighbouring speech run.

    `gap_tol` is what makes this work on the words that actually broke. A stop
    consonant is a SILENT CLOSURE followed by a release burst, so "landlord",
    "it" and "headcount" go quiet mid-phoneme and come back. A walk that halts
    at the first sub-threshold sample stops inside the closure and still clips
    the release, which is why the first pass at this fix moved nothing on the
    CBRE joins. Bridging up to ~90ms of silence (a typical closure) reaches the
    burst. It cannot run into the next word: runs are already merged at
    --min-gap 0.55s, so the nearest speech is further away than max_travel.
    """
    n=len(dbs)
    if n==0: return t
    j=int(round(t/HOP))
    if j<0 or j>=n: return t
    limit=None if stop_at is None else int(round(stop_at/HOP))
    tol=max(1,int(gap_tol/HOP))
    last_good=j; quiet=0; k=j
    for _ in range(max(0,int(max_travel/HOP))):
        k+=direction
        if k<0 or k>=n: break
        if limit is not None and ((direction>0 and k>=limit) or (direction<0 and k<=limit)):
            break
        if dbs[k]>thr:
            last_good=k; quiet=0
        else:
            quiet+=1
            if quiet>tol: break
    return last_good*HOP

def head_onset(dbs, seg_start, seg_end, thr, min_sustain=0.15):
    # First time the envelope sustains above `thr` for >= min_sustain within
    # [seg_start, seg_end]. Used by --head-trim to skip a settling / room-tone
    # lead-in that sits ABOVE the silence gate (so silences() never cut it) but
    # comes before the first real word: whisper front-loads the first token onto
    # it, loudnorm amplifies it, and it reads as "a pause before he says anything".
    a=max(0,int(seg_start/HOP)); b=min(len(dbs),int(seg_end/HOP))
    need=max(1,int(min_sustain/HOP)); run=0
    for i in range(a,b):
        if dbs[i]>=thr:
            run+=1
            if run>=need: return (i-(need-1))*HOP
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
    ap.add_argument("--edge-margin",type=float,default=6.0,
        help="dB above the measured floor that still counts as AUDIBLE when "
             "placing a boundary. Sits well below the speech gate on purpose: it "
             "tracks a word's decay, not the gate crossing, so a tail ending in "
             "an unvoiced stop or nasal is not cut off mid-phoneme.")
    ap.add_argument("--tail-extra",type=float,default=0.25,
        help="how far past --padr the decay search may travel to find a word's "
             "real end (cap; it also stops at the next speech run)")
    ap.add_argument("--grade",default="",
        help="ffmpeg filter string applied INSIDE the segment pass, e.g. "
             "'eq=brightness=0.05:contrast=1.1:saturation=1.06'. Use this rather "
             "than grading the finished cut: a separate pass is an extra full "
             "lossy generation, and raising contrast on an already-compressed "
             "encode amplifies its artefacts.")
    ap.add_argument("--lead",type=float,default=0.03,
        help="silence kept outside a measured boundary. Small on purpose: the "
             "onset is measured, so the old fixed 0.10s lead-in was audible as "
             "the next word coming in late at every join.")
    a=ap.parse_args()

    wd=a.workdir; os.makedirs(f"{wd}/audio",exist_ok=True)
    outbase=os.path.splitext(os.path.basename(a.out))[0]   # parallel-safe scratch
    segdir=f"{wd}/segs_{outbase}"; os.makedirs(segdir,exist_ok=True)
    clauses=json.load(open(a.clauses))
    srcs={c["src"] for c in clauses}

    SIL={}; FLOOR={}; WAVP={}; ENV={}
    for src in srcs:
        wav=f"{wd}/audio/{os.path.splitext(os.path.basename(src))[0]}.wav"
        if not os.path.exists(wav):
            subprocess.run(["ffmpeg","-nostdin","-y","-i",src,"-ar","16000","-ac","1",
                wav,"-hide_banner","-loglevel","error"],check=True)
        WAVP[src]=wav
        ENV[src]=envelope(wav)
        fl=estimate_floor(ENV[src])
        FLOOR[src]=fl
        thr=a.silence_db
        if a.auto_floor:
            thr=min(-22.0, max(a.silence_db, fl+a.floor_margin))   # never below default, capped so it can't eat speech
            print(f"auto-floor: {os.path.basename(src)} floor ~{fl:.1f}dB -> silence gate {thr:.1f}dB")
        SIL[src]=silences(ENV[src],thr,a.d)

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
            onset=head_onset(ENV[src], runs[0][0], runs[0][1], FLOOR[src]+a.head_margin)
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
        # Decay-aware boundaries (2026-08-27). The level gate marks a run's edges
        # where the ENERGY crossed, not where the WORD did, so a fixed pad is
        # wrong in both directions and wrong by a different amount per word:
        #  - tails ending in an unvoiced stop or nasal stay audible past the
        #    gate, and padr clipped them (measured: up to 0.19s, on "landlord",
        #    "them", "it", "entertainment", "headcount");
        #  - crisp onsets don't need padl at all, and pasting a fixed 0.10s of
        #    room tone in front of every run is the late-sounding next word.
        # So: measure each edge against a threshold near the floor, and keep the
        # pads as CAPS on how far that search may travel. e+padr stays a floor on
        # the tail, so this can never trim tighter than the old behaviour did.
        env=ENV[src]; fl=FLOOR.get(src)
        edge_thr=(fl+a.edge_margin) if fl is not None else (a.silence_db-6.0)
        for i,(s,e) in enumerate(runs):
            prev_end=runs[i-1][1] if i>0 else None
            next_start=runs[i+1][0] if i<len(runs)-1 else None
            onset=audible_edge(env,s,-1,edge_thr,a.padl,stop_at=prev_end)
            A=max(cs, onset-a.lead)
            last = (i==len(runs)-1)
            if last and protect:
                B=ce                          # keep quiet trailing word
            else:
                tail=audible_edge(env,e,+1,edge_thr,a.padr+a.tail_extra,stop_at=next_start)
                B=min(ce, max(e+a.padr, tail+a.lead))
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
        z=ALT[i%len(ALT)]; W=round(media.W*z); H=round(media.H*z)
        if W%2: W+=1
        if H%2: H+=1
        # --grade rides HERE, inside the segment pass, so a brightness lift costs
        # ZERO extra generations. Grading the finished cut as a separate ffmpeg
        # run (what the 08-24 batch did to popmart and mrbeast) is a whole extra
        # lossy encode of the entire video on top of an already 3-generation
        # chain, and those were the two files the creator called low quality.
        grade=(a.grade+",") if a.grade else ""
        vf=(f"scale={W}:{H}:force_original_aspect_ratio=increase,"
            f"crop={media.W}:{media.H},setsar=1,{grade}fps=30,"
            f"tpad=stop_mode=clone:stop_duration=0.3")
        # -ss/-to (not -t): input -t measures from the packet where reading
        # starts, not from the seek point, and shaves ~5-10ms of AUDIO per
        # segment. -to is sample-exact.
        subprocess.run(["ffmpeg","-nostdin","-y","-ss",f"{s:.3f}","-to",f"{e:.3f}",
            "-i",src,
            "-map","0:v","-vf",vf,"-frames:v",str(nfr),
            # Segments are throwaway intermediates that get re-encoded at the
            # concat, so crf 12 here is effectively transparent and stops the
            # first generation eating detail the later ones can never restore.
            "-c:v","libx264","-preset","veryfast","-crf","12","-pix_fmt","yuv420p",
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
        "-c:v","libx264","-preset","medium","-crf","16","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","192k",a.out,"-hide_banner","-loglevel","error"],check=True)
    os.remove(tmpv); os.remove(tmpa)
    shutil.rmtree(segdir,ignore_errors=True)   # segments are spent once concatenated
    # probes go through yaplib.media: a failed ffprobe raises with its own
    # stderr instead of turning into float('') on the next line.
    dur=media.probe_duration(a.out)
    # DRIFT GATE: video and audio stream lengths must match. Any excess picture
    # means the per-segment frame pacing failed and lips will slide off the voice.
    drift=media.drift(a.out)
    print(f"{len(keeps)} segments -> {a.out}  ({dur:.2f}s, video-audio drift {drift:+.3f}s)")
    if abs(drift)>media.DRIFT_LIMIT_CUT:   # 2 frames; AAC edge padding accounts for < 1
        print(f"DRIFT GATE FAILED: picture is {drift:+.3f}s vs voice "
              f"(limit {media.DRIFT_LIMIT_CUT:.3f}s). Do not ship; the cut stage is broken.")
        sys.exit(2)

if __name__=="__main__":
    main()

#!/usr/bin/env python3
"""Seam QA: probe the audio around every cut join for the artifacts that ship
silently: digital holes (dropouts) and step clicks. Run it on the CUT or the
FINAL against the keeps json yapcut writes.

A hole is a >=15ms stretch near-silent (<= --hole-db) while the surrounding
0.3s carries real level (>= hole-db + 22dB): room tone does not drop to digital
zero by itself, a bad splice does.

Usage: seam_qa.py --keeps .yap_build/keeps_full_x.json --video final.mp4
Exit 2 if any join fails (Contract 1: 2 = FAIL), so gates.sh can fail the build;
0 when every join is clean.
"""
import argparse, json, math, os, struct, sys, tempfile, wave

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import media  # noqa: E402

def load_pcm(video):
    tmp=tempfile.NamedTemporaryFile(suffix=".wav",delete=False)
    tmp.close()
    media.ffmpeg(["-i",video,"-ar","48000","-ac","1","-c:a","pcm_s16le",tmp.name],
                 what="ffmpeg pcm extract")
    w=wave.open(tmp.name,"rb"); fr=w.getframerate()
    sm=struct.unpack(f"<{w.getnframes()}h",w.readframes(w.getnframes()))
    w.close(); os.unlink(tmp.name)
    return sm,fr

def win_dbs(sm,fr,t0,t1,win=0.015):
    a=max(0,int(t0*fr)); b=min(len(sm),int(t1*fr)); step=max(1,int(win*fr))
    out=[]
    for i in range(a,b-step,step):
        c=sm[i:i+step]
        r=math.sqrt(sum(x*x for x in c)/len(c))/32768.0
        out.append(20*math.log10(r) if r>0 else -99.0)
    return out

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--keeps",required=True)
    ap.add_argument("--video",required=True)
    ap.add_argument("--hole-db",type=float,default=-65.0)
    ap.add_argument("--span",type=float,default=0.30)
    a=ap.parse_args()
    keeps=json.load(open(a.keeps))
    joins=[]; t=0.0
    for k in keeps[:-1]:
        t+=k["b"]-k["a"]; joins.append(t)
    sm,fr=load_pcm(a.video)
    bad=0
    for j,t in enumerate(joins):
        dbs=win_dbs(sm,fr,t-a.span,t+a.span)
        if not dbs: continue
        lo,hi=min(dbs),max(dbs)
        hole=lo<=a.hole_db and hi>=a.hole_db+22
        flag="HOLE" if hole else "ok"
        if hole: bad+=1
        print(f"join{j} @{t:7.2f}s  floor {lo:6.1f} dB / peak {hi:6.1f} dB  {flag}")
    print(f"{len(joins)} joins, {bad} with splice holes")
    sys.exit(2 if bad else 0)

if __name__=="__main__":
    main()

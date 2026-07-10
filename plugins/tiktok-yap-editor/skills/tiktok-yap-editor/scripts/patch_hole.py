#!/usr/bin/env python3
"""Surgically fill a splice hole (digital-silence dropout) in a video's audio
with adjacent room tone. Video stream untouched. Usage: patch_hole.py in.mp4 t_join"""
import struct, subprocess, sys, wave, math, os
src, tj = sys.argv[1], float(sys.argv[2])
wav = src + ".patch.wav"
subprocess.run(["ffmpeg","-nostdin","-y","-i",src,"-ar","48000","-ac","2","-c:a","pcm_s16le",wav,"-hide_banner","-loglevel","error"],check=True)
w=wave.open(wav,"rb"); fr=w.getframerate(); nch=w.getnchannels()
frames=bytearray(w.readframes(w.getnframes())); w.close()
n=len(frames)//(2*nch)
def rms_db(i0,i1):
    tot=0; cnt=0
    for i in range(i0,i1):
        for c in range(nch):
            v=struct.unpack_from("<h",frames,(i*nch+c)*2)[0]; tot+=v*v; cnt+=1
    r=math.sqrt(tot/max(1,cnt))/32768.0
    return 20*math.log10(r) if r>0 else -99
win=int(0.010*fr)
lo,hi=max(0,int((tj-0.35)*fr)),min(n-win-1,int((tj+0.35)*fr))
holes=[i for i in range(lo,hi-win,win) if rms_db(i,i+win)<=-65]
if not holes:
    print("no hole found"); sys.exit(1)
h0,h1=holes[0],holes[-1]+win
pad=int(0.004*fr)
h0-=pad; h1+=pad
dur=h1-h0
donor0=h0-dur-int(0.02*fr)
print(f"hole {h0/fr:.3f}-{h1/fr:.3f}s ({1000*dur/fr:.0f}ms), donor at {donor0/fr:.3f}s")
for i in range(dur):
    for c in range(nch):
        v=struct.unpack_from("<h",frames,((donor0+i)*nch+c)*2)[0]
        # fade the donor edges in/out over 4ms
        f=min(1.0,i/pad if pad else 1.0,(dur-i)/pad if pad else 1.0)
        old=struct.unpack_from("<h",frames,((h0+i)*nch+c)*2)[0]
        struct.pack_into("<h",frames,((h0+i)*nch+c)*2,int(v*f+old*(1-f)))
w=wave.open(wav,"wb"); w.setnchannels(nch); w.setsampwidth(2); w.setframerate(fr)
w.writeframes(bytes(frames)); w.close()
out=src+".patched.mp4"
subprocess.run(["ffmpeg","-nostdin","-y","-i",src,"-i",wav,"-map","0:v","-map","1:a","-c:v","copy","-c:a","aac","-b:a","192k",out,"-hide_banner","-loglevel","error"],check=True)
os.replace(out,src); os.remove(wav)
print(f"patched in place: {src}")

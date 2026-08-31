#!/usr/bin/env python3
"""segment_corpus.py: split the voice corpus by REGISTER and MODE, and emit the one that matters.

WHY. Targets derived from voice-corpus/corpus.txt as a single pool are wrong in a way that
shapes every batch, and in the reference deployment it went unnoticed for weeks. The pool is not
one voice:

    calls, spoken banter      3553w   median  7   mean 11.0   like 48.4/1k
    capture, spoken on work    737w   median 17   mean 19.1   like 35.3/1k
    capture, TYPED on work     437w   median 19   mean 22.1   like  2.3/1k   <- not speech

In the reference deployment 76% of the pool was a casual video call about hobbies. A third of the
work material was typed, not spoken, and its "like" rate of 2.3 per 1000 words against
35.3 for speech proves the two cannot be pooled. The show is a performed
monologue about companies, so the ONLY on-target material is the middle row.

The consequence was concrete: pooled targets said median 8 / mean 12.5, so check_fidelity's
band of "mean 9 to 13" looked confirmed. His work speech runs mean 19.1. The gate had been
requiring sentences about half the length of how the creator actually talks about their subject, and every
batch was written to it.

Teleprompter reads stay excluded (an audit found 71/71 were the creator reading the
AI's own scripts back, so measuring them measures the AI). That exclusion is correct and it is
also why the on-target corpus is thin: it removed the only performed-monologue source.
The fix is supply, not arithmetic.

    python3 scripts/segment_corpus.py
"""
import glob, json, os, pathlib, re, statistics, sys

from voice_home import radar_home as home

H = home()

def clean(t):
    t = re.sub(r'^#.*$', '', t, flags=re.M)
    t = re.sub(r'^mode:.*$', '', t, flags=re.M)
    t = re.sub(r'^_.*_$', '', t, flags=re.M)
    t = re.sub(r'^\s*-\s*', '', t, flags=re.M)
    return re.sub(r'\n{2,}', '\n', t).strip()

buckets = {"work-spoken": [], "work-typed": [], "banter-spoken": []}

for f in sorted(glob.glob(str(H / "capture" / "*.md"))):
    raw = open(f).read()
    m = re.search(r'mode: *(\w+)', raw)
    mode = m.group(1) if m else "unknown"
    key = "work-typed" if mode == "typed" else "work-spoken"
    buckets[key].append((os.path.basename(f), clean(raw)))

for f in sorted(glob.glob(str(H / "voice-corpus" / "granola" / "*.md"))):
    raw = open(f).read()
    # a granola call is banter unless its own header says otherwise
    buckets["banter-spoken"].append((os.path.basename(f), clean(raw)))

for f in sorted(glob.glob(str(H / "voice-corpus" / "manual" / "*.md"))):
    buckets["work-spoken"].append((os.path.basename(f), clean(open(f).read())))

def stats(text):
    S = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text.replace('\n', ' ')) if s.strip()]
    if len(S) < 5:
        return None
    wc = sorted(len(s.split()) for s in S)
    W = len(re.findall(r"[A-Za-z']+", text))
    return {"words": W, "sentences": len(S), "median": statistics.median(wc),
            "mean": round(statistics.mean(wc), 1), "max": max(wc)}

out = {}
for k, files in buckets.items():
    text = "\n".join(t for _, t in files)
    p = H / "voice-corpus" / f"corpus-{k}.txt"
    p.write_text(text + "\n", encoding="utf-8")
    st = stats(text)
    out[k] = {"files": [n for n, _ in files], **(st or {"words": len(text.split())})}
    tag = "  <- THE TARGET REGISTER" if k == "work-spoken" else ""
    print(f"{k:<15} {out[k].get('words',0):>5}w  " +
          (f"median {st['median']:>3.0f} mean {st['mean']:>5.1f} max {st['max']:>3}" if st else "too thin") + tag)

(H / "voice-corpus" / "segments.json").write_text(json.dumps(out, indent=2) + "\n")
print(f"\nwrote corpus-work-spoken.txt, corpus-work-typed.txt, corpus-banter-spoken.txt, segments.json")
print("\nTHE TARGET CORPUS IS THIN. Everything downstream is capped by it: derive targets from")
print("737 words and they are provisional. 20-30 minutes of unscripted teardown talk would")
print("take it past 4000 and make the whole stack trustworthy.")

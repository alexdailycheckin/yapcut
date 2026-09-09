#!/usr/bin/env python3
"""Re-anchor an overlays JSON from an OLD cut's timeline onto a NEW cut's timeline
by spoken-word index. When a clip is re-cut (pauses / lead-in removed) the word
SEQUENCE is unchanged, so each overlay's anchor word keeps its index; only its
wall-clock time moves. For each overlay we find the nearest old token to its
start, keep the small lead offset, and place it at that token's NEW time,
preserving duration. Lets you reuse hand-placed receipts across a re-cut instead
of re-timing them by hand.

Usage: reanchor_overlays.py --old-overlays X_overlays.json --old-words w_old.json \
         --new-words w_new.json --out X_new_overlays.json [--strip-y]
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import words as ywords  # noqa: E402

def toks(p):
    return [s for s, _e, _t in ywords.load_words(p)]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old-overlays", required=True)
    ap.add_argument("--old-words", required=True)
    ap.add_argument("--new-words", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--strip-y", action="store_true",
                    help="drop per-overlay y so the hard-coded standard positions apply")
    a = ap.parse_args()
    ov = json.load(open(a.old_overlays))
    old, new = toks(a.old_words), toks(a.new_words)
    n = min(len(old), len(new))
    if len(old) != len(new):
        print(f"reanchor: WARNING token count old={len(old)} new={len(new)}; "
              f"mapping against first {n} (verify receipts land right)")
    out = []
    for o in ov:
        s = float(o["start"]); dur = float(o["end"]) - s
        i = min(range(n), key=lambda k: abs(old[k] - s))   # nearest old token
        ns = max(0.0, round(new[i] + (s - old[i]), 2))      # keep lead offset
        no = dict(o); no["start"] = ns; no["end"] = round(ns + dur, 2)
        if a.strip_y and "y" in no:
            del no["y"]
        out.append(no)
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"reanchor: {len(out)} overlays -> {a.out}")

if __name__ == "__main__":
    main()

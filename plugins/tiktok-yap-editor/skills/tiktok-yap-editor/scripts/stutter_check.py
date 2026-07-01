#!/usr/bin/env python3
"""Catch stutters and restarts in a yap take so they never ship.

Alex kept hitting the same defect: a take where he says a word twice ("the
the"), restarts a clause ("you're not bad at this ... you're not bad at this"),
or the source has a triple restart ("now use AI, now use AI, now use AI in
their buying process"). These were caught BY HAND, clip by clip. This makes it
automatic: run it on the word-level transcript and it reports every stutter
with timestamps, plus a ready-to-use caption drop-list and video cut-ranges.

Input is the SAME whisper JSON build_ass.py eats: whisper-cli -oj -ml 1 -sow
-dtw  ->  {"transcription":[{"offsets":{"from":ms,"to":ms},"text":"..."}]}.
Word indices match build_ass.py exactly (non-empty words only), so the emitted
{"drop":[...]} feeds straight into build_ass.py --corrections.

Usage:
  python3 stutter_check.py --words words.json
      [--emit-corrections fix.json]   # write {"drop":[idx,...]} for captions
      [--max-phrase 6] [--gap 3] [--strict]
Exit code: 0 = clean, 2 = stutters found (so a QA gate can fail the build).

It KEEPS the later (usually cleaner) delivery and drops the earlier repeat.
Function-word dups and >=3x runs are HIGH confidence; a one-off content-word
repeat (could be deliberate emphasis: "very very") is flagged MEDIUM so a human
can veto. --strict drops MEDIUM too.
"""
import argparse, json, re, sys

FUNCTION = {"the", "a", "an", "i", "you", "we", "they", "it", "to", "and",
            "of", "that", "this", "is", "in", "on", "so", "but", "for", "my",
            "your", "no", "not", "do", "dont", "im", "its", "be", "he", "she"}


def norm(t):
    return re.sub(r"[^a-z0-9']", "", t.lower())


def load_words(path):
    d = json.load(open(path))
    out = []
    for s in d["transcription"]:
        t = s["text"].strip()
        if not t:
            continue
        out.append((s["offsets"]["from"] / 1000.0,
                    s["offsets"]["to"] / 1000.0, t, norm(t)))
    return out  # index here == build_ass.py word index


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", required=True)
    ap.add_argument("--emit-corrections", default="")
    ap.add_argument("--max-phrase", type=int, default=6)
    ap.add_argument("--gap", type=int, default=3,
                    help="allow up to N filler words between a restart's two halves")
    ap.add_argument("--strict", action="store_true",
                    help="also drop MEDIUM-confidence (one-off content-word) repeats")
    a = ap.parse_args()

    w = load_words(a.words)
    n = len(w)
    tok = [x[3] for x in w]
    flags = []           # (start_i, end_i_exclusive_to_drop, kind, conf, text, t0, t1)
    covered = [False] * n

    # --- Pass A: immediate single-word duplicate runs (the the / no no no) ---
    i = 0
    while i < n:
        j = i + 1
        while j < n and tok[j] and tok[j] == tok[i]:
            j += 1
        run = j - i
        if run >= 2 and tok[i]:
            conf = "HIGH" if (run >= 3 or tok[i] in FUNCTION) else "MEDIUM"
            # keep the LAST occurrence, drop i..j-2
            for k in range(i, j - 1):
                covered[k] = True
            flags.append((i, j - 1, f"repeat x{run}", conf,
                          " ".join(w[k][2] for k in range(i, j)),
                          w[i][0], w[j - 2][1]))
            i = j
        else:
            i += 1

    # --- Pass B/C: phrase restart, adjacent or with a small filler gap ---
    # longest n first so "you're not bad at this" wins over "not bad".
    for L in range(a.max_phrase, 1, -1):
        i = 0
        while i + 2 * L <= n + a.gap:
            if i + L > n or any(covered[i:i + L]) or not all(tok[i:i + L]):
                i += 1; continue
            first = tok[i:i + L]
            matched = False
            for g in range(0, a.gap + 1):
                s = i + L + g
                if s + L > n:
                    break
                if any(covered[s:s + L]):
                    continue
                if tok[s:s + L] == first:
                    # drop the FIRST block + any filler gap, keep the 2nd
                    for k in range(i, s):
                        covered[k] = True
                    flags.append((i, s, f"restart {L}w" + (f" +{g} filler" if g else ""),
                                  "HIGH", " ".join(w[k][2] for k in range(i, s + L)),
                                  w[i][0], w[s - 1][1]))
                    matched = True
                    i = s + L
                    break
            if not matched:
                i += 1

    flags.sort(key=lambda f: f[0])
    keep = [f for f in flags if a.strict or f[3] == "HIGH"]

    if not flags:
        print("clean: no stutters or restarts detected")
        return

    print(f"found {len(flags)} stutter/restart span(s) "
          f"({sum(1 for f in flags if f[3]=='HIGH')} HIGH):\n")
    for st, en, kind, conf, text, t0, t1 in flags:
        act = "DROP" if (conf == "HIGH" or a.strict) else "review"
        print(f"  [{conf:6}] {t0:6.2f}-{t1:6.2f}s  {kind:18} {act:6} "
              f"words {st}-{en-1}  | \"{text}\"")

    drop = sorted({k for f in keep for k in range(f[0], f[1])})
    print(f"\ncaption drop indices ({len(drop)} words): {drop}")
    print("video cut-ranges to remove (seconds):")
    for st, en, kind, conf, text, t0, t1 in keep:
        print(f"  {t0:.2f} -> {t1:.2f}")

    if a.emit_corrections:
        try:
            existing = json.load(open(a.emit_corrections))
        except Exception:
            existing = {}
        existing.setdefault("drop", [])
        existing["drop"] = sorted(set(existing["drop"]) | set(drop))
        json.dump(existing, open(a.emit_corrections, "w"), indent=2)
        print(f"\nwrote/merged {len(drop)} drops into {a.emit_corrections}")

    sys.exit(2)


if __name__ == "__main__":
    main()

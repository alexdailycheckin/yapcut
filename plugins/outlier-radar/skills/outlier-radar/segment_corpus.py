#!/usr/bin/env python3
"""segment_corpus.py: split the voice corpus by REGISTER and MODE, and emit the one that matters.

WHY. Targets derived from voice-corpus/corpus.txt as a single pool are wrong in a way that
shapes every batch, and in the reference deployment it went unnoticed for weeks. The pool is
not one voice:

    calls, spoken banter      3553w   median  7   mean 11.0   like 48.4/1k
    capture, spoken on work    737w   median 17   mean 19.1   like 35.3/1k
    capture, TYPED on work     437w   median 19   mean 22.1   like  2.3/1k   <- not speech

In the reference deployment 76% of the pool was a casual video call about hobbies. A third of
the work material was typed, not spoken, and its "like" rate of 2.3 per 1000 words against
35.3 for speech proves the two cannot be pooled. The show is a performed monologue about
companies, so the ONLY on-target material is the middle row.

The consequence was concrete: pooled targets said median 8 / mean 12.5, so check_fidelity's
band of "mean 9 to 13" looked confirmed. His work speech runs mean 19.1. The gate had been
requiring sentences about half the length of how the creator actually talks about their
subject, and every batch was written to it.

REGISTERS (2026-09-09, audit Q1 item 7). Every source file may carry a header line

    register: work | banter | personal

and is filed by it. Until this existed every Granola call was filed as banter without its
header being read, so the on-subject customer and prospect calls the creator already held
never reached the targets. Defaults when the header is absent: capture/ is work (that is
what a capture is), voice-corpus/manual/ is work, voice-corpus/granola/ is banter. A
`mode: typed` capture is work-typed: writing, not speech, never pooled with speech.
granola_to_corpus.py in the workspace writes the header (--register, or work when the
meeting title matches radar-config.json voice.work_title_regex).

TWO GUARDS, both from the 2026-09-09 audit of the reference workspace.
  1. A paragraph that OPENS with a square-bracket tag ("[context, NOT for script: ...]",
     "[work-journal 2026-07-22, same story] A head of growth told me ...") is a note about
     the speech, not the speech, and is dropped from every derived corpus. One such note
     carried a client's identity and a family member's employer into a writer prompt.
  2. This script never deletes hand-filed material. A line in an existing corpus-*.txt that
     no source file reproduces is KEPT, appended after the derived text, and reported, with
     the ask to file it under voice-corpus/manual/ with a register header so the derivation
     becomes reproducible. The reference workspace carried 16,000 words of pasted video
     transcripts inside the corpus files and nowhere else; a source-only rebuild would have
     deleted every one of them.

Teleprompter reads stay excluded (an audit found 71/71 were the creator reading the AI's own
scripts back, so measuring them measures the AI). That exclusion is correct and it is also
why the on-target corpus is thin: it removed the only performed-monologue source. The fix is
supply, not arithmetic: the on-subject calls already in Granola, filed with register: work.

    python3 segment_corpus.py [--dir <workspace>]

Exit codes (Contract 1): 0 when a work-spoken corpus was written, 1 when it is empty (an
onboarding state: nothing on-subject has been captured yet), 2 when the workspace is missing.
"""
import glob
import json
import os
import re
import statistics
import sys

# realpath locates the sibling module through the workspace symlink; the workspace itself is
# resolved by yapcut_home and never by following a symlink (see yapcut_home.py).
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yapcut_home import radar_home  # noqa: E402

REGISTERS = ("work", "banter", "personal")
REG_RE = re.compile(r"^register:\s*([A-Za-z]+)\s*$", re.M | re.I)
MODE_RE = re.compile(r"^mode:\s*([A-Za-z]+)", re.M | re.I)
BRACKET_PARA = re.compile(r"^\s*\[[^\]]*\].*$", re.M)

# (glob under the workspace, register when the file carries no header)
SOURCES = (
    ("capture/*.md", "work"),
    ("voice-corpus/manual/*.md", "work"),
    ("voice-corpus/granola/*.md", "banter"),
)
BUCKETS = ("work-spoken", "work-typed", "banter-spoken", "personal-spoken")
THIN_WORDS = 4000


def clean(t):
    t = re.sub(r"^#.*$", "", t, flags=re.M)
    t = re.sub(r"^(mode|register):.*$", "", t, flags=re.M | re.I)
    t = re.sub(r"^_.*_$", "", t, flags=re.M)
    t = re.sub(r"^\s*-\s*", "", t, flags=re.M)
    t = BRACKET_PARA.sub("", t)            # guard 1: notes about the speech
    t = re.sub(r"[ \t]{2,}", " ", t)
    return re.sub(r"\n{2,}", "\n", t).strip()


def register_of(raw, default):
    """(register, had_header). An unknown value falls back to the default and is reported."""
    m = REG_RE.search(raw)
    if not m:
        return default, None
    r = m.group(1).lower()
    if r in REGISTERS:
        return r, True
    return default, r


def stats(text):
    S = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.replace("\n", " ")) if s.strip()]
    if len(S) < 5:
        return None
    wc = sorted(len(s.split()) for s in S)
    W = len(re.findall(r"[A-Za-z']+", text))
    return {"words": W, "sentences": len(S), "median": statistics.median(wc),
            "mean": round(statistics.mean(wc), 1), "max": max(wc)}


def _norm(line):
    return re.sub(r"\s+", " ", line).strip()


def words_in(text):
    return len(re.findall(r"[A-Za-z']+", text))


def merge_existing(path, derived):
    """Guard 2. Returns (text_to_write or None to leave the file alone, kept_words, kept_lines).
    Every existing line no source reproduces is kept after the derived text."""
    if not path.exists():
        return derived, 0, 0
    existing = path.read_text(encoding="utf-8")
    have = {_norm(l) for l in derived.splitlines() if l.strip()}
    kept = [l for l in existing.splitlines() if l.strip() and _norm(l) not in have]
    if not kept:
        return derived, 0, 0
    kept_words = sum(words_in(l) for l in kept if not l.lstrip().startswith("#"))
    if not derived:
        # nothing derived for this register: the file is entirely hand-filed, leave it as is
        return None, kept_words, len(kept)
    return derived + "\n" + "\n".join(kept), kept_words, len(kept)


def main():
    H = radar_home()
    vc = H / "voice-corpus"
    vc.mkdir(parents=True, exist_ok=True)

    buckets = {k: [] for k in BUCKETS}
    reg_counts = {r: 0 for r in REGISTERS}
    headered = defaulted = 0
    odd = []
    for pattern, default in SOURCES:
        for f in sorted(glob.glob(str(H / pattern))):
            raw = open(f, encoding="utf-8").read()
            reg, had = register_of(raw, default)
            if had is True:
                headered += 1
            else:
                defaulted += 1
                if had:
                    odd.append((os.path.basename(f), had, default))
            m = MODE_RE.search(raw)
            mode = m.group(1).lower() if m else "spoken"
            if mode == "typed" and reg != "work":
                print(f"note: {os.path.basename(f)} is typed but register {reg}; only work "
                      f"has a typed split, filed as {reg}-spoken")
            key = "work-typed" if (mode == "typed" and reg == "work") else f"{reg}-spoken"
            buckets[key].append((os.path.basename(f), clean(raw)))
            reg_counts[reg] += 1

    for name, value, default in odd:
        print(f"warn: {name} says register: {value}, not one of {'|'.join(REGISTERS)}; "
              f"filed as {default}")

    out = {"_registers": reg_counts, "_headers": {"with_register_header": headered,
                                                   "defaulted": defaulted}}
    kept_total = 0
    for k, files in buckets.items():
        derived = "\n".join(t for _, t in files if t)
        p = vc / f"corpus-{k}.txt"
        text, kept_words, kept_lines = merge_existing(p, derived)
        if text is not None:
            p.write_text(text + "\n", encoding="utf-8")
        final = p.read_text(encoding="utf-8") if p.exists() else ""
        st = stats(final)
        out[k] = {"register": k.split("-")[0], "files": [n for n, _ in files],
                  "derived_words": words_in(derived), "kept_words": kept_words,
                  "kept_lines": kept_lines, **(st or {"words": words_in(final)})}
        kept_total += kept_words
        tag = "  <- THE TARGET REGISTER" if k == "work-spoken" else ""
        shape = (f"median {st['median']:>3.0f} mean {st['mean']:>5.1f} max {st['max']:>3}"
                 if st else ("empty" if not final.strip() else "too thin"))
        kept = f"  (+{kept_words}w hand-filed, kept)" if kept_words else ""
        print(f"{k:<16} {out[k].get('words', 0):>6}w  {len(files):>2} file(s)  {shape}{tag}{kept}")

    (vc / "segments.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\nregisters: " + ", ".join(f"{r} {n}" for r, n in reg_counts.items())
          + f"   ({headered} file(s) carried a register header, {defaulted} defaulted)")
    print(f"wrote corpus-<register>-spoken.txt, corpus-work-typed.txt, segments.json under {vc}")
    if kept_total:
        print(f"\nKEPT {kept_total} hand-filed words that no source file reproduces (guard 2). To make the")
        print("derivation reproducible, file that material under voice-corpus/manual/<name>.md with a")
        print("`register: work|banter|personal` header line; this script will then derive it.")

    work = out["work-spoken"].get("words", 0)
    if not work:
        print("\nNO WORK-SPOKEN CORPUS YET. Nothing on-subject and spoken has been filed: pull 8 to 10")
        print("customer or prospect calls through granola_to_corpus.py (register: work) or drop")
        print("transcripts in capture/, then run derive_voice_targets.py.")
        return 1
    if work < THIN_WORDS:
        print(f"\nTHE TARGET CORPUS IS THIN ({work} words). Everything downstream is capped by it:")
        print(f"targets derived from it are provisional until it passes ~{THIN_WORDS}. The supply is the")
        print("on-subject calls already in Granola, filed with register: work, not a phone recording.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

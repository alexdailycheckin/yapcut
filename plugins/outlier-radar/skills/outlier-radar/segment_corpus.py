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
# FORM, added 2026-09-20, and it cross-cuts register rather than subdividing it.
#
# Register answers "what is he talking about". Form answers "is anybody else in the room",
# and the 2026-09-18 measurement says that second question moves the delivery numbers more
# than the first one does:
#
#     monologue to camera   3,564w   cut-off 0.0/1k   um-uh  7.3   like 11.8
#     dialogue on calls     9,733w   cut-off 10.0/1k  um-uh 18.1   like 27.4
#
# A cut-off word (`be-`, `yo-`, `i-`) runs 10 per 1000 in conversation and ZERO across
# 3,564 words of them alone with a camera. It is an artifact of being interrupted, not a
# feature of their delivery. The show is a performed monologue, so a script written to the
# conversation rates is written to the wrong speaker, and until this existed the brief
# served exactly those rates: `targets.json` derives from work-spoken, which is 9 sales
# calls plus 5 conversation extracts.
#
# So form gets its own DERIVED VIEW, corpus-monologue-spoken.txt, pooling every spoken
# source that carries `form: monologue` whatever its register. Subject does not transfer
# across registers but delivery physics does, which is why a personal-register video is
# admissible evidence for how he sounds and inadmissible as a passage to imitate.
# derive_voice_targets.py reads the view into targets.json `delivery`; the passages and the
# sentence physics still come from work-spoken.
FORMS = ("monologue", "dialogue")
FORM_RE = re.compile(r"^form:\s*([A-Za-z]+)", re.M | re.I)
MONO_VIEW = "corpus-monologue-spoken.txt"
# The default is dialogue, deliberately, and it is not a guess about the file. capture/ LOOKS
# like one voice because it holds the creator's turns only, but every capture is an extract
# from a call ("mode: granola | source: <creator> <> [prospect]"), so defaulting capture/ to
# monologue would pour conversation straight into the view it exists to keep clean. A file is a
# monologue when it says so and never because of where it sits.
FORM_DEFAULT = "dialogue"
BRACKET_PARA = re.compile(r"^\s*\[[^\]]*\].*$", re.M)
# A trailing editorial annotation, anywhere on a line: "... <- NOT CAPTURED",
# "... <- his words". BRACKET_PARA only catches a note that OWNS its line, and
# guard 2 preserves hand-filed corpus text that no source reproduces, so a marker
# baked in by an older build survives every rebuild. One reached a blind-read
# sheet on 2026-09-18 and made a passage of the creator's own writing unreadable.
TRAILING_NOTE = re.compile(r"\s*<-+\s*[A-Z][^\n]*$", re.M)

# (glob under the workspace, register when the file carries no header)
SOURCES = (
    ("capture/*.md", "work"),
    ("voice-corpus/manual/*.md", "work"),
    ("voice-corpus/granola/*.md", "banter"),
)
STRICT = set()
BUCKETS = ("work-spoken", "work-typed", "banter-spoken", "personal-spoken")
THIN_WORDS = 4000


def clean(t):
    t = re.sub(r"^#.*$", "", t, flags=re.M)
    t = re.sub(r"^(mode|register|form|source):.*$", "", t, flags=re.M | re.I)
    t = re.sub(r"^_.*_$", "", t, flags=re.M)
    t = re.sub(r"^\s*-\s*", "", t, flags=re.M)
    t = BRACKET_PARA.sub("", t)            # guard 1: notes about the speech
    t = TRAILING_NOTE.sub("", t)           # guard 1b: notes appended to a line
    t = re.sub(r"[ \t]{2,}", " ", t)
    return re.sub(r"\n{2,}", "\n", t).strip()


def form_of(raw):
    """(form, odd_value). Absent or unknown falls back to FORM_DEFAULT and is reported."""
    m = FORM_RE.search(raw)
    if not m:
        return FORM_DEFAULT, None
    f = m.group(1).lower()
    if f in FORMS:
        return f, None
    return FORM_DEFAULT, f


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


def merge_existing(path, derived, strict=False):
    """Guard 2. Returns (text_to_write or None to leave the file alone, kept_words, kept_lines).
    Every existing line no source reproduces is kept after the derived text.

    `strict` turns guard 2 OFF for THIS bucket and rebuilds it from sources alone. Guard 2 exists so a
    hand-filed line is never silently lost, but it has a cost that bit twice on
    2026-09-18: material PULLED from the corpus does not leave, because deleting its
    source file makes its lines orphaned rather than derived, and guard 2 then
    preserves them forever. Removing a source is a deliberate act, and it has to
    actually remove the words. Use --strict after quarantining anything, then check
    the diff."""
    if strict:
        return derived, 0, 0
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
    global STRICT
    # --strict takes the bucket(s) to rebuild, and the argument is REQUIRED. A global
    # --strict dropped 19,970 hand-filed words of banter and personal corpus on
    # 2026-09-18 while the intent was to clean one bucket. Turning guard 2 off is
    # correct after a quarantine and catastrophic anywhere else, so it is scoped.
    if "--strict" in sys.argv:
        i = sys.argv.index("--strict")
        arg = sys.argv[i + 1] if i + 1 < len(sys.argv) else None
        if not arg or arg.startswith("-"):
            print(f"--strict needs the bucket to rebuild: {' | '.join(BUCKETS)} (or 'all').\n"
                  f"It turns guard 2 off, so every line the named bucket cannot derive from a\n"
                  f"source file is DROPPED. Use it after quarantining a source, then read the\n"
                  f"git diff before committing.")
            return 2
        del sys.argv[i:i + 2]
        STRICT = set(BUCKETS) if arg == "all" else {b.strip() for b in arg.split(",")}
        unknown = STRICT - set(BUCKETS)
        if unknown:
            print(f"unknown bucket(s): {', '.join(sorted(unknown))}. "
                  f"Known: {' | '.join(BUCKETS)}")
            return 2
        print(f"--strict {', '.join(sorted(STRICT))}: guard 2 is OFF for "
              f"{'that bucket' if len(STRICT) == 1 else 'those buckets'}; anything not in a "
              f"source file is dropped. Every other bucket is untouched.\n")
    H = radar_home()
    vc = H / "voice-corpus"
    vc.mkdir(parents=True, exist_ok=True)

    buckets = {k: [] for k in BUCKETS}
    mono = []                       # the form cross-cut: every spoken monologue, any register
    reg_counts = {r: 0 for r in REGISTERS}
    form_counts = {f: 0 for f in FORMS}
    headered = defaulted = 0
    odd = []
    odd_form = []
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
            body = clean(raw)
            buckets[key].append((os.path.basename(f), body))
            reg_counts[reg] += 1
            form, odd_f = form_of(raw)
            if odd_f:
                odd_form.append((os.path.basename(f), odd_f))
            if mode != "typed":
                form_counts[form] += 1
                if form == "monologue":
                    mono.append((os.path.basename(f), body))

    for name, value, default in odd:
        print(f"warn: {name} says register: {value}, not one of {'|'.join(REGISTERS)}; "
              f"filed as {default}")
    for name, value in odd_form:
        print(f"warn: {name} says form: {value}, not one of {'|'.join(FORMS)}; "
              f"filed as {FORM_DEFAULT}")

    out = {"_registers": reg_counts, "_headers": {"with_register_header": headered,
                                                   "defaulted": defaulted}}
    kept_total = 0
    for k, files in buckets.items():
        derived = "\n".join(t for _, t in files if t)
        p = vc / f"corpus-{k}.txt"
        text, kept_words, kept_lines = merge_existing(p, derived, strict=(k in STRICT))
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

    # The form view. Rebuilt from sources every run and never merged, because it is a
    # PROJECTION of files that already live in a register bucket, not a place anything is
    # filed. Guard 2 protects hand-filed material; a hand-filed line here would be invisible
    # in every register corpus and would quietly become a source of truth nothing can
    # reproduce. The banner says so inside the file.
    mono_text = "\n".join(t for _, t in mono if t)
    mp = vc / MONO_VIEW
    if mono_text:
        banner = ("# DERIVED VIEW, rebuilt by segment_corpus.py on every run. Do not hand-file\n"
                  "# here: edits are silently overwritten. This pools every spoken source with\n"
                  "# `form: monologue`, any register, because delivery physics transfer across\n"
                  "# registers and subject does not. Sourced from: "
                  + ", ".join(n for n, _ in mono) + "\n")
        mp.write_text(banner + mono_text + "\n", encoding="utf-8")
    elif mp.exists():
        mp.unlink()
    mst = stats(mono_text) if mono_text else None
    out["monologue-spoken"] = {"_view": True, "form": "monologue", "pools_registers": True,
                               "files": [n for n, _ in mono],
                               "derived_words": words_in(mono_text),
                               **(mst or {"words": words_in(mono_text)})}
    shape = (f"median {mst['median']:>3.0f} mean {mst['mean']:>5.1f} max {mst['max']:>3}"
             if mst else ("empty" if not mono_text.strip() else "too thin"))
    print(f"{'monologue-spoken':<16} {out['monologue-spoken'].get('words', 0):>6}w  "
          f"{len(mono):>2} file(s)  {shape}  <- THE DELIVERY VIEW (cross-cut, form)")

    (vc / "segments.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"\nregisters: " + ", ".join(f"{r} {n}" for r, n in reg_counts.items())
          + f"   ({headered} file(s) carried a register header, {defaulted} defaulted)")
    print("forms:     " + ", ".join(f"{f} {n}" for f, n in form_counts.items())
          + f"   (spoken files only; absent header defaults to {FORM_DEFAULT})")
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
    mono_w = out["monologue-spoken"].get("words", 0)
    if not mono_w:
        print("\nNO MONOLOGUE VIEW. Nothing carries `form: monologue`, so targets.json will have no")
        print("`delivery` block and the brief will serve CONVERSATION marker rates to a writer")
        print("writing a monologue. Add `form: monologue` to any source that is the creator alone")
        print("talking:")
        print("a to-camera video, a voice memo, a recorded solo take.")
    if work < THIN_WORDS:
        print(f"\nTHE TARGET CORPUS IS THIN ({work} words). Everything downstream is capped by it:")
        print(f"targets derived from it are provisional until it passes ~{THIN_WORDS}. The supply is the")
        print("on-subject calls already in Granola, filed with register: work, not a phone recording.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

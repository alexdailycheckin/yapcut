#!/usr/bin/env python3
"""voice_brief.py: emit the writing brief. Run it BEFORE writing any spoken script.

WHY THIS EXISTS, and it is the most important file in the voice stack.

In the reference deployment a 64-agent fan-out rewrote 8 show episodes and the creator
rejected the result in the same terms as the batch before it: "they still are written in
the same voice that you always write." The cause was not scale, model or prompt length.
It was this:

    The writers were given a DESCRIPTION of the voice. They were never shown the voice itself.

All 32 writer agents received the same handful of adjectives, varied only by a register
label. There were 4,717 words of the creator actually talking sitting in voice-corpus/
and not one line of it entered any of the 64 prompts. A model given
a description of a voice produces an imitation of the description, which is precisely the
generic confident-operator register that keeps getting rejected. A model shown 20 verbatim passages
imitates the passages.

So the few-shot cannot be advice, because advice is the thing that failed. It has to be a
step that MECHANICALLY produces the prompt, so that no future session, and no Sunday cloud
run, has to remember to ground itself. That is what this file is.

    python3 voice_brief.py [--dir <workspace>]     # the brief, for pasting into a writer prompt
    python3 voice_brief.py --week 2026-09-07       # deterministic sample rotation per week
    python3 voice_brief.py --samples 24            # more few-shot passages
    python3 voice_brief.py --corpus-file <path>    # sample another file, explicitly

ONE CORPUS. The passages come from voice-corpus/corpus-work-spoken.txt, the same file the
targets are derived from, and from nothing else unless --corpus-file names another path out
loud. The old fallback to the pooled corpus.txt is gone: it handed writers off-topic small
talk as the specification (2026-08-30). Showing a model the wrong register and demanding the
right one is the same class of error as describing the voice instead of showing it.

Regenerate targets first if the corpus has grown:  python3 derive_voice_targets.py

Exit codes (Contract 1): 0 brief printed, 1 when the corpus or targets.json is missing (an
onboarding state: run segment_corpus.py then derive_voice_targets.py), 2 usage.
"""
import json
import os
import pathlib
import re
import statistics
import sys


# realpath locates the sibling module through the workspace symlink; the workspace itself is
# resolved by yapcut_home and never by following a symlink (see yapcut_home.py).
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yapcut_home import radar_home  # noqa: E402

WORK_CORPUS = "corpus-work-spoken.txt"


def scrub(text):
    """Markdown headers and build metadata leak into corpus.txt and were being shown to
    writers as if they were speech ("### capture / 2026-07-26-review-responses (84w,
    capture) I know we work with one customer..."). Strip them here as well as at build
    time, because a sample is worthless the moment it contains something the creator never said."""
    text = re.sub(r"^#+.*$", "", text, flags=re.M)
    text = re.sub(r"^_.*_$", "", text, flags=re.M)
    text = re.sub(r"^mode:.*$", "", text, flags=re.M)
    text = re.sub(r"###[^\n]*?\(\d+w,[^)]*\)", "", text)
    text = re.sub(r"^\s*-\s*", "", text, flags=re.M)
    # Bracketed editorial annotations are not speech, and in the capture files they carry
    # SENSITIVE context: one sample handed to a writer in the reference deployment carried a
    # client's identity and a private detail about a family member's employer. Never ship a [ ... ] block
    # into a prompt. Non-greedy and multiline so a note spanning lines is removed whole.
    text = re.sub(r"\[[^\]]*\]", " ", text, flags=re.S)
    text = re.sub(r"\(context[^)]*\)", " ", text, flags=re.I | re.S)
    return re.sub(r"[ \t]{2,}", " ", text)


def sentences(text):
    text = text.replace("\n", " ")
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def pick_samples(corpus, targets, n, seed_str):
    """Choose few-shot passages that DEMONSTRATE the profile rather than just sampling it.

    Two selection rules, both derived from the 2026-08-30 failure:
      1. Prefer passages carrying the creator's top discourse markers, because their absence was the
         loudest measured difference (the creator ran "like" at 42.2 per 1000 words, the
         rejected batch ran 2.8).
      2. Guarantee at least 3 passages containing a runaway sentence over 45 words. Real
         speech reached 98 words with 1.6% of sentences past 45; the rejected batch held
         128 sentences with a maximum of 38 and nothing over 45. A model shown only tidy
         passages will write tidy prose, so the tail has to be visible in the examples.

    Rotation is deterministic on the week string so two sessions writing the same week get
    the same brief, and consecutive weeks do not overfit to one slice of the corpus."""
    sents = sentences(corpus)
    # windows of 3 to 5 sentences, so each sample shows cadence CHANGING, not one line
    windows = []
    i = 0
    while i < len(sents) - 2:
        size = 3 + (i % 3)
        w = sents[i:i + size]
        if w:
            windows.append(" ".join(w))
        i += size
    markers = [m for m, _ in sorted(
        (targets or {}).get("speech_markers_per_1k", {}).items(), key=lambda kv: -kv[1])[:6]]

    def score(w):
        low = w.lower()
        m = sum(1 for k in markers if re.search(r"\b" + re.escape(k) + r"\b", low))
        wc = [len(x.split()) for x in sentences(w)]
        spread = (max(wc) - min(wc)) if wc else 0
        return m * 3 + min(spread, 30) / 10.0

    runaway = [w for w in windows if any(len(x.split()) > 45 for x in sentences(w))]
    rest = [w for w in windows if w not in runaway]
    rest.sort(key=score, reverse=True)
    runaway.sort(key=score, reverse=True)

    off = sum(ord(c) for c in seed_str) if seed_str else 0
    take_tail = runaway[:3] if runaway else []
    pool = rest[:max(0, n * 3)]
    if pool:
        pool = pool[off % len(pool):] + pool[:off % len(pool)]
    picked = take_tail + pool[:max(0, n - len(take_tail))]
    return picked, len(runaway)


def main():
    week = ""
    if "--week" in sys.argv:
        i = sys.argv.index("--week")
        week = sys.argv[i + 1]
        del sys.argv[i:i + 2]
    n = 18
    if "--samples" in sys.argv:
        i = sys.argv.index("--samples")
        n = int(sys.argv[i + 1])
        del sys.argv[i:i + 2]
    corpus_file = None
    if "--corpus-file" in sys.argv:
        i = sys.argv.index("--corpus-file")
        if i + 1 >= len(sys.argv):
            print("--corpus-file needs a path")
            return 2
        corpus_file = sys.argv[i + 1]
        del sys.argv[i:i + 2]
    if "--pooled" in sys.argv:
        print("--pooled was removed 2026-09-09: the pooled corpus is the wrong register. "
              "Use --corpus-file <path> if you really mean another file.")
        return 2

    home = radar_home()
    # REGISTER: must match derive_voice_targets.py. Reading the pooled corpus.txt here was
    # a real bug caught 2026-08-30: the targets came from the on-subject segment while the
    # few-shot passages came from the pool, so most examples handed to the writers were
    # off-topic small talk. The corpus is the work register or it is named out loud.
    cpath = home / "voice-corpus" / WORK_CORPUS
    if corpus_file:
        cpath = pathlib.Path(os.path.abspath(os.path.expanduser(corpus_file)))
        if cpath.name != WORK_CORPUS:
            print(f"# WARNING: sampling {cpath.name}, not {WORK_CORPUS}. The passages below are "
                  "NOT the register the targets describe.")
    tpath = home / "voice-corpus" / "targets.json"
    rpath = home / "voice-corpus" / "rejections.json"
    if not cpath.exists():
        print(f"no corpus at {cpath}. Nothing can ground a voice without it. Run "
              "segment_corpus.py first.")
        return 1
    corpus = scrub(cpath.read_text(encoding="utf-8"))
    targets = json.loads(tpath.read_text(encoding="utf-8")) if tpath.exists() else None
    if targets is None:
        print("no voice-corpus/targets.json. Run: python3 derive_voice_targets.py")
        return 1
    rejections = (json.loads(rpath.read_text(encoding="utf-8")).get("rejections", [])
                  if rpath.exists() else [])

    sw, sh, wd = targets["sentence_words"], targets["shape"], targets["words"]
    mk = sorted(targets.get("speech_markers_per_1k", {}).items(), key=lambda kv: -kv[1])[:8]
    samples, n_runaway = pick_samples(corpus, targets, n, week)

    print("# THE VOICE BRIEF")
    print("# Generated by voice_brief.py from voice-corpus/. Do not paraphrase this")
    print("# into adjectives: the passages below ARE the specification. Match them.")
    print(f"# corpus: {targets['corpus']['words']} words, {targets['corpus']['sentences']} sentences"
          + (f" | week {week}" if week else ""))
    print()
    print("## HOW THEY ACTUALLY TALK (measured, not chosen)")
    print()
    print(f"- Sentence length: median {sw['median']:.0f} words, mean {sw['mean']}. Most lines are SHORT.")
    print(f"- But the tail is the voice: p90 {sw['p90']}, longest {sw['max']} words.")
    print(f"  {sh['pct_over_30']}% of their sentences pass 30 words and {sh['pct_over_45']}% pass 45.")
    print(f"  **Write at least one runaway sentence per batch**: 50 to 90 words, one breath,")
    print(f"  going into the why and then the consequence and then an aside without stopping.")
    print(f"  A batch whose longest sentence is under 45 words has been edited into prose.")
    print(f"- {sh['pct_under_5']}% of their sentences are under 5 words. Short lines break the runs.")
    print(f"- Word size: {wd['syllables_per_word']} syllables/word, reading grade "
          f"{wd['flesch_kincaid_grade']}. Plain words. If a shorter word exists, it wins.")
    print(f"- Contractions: {targets['contraction_rate_pct']}% of contractable pairs. Nearly always.")
    print()
    print("## THE DISCOURSE MARKERS ARE NOT OPTIONAL")
    print()
    print("Their absence is the single loudest tell. Rates per 1000 words in their real speech:")
    print("  " + ", ".join(f"{k} {v}" for k, v in mk))
    print()
    print("Quotative \"like\" is a common signature: \"and they're like, yeah, but they're all vanity")
    print("metrics\". A script with none of these reads as an essay performed aloud, which is")
    print("the exact note that comes back on every rejected batch. NOTE: the `copywriting` skill's")
    print("sentence layer deletes hedges and filler because in WRITTEN copy they are waste.")
    print("For a SPOKEN script they are the texture. That carve-out is deliberate.")
    print()
    if rejections:
        print("## ALREADY REJECTED BY HIM. Do not reproduce these or their shape.")
        print()
        for r in rejections:
            pat = r["pattern"] if not r.get("is_regex") else f"[{r.get('class','pattern')}]"
            print(f"- \"{pat}\" ({r.get('date','?')}): {r.get('why','')[:150]}")
        print()
        print("spoken_lint.py FAILS on every one of these, so a draft carrying one")
        print("does not ship. When the creator kills a line, append it to voice-corpus/rejections.json.")
        print()
    print("## READ THESE, THEN WRITE. This is the creator talking, verbatim.")
    print()
    print(f"({len(samples)} passages, {n_runaway} runaway-sentence passages available in corpus)")
    print()
    for i, s in enumerate(samples, 1):
        wc = [len(x.split()) for x in sentences(s)]
        tag = "  <- RUNAWAY SENTENCE, this is the shape to copy" if max(wc) > 45 else ""
        print(f"--- {i} (sentence lengths: {', '.join(str(x) for x in wc)}){tag}")
        print(s.strip())
        print()
    print("## THE TEST")
    print()
    print("Before returning a draft, read it against the passages above and answer: if these")
    print("were shuffled together, could a stranger pick out which one was generated? If yes,")
    print("it is not done. That question is run mechanically, and it is the ruling machine test:")
    print(f"    python3 turing_check.py --week {week or '<week>'} [--judge claude]")
    return 0


if __name__ == "__main__":
    sys.exit(main())

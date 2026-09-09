#!/usr/bin/env python3
"""derive_voice_targets.py: measure the creator's REAL speech and write voice-corpus/targets.json.

WHY THIS EXISTS.

Every threshold that governed the voice of this show was a hand-written guess. The worst
of them, `STDEV_FLOOR = 8.0` in spoken_lint.py, sat directly underneath a comment reading
"derive these from the creator's corpus with --corpus rather than trusting the numbers".
That instruction was impossible to follow: spoken_lint.py is a symlink into the plugin repo
and located the corpus with Path.resolve(), which follows the symlink OUT of the workspace,
so --corpus printed one error line and exited on every run it ever had. Fixed 2026-08-30.

The deeper failure the fix exposed, and the reason this file writes a PROFILE rather than a
few floors: summary statistics do not pin a voice. On 2026-08-30 a batch of 8 scripts hit
the creator's median and mean almost exactly and still read as written prose to the creator.
The distribution says why:

    creator, really talking   median  8   mean 12.5   p90 29   max 98   >30w 8.4%  >45w 1.6%
    the generated batch       median  8   mean 11.6   p90 27   max 38   >30w 6.6%  >45w 0.0%

Real speech has a FAT TAIL: mostly short lines, with occasional 50-to-98-word runs where they
keeps going into the why and then the consequence in one breath. Across 128 generated
sentences there was not one sentence over 45 words. The old gate asked for `max >= 25`,
which a 26-word sentence satisfies, so it certified homogenised output as compliant. A mean
and a stdev can be satisfied a hundred ways; percentiles can only be satisfied by the right
shape.

So the contract is: this script measures, `targets.json` records, and the gates read. No
number in this pipeline is allowed to come from taste again. Re-run it whenever the corpus
grows; the targets move on their own and nothing has to be remembered.

    python3 derive_voice_targets.py [--dir <workspace>]   # write voice-corpus/targets.json
    python3 derive_voice_targets.py --print               # show the profile, write nothing
    python3 derive_voice_targets.py --corpus-file <path>  # measure another file, explicitly

ONE CORPUS. This reads voice-corpus/corpus-work-spoken.txt and nothing else unless
--corpus-file names another path out loud. The old --pooled switch is gone: it measured the
banter pool and produced the mean-12.5 target that broke 8 scripts, and a switch that quiet
is a switch someone flips by accident. Targets from any other register misgrade every batch.

Exit codes (Contract 1): 0 written, 1 when the corpus is missing or too thin to measure (an
onboarding state, run segment_corpus.py first), 2 when the workspace is missing.
"""
import json
import os
import pathlib
import re
import statistics
import sys

# Discourse markers. These are NOT stylistic garnish, they are the load-bearing finding of
# the 2026-08-30 diagnosis: in the reference deployment the creator said "like" 42.6 times
# per 1000 words and the generated batch said it 2.8 times. Quotative "like" was their
# documented signature ("and they're like, yeah, but they're all vanity metrics") and it was
# absent from every script. The reason is
# upstream: the `copywriting` skill's sentence layer binds every lane with no short-form
# exemption, and it cuts hedges and filler on sight because in WRITTEN copy they are waste.
# In speech they are the texture that makes a person sound like they are thinking in real
# time. Measure them here so a gate can require them.
MARKERS = [
    "like", "you know", "i mean", "really", "basically", "actually", "obviously",
    "honestly", "literally", "i think", "i guess", "kind of", "sort of", "right",
    "and then", "but then", "anyway", "just", "so", "i don't know", "or whatever",
]

CONTRACTIONS = re.compile(
    r"\b\w+'(?:s|t|re|ve|ll|d|m)\b", re.I)
EXPANDABLE = re.compile(
    r"\b(?:it is|that is|do not|does not|did not|cannot|can not|will not|would not|"
    r"is not|are not|was not|were not|have not|has not|had not|I am|I have|I will|"
    r"I would|you are|you will|they are|we are|there is|here is|let us)\b", re.I)


def sentences(text):
    text = text.replace("\n", " ")
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def syllables(word):
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    n, prev = 0, False
    for ch in w:
        cur = ch in "aeiouy"
        if cur and not prev:
            n += 1
        prev = cur
    if w.endswith("e") and n > 1:
        n -= 1
    return max(1, n)


# realpath locates the sibling module through the workspace symlink; the workspace itself is
# resolved by yapcut_home and never by following a symlink (see yapcut_home.py).
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yapcut_home import radar_home  # noqa: E402

WORK_CORPUS = "corpus-work-spoken.txt"
MIN_SENTENCES = 30


def scrub(text):
    """Comment lines, provenance lines and header keys are not speech. corpus files may carry
    them (a hand-filed file starts with # lines), and counting them would measure the notes."""
    text = re.sub(r"^#.*$", "", text, flags=re.M)
    text = re.sub(r"^_.*_$", "", text, flags=re.M)
    text = re.sub(r"^(mode|register):.*$", "", text, flags=re.M | re.I)
    return text


def profile(text, derived_from=WORK_CORPUS):
    text = scrub(text)
    sents = sentences(text)
    if len(sents) < MIN_SENTENCES:
        return None
    wc = sorted(len(s.split()) for s in sents)
    n = len(wc)
    words = re.findall(r"[A-Za-z']+", text)
    W = len(words)
    syl = sum(syllables(w) for w in words)
    low = text.lower()

    def pct_over(k):
        return round(100.0 * sum(1 for w in wc if w > k) / n, 1)

    def pctile(p):
        return wc[min(n - 1, int(p * n))]

    marker_rates = {}
    for m in MARKERS:
        hits = len(re.findall(r"\b" + re.escape(m) + r"\b", low))
        if hits:
            marker_rates[m] = round(hits / W * 1000, 1)

    contr = len(CONTRACTIONS.findall(text))
    expand = len(EXPANDABLE.findall(text))
    contr_rate = round(100.0 * contr / max(1, contr + expand), 1)

    openers = {}
    for s in sents:
        first = " ".join(s.split()[:2]).lower().strip(".,!?")
        if first:
            openers[first] = openers.get(first, 0) + 1
    top_openers = sorted(openers.items(), key=lambda kv: -kv[1])[:15]

    return {
        "_derived_from": f"voice-corpus/{derived_from}",
        "_register": ("The creator speaking, unscripted, ABOUT THEIR SUBJECT. Not the pooled corpus: that is "
                      "76% casual banter (median 7) and pooling it hid the fact that on-subject "
                      "speech runs median 17. Not the typed captures either: those are writing, "
                      "and their 'like' rate of 2.3/1k against 35.3/1k for their speech proves it."),
        "_provisional": ("Derived from a THIN corpus. Treat every number here as directional "
                         "until the on-target corpus passes ~4000 words. The supply fix is "
                         "20-30 minutes of unscripted teardown talk, not more arithmetic."),
        "_note": ("Measured, never chosen. Regenerate with derive_voice_targets.py "
                  "whenever the corpus grows. Any gate reading a number that is not in "
                  "this file is reading a guess."),
        "corpus": {"sentences": n, "words": W},
        "sentence_words": {
            "median": statistics.median(wc),
            "mean": round(statistics.mean(wc), 1),
            "stdev": round(statistics.pstdev(wc), 1),
            "p10": pctile(0.10), "p25": pctile(0.25), "p50": pctile(0.50),
            "p75": pctile(0.75), "p90": pctile(0.90), "p95": pctile(0.95),
            "max": max(wc),
        },
        "shape": {
            "pct_under_5": round(100.0 * sum(1 for w in wc if w < 5) / n, 1),
            "pct_over_20": pct_over(20),
            "pct_over_30": pct_over(30),
            "pct_over_45": pct_over(45),
            "_why": ("The fat tail is the voice. A script that satisfies median and mean "
                     "and carries nothing over 45 words is prose: that is exactly what "
                     "shipped on 2026-08-30, 0.0% over 45 across 128 sentences against "
                     "a corpus at 1.6%. Over a 5-episode batch expect 1 to 2 runaway sentences."),
        },
        "words": {
            "syllables_per_word": round(syl / W, 2),
            "flesch_kincaid_grade": round(0.39 * (W / n) + 11.8 * (syl / W) - 15.59, 1),
        },
        "speech_markers_per_1k": marker_rates,
        "contraction_rate_pct": contr_rate,
        "top_openers": top_openers,
    }


def main():
    home = radar_home()
    # REGISTER, added 2026-08-30 and this is the whole ballgame. corpus.txt pools three
    # different voices and is 76% casual banter; deriving from it produced a mean of 12.5
    # that appeared to confirm check_fidelity's "mean 9 to 13" band, when their unscripted
    # WORK speech runs 17.8. The show is a performed monologue about companies, so the
    # target is corpus-work-spoken.txt. Run segment_corpus.py to build it.
    src = home / "voice-corpus" / WORK_CORPUS
    if "--pooled" in sys.argv:
        print("--pooled was removed 2026-09-09: the pooled corpus is the wrong register and "
              "produced the targets that broke 8 scripts. Use --corpus-file <path> if you "
              "really mean another file.")
        return 2
    if "--corpus-file" in sys.argv:
        i = sys.argv.index("--corpus-file")
        if i + 1 >= len(sys.argv):
            print("--corpus-file needs a path")
            return 2
        src = pathlib.Path(os.path.abspath(os.path.expanduser(sys.argv[i + 1])))
        if src.name != WORK_CORPUS:
            print(f"WARNING: measuring {src.name}, not {WORK_CORPUS}. Targets from any other "
                  "register misgrade every batch; only do this to compare, never to ship.")
    if not src.exists():
        print(f"no corpus at {src}. Run segment_corpus.py first (it files capture/, "
              "voice-corpus/manual/ and voice-corpus/granola/ by register).")
        return 1
    prof = profile(src.read_text(encoding="utf-8"), derived_from=src.name)
    if prof is None:
        n = len(sentences(scrub(src.read_text(encoding="utf-8"))))
        print(f"corpus too thin to derive targets from: {n} sentences in {src.name}, need "
              f"{MIN_SENTENCES}+. Supply is the fix: on-subject calls filed with register: work.")
        return 1
    if "--print" in sys.argv:
        print(json.dumps(prof, indent=2))
        return 0
    out = home / "voice-corpus" / "targets.json"
    out.write_text(json.dumps(prof, indent=2) + "\n", encoding="utf-8")
    s, w = prof["corpus"]["sentences"], prof["corpus"]["words"]
    sw, sh = prof["sentence_words"], prof["shape"]
    print(f"wrote {out}  ({s} sentences, {w} words)")
    print(f"  sentence words: median {sw['median']:.0f}  mean {sw['mean']}  "
          f"p90 {sw['p90']}  max {sw['max']}")
    print(f"  shape: {sh['pct_under_5']}% under 5w, {sh['pct_over_30']}% over 30w, "
          f"{sh['pct_over_45']}% over 45w")
    print(f"  syllables/word {prof['words']['syllables_per_word']}  "
          f"grade {prof['words']['flesch_kincaid_grade']}  "
          f"contractions {prof['contraction_rate_pct']}%")
    top = sorted(prof["speech_markers_per_1k"].items(), key=lambda kv: -kv[1])[:8]
    print("  speech markers /1k: " + ", ".join(f"{k} {v}" for k, v in top))
    return 0


if __name__ == "__main__":
    sys.exit(main())

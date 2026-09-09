#!/usr/bin/env python3
"""
The objective half of QA. Replaces "the model grades its own read-aloud test".

Three checks:
  1. FIDELITY  what share of the finished script's words came from the capture.
               Below 0.90 the model started ghostwriting again.
  2. FINGERPRINT  does the script move like the creator talks, per references/voice-fingerprint.md.
  3. LINKEDIN  the numeral law, the source law, and a legal qa value, run over the
               linkedin[] lane and every embedded twin body. Video-only until
               2026-08-13, which is why written posts could never leave pre-QA.
  4. SPOKEN    does it survive being said out loud. WARN ONLY. Added 2026-08-16 after
               the creator rejected the 08-17 batch for reading as prose while passing every
               cadence target: the numbers were tuned against the previous failure and
               the writer adapted. See the SPOKEN GATE block below for the delivery
               evidence behind each threshold.

Usage:
  python3 check_fidelity.py capture.md script.txt
  python3 check_fidelity.py --week weeks/2026-08-02.json     # whole batch, incl. cadence clash
"""

import json
import os
import re
import statistics
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))


def _resolve_home():
    """Workspace resolution, same order as the rest of the skill:
    --dir <path> | $OUTLIER_RADAR_HOME | cwd with weeks/ | skill root | ~/outlier-radar."""
    if "--dir" in sys.argv:
        i = sys.argv.index("--dir")
        home = os.path.expanduser(sys.argv[i + 1])
        del sys.argv[i:i + 2]
        return home
    env = os.environ.get("OUTLIER_RADAR_HOME")
    if env:
        return os.path.expanduser(env)
    if os.path.isdir(os.path.join(os.getcwd(), "weeks")):
        return os.getcwd()
    if os.path.isdir(os.path.join(HERE, "weeks")):
        return HERE
    return os.path.expanduser("~/outlier-radar")


RADAR = _resolve_home()

FILLER = {
    "like", "you", "know", "sort", "of", "kind", "i", "mean", "um", "uh", "yeah",
    "so", "just", "really", "actually", "basically",
}

QUOTED = re.compile(
    r"\b(?:i|he|she|they|we)\s+(?:was|were|'s|is|are)\s+like\b"
    r"|\btold me\b|\bhe said\b|\bshe said\b|\bthey said\b|\bi said\b"
    r"|\bi told\s+(?:him|her|them)\b|\bgoes,\s|\bsaid,\s",
    re.I,
)


def words(text):
    return re.findall(r"[a-z0-9']+", text.lower())


def sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def fidelity(capture, script, fact_fixes=()):
    """Share of script words available in the capture. Filler is excluded from the
    denominator: deleting 'like' is editing, not invention.

    fact_fixes are corrections the editor DECLARED (a wrong number, a mistaken
    mechanism). Their words join the allowed pool, because fixing a false claim is
    the one kind of rewriting that must not be discouraged. Undeclared changes still
    count against fidelity, which is the point: you have to say what you changed.

    Matching is PRESENCE-based, not count-based (changed 2026-07-26): a word the
    creator used may be reused, because callback endings deliberately repeat the
    opening words, and repeating his own words is editing, not ghostwriting. The
    gate still catches what matters: words he never said."""
    pool = {w for w in words(capture) if w not in FILLER}
    for fix in fact_fixes:
        pool.update(w for w in words(fix) if w not in FILLER)
    scr = [w for w in words(script) if w not in FILLER]
    if not scr:
        return 0.0
    matched = sum(1 for w in scr if w in pool)
    return matched / len(scr)


def trigram_share(capture, script, fact_fixes=()):
    """Second fidelity axis (added 2026-07-26 after the audit): word-presence catches
    vocabulary, not authorship. A ghostwriter can recombine the creator's words into
    new sentences and score 1.00. Trigram share catches that: faithful edits of real
    captures score 0.61-0.86 (measured on this repo), ghostwritten text scores ~0.0.
    Gate: >= 0.50."""
    def tri(ws):
        return set(zip(ws, ws[1:], ws[2:]))
    cw = words(capture)
    for fix in fact_fixes:
        cw += words(fix)
    st, ct = tri(words(script)), tri(cw)
    if not st:
        return 0.0
    return len(st & ct) / len(st)


def fingerprint(script):
    sents = sentences(script)
    lens = [len(s.split()) for s in sents if s.split()]
    if not lens:
        return {}
    return {
        "sentences": len(lens),
        "mean": round(statistics.mean(lens), 1),
        "median": statistics.median(lens),
        "max": max(lens),
        "min": min(lens),
        "stdev": round(statistics.pstdev(lens), 1),
        "over20_pct": round(100.0 * len([n for n in lens if n > 20]) / len(lens), 1),
        "quoted_dialogue": bool(QUOTED.search(script)),
        "words": sum(lens),
    }


# The cadence floors were recalibrated on 2026-08-24 against a real unscripted speech
# corpus, after the old ones turned out to be sitting at roughly half of it: a stdev floor
# of 6 against a speaker measuring 12.1, cleared at a median of 7.2 across everything that
# had shipped. Raising a floor retroactively fails work that was written to the old bar and
# cannot be rewritten, so the new numbers apply from the first week AFTER the change and
# older weeks keep the floors they were written under. Self-expiring, so there is no flag
# to remember and nothing to clean up later.
FLOORS_FROM = "2026-08-31"
FLOORS_NEW = {"stdev": 8.0, "over20_pct": 15.0}
FLOORS_OLD = {"stdev": 6.0, "over20_pct": 0.0}


def load_targets():
    """voice-corpus/targets.json, written by scripts/derive_voice_targets.py from the
    creator's REAL unscripted speech in the target register. Added 2026-08-30.

    Until this existed every band in this file was a guess, and one of them was doing
    active harm. `mean 9 to 13` was set from a pooled corpus that is 76% casual banter
    (median 7). the creator's unscripted speech ABOUT WORK, which is what this show is, runs
    mean 17.8 and median 17. So for weeks the gate required sentences about half the
    length of how he actually talks about business, every batch was written to satisfy
    it, and he kept reporting that the results read as written prose with weird
    structure. He was right and the gate was the cause."""
    p = os.path.join(RADAR, "voice-corpus", "targets.json")
    if not os.path.exists(p):
        return None
    try:
        with open(p) as fh:
            return json.load(fh)
    except Exception:
        return None


TARGETS = load_targets()


def floors_for(week_date):
    """Measured floors when targets.json is present, else the old guesses.

    The MEAN band is centred on his measured mean with a tolerance wide enough that a
    performed 60-second script is not forced to match conversational scatter exactly.
    Everything else is read straight off the profile."""
    if TARGETS:
        sw = TARGETS["sentence_words"]
        sh = TARGETS["shape"]
        return {
            "stdev": max(4.0, round(sw["stdev"] * 0.6, 1)),
            "over20_pct": max(0.0, round(sh["pct_over_20"] * 0.6, 1)),
            "mean_lo": round(sw["mean"] - 4.5, 1),
            "mean_hi": round(sw["mean"] + 4.5, 1),
            "p90": sw["p90"],
            "_measured": True,
        }
    return FLOORS_NEW if (week_date or "") >= FLOORS_FROM else FLOORS_OLD


def verdict(fp, fid=None, tri=None, floors=None):
    """Gates from references/voice-fingerprint.md. Returns a list of failures."""
    floors = floors or FLOORS_NEW
    fails = []
    if fid is not None and fid < 0.90:
        fails.append(f"FIDELITY {fid:.2f} below 0.90, the model is ghostwriting")
    if tri is not None and tri < 0.50:
        fails.append(f"TRIGRAM {tri:.2f} below 0.50, sentences are not the creator's")
    if not fp:
        return ["empty script"]
    p90 = floors.get("p90", 25)
    if fp["max"] < p90:
        fails.append(f"longest sentence {fp['max']}w, below the p90 of his own speech "
                     f"({p90}w). The old rule asked for 25, which a 26-word sentence "
                     f"satisfied, and that is how 8 homogenised scripts passed on 08-30.")
    if fp.get("over20_pct", 0) < floors["over20_pct"]:
        fails.append(f"only {fp.get('over20_pct', 0):.0f}% of sentences over 20 words "
                     f"(target {floors['over20_pct']:.0f}%), the long causal run is missing")
    if fp["min"] > 5:
        fails.append(f"no sentence under 5 words (shortest {fp['min']}), no variance")
    if fp["stdev"] < floors["stdev"]:
        fails.append(f"stdev {fp['stdev']} below {floors['stdev']:.0f}, cadence is flat")
    lo = floors.get("mean_lo", 9)
    hi = floors.get("mean_hi", 13)
    if not lo <= fp["mean"] <= hi:
        src = ("his measured work-speech mean of "
               f"{TARGETS['sentence_words']['mean']}" if floors.get("_measured")
               else "the pre-2026-08-30 guess")
        fails.append(f"mean {fp['mean']} outside {lo} to {hi} (band from {src})")
    return fails


# ---- the SPOKEN gate (warn only) -------------------------------------------
# Added 2026-08-16. The cadence half above is necessary and not sufficient: the whole
# 08-17 batch passed mean, stdev, long-run and short-line and the creator still rejected it
# for sounding written. These are the axes cadence never looked at.
#
# The thresholds are delivery evidence, not taste. From the five filmed 08-10 reads
# (~12.6 min, whisper word-level plus a silence-accurate segmenter):
#   - the news-open beats went in ONE take, 5/5. Every multi-take line was a takeaway
#     or a button. So this gate is POSITION-AWARE and leans on the closing slots;
#     gating the opens means fixing prose that already works.
#   - worst line, 5 attempts: "Every hour your buyer needs a person is an hour you pay
#     for forever." Uncontracted, symmetrical, 24 words. Three aborts broke at the
#     symmetry pivot.
#   - where he did NOT restart he silently rewrote toward speech, always the same
#     direction: runways into fragments, spoken connectives, periphrastic frames.
#   - Disney's scripted cold open, a two-beat epigram, he skipped entirely. It cost the
#     episode its hook. That is the strongest single argument for the epigram ban.
#   - Coors' button "built a sequence" became "what Coors Light did was buy a sequence",
#     which overwrote the built/buy contrast the argument rested on. He could not say
#     the epigram and the repair he could say destroyed the point.
# Caveat kept on purpose: n is small, one session, and fatigue is confounded (the
# 5-attempt line sits 123s into a 168s take). Position in take may do some of this
# work. It does not explain the Disney skip, which was at 0s.

CONTRACTION_FLOOR = 0.55          # closing slots
CONTRACTION_FLOOR_WHOLE = 0.35    # whole script, a looser sanity line

FRANCHISE = re.compile(r"^so how does .+ actually sells?\?$", re.I)
# the three approved takeaway openers (references/the-show.md, creator's call 2026-08-02).
# These are franchise glue like the device: they are SUPPOSED to repeat, so they are
# exempt from the seam and lecture checks. Only ADJACENCY is policed.
APPROVED_TAKEAWAY = re.compile(
    r"here'?s how you can do the same\.|here'?s what you can learn\.|"
    r"here'?s what you can apply from this lesson\.", re.I)
TAKEAWAY_SLOT = re.compile(
    r"here'?s (?:how|what) you can\b|\bthe (?:lesson|takeaway|point) (?:here )?is\b",
    re.I)

UNCONTRACTED = re.compile(
    r"\b(it is|that is|there is|here is|what is|he is|she is|they are|you are|"
    r"we are|i am|do not|does not|did not|is not|are not|was not|were not|"
    r"will not|would not|should not|could not|cannot|have not|has not|had not|"
    r"let us|you will|we will|they will|you have|we have|they have)\b", re.I)
CONTRACTED = re.compile(r"\b\w+['’](s|t|re|ve|ll|d|m)\b", re.I)

# banned outright by voice-card.md, not rationed
EPIGRAM = re.compile(
    r"\b(?:is|are|was|were)\s+not\s+(?:a|an|the)?\s*\w+[.,]\s*"
    r"(?:it|that|they|it'?s|that'?s)\s+(?:is|are|'s)?\s*(?:a|an|the)?\s*\w+", re.I)
NEG_PARALLEL = re.compile(r"\bit'?s not just \w+.{0,24}it'?s\b", re.I)

# an essay's stage directions and strawmen. The approved takeaway lines are NOT here.
LECTURE = [
    (re.compile(r"\bthe assumption is\b|\bthe answer everyone gives is\b", re.I),
     "the strawman beat, verbatim from the template"),
    (re.compile(r"\bwhat (?:this|that) (?:teaches|tells) (?:us|you)\b", re.I),
     "\"what this teaches us\", lecture register"),
    (re.compile(r"\bnotice what\b|\bwatch what\b", re.I),
     "\"notice/watch what\", a stage direction to a reader"),
]

SEAM_FAMILIES = [
    ("strawman", re.compile(
        r"\b(the assumption is|the answer everyone gives is|everyone says|"
        r"everyone credits|everyone thinks|the obvious read is)\b", re.I)),
    ("naming", re.compile(
        r"\bthat'?s the (?:whole|trick|campaign|deal|method|strategy|point)\b"
        r"|\bthat is the (?:whole|trick|campaign|deal|method|strategy|point)\b", re.I)),
]


def _paras(text):
    return [p.strip() for p in text.split("\n") if p.strip()]


def _norm(s):
    return [w.lower().strip(".,;:!?\"'") for w in s.split() if w.strip(".,;:!?\"'")]


def contraction_rate(text):
    """(rate, [phrases]) or (None, []) when there is too little to judge."""
    unc = UNCONTRACTED.findall(text)
    con = CONTRACTED.findall(text)
    if len(unc) + len(con) < 3:
        return None, []
    return (len(con) / (len(unc) + len(con)),
            [m.group(0).lower() for m in UNCONTRACTED.finditer(text)])


def symmetric_pairs(text):
    """Adjacent sentences, or comma/and limbs, running the same frame at near-equal
    length. The shape that broke three takes at the pivot."""
    out = []
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
    for a, b in zip(sents, sents[1:]):
        wa, wb = _norm(a), _norm(b)
        if not (4 <= len(wa) <= 26 and 4 <= len(wb) <= 26):
            continue
        if abs(len(wa) - len(wb)) > max(3, 0.35 * max(len(wa), len(wb))):
            continue
        if wa[0] == wb[0] or (len(wa) > 1 and len(wb) > 1 and wa[1] == wb[1]):
            out.append(f"{a}  ||  {b}")
    for s in sents:
        limbs = [l for l in re.split(r",| and ", s) if len(_norm(l)) >= 3]
        for a, b in zip(limbs, limbs[1:]):
            wa, wb = _norm(a), _norm(b)
            if len(wa) >= 4 and abs(len(wa) - len(wb)) <= 1 and wa[0] == wb[0]:
                out.append(s.strip())
                break
    return out


def epigram_hits(text):
    out = ["antithesis epigram (banned outright): \"%s\"" % m.group(0).strip()
           for m in EPIGRAM.finditer(text)]
    if NEG_PARALLEL.search(text):
        out.append("negative parallelism (\"it's not just X, it's Y\"), banned")
    return out


def slots(text):
    """{'open', 'body', 'takeaway', 'button'}. Beats are positional, not syntactic."""
    ps = _paras(text)
    if not ps:
        return {"open": [], "body": [], "takeaway": [], "button": None}
    dev = next((i for i, p in enumerate(ps) if FRANCHISE.match(p)), None)
    rest = ps[dev + 1:] if dev is not None else ps[1:]
    button = rest[-1] if rest else None
    mid = rest[:-1] if rest else []
    return {
        "open": ps[:dev + 1] if dev is not None else ps[:1],
        "body": [p for p in mid if not TAKEAWAY_SLOT.search(p)],
        "takeaway": [p for p in mid if TAKEAWAY_SLOT.search(p)],
        "button": button,
    }


def spoken_report(text, script_class="testimony"):
    """Position-weighted warnings. Never fails a batch."""
    sl = slots(text)
    warns = []

    rate, phrases = contraction_rate(text)
    if rate is not None and rate < CONTRACTION_FLOOR_WHOLE:
        warns.append("contractions %.0f%% across the script (speech runs 80-90%%): %s"
                     % (rate * 100, ", ".join(sorted(set(phrases))[:5])))

    closing = " ".join(sl["takeaway"] + ([sl["button"]] if sl["button"] else []))
    if closing:
        crate, _ = contraction_rate(closing)
        if crate is not None and crate < CONTRACTION_FLOOR:
            warns.append("closing slots only %.0f%% contracted; these are the beats "
                         "that took multiple takes on 08-10" % (crate * 100))

    button = sl["button"]
    if button:
        why = list(epigram_hits(button))
        brate, bph = contraction_rate(button)
        if brate is not None and brate < CONTRACTION_FLOOR:
            why.append("button %.0f%% contracted (%s)"
                       % (brate * 100, ", ".join(bph[:3])))
        sym = symmetric_pairs(button)
        if sym:
            why.append("button is balanced/symmetrical: \"%s\"" % sym[0][:70])
        warns += ["button: " + w for w in why]
        if len(why) >= 2:
            warns.append("button: FULL RISK STACK on the terminal beat, the shape that "
                         "took 5 takes on Atlassian and got skipped on Disney")

    for p in sl["takeaway"]:
        warns += ["takeaway: " + e for e in epigram_hits(p)]
        for s in symmetric_pairs(p)[:1]:
            warns.append("takeaway is symmetrical: \"%s\"" % s[:70])

    warns += [why for rx, why in LECTURE if rx.search(text)]

    if not (QUOTED.search(text) or re.search(r"[\"“][^\"”]{0,200}?(?:\s+\S+){2,}[\"”]", text)):
        # CONDITIONAL ON SUPPLY, changed 2026-08-24, and this is a fabrication fix rather
        # than a style change. The unconditional version of this warning demanded a quote
        # whether or not one existed. A research script whose sources contain no usable
        # quote has exactly two ways to clear it: leave the warning standing, or invent a
        # quote. On 2026-08-23 a batch invented two, and an invented quote satisfies every
        # check in this file perfectly because they all look at shape rather than source.
        # So the demand is now scoped to the class that has a capture to draw a real quote
        # from. For research, no quote available means no quote, and the script ships.
        if script_class == "testimony":
            warns.append("no quoted dialogue, and this is testimony: the capture has one, "
                         "use it (constitution rule 4, a person and a quoted line are the spine)")

    # A script with no first person reads as an essay rather than a person talking, and it
    # is upstream of a low contraction density, because "I'm" cannot appear in a script
    # with no "I" in it. Warn only: some formats legitimately carry none.
    if not re.search(r"\b(I|I'm|I've|I'd|I'll|me|my|mine)\b", text):
        warns.append("no first person anywhere: reserved for receipts, mistakes and "
                     "ownership does not mean absent")
    return warns


def batch_spoken(scripts_in_order):
    """[(id, text)] in slate order. Batch-level seams the cadence clash cannot see:
    it compares OPENING lines only, and the 08-17 batch passed that with five
    different openings while all five middles ran the same beats."""
    out = []
    for name, rx in SEAM_FAMILIES:
        hits = [sid for sid, t in scripts_in_order if rx.search(t)]
        if len(hits) > 1:
            out.append("%s beat repeats in %d/%d scripts: %s"
                       % (name, len(hits), len(scripts_in_order), ", ".join(hits)))

    seen = {}
    for sid, t in scripts_in_order:
        for p in _paras(t):
            if FRANCHISE.match(p) or APPROVED_TAKEAWAY.search(p):
                continue
            ws = _norm(p)
            if len(ws) >= 4:
                seen.setdefault(" ".join(ws[:4]), set()).add(sid)
    for seam, ids in sorted(seen.items(), key=lambda x: -len(x[1])):
        if len(ids) > 1:
            out.append("paragraph opening \"%s...\" repeats in %d scripts"
                       % (seam, len(ids)))

    # the approved takeaway lines are meant to repeat, but not back to back
    prev = None
    for sid, t in scripts_in_order:
        m = APPROVED_TAKEAWAY.search(t)
        cur = m.group(0).lower() if m else None
        if cur and cur == prev:
            out.append("takeaway line \"%s\" used on two ADJACENT episodes (%s); "
                       "the-show.md says rotate" % (cur, sid))
        prev = cur
    return out


def opening_shape(script):
    """Crude syntactic shape of the first sentence, for batch cadence clash."""
    s = sentences(script)
    if not s:
        return "empty"
    first = s[0].split()
    return " ".join(w.lower() if w.lower() in
                    {"i", "you", "we", "they", "he", "she", "the", "a", "this",
                     "there", "so", "and", "but", "here", "two", "three", "every",
                     "most", "your", "my", "it"} else "X"
                    for w in first[:4])


# ---- the LinkedIn gate ------------------------------------------------------
# Added 2026-08-13. Before this, run_week walked distribution[] + office[] only,
# so nothing in the linkedin[] lane and no embedded twin body was reachable by
# any machine check: they could be born pre-QA and never leave it. A post has no
# capture and is read rather than spoken, so fidelity and cadence do not apply.
# What does apply is the numeral law, the source law, and a legal qa value. The
# two-question gate stays a human read, it always was.

ALLOWED_QA = {"passed", "pending-approval"}

CARDINALS = (
    "two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen twenty thirty forty "
    "fifty sixty seventy eighty ninety"
).split()

SCALES = ["hundred", "thousand", "million", "billion", "trillion"]

# 'one' is deliberately never flagged: it is nearly always the determiner
# ("pick one use case", "the only one"), and nobody writes "1 use case".
# Ordinals are prose for the same reason.
ORDINALS = set("first second third fourth fifth sixth seventh eighth ninth "
               "tenth".split())

# a number word sitting AFTER one of these is a label, not a quantity:
# "move two", "day two", "phase three". Those stay words.
LABEL_NOUNS = set("move day step phase card part option week slot round tier "
                  "act chapter version edition no".split())


def numeral_law(body):
    """SKILL.md: every number is a numeral, never spelled out in letters.

    Returns (fails, warns). The split is the point: 'Six percent do not' is
    unarguable, while 'Half right' is a rhetorical half that would acquire
    false precision as '50%'. Fails are mechanical, warns want a human.
    """
    fails, warns = [], []
    toks = re.findall(r"[A-Za-z%$']+|\d[\d.,]*", body)
    low = [t.lower() for t in toks]
    for i, t in enumerate(low):
        prev = low[i - 1] if i else ""
        nxt = low[i + 1] if i + 1 < len(low) else ""
        ctx = " ".join(toks[max(0, i - 4):i + 3])
        if t in ("half", "twice", "double"):
            warns.append(f"'{t}' spelled out: ...{ctx}...")
        elif t == "one" or t in ORDINALS:
            continue
        elif t in SCALES:
            # '$1.8 billion' is correct usage. A bare 'billion' is not.
            if not re.match(r"^\d", prev):
                fails.append(f"scale word '{t}' with no numeral in front: ...{ctx}...")
        elif t in CARDINALS:
            if nxt in ("percent", "per"):
                fails.append(f"spelled-out stat '{t} percent': ...{ctx}...")
            elif prev not in LABEL_NOUNS:
                fails.append(f"spelled-out number '{t}': ...{ctx}...")
    return fails, warns


def source_law(body, sources):
    """Every number that gets read has a URL behind it."""
    figures = re.findall(r"\$\s?\d[\d.,]*|\bEUR\s?\d[\d.,]*|\b\d[\d.,]*\s?%", body)
    urls = [s.get("url") for s in (sources or [])
            if isinstance(s, dict) and s.get("url")]
    if figures and not urls:
        return [f"{len(figures)} figure(s) in the body, no source URL on the item: "
                f"{figures[:4]}"]
    return []


def run_linkedin(d):
    """The linkedin[] lane plus every embedded twin body."""
    rows = [(p.get("id"), p, p.get("sources"), "lane")
            for p in d.get("linkedin", [])]
    for it in d.get("distribution", []):
        tw = it.get("linkedin")
        if tw:
            # the twin borrows the parent episode's already-verified sources
            rows.append((tw.get("id"), tw, it.get("sources"), "twin"))

    if not rows:
        return 0
    print(f"\n--- LinkedIn gate: {len(rows)} posts ---")

    # tracking is keyed by id in both the dashboard's localStorage and
    # performance.jsonl ("latest measured per id wins"), so a duplicate id means
    # one post silently overwrites the other's numbers. Twins and the lane were
    # numbered independently and collided the first week both were populated.
    dupes = [i for i, n in Counter(r[0] for r in rows).items() if n > 1]
    if dupes:
        print(f"!! DUPLICATE IDS: {sorted(dupes)}")
        print("   each points at two different posts; measurement keyed on id "
              "will overwrite one with the other")

    bad = 0
    for pid, post, sources, kind in rows:
        body = post.get("body", "") or ""
        fails, warns = numeral_law(body)
        fails += source_law(body, sources)
        qa = post.get("qa")
        if qa not in ALLOWED_QA:
            fails.append(f"qa={qa!r} is not a state the dashboard can render; "
                         f"legal values are {sorted(ALLOWED_QA)}")
        flag = "PASS" if not fails else "FAIL"
        if fails:
            bad += 1
        print(f"[{flag}] {pid}  ({kind}, {len(words(body))} words, qa={qa})")
        for f in fails:
            print(f"        {f}")
        for w in warns:
            print(f"        warn: {w}")
    print(f"{bad}/{len(rows)} failed the LinkedIn gate")
    print("two-question gate (insider-entertaining AND usable, creator's call 2026-08-19) is still a human read")
    return bad


def run_week(path):
    d = json.load(open(path))
    items = d.get("distribution", []) + d.get("office", [])
    shapes = Counter()
    classes = Counter()
    spoken = {}
    bad = 0
    floors = floors_for(d.get("week", ""))
    note = "" if floors is FLOORS_NEW else (
        f"  (cadence floors: pre-{FLOORS_FROM}, stdev {floors['stdev']:.0f}, long-run rule off. "
        f"This week was written before the 2026-08-24 recalibration.)")
    print(f"{len(items)} scripts in {os.path.basename(path)}{note}\n")
    if TARGETS is None:
        # PRODUCTION SAFETY, added 2026-08-30. Falling back silently to the pre-2026-08-30
        # constants would hand every new creator the exact defect that broke 8 of the creator's
        # scripts: a mean band of 9 to 13 when his real work speech measures 17.8. The
        # numbers below were never measured against anyone's voice, so say so loudly rather
        # than let a creator write a whole batch to them believing they are grounded.
        print("!! NO voice-corpus/targets.json: cadence bands are UNVALIDATED DEFAULTS,")
        print("!! not measured against your voice. They are the numbers that made 8 scripts")
        print("!! read as written prose on 2026-08-30 (they demanded sentences roughly half")
        print("!! the length of real unscripted speech about work).")
        print("!! Fix, once, about 30 minutes: record yourself talking through 4-5 subjects")
        print("!! in your niche unscripted, drop the transcripts in capture/, then run")
        print("!!   python3 scripts/segment_corpus.py && python3 scripts/derive_voice_targets.py")
        print()
    for it in items:
        # FIDELITY is testimony-only: it compares a script against a capture on disk, and
        # research has no capture by design. CADENCE is not. The original skip sent
        # `research` down the same branch as `format` and measured neither, which was
        # right until 2026-08-01, when the show became fully-authored research class
        # written in the creator's voice. From then on the fingerprint targets applied to it and
        # nothing checked them: on 2026-08-16 three of five episodes in weeks/2026-08-17
        # were shipping under stdev 6 with no sentence over 25 words, and the PostHog cut
        # was rejected by the creator for reading badly out loud before any tool caught it.
        # So: `format` still skips (beats, often no prose at all), `research` now gets the
        # cadence half of the gate and skips only the capture-dependent half.
        cls = it.get("script_class", "testimony")
        classes[cls] += 1
        if cls == "format":
            print(f"[ -- ] {it.get('id')}  script_class=format, format gate applies, not measured here")
            continue

        # the hook and the body are one continuous read on the dashboard, so measure
        # them together: a quote that lives in spoken_hook still counts
        script = ((it.get("spoken_hook", "") or "") + "\n" + (it.get("script", "") or "")).strip()
        fp = fingerprint(script)
        cap = (it.get("capture") or {})
        fid = tri = None
        src = cap.get("source")
        if src and os.path.exists(os.path.join(RADAR, src)):
            captext = open(os.path.join(RADAR, src)).read()
            fixes = cap.get("fact_fixes", [])
            fid = fidelity(captext, script, fixes)
            tri = trigram_share(captext, script, fixes)
        fails = verdict(fp, fid, tri, floors)
        if fid is None and cls == "testimony":
            # a testimony script with no resolvable capture is not measurable, and
            # unmeasurable means unfilmable (audit 2026-07-26): never print n/a as a pass
            fails.append("NO CAPTURE SOURCE on disk; testimony without a capture is not filmable")
        shapes[opening_shape(script)] += 1
        flag = "PASS" if not fails else "FAIL"
        if fails:
            bad += 1
        shown = f"{fid:.2f}" if fid is not None else "n/a"
        print(f"[{flag}] {it.get('id')}  mean {fp.get('mean')} max {fp.get('max')} "
              f"stdev {fp.get('stdev')} quoted {fp.get('quoted_dialogue')} "
              f"fidelity {shown}")
        for f in fails:
            print(f"        {f}")
        # the spoken gate never fails a batch, it only tells you what will fight the
        # mouth on the day. Collected here so it prints next to the cadence numbers
        # it is meant to qualify.
        spoken[it.get("id")] = script
        for w in spoken_report(script, cls):
            print(f"        warn: {w}")
    clash = [(s, n) for s, n in shapes.most_common() if n > 1]
    print(f"\nclass distribution: {dict(classes)}  (watch for drift toward convenient format/research tagging)")
    print(f"{bad}/{len(items)} failed the fingerprint gate")
    if clash:
        print("cadence clash, these openings repeat:")
        for s, n in clash:
            print(f"   {n}x  '{s}...'")
    else:
        print("no cadence clash")

    # NOTE opening_shape() reduces the first 4 tokens to a stopword mask, so any
    # declarative opening with 4 content words reads as 'X X X X' and clashes with
    # every other one. Treat a clash it reports as a prompt to look, never as a
    # reason to rewrite copy. The batch check below is the one with teeth.
    batch = batch_spoken(list(spoken.items()))
    if batch:
        print("\nspoken gate, batch level (warn only):")
        for b in batch:
            print(f"   {b}")
    else:
        print("\nspoken gate, batch level: no shared seams")

    run_linkedin(d)


def main():
    if "--week" in sys.argv:
        run_week(sys.argv[sys.argv.index("--week") + 1])
        return
    if len(sys.argv) < 3:
        print(__doc__)
        return
    capture = open(sys.argv[1]).read()
    script = open(sys.argv[2]).read()
    fixes = []
    if "--fact-fix" in sys.argv:
        fixes = sys.argv[sys.argv.index("--fact-fix") + 1:]
    fid = fidelity(capture, script, fixes)
    tri = trigram_share(capture, script, fixes)
    fp = fingerprint(script)
    print(f"fidelity        {fid:.2f}   (>= 0.90)   trigrams {tri:.2f} (>= 0.50)"
          + (f"   [{len(fixes)} declared fact fix]" if fixes else ""))
    print(f"sentences       {fp['sentences']}  mean {fp['mean']}  median {fp['median']}  "
          f"min {fp['min']}  max {fp['max']}  stdev {fp['stdev']}")
    print(f"quoted dialogue {fp['quoted_dialogue']}")
    print(f"spoken words    {fp['words']}  (~110 for 34s, ~170 for 55s)")
    fails = verdict(fp, fid, tri)
    print("\nPASS" if not fails else "\nFAIL")
    for f in fails:
        print(f"  {f}")


if __name__ == "__main__":
    main()

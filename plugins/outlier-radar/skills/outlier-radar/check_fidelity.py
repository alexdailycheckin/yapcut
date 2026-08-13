#!/usr/bin/env python3
"""
The objective half of QA. Replaces "the model grades its own read-aloud test".

Three checks:
  1. FIDELITY  what share of the finished script's words came from the capture.
               Below 0.90 the model started ghostwriting again.
  2. FINGERPRINT  does the script move like Alex talks, per references/voice-fingerprint.md.
  3. LINKEDIN  the numeral law, the source law, and a legal qa value, run over the
               linkedin[] lane and every embedded twin body. Video-only until
               2026-08-13, which is why written posts could never leave pre-QA.

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
        "quoted_dialogue": bool(QUOTED.search(script)),
        "words": sum(lens),
    }


def verdict(fp, fid=None, tri=None):
    """Gates from references/voice-fingerprint.md. Returns a list of failures."""
    fails = []
    if fid is not None and fid < 0.90:
        fails.append(f"FIDELITY {fid:.2f} below 0.90, the model is ghostwriting")
    if tri is not None and tri < 0.50:
        fails.append(f"TRIGRAM {tri:.2f} below 0.50, sentences are not the creator's")
    if not fp:
        return ["empty script"]
    if fp["max"] < 25:
        fails.append(f"no sentence over 25 words (longest {fp['max']}), flat machine rhythm")
    if fp["min"] > 5:
        fails.append(f"no sentence under 5 words (shortest {fp['min']}), no variance")
    if fp["stdev"] < 6:
        fails.append(f"stdev {fp['stdev']} below 6, cadence is flat")
    if not 9 <= fp["mean"] <= 13:
        fails.append(f"mean {fp['mean']} outside 9 to 13")
    return fails


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
    print("two-question gate (insider-entertaining OR usable) is still a human read")
    return bad


def run_week(path):
    d = json.load(open(path))
    items = d.get("distribution", []) + d.get("office", [])
    shapes = Counter()
    classes = Counter()
    bad = 0
    print(f"{len(items)} scripts in {os.path.basename(path)}\n")
    for it in items:
        # only `testimony` is measured. `format` scripts often have no prose at all and
        # `research` narration is verified facts about someone else, so both are gated
        # elsewhere (see the class gates in SKILL.md).
        cls = it.get("script_class", "testimony")
        classes[cls] += 1
        if cls != "testimony":
            print(f"[ -- ] {it.get('id')}  script_class={cls}, "
                  f"{'format gate' if cls == 'format' else 'research gate'} applies, not measured here")
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
        fails = verdict(fp, fid, tri)
        if fid is None:
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
    clash = [(s, n) for s, n in shapes.most_common() if n > 1]
    print(f"\nclass distribution: {dict(classes)}  (watch for drift toward convenient format/research tagging)")
    print(f"{bad}/{len(items)} failed the fingerprint gate")
    if clash:
        print("cadence clash, these openings repeat:")
        for s, n in clash:
            print(f"   {n}x  '{s}...'")
    else:
        print("no cadence clash")

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

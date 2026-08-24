#!/usr/bin/env python3
"""spoken_lint.py: catch the shapes that pass a cadence gate and still sound written.

WHY THIS EXISTS.

check_fidelity.py measures the DISTRIBUTION of sentence length: a mean band, one long
sentence, one short one, a stdev floor. It never looks at ARRANGEMENT. That gap has a
cost, because the cheapest way to buy stdev and satisfy "one short sentence" is to stack
two-word fragments:

    Snacks, fintech, telecom, retail. One person. 4 industries.
    Defence. Government. Regulated codebases.

Both clear every cadence number. Neither is speech. Punchy is not the standard, because
plenty of machine writing is punchy; the standard is that a person would say the line out
loud without saying extra things.

THE THRESHOLD IS MEASURED, NOT INVENTED. The obvious detector, "3 short sentences in a
row", is wrong, and running --corpus against a real transcript shows why: people stack
short sentences constantly. What they do not do is stack VERBLESS NOUN LABELS. Their
short runs are speech acts, backchannel and self-interruption, and almost all of them
carry a verb. That is the whole discriminator, and it is why this file measures
verblessness rather than length.

Run `--corpus` to derive the thresholds from the creator's own voice corpus before
trusting the defaults, and re-derive them as the corpus grows. On the corpus this was
built against, a run of 2 noun labels appeared once in 379 sentences and a run of 3 never
appeared at all, so 2 grades medium and 3 or more grades high. Do not hand-set these.

This tool FLAGS. It does not rewrite. Only findings whose fix is a pure deletion are
touched by --apply-safe; everything else is left for a human, because a rewrite is a
writing decision and this is a linter.

Usage:
  python3 scripts/spoken_lint.py --week weeks/<date>.json
  python3 scripts/spoken_lint.py --week weeks/<date>.json --json out.json
  python3 scripts/spoken_lint.py --corpus
  python3 scripts/spoken_lint.py --week weeks/<date>.json --apply-safe

Exit 1 if anything was flagged, so a build step can gate on it.
"""
import argparse
import json
import pathlib
import re
import statistics
import sys

# --- verb detection --------------------------------------------------------
# No NLP dependency and none wanted. The fragments this has to judge are short and
# their vocabulary is small, so a curated finite-verb set plus contractions and a
# couple of morphology rules is accurate enough. Validated against a real transcript:
# with backchannel excluded it finds one noun-label run in 379 sentences of speech.
VERBS = set("""
am is are was were be been being get gets got getting have has had having do does did
doing go goes went going going come comes came make makes made making take takes took
say says said tell tells told know knows knew think thinks thought see sees saw look
looks looked want wants wanted need needs needed like likes liked use uses used try
tries tried put puts run runs ran ranks ranked rank buy buys bought sell sells sold
pay pays paid spend spends spent give gives gave gave find finds found work works worked
call calls called ask asks asked keep keeps kept let lets leave leaves left move moves
moved grow grows grew fell fall falls rose rise rises hire hires hired hiring build
builds built read reads write writes wrote publish publishes published cover covers
covered ship ships shipped launch launches launched cut cuts cost costs charge charges
lease leases leasing own owns owned convert converts converted approve approves approved
deploy deploys deployed license licenses licensed operate operates operating queue
queues stop stops stopped start starts started happen happens happened matter matters
prove proves proved beat beats won win wins lost lose loses show shows showed report
reports reported add adds added drew draws draw hand hands handed wheel wheels turn
turns turned bring brings brought seem seems appear appears becomes become became
can could will would shall should may might must cannot wont dont doesnt didnt isnt
arent wasnt werent havent hasnt hadnt cant couldnt wouldnt shouldnt lets teach teaches
love loves hate hates play plays swim swims remember remembers
""".split())

# Backchannel and discourse markers. These are verbless but they are SPEECH ACTS rather
# than noun labels, and speakers produce them constantly: on the corpus this was built
# against, every single verbless run in the transcript was made of these. Counting them
# as the written shape would flag the most human thing in the file, so a fragment led by
# one of these, or phrased as a question, is exempt.
INTERJ = set("""
yeah yes yep yup no nope nah okay ok alright right exactly sure wait yo hey hi hello
fuck shit damn wow oh ah huh hmm nice cool true same agreed thanks sorry please
maybe probably actually anyway honestly obviously literally basically well so
what why where when who how which whatever really seriously
""".split())
INTERJ_PHRASE = {"me too", "of course", "no way", "for sure", "not really", "i know",
                 "i mean", "you know", "that's it", "there you are"}

CONTRACTION = re.compile(r"\b\w+'(s|re|ll|ve|d|m|t)\b", re.I)
ING_ED = re.compile(r"\b\w{4,}(ing|ed)\b", re.I)


def is_speech_act(chunk: str) -> bool:
    """A verbless fragment that is still something a person says out loud."""
    s = chunk.strip()
    if s.endswith("?"):
        return True
    low = re.sub(r"[^\w\s']", "", s).strip().lower()
    if not low:
        return True
    if low in INTERJ_PHRASE:
        return True
    return low.split()[0] in INTERJ


def has_verb(chunk: str) -> bool:
    words = re.findall(r"[A-Za-z']+", chunk.lower())
    if not words:
        return False
    if any(w.strip("'") in VERBS for w in words):
        return True
    if CONTRACTION.search(chunk):
        return True
    if ING_ED.search(chunk):
        return True
    return False


NUMCOMMA = re.compile(r"(?<=\d),(?=\d)")


def split_chunks(sentence: str):
    """Comma chunks, with commas INSIDE numbers protected. Without this, 394,300 reads
    as two chunks and every figure in the batch looks like a list."""
    safe = NUMCOMMA.sub("\u0000", sentence.rstrip(".!?"))
    return [c.replace("\u0000", ",").strip() for c in safe.split(",") if c.strip()]


BULLET = re.compile(r"^\s*(?:[\u21b3\u2192\u2022\-\*]|\d+[.)])\s+")


def sentences(text: str):
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


# --- the checks ------------------------------------------------------------
NEG_PAIR = re.compile(r"\bno\s+[\w-]+\s*,\s*no\s+[\w-]+", re.I)
NEG_NOTJUST = re.compile(r"\b(it|that|this)(?:'s| is| was)\s+not\s+(just\s+)?[^.,;]{2,40}[,.]\s*(it|that|this)(?:'s| is| was)\b", re.I)
NEG_ISNOT = re.compile(r"\b(is|are|was|were)\s+not\s+[^.]{2,50}\.\s*(It|They|That)\s+(is|are|was|were)\b")
ABSENCE = re.compile(r"\b(nothing|nobody|no one|not one|zero)\b", re.I)
ABSENCE_ACTION = re.compile(r"\b(ran|bought|paid|spent|said|advertised|posted|placed|paid for|does|do)\b", re.I)
COLON_LIST = re.compile(r"^[^:]{3,60}:\s+[^.]*,[^.]*,", re.S)


def lint_text(text: str, where: str, spoken: bool):
    """spoken=True for script/hook fields, which are read aloud. Body fields are read
    on a screen, so the colon and table checks do not apply to them."""
    out = []
    sents = sentences(text)
    verbless = [(not has_verb(s)) and (not is_speech_act(s))
                and not (BULLET.match(s) and not spoken) for s in sents]

    # 1. verbless run: 2+ consecutive noun-label fragments
    i = 0
    while i < len(sents):
        if verbless[i]:
            j = i
            while j + 1 < len(sents) and verbless[j + 1]:
                j += 1
            n = j - i + 1
            if n >= 2:
                out.append({
                    "check": "verbless_run", "where": where,
                    "severity": "high" if n >= 3 else "medium",
                    "text": " ".join(sents[i:j + 1]),
                    "why": f"{n} verbless noun labels in a row. Speakers stack short "
                           f"sentences constantly, but those are speech acts. A run of "
                           f"bare noun labels is a caption read aloud, and it exists to "
                           f"buy cadence stdev cheaply. Run --corpus for the baseline.",
                    "fix": "needs-words",
                })
            i = j + 1
        else:
            i += 1

    for s in sents:
        # 2. verbless comma list inside one sentence
        chunks = split_chunks(s)
        if len(chunks) >= 3 and not has_verb(s) and not (BULLET.match(s) and not spoken):
            out.append({
                "check": "verbless_list", "where": where, "severity": "high",
                "text": s,
                "why": f"{len(chunks)} comma-separated noun chunks and no verb in the "
                       f"sentence. Same shape as the run, packed into one line.",
                "fix": "needs-words",
            })
        # 3. negative parallelism, already banned in voice-card section 7
        if NEG_PAIR.search(s) or NEG_NOTJUST.search(s) or NEG_ISNOT.search(s):
            out.append({
                "check": "negative_parallelism", "where": where, "severity": "high",
                "text": s,
                "why": "voice-card section 7 bans this outright: state the thing. The "
                       "negative half is setup, not information.",
                "fix": "delete-negative-clause",
            })
        # 4. unverifiable absence claim
        if (ABSENCE.search(s) and ABSENCE_ACTION.search(s)
                and not re.search(r"\b(you|your|yours|yourself)\b", s, re.I)):
            out.append({
                "check": "absence_claim", "where": where, "severity": "high",
                "text": s,
                "why": "asserts that something did not happen. No artifact can prove a "
                       "negative, so this can never carry a receipt, and the source gate "
                       "cannot see it because it holds no number, date or name.",
                "fix": "delete",
            })
        if spoken:
            # 5. a caption read aloud
            if COLON_LIST.match(s):
                out.append({
                    "check": "colon_list_spoken", "where": where, "severity": "medium",
                    "text": s,
                    "why": "a colon followed by a comma list. Nobody speaks a colon. This "
                           "is on-screen text with a voice over it.",
                    "fix": "needs-words",
                })

    # 6. a data table read aloud: 3+ consecutive short sentences that each carry a figure
    if spoken:
        numish = [bool(re.search(r"\d", s)) and len(s.split()) <= 10 for s in sents]
        i = 0
        while i < len(sents):
            if numish[i]:
                j = i
                while j + 1 < len(sents) and numish[j + 1]:
                    j += 1
                if j - i + 1 >= 3:
                    out.append({
                        "check": "number_table_spoken", "where": where, "severity": "medium",
                        "text": " ".join(sents[i:j + 1]),
                        "why": f"{j - i + 1} short figure-bearing sentences in a row. That is a "
                               f"table being read out. The pack's own rule says if the artifact "
                               f"on screen carries the number, do not read the number.",
                        "fix": "needs-words",
                    })
                i = j + 1
            else:
                i += 1
    return out


# --- the recalibrated per-script targets (voice-fingerprint.md, 2026-08-24) ----------
# Script-level floors. check_fidelity.py carries the same numbers as hard gates from
# 2026-08-31 onward; these stay here as a warn-only second opinion.
# Derive these from the creator's corpus with --corpus rather than trusting the numbers.
STDEV_FLOOR = 8.0        # unscripted speech ran 12.1 on the corpus this was built against
OVER20_FLOOR = 15.0      # unscripted speech ran 20.3% of sentences over 20 words
FIRST_PERSON = re.compile(r"\b(I|I'm|I've|I'd|I'll|me|my|mine)\b")


def check_targets(it):
    """Script-level floors. Separate from the sentence-level checks above because these
    describe the whole distribution, not one line."""
    import statistics
    out = []
    sents = sentences(it.get("script") or "")
    if len(sents) < 3:
        return out
    wc = [len(s.split()) for s in sents]
    sd = statistics.pstdev(wc)
    over20 = 100.0 * sum(1 for w in wc if w > 20) / len(wc)
    if sd < STDEV_FLOOR:
        out.append({"check": "stdev_floor", "where": f"{it['id']}.script", "severity": "high",
                    "text": f"stdev {sd:.1f}", "fix": "needs-words",
                    "why": f"below the floor of {STDEV_FLOOR}. Unscripted speech measured 12.1 on the "
                           f"reference corpus. A floor set at half the corpus gets passed, not failed."})
    if over20 < OVER20_FLOOR:
        out.append({"check": "long_run_floor", "where": f"{it['id']}.script", "severity": "high",
                    "text": f"{over20:.1f}% of sentences over 20 words", "fix": "needs-words",
                    "why": f"below {OVER20_FLOOR}%. Unscripted speech measured 20.3%. The long causal "
                           f"run is the voice and it is the thing most consistently missing."})
    if not any(FIRST_PERSON.search(s) for s in sents):
        out.append({"check": "no_first_person", "where": f"{it['id']}.script", "severity": "high",
                    "text": "no first person anywhere in the script", "fix": "needs-words",
                    "why": "a script with no first person reads as an essay rather than a person "
                           "talking, and it is upstream of low contraction density, because "
                           "\"I'm\" cannot appear in a script with no \"I\" in it. Reserving the "
                           "first person for receipts and ownership does not mean removing it."})
    return out


FIELDS_SPOKEN = ("spoken_hook", "script")
FIELDS_WRITTEN = ("body",)


def lint_week(path: pathlib.Path):
    d = json.loads(path.read_text(encoding="utf-8"))
    findings = []
    for lane in ("distribution", "office", "linkedin"):
        for it in d.get(lane) or []:
            # format class is a skit: speaker marks, deliberately clipped, words are the
            # trend's, not the creator's. Gate-1 only per constitution rule 3, so it is not held
            # to the spoken-prose standard and linting it only produces noise.
            if it.get("script_class") == "format":
                continue
            for f in FIELDS_SPOKEN:
                if it.get(f):
                    findings += lint_text(it[f], f"{it['id']}.{f}", spoken=True)
            for f in FIELDS_WRITTEN:
                if it.get(f):
                    findings += lint_text(it[f], f"{it['id']}.{f}", spoken=False)
            tw = it.get("linkedin")
            if isinstance(tw, dict) and tw.get("body"):
                findings += lint_text(tw["body"], f"{tw.get('id','twin')}.body", spoken=False)
            if lane == "distribution":
                findings += check_targets(it)
    return d, findings


def corpus_baseline():
    p = pathlib.Path(__file__).resolve().parent.parent / "voice-corpus" / "corpus.txt"
    if not p.exists():
        sys.exit("no voice-corpus/corpus.txt")
    sents = sentences(p.read_text(encoding="utf-8"))
    wc = [len(s.split()) for s in sents]
    verbless = [(not has_verb(s)) and (not is_speech_act(s)) for s in sents]
    runs, cur = [], 0
    for v in verbless:
        if v:
            cur += 1
        else:
            if cur:
                runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    print(f"unscripted corpus: {len(sents)} sentences, {sum(wc)} words")
    print(f"  mean {statistics.mean(wc):.1f}  median {statistics.median(wc):.0f}  "
          f"stdev {statistics.pstdev(wc):.1f}  longest {max(wc)}")
    print(f"  verbless NOUN-LABEL fragments (excluding backchannel): {sum(verbless)} ({100*sum(verbless)/len(sents):.1f}%)")
    print(f"  RUNS of 2+ noun labels: {sum(1 for r in runs if r >= 2)}   "
          f"longest run: {max(runs) if runs else 0}")
    print("\nRuns of 2 grade medium (he does that once in 379 sentences).")
    print("Runs of 3+ grade high (no precedent in the corpus at all).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week")
    ap.add_argument("--json")
    ap.add_argument("--corpus", action="store_true")
    ap.add_argument("--apply-safe", action="store_true",
                    help="apply ONLY the pure-deletion fixes, never a rewrite")
    a = ap.parse_args()

    if a.corpus:
        corpus_baseline()
        return

    if not a.week:
        sys.exit("need --week or --corpus")
    path = pathlib.Path(a.week)
    d, findings = lint_week(path)

    order = {"high": 0, "medium": 1}
    findings.sort(key=lambda f: (order.get(f["severity"], 9), f["where"]))
    by_check = {}
    for f in findings:
        by_check.setdefault(f["check"], []).append(f)

    for f in findings:
        print(f"\n[{f['severity'].upper()}] {f['check']}  {f['where']}")
        print(f"  > {f['text'][:190]}")
        print(f"  why: {f['why']}")
        print(f"  fix: {f['fix']}")

    print(f"\n{len(findings)} flagged in {path.name}")
    for k, v in sorted(by_check.items(), key=lambda kv: -len(kv[1])):
        print(f"  {k:24} {len(v)}")
    safe = [f for f in findings if f["fix"] == "delete"]
    print(f"\n{len(safe)} are a pure deletion. The rest need a human, because a "
          f"rewrite is a writing decision and this is a linter.")

    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(findings, indent=2, ensure_ascii=False),
                                        encoding="utf-8")
        print(f"wrote {a.json}")

    if a.apply_safe and safe:
        bak = path.with_suffix(path.suffix + ".bak-spokenlint")
        bak.write_text(json.dumps(d, indent=2, ensure_ascii=False), encoding="utf-8")
        raw = path.read_text(encoding="utf-8")
        n = 0
        for f in safe:
            frag = json.dumps(f["text"], ensure_ascii=False)[1:-1]
            if frag in raw:
                raw = raw.replace(frag + " ", "", 1) if frag + " " in raw else raw.replace(frag, "", 1)
                n += 1
        path.write_text(raw, encoding="utf-8")
        print(f"applied {n} deletion(s). backup at {bak.name}. Re-run check_fidelity.py.")

    sys.exit(1 if findings else 0)


if __name__ == "__main__":
    main()

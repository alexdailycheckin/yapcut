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

SEVERITY AND EXIT CODES (Contract 1, 2026-09-09).
  high    a categorical, provable or ledger-backed defect: a verbless run or list, a
          rejected phrase, negative parallelism, an absence claim. rc 2.
  medium  a distribution or arrangement finding that wants a human read: the cadence
          floors, the flat tail, the speech-marker rate, colon lists, number tables. rc 1.
  warn    an onboarding state, not a defect: no targets.json yet. rc 1.
`--strict-cadence` grades the cadence findings high again; that flip is the creator's call.

Before 2026-09-09 the cadence floors here were hand-set (STDEV_FLOOR 8.0, OVER20_FLOOR
15.0) under a comment saying to derive them, and a missing targets.json was a HIGH finding
on every fresh install. Both are fixed: floors read from targets.json when it exists, and
the zero-of-five speech-marker test is now a RATE against the corpus, because a batch can
carry one "like" per script and still run at a tenth of how the creator talks.

Usage:
  python3 spoken_lint.py --week weeks/<date>.json [--dir <workspace>]
  python3 spoken_lint.py --week weeks/<date>.json --json out.json
  python3 spoken_lint.py --corpus
  python3 spoken_lint.py --week weeks/<date>.json --apply-safe
  python3 spoken_lint.py --week weeks/<date>.json --strict-cadence
"""
import argparse
import json
import os
import pathlib
import re
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yapcut_home import radar_home  # noqa: E402

# Consumed here so argparse below never sees --dir. The lint itself can run without a
# workspace (targets become a WARN); --corpus cannot, and asks again with required=True.
HOME = radar_home(required=False)

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


BULLET = re.compile(r"^\s*(?:[↳→•\-\*]|\d+[.)])\s+")


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


# --- the per-script cadence floors --------------------------------------------------
# Read from targets.json when it exists (stdev and over-20 share at 60% of the measured
# corpus value, the same derivation check_fidelity.py uses so the two tools agree on a
# batch). The constants below are the pre-2026-09-09 hand-set fallbacks and only apply
# when no corpus has been measured yet, which the no_targets WARN already announces.
FLOORS_FROM = "2026-08-31"   # mirrors check_fidelity.py: never fail work written to the old bar
STDEV_FLOOR = 8.0        # fallback: unscripted speech ran 12.1 on the corpus this was built against
OVER20_FLOOR = 15.0      # fallback: unscripted speech ran 20.3% of sentences over 20 words
FIRST_PERSON = re.compile(r"\b(I|I'm|I've|I'd|I'll|me|my|mine)\b")

# Findings in this set describe a distribution, not a defect. They grade medium unless
# --strict-cadence (set in main) says otherwise.
CADENCE_CHECKS = {"stdev_floor", "long_run_floor", "tail_flat", "batch_no_runaway",
                  "marker_rate"}
STRICT_CADENCE = False

# A batch whose speech-marker rate sits under this share of the corpus rate is written
# prose with a few markers sprinkled on. 25% is generous on purpose: a performed script is
# tighter than a call, and the point is to catch a tenth of the rate, not two thirds.
MARKER_RATE_FLOOR = 0.25

# Measured numbers worth printing even when they clear a floor, so a pass is a number
# and not a silence. Filled by the batch checks, printed once in main.
INFO = []


def _cadence(sev):
    return "high" if STRICT_CADENCE else sev


def _floors(targets):
    if targets:
        sw, sh = targets.get("sentence_words", {}), targets.get("shape", {})
        return (max(4.0, round(float(sw.get("stdev", STDEV_FLOOR / 0.6)) * 0.6, 1)),
                max(0.0, round(float(sh.get("pct_over_20", OVER20_FLOOR / 0.6)) * 0.6, 1)),
                "measured")
    return STDEV_FLOOR, OVER20_FLOOR, "fallback"


def load_targets():
    """The measured profile from voice-corpus/targets.json, or None. Written by
    derive_voice_targets.py. Added 2026-08-30: before this, every threshold in
    this file was a guess, because the --corpus mode meant to replace them could never
    find the corpus (symlink + Path.resolve, see yapcut_home.py)."""
    if HOME is None:
        return None
    p = HOME / "voice-corpus" / "targets.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def load_rejections():
    """Phrases the creator has explicitly killed. See voice-corpus/rejections.json for why this
    is the only layer that accumulates his taste across sessions."""
    if HOME is None:
        return []
    p = HOME / "voice-corpus" / "rejections.json"
    if not p.exists():
        return []
    try:
        return json.loads(p.read_text(encoding="utf-8")).get("rejections", [])
    except Exception:
        return []


def check_rejected(it):
    """FAIL on any phrase the creator has already rejected. Absolute, not a threshold: they said
    it, so it does not ship again."""
    out = []
    text = ((it.get("spoken_hook") or "") + "\n" + (it.get("script") or it.get("body") or ""))
    for r in load_rejections():
        pat = r.get("pattern", "")
        if not pat:
            continue
        flags = re.I | (re.M if r.get("is_regex") else 0)
        hit = (re.search(pat, text, flags) if r.get("is_regex")
               else re.search(re.escape(pat), text, re.I))
        if hit:
            out.append({"check": "rejected_phrase", "where": f"{it['id']}.script",
                        "severity": "high", "text": hit.group(0)[:90].strip(),
                        "fix": "rewrite",
                        "why": f"the creator rejected this on {r.get('date','?')}: {r.get('why','')}"})
    return out


def check_speech_shape(it, targets):
    """The flat tail, per script. The creator's real speech runs to 98 words and 1.6% of
    their sentences pass 45. The 8 scripts of 2026-08-30 held 128 sentences and not one
    over 45, while passing every old gate, because the old rule asked for `max >= 25`.
    The runaway sentence is the single most distinctive thing about how he talks.

    The zero-of-five speech-marker test that used to live here moved to
    batch_marker_rate(): a rate against the corpus, because zero was the only value it
    could see and a batch can carry one token per script and still run at a tenth of the
    creator's rate."""
    out = []
    if not targets:
        return out
    text = (it.get("script") or "")
    sents = sentences(text)
    if len(sents) < 3:
        return out
    wc = [len(x.split()) for x in sents]
    p90 = targets["sentence_words"].get("p90", 29)
    if max(wc) < p90:
        out.append({"check": "tail_flat", "where": f"{it['id']}.script",
                    "severity": _cadence("medium"),
                    "text": f"longest sentence {max(wc)}w, his p90 is {p90}w",
                    "fix": "needs-words",
                    "why": ("no sentence even reaches the 90th percentile of his own speech. "
                            "Cadence stdev can be bought with choppiness; the long causal "
                            "run cannot be faked by punctuation.")})
    return out


def batch_marker_rate(items, targets):
    """Speech markers per 1000 words across the batch against the corpus rate for the same
    markers. He runs "like" at 40 per 1000 words; the rejected 08-30 batch ran it at 2.8
    and the 08-31 batch stayed at that level while clearing every cadence floor. Their
    absence is the loudest single difference between his transcripts and generated script,
    and the cause is upstream in the `copywriting` sentence layer, which cuts filler on
    sight because in written copy filler is waste."""
    if not targets or not items:
        return []
    rates = targets.get("speech_markers_per_1k") or {}
    top = sorted(rates.items(), key=lambda kv: -kv[1])[:8]
    if not top:
        return []
    corpus_rate = sum(v for _, v in top)
    text = " ".join((it.get("spoken_hook") or "") + " " + (it.get("script") or "") for it in items)
    low = text.lower()
    W = len(re.findall(r"[A-Za-z']+", low))
    if W < 200:
        return []
    hits = sum(len(re.findall(r"\b" + re.escape(m) + r"\b", low)) for m, _ in top)
    batch_rate = hits / W * 1000.0
    INFO.append(f"speech markers: batch {batch_rate:.1f}/1k over {W} words, corpus "
                f"{corpus_rate:.1f}/1k ({100 * batch_rate / corpus_rate:.0f}% of the creator's rate, "
                f"floor {int(MARKER_RATE_FLOOR * 100)}%)")
    if batch_rate < MARKER_RATE_FLOOR * corpus_rate:
        return [{"check": "marker_rate", "where": "batch", "severity": _cadence("medium"),
                 "text": (f"{batch_rate:.1f} markers per 1k words across {W} words, corpus runs "
                          f"{corpus_rate:.1f} ({100 * batch_rate / corpus_rate:.0f}% of his rate)"),
                 "fix": "needs-words",
                 "why": ("the batch carries his discourse markers at under "
                         f"{int(MARKER_RATE_FLOOR * 100)}% of the rate he speaks them: "
                         + ", ".join(f"{m} {v}/1k" for m, v in top[:5])
                         + ". Written prose with a few markers sprinkled on reads exactly "
                           "like the batches he rejected.")}]
    return []


def batch_tail(items, targets):
    """Batch-level: 1.6% over 45 words means not every episode needs a runaway sentence,
    but a whole batch without one is prose. Checked across the batch, not per script.
    A week with no spoken script at all (a LinkedIn-only week) has no batch to judge."""
    if not targets or not items:
        return []
    thresh = 45
    longest = 0
    for it in items:
        for x in sentences(it.get("script") or ""):
            longest = max(longest, len(x.split()))
    if longest < thresh:
        return [{"check": "batch_no_runaway", "where": "batch", "severity": _cadence("medium"),
                 "text": f"longest sentence in the whole batch is {longest}w",
                 "fix": "needs-words",
                 "why": (f"{targets['shape'].get('pct_over_45', 1.6)}% of his sentences pass "
                         f"{thresh} words and his longest is "
                         f"{targets['sentence_words'].get('max', 98)}. A batch with no "
                         "runaway sentence anywhere has been edited to prose. Exactly what "
                         "shipped on 2026-08-30.")}]
    return []


def check_targets(it, targets, week_date=""):
    """Script-level floors. Separate from the sentence-level checks above because these
    describe the whole distribution, not one line.

    The two RECALIBRATED floors (stdev, long-run) are grandfathered exactly as
    check_fidelity.py grandfathers them: they apply from FLOORS_FROM onward and older
    weeks keep the bar they were written under. Added 2026-08-30. Without this the two
    tools disagreed on the same batch, and this one printed [HIGH] on work that was
    written to the old floor and could not be rewritten. Self-expiring; nothing to clean
    up. no_first_person is NOT grandfathered, because it was never recalibrated."""
    out = []
    floors_live = (week_date or "") >= FLOORS_FROM
    sd_floor, over20_floor, origin = _floors(targets)
    sents = sentences(it.get("script") or "")
    if len(sents) < 3:
        return out
    wc = [len(s.split()) for s in sents]
    sd = statistics.pstdev(wc)
    over20 = 100.0 * sum(1 for w in wc if w > 20) / len(wc)
    if floors_live and sd < sd_floor:
        out.append({"check": "stdev_floor", "where": f"{it['id']}.script",
                    "severity": _cadence("medium"),
                    "text": f"stdev {sd:.1f}", "fix": "needs-words",
                    "why": f"below the {origin} floor of {sd_floor}. A floor set at half the "
                           f"corpus gets passed, not failed; this one is 60% of the measured stdev."})
    if floors_live and over20 < over20_floor:
        out.append({"check": "long_run_floor", "where": f"{it['id']}.script",
                    "severity": _cadence("medium"),
                    "text": f"{over20:.1f}% of sentences over 20 words", "fix": "needs-words",
                    "why": f"below the {origin} floor of {over20_floor}%. The long causal "
                           f"run is the voice and it is the thing most consistently missing."})
    if not any(FIRST_PERSON.search(s) for s in sents):
        out.append({"check": "no_first_person", "where": f"{it['id']}.script", "severity": "medium",
                    "text": "no first person anywhere in the script", "fix": "needs-words",
                    "why": "a script with no first person reads as an essay rather than a person "
                           "talking, and it is upstream of low contraction density, because "
                           "\"I'm\" cannot appear in a script with no \"I\" in it. Reserving the "
                           "first person for receipts and ownership does not mean removing it."})
    return out


FIELDS_SPOKEN = ("spoken_hook", "script")
FIELDS_WRITTEN = ("body",)
VIDEO_LANES = ("distribution", "office")


def lint_week(path: pathlib.Path):
    d = json.loads(path.read_text(encoding="utf-8"))
    findings = []
    targets = load_targets()
    spoken_items = []
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
            findings += check_rejected(it)
            # Both video lanes are spoken. Until 2026-09-09 only distribution[] was
            # measured here while check_fidelity.py measured office[] too, which is one
            # of the ways the two tools disagreed on the same batch.
            if lane in VIDEO_LANES and it.get("script"):
                findings += check_targets(it, targets, d.get("week", ""))
                findings += check_speech_shape(it, targets)
                spoken_items.append(it)
    findings += batch_tail(spoken_items, targets)
    findings += batch_marker_rate(spoken_items, targets)
    if targets is None and spoken_items:
        findings.append({"check": "no_targets", "where": "workspace", "severity": "warn",
                         "text": "voice-corpus/targets.json missing",
                         "fix": "run segment_corpus.py then derive_voice_targets.py",
                         "why": ("an onboarding state, not a defect: without it the speech-shape "
                                 "checks cannot run and the cadence floors fall back to the "
                                 "pre-2026-09-09 constants.")})
    return d, findings


def corpus_path():
    home = HOME if HOME is not None else radar_home()
    p = home / "voice-corpus" / "corpus-work-spoken.txt"
    return p if p.exists() else home / "voice-corpus" / "corpus.txt"


def corpus_baseline():
    p = corpus_path()
    if not p.exists():
        print(f"no corpus at {p}")
        sys.exit(1)
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
    print(f"unscripted corpus ({p.name}): {len(sents)} sentences, {sum(wc)} words")
    print(f"  mean {statistics.mean(wc):.1f}  median {statistics.median(wc):.0f}  "
          f"stdev {statistics.pstdev(wc):.1f}  longest {max(wc)}")
    print(f"  verbless NOUN-LABEL fragments (excluding backchannel): {sum(verbless)} ({100*sum(verbless)/len(sents):.1f}%)")
    print(f"  RUNS of 2+ noun labels: {sum(1 for r in runs if r >= 2)}   "
          f"longest run: {max(runs) if runs else 0}")
    print("\nRuns of 2 grade medium (he does that once in 379 sentences).")
    print("Runs of 3+ grade high (no precedent in the corpus at all).")


SEV_RC = {"high": 2, "medium": 1, "warn": 1}


def main():
    global STRICT_CADENCE
    ap = argparse.ArgumentParser()
    # --dir is resolution option 1 in the playbook's documented order, and argparse never
    # knew about it: passing it crashed with exit 2 and no output, so anyone following the
    # documentation hit an argparse error instead of a lint run. radar_home() consumes it
    # from sys.argv at import when present; declaring it here keeps argparse from
    # rejecting it in the cases where it does not (e.g. --dir after --week).
    ap.add_argument("--dir", help="workspace directory (resolution option 1)")
    ap.add_argument("--week")
    ap.add_argument("--json")
    ap.add_argument("--corpus", action="store_true")
    ap.add_argument("--strict-cadence", action="store_true",
                    help="grade the cadence findings high (rc 2) instead of medium")
    ap.add_argument("--apply-safe", action="store_true",
                    help="apply ONLY the pure-deletion fixes, never a rewrite")
    a = ap.parse_args()
    STRICT_CADENCE = a.strict_cadence

    if a.corpus:
        corpus_baseline()
        return 0

    if not a.week:
        print("need --week or --corpus")
        return 2
    path = pathlib.Path(a.week)
    if not path.exists() and HOME is not None and not path.is_absolute():
        alt = HOME / a.week
        if alt.exists():
            path = alt
    if not path.exists():
        print(f"no week file at {path}")
        return 2
    d, findings = lint_week(path)

    order = {"high": 0, "medium": 1, "warn": 2}
    findings.sort(key=lambda f: (order.get(f["severity"], 9), f["where"]))
    by_check = {}
    for f in findings:
        by_check.setdefault(f["check"], []).append(f)

    for f in findings:
        print(f"\n[{f['severity'].upper()}] {f['check']}  {f['where']}")
        print(f"  > {f['text'][:190]}")
        print(f"  why: {f['why']}")
        print(f"  fix: {f['fix']}")

    for line in INFO:
        print(f"\n{line}")
    print(f"\n{len(findings)} flagged in {path.name}")
    for k, v in sorted(by_check.items(), key=lambda kv: -len(kv[1])):
        print(f"  {k:24} {len(v)}  [{v[0]['severity']}]")
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

    n_high = sum(1 for f in findings if f["severity"] == "high")
    n_other = len(findings) - n_high
    rc = max([SEV_RC.get(f["severity"], 1) for f in findings] or [0])
    print(f"\nspoken_lint: {n_high} high, {n_other} medium/warn -> rc {rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())

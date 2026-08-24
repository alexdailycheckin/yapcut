#!/usr/bin/env python3
"""
The LinkedIn selector. Answers two questions the engine currently answers by accident:
which SHAPE does each week's substance become on LinkedIn, and what MIX does the week ship.

Why this exists. The week file's twins inherit the video's post_type (all five items in
weeks/2026-08-10.json are receipt-react) because the LinkedIn side has no shape-selection
step of its own. post-types.md picks the SCREEN shape for video. This picks the FEED shape
for text, from the same substance, using different rules, because the two surfaces reward
different things.

What it does and does not do. It computes what is computable: character band, enumeration
shape, proof presence, job mix, format monoculture, repeat companies, carousel opportunity.
It DECLARES what needs judgment rather than faking inference: whether a claim is genuinely
arguable, whether a story carries real friction, whether a list is an ordering argument.
Undeclared items get flagged, not guessed. A tool that pretends to detect contrarianism
with a regex is worse than one that asks.

Two lanes, and they are not the same lane. Video scripts in distribution[] carry an
optional twin; posts written for the feed alone live in the week file's linkedin[] lane.
Both compete for the same five slots on score, and at most TWIN_CAP of them may be twins,
so a five-company show week can no longer force five company posts onto LinkedIn.

Usage:
  python3 scripts/select_linkedin.py                          latest week
  python3 scripts/select_linkedin.py --week weeks/2026-08-10.json
  python3 scripts/select_linkedin.py --weights               show the scoring weights
  python3 scripts/select_linkedin.py --twin-cap 2            override the twin ceiling
  python3 scripts/select_linkedin.py --no-write              report only, do not write

It writes shape, job, post_day, post_slot and post_why back onto each selected
post, and twin_cut: true onto the video twins that did not earn a slot. Set
"post_day_locked": true on a post to pin its day by hand: the selector keeps that day and
fills the remaining slots around it.
"""

import datetime
import glob
import json
import os
import re
import sys
import textwrap

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

# Reach band from the platform research; see linkedin-engine save-mechanics.md.
BAND_LO, BAND_HI, HARD_STOP, SHORT_MAX, DEAD_LO, DEAD_HI = 1300, 1900, 2500, 300, 600, 1000

# Target mix per 5-post week. Not a taste ratio: a portfolio.
# Follower growth = reach to non-followers x follow conversion. Reach posts bring
# strangers, authority posts convert them and farm saves (a save is worth ~5x a like
# in reach), relatability retains. Drop any leg and the funnel starves.
# PLAYBOOK IS ITS OWN LEG as of 2026-08-11, on Alex's directive: give people useful things
# they can actually apply themselves to win. It used to sit inside "authority" alongside
# teardowns, which meant the mix could be satisfied by two analyses and ship nothing
# runnable. Splitting it makes the useful leg a requirement rather than a preference.
#
# RELATABILITY IS TARGETED AT ZERO, also Alex's call, and the honest reason is that this
# engine cannot source it. A confession needs a real failure and a model cannot have one.
# Every attempt to fill the leg came from mining Alex's own journal, which produced posts
# he did not want and would not have written. The format stays defined below, so a
# confession still types correctly on the rare week Alex writes one himself, and the mix
# simply does not ask for one. A leg nothing can supply is not a target, it is a nag.
# Both of these read from radar-config.json when present, because they are the
# two knobs that are the CREATOR'S, not the method's: what subject lane the feed
# posts stay inside, and how many slots each job class gets. The defaults are
# the research priors this file documents; a config pins your own.
#   "selector": {"target_mix": {"reach": 2, "playbook": 2, "authority": 1},
#                "lane": "your subject, one line"}
def _selector_cfg():
    for p in (os.path.join(RADAR, "radar-config.json"),
              os.path.join(HERE, "radar-config.json")):
        if os.path.exists(p):
            try:
                return json.load(open(p)).get("selector") or {}
            except Exception:
                pass
    return {}


_SCFG = _selector_cfg()
TARGET_MIX = _SCFG.get("target_mix") or {"reach": 2, "playbook": 2, "authority": 1}

# How many of the week's video scripts may also ship as LinkedIn twins.
#
# This cap is the whole reason the mix was unreachable before 2026-08-11. The twin was
# gated 1:1 to the video slate, so LinkedIn could only ever ship what the show had
# already commissioned. A five-company show week therefore forced five company posts,
# and no amount of reshaping at publish time could produce a confession that nothing
# upstream had written. The show and the feed have different jobs and are allowed to
# disagree about what a week contains.
#
# So a twin is now a CANDIDATE, not an entitlement. Video scripts compete for slots
# against LinkedIn-only posts, the best three at most get through, and the rest ship
# as video only. Losing the twin costs nothing: the script still films, and it still
# goes out on TikTok, Reels, Shorts and YouTube where reach, not the ICP, is the job.
TWIN_CAP = 3

# Starting weights. These are PRIORS from the research, not learned. log_perf.py
# replaces them with Alex's own numbers once a dimension clears its minimum n.
WEIGHTS = {
    "carousel_shaped": 30,   # document posts ~6.60% vs ~2.00% text-only. Biggest single lever.
    "has_verified_number": 20,
    "news_peg": 18,          # full at <=3 days, half at 4-7, zero after. See PEG_DECAY.
    "angle_unclaimed": 12,   # a saturated STORY can still carry an unclaimed ANGLE
    "arguable": 15,          # comment velocity in the first 30-60min
    "executable": 15,        # save probability
    "in_lane": 10,           # topic authority
    "repeat_company_8wk": -25,
    "dead_zone_length": -20,
    "no_proof": -30,
}

# The peg decays with SATURATION IN THE ICP'S FEED, not with clock time, and B2B
# LinkedIn saturates slower than consumer media. A Friday earnings story posted Monday
# is on time, not late. Corrected 2026-08-10 from a flat 48h cliff, which was imported
# from a general news-jack heuristic and failed every real item in the week file.
def peg_decay(days):
    if days is None:
        return None
    if days <= 3:
        return 1.0
    if days <= 7:
        return 0.5
    return 0.0

FORMATS = {
    "F1_playbook": "playbook",
    "F2_newsjack": "reach",
    "F2_teardown": "authority",
    "F3_reorder": "reach",
    "F4_confession": "relatability",
    "SHORT": "reach",
}

JOB_WHY_SHORT = {
    "reach": "No acquisition engine, so the week only reaches existing followers.",
    "playbook": "Nothing the reader can run, so the week teaches without helping.",
    "authority": "Nothing farms saves, and a save is worth about 5x a like in reach.",
    "relatability": "Nothing human, so new visitors have no reason to follow rather than read.",
}

# Where each leg's substance comes from. Written down because getting this wrong is what
# produced two weeks of bad posts: authority was drafted from Alex's work journal when it
# should have come off the same research as reach, and playbooks were drafted from the
# show corpus when what his audience wanted was this week's releases.
# THE LANE. Every leg stays inside it (Alex, 2026-08-11): GTM, growth, CMO, sales, social
# media and organic marketing. He is a Head of Growth writing for his own peers.
#
# This exists because the playbook leg drifted twice. Both times it drifted the same way:
# toward SEO and AEO technical work, because that is what Reach sells and it is the nearest
# thing to hand. It is not the subject. [redacted vault file] puts AEO inside pillar 3 as ONE
# channel, and the subject is how products and companies reach their market and get bought.
# A post about writing a GA4 regex is in Reach's product lane, not in Alex's subject lane.
LANE = _SCFG.get("lane") or (
    "The creator's own subject lane, one line, set it in radar-config.json "
    "(selector.lane). Every leg stays inside it; the tools or channels you "
    "sell with are one channel inside the lane, never the subject.")

JOB_SOURCE = {
    "reach": ("the show's news sweep. One company, one live peg, one unclaimed angle."),
    "playbook": ("DEMAND, not supply. Find what the ICP is measurably stuck on, then build "
                 "the artefact that settles it. The three-way intersection is the whole "
                 "method: (1) what they are stuck on, evidenced by a survey number, (2) "
                 "where that pain is worst inside Alex's lane, (3) where the CONSENSUS "
                 "ANSWER IS WRONG and you can prove it. Miss (3) and forty people wrote "
                 "the same post that week. Pitch every move at the READER'S OWN ALTITUDE: "
                 "a Head of Growth decides, delegates and defends, they do not open an "
                 "admin panel. Not the show corpus, not Alex's notes."),
    "authority": ("the show's own banked teardowns, cross-cut. The PATTERN across "
                  "companies rather than one company on one peg, so it makes no new "
                  "factual claim and stays evergreen."),
    "relatability": ("Alex himself, and nothing else can supply it. Targeted at zero for "
                     "that reason. Do not mine the work journal for one."),
}


def latest_week():
    files = sorted(glob.glob(os.path.join(RADAR, "weeks", "*.json")))
    return files[-1] if files else None


def enumerated_units(body):
    """Count discrete headed units. This is what makes a post carousel-shaped."""
    n = 0
    for line in body.split("\n"):
        s = line.strip()
        if not s:
            continue
        if re.match(r"^\d+[\.\)]\s", s):
            n += 1
        elif re.match(r"^[→↳•\-\*]\s", s):
            n += 1
        elif re.match(r"^[A-Z][A-Z \-/]{2,28}$", s):
            n += 1
    return n


# Verbs a reader can act on. Deliberately mundane: a playbook move is "list", "open",
# "write down", never "leverage" or "rethink". Extend it when a real post gets flagged
# wrongly, never to make a weak post pass.
IMPERATIVES = {
    "add", "agree", "anchor", "ask", "attach", "audit", "block", "book", "build", "call", "change", "check",
    "bring", "choose", "compare", "count", "cut", "draft", "export", "find", "fix", "get",
    "give", "go",
    "keep", "kill", "leave", "list",
    "map", "mark", "measure", "mine", "move", "name", "note", "open", "pick", "post",
    "pull", "put", "read", "record", "remove", "reply", "review", "run", "send", "set",
    "ship", "show", "start", "stop", "swap", "take", "test", "track", "watch", "write",
}


def playbook_moves(body):
    """How many headed units are followed by something the reader can actually run.

    Added 2026-08-11 after Alex flagged that the first authority post was typed
    F1_playbook, passed every shape check, and still gave nobody anything to do. It
    cross-cut five patterns across thirteen companies and every unit was a DIAGNOSIS:
    true, useful to understand, impossible to act on before Monday.

    The shape gate (3+ headed units) only proves the post is formatted like a playbook.
    This checks whether each unit opens with an instruction. It is a heuristic and it is
    labelled as one: it cannot judge whether the move is a GOOD move, only whether a move
    was named at all. That is still the difference between a playbook and an essay with
    headings.
    """
    # Two legal head shapes: numbered sentence case ("1. Agree the denominator."),
    # the standard since Alex unlearned all-caps headers (2026-08-14), and the legacy
    # caps header, still recognised so old weeks keep parsing. A numbered head carries
    # its own verb; a caps head is checked on the line after it.
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    moves = 0
    heads = 0
    for i, l in enumerate(lines):
        if re.match(r"^\d+[\.\)]\s+\S", l) and len(l) <= 60:
            heads += 1
            first = re.sub(r"^[^A-Za-z]+", "", l).split()
            follow = re.sub(r"^[^A-Za-z]+", "", lines[i + 1]).split() if i + 1 < len(lines) else []
            if (first and first[0].lower().rstrip(",.") in IMPERATIVES) or \
               (follow and follow[0].lower().rstrip(",.") in IMPERATIVES):
                moves += 1
        elif re.match(r"^[A-Z][A-Z \-/]{2,28}$", l):
            heads += 1
            if i + 1 < len(lines):
                first = re.sub(r"^[^A-Za-z]+", "", lines[i + 1]).split()
                if first and first[0].lower().rstrip(",.") in IMPERATIVES:
                    moves += 1
    return moves, heads


def has_number(text):
    """A magnitude, not just any digit. Fixed 2026-08-10: the first version required a
    symbol or an abbreviation, so it missed spelled-out magnitudes ("1.8 million cases")
    and ISO currency codes ("EUR2.26 billion") and scored the Coors twin at zero proof."""
    return bool(re.search(
        r"\d[\d,\.]*\s*(%|bn\b|m\b|k\b|x\b|million|billion|trillion|thousand)"
        r"|[$£€]\s?\d"
        r"|\b(?:EUR|USD|GBP)\s?\d",
        text, re.I))


def band(n):
    if n <= SHORT_MAX:
        return "short"
    if DEAD_LO <= n <= DEAD_HI:
        return "DEAD ZONE"
    if BAND_LO <= n <= BAND_HI:
        return "reach band"
    if n < BAND_LO:
        return "under band"
    if n > HARD_STOP:
        return "OVER HARD STOP"
    return "past band"


def features(item):
    tw = item.get("linkedin") or {}
    body = tw.get("body") or ""
    script = item.get("script") or ""
    f = {
        "chars": len(body),
        "band": band(len(body)),
        "units": enumerated_units(body),
        "has_verified_number": bool(has_number(body) and item.get("sources")),
        "no_proof": not item.get("sources"),
        "in_lane": item.get("facet") in ("gtm-distribution", "organic"),
        "carousel_shaped": enumerated_units(body) >= 3,
    }
    f["moves"], f["heads"] = playbook_moves(body)
    # Declared-only fields. Absent means unknown, never assumed false.
    for k in ("news_peg_days", "angle_unclaimed", "arguable", "executable",
              "ordering_claim", "friction_story", "evergreen", "deadline"):
        f[k] = tw.get(k, item.get(k))
    f["peg_decay"] = peg_decay(f["news_peg_days"])
    # A wildcard has no peg BY DESIGN, which is not the same as a peg nobody measured.
    need = ["arguable", "executable"] + ([] if f.get("evergreen") else ["news_peg_days"])
    f["undeclared"] = [k for k in need if f[k] is None]
    return f, body, script


def propose_format(item, f):
    """Declared wins. Otherwise propose from substance, with confidence.

    `linkedin_format` is a HUMAN override and nothing else writes to it. The computed
    result is persisted to `shape`, deliberately a different key: for a few hours on
    2026-08-11 the selector wrote its own answer back to `linkedin_format`, which this
    function reads as a declaration, so run two treated run one's guess as Alex's
    instruction and the tool could never revise itself. Two pegged playbooks stayed typed
    as newsjacks through three attempts to fix the precedence, because the precedence was
    never reached. Never persist a computed value to the key that overrides the computation.
    """
    tw = item.get("linkedin") or {}
    if tw.get("linkedin_format") in FORMATS:
        return tw["linkedin_format"], "declared by hand"
    if item.get("script_class") == "testimony" and f.get("friction_story"):
        return "F4_confession", "high"
    if f["carousel_shaped"] and f.get("ordering_claim"):
        return "F3_reorder", "high"
    # A RUNNABLE PLAYBOOK OUTRANKS ITS OWN NEWS PEG. Reordered 2026-08-11: the peg check
    # used to sit above this, so anything with a peg became a newsjack. That broke the
    # moment playbook became its own leg, because the best playbooks are pegged to a
    # platform change that shipped this week. Two finished playbooks sat in linkedin[]
    # while the verdict reported the playbook leg as 0 of 2.
    #
    # The peg decides WHEN to post, not WHAT the post is. Every unit naming a move is the
    # test, so this only fires on posts that pass the playbook gate rather than on anything
    # merely formatted with headings.
    if f["carousel_shaped"] and f["heads"] and f["moves"] >= f["heads"]:
        return "F1_playbook", "high: every unit names a move"
    if f.get("peg_decay"):
        return "F2_newsjack", "high" if f["peg_decay"] == 1.0 else "high: peg half-decayed"
    if f["carousel_shaped"]:
        return "F1_playbook", "medium: formatted as a playbook, units not all moves"
    if f["chars"] <= SHORT_MAX:
        return "SHORT", "medium"
    if item.get("script_class") == "research":
        if f.get("evergreen"):
            return "F2_teardown", "high: evergreen wildcard, authority by design"
        if f.get("news_peg_days") is not None:
            return "F2_teardown", f"medium: peg expired at {f['news_peg_days']}d, stands on its own"
        return "F2_teardown", "low: research prose, peg not declared and not enumerated"
    return "F2_teardown", "low: fell through, assign by hand"


def score(f, fmt):
    s, why = 0, []
    for key in ("carousel_shaped", "has_verified_number", "arguable", "executable",
                "in_lane", "angle_unclaimed", "no_proof"):
        if f.get(key):
            s += WEIGHTS[key]
            why.append(f"{key} {WEIGHTS[key]:+d}")
    if f.get("peg_decay"):
        pts = int(round(WEIGHTS["news_peg"] * f["peg_decay"]))
        s += pts
        why.append(f"news_peg({f['news_peg_days']}d) {pts:+d}")
    elif f.get("news_peg_days") is not None and f["peg_decay"] == 0.0:
        why.append(f"news_peg({f['news_peg_days']}d) +0 expired")
    if f["band"] == "DEAD ZONE":
        s += WEIGHTS["dead_zone_length"]
        why.append(f"dead_zone_length {WEIGHTS['dead_zone_length']:+d}")
    return s, why


def relatability_candidates(anchor, window=9):
    """Surface what the logged week holds, so the relatability question is warm.

    Relatability is the one leg that cannot be sourced from research. Reach and authority
    both come off the show's sweep; a confession needs a real failure that only Alex knows
    happened. So the selector asks rather than infers, exactly as it already does for
    `arguable` and `friction_story`, and a regex that tried to detect real friction would
    be worse than the question.

    Asked cold ("anything to confess this week?") the answer is always no, because nobody
    remembers their own week on demand. So this reads work-journal/ over the window ending
    at the anchor and puts the actual candidates on screen. `content_seeds` carry the angle,
    the verbatim scene and a `naming` line stating what to abstract; `tensions` are the
    rawer version of the same thing. Alex picks or says none, and neither answer is guessed.
    """
    try:
        d0 = datetime.date.fromisoformat(anchor)
    except Exception:
        return []
    out = []
    for i in range(window, -1, -1):
        day = (d0 - datetime.timedelta(days=i)).isoformat()
        path = os.path.join(RADAR, "work-journal", f"{day}.json")
        if not os.path.exists(path):
            continue
        try:
            j = json.load(open(path))
        except (ValueError, OSError):
            continue
        for seed in (j.get("content_seeds") or []):
            if isinstance(seed, dict) and seed.get("angle"):
                out.append({"day": day, "angle": seed["angle"],
                            "naming": seed.get("naming"), "kind": "seed"})
        for t in (j.get("tensions") or []):
            if isinstance(t, str) and t.strip():
                out.append({"day": day, "angle": t, "naming": None, "kind": "tension"})
    # Seeds before tensions, then most recent first. A seed already carries the scene and
    # the naming line, so it is closer to a post; a tension is raw and needs the work.
    # First person outranks both, because relatability needs Alex IN the story rather than
    # observing it, and "I" in the angle is the cheapest honest proxy for that.
    def rank(c):
        first_person = re.match(r"^(I|My|We|Our)\b", c["angle"]) is not None
        return (0 if c["kind"] == "seed" else 1, 0 if first_person else 1, c["day"])
    out.sort(key=lambda c: (rank(c)[0], rank(c)[1], [-ord(x) for x in c["day"]]))
    return out


def allocate(rows, twin_cap, slots=5):
    """Fill the week's slots against TARGET_MIX. Returns (selected, cut).

    Two rules, in this order, and the order is the point.

    MIX FIRST. Slots belong to a job class before they belong to a post, so the best
    reach post cannot take a slot the week owes to relatability. Ranking everything on
    one list and taking the top five is what produces a monoculture: the strongest
    items in a research-heavy week are all the same shape, so they win every slot and
    the week ships one post five times.

    TWINS COMPETE. Inside a class, a twin and a LinkedIn-only post are ranked on the
    same score with no bonus for having a video attached. A twin that loses is CUT from
    the feed, not softened: it still films and still ships everywhere else.

    Leftover slots go to the best remaining candidates of any class, because an unfilled
    slot is worse than an imperfect mix. Twins fill those too, up to the cap.
    """
    by_job = {}
    for r in rows:
        by_job.setdefault(r[5], []).append(r)
    for v in by_job.values():
        v.sort(key=lambda r: (-r[0], str(r[1].get("id"))))

    selected, twins_taken = [], 0

    def take(r):
        nonlocal twins_taken
        selected.append(r)
        if r[1].get("_kind") == "twin":
            twins_taken += 1

    def eligible(r):
        return r[1].get("_kind") != "twin" or twins_taken < twin_cap

    for job, want in TARGET_MIX.items():
        for r in by_job.get(job, [])[:]:
            if sum(1 for x in selected if x[5] == job) >= want:
                break
            if eligible(r):
                take(r)

    # Spare slots: best of what is left, regardless of class.
    spare = [r for r in rows if r not in selected]
    spare.sort(key=lambda r: (-r[0], str(r[1].get("id"))))
    for r in spare:
        if len(selected) >= slots:
            break
        if eligible(r):
            take(r)

    cut = [r for r in rows if r not in selected]
    return selected, cut


def next_decay_step(days):
    """Days until this peg loses value again. That, not age, is what makes a post urgent:
    a 7-day peg expiring tomorrow outranks a 5-day peg with three days left."""
    if days is None:
        return None
    if days <= 3:
        return 4 - days      # falls to half
    if days <= 7:
        return 8 - days      # falls to zero
    return None              # already spent


def days_until(deadline, anchor):
    """Days from the week's anchor to a declared deadline. None if there isn't one.

    A DEADLINE INVERTS THE DECAY MODEL and that is why it needs its own field. A news peg
    loses value as it ages, so the sort races the clock downward. A dated cutoff the reader
    has to act before gets MORE urgent as it approaches, and the post is worthless the day
    after. Scored as news it would look half-decayed and drift down the order; treated as a
    deadline it holds the front of the queue until it ships.

    Found while writing the Google Ads AI Max playbook, whose value is the three weeks of
    prep time it buys. Posted after 1 September it is not a weaker post, it is a wrong one.
    """
    if not deadline:
        return None
    try:
        d = datetime.date.fromisoformat(deadline)
        a = datetime.date.fromisoformat(anchor)
    except (ValueError, TypeError):
        return None
    return (d - a).days


def weekdays_from(anchor, n):
    import datetime
    try:
        d0 = datetime.date.fromisoformat(anchor)
    except Exception:
        return [None] * n
    out, d = [], d0
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d)
        d += datetime.timedelta(days=1)
    return out


def schedule(rows, anchor):
    """Post order by URGENCY (how fast the item loses value), not by score.

    The order is TOTAL and reproducible: soonest decay step, then higher score, then id.
    Nothing about the ordering is left to a judgment call, and re-running on the same week
    always produces the same days. Score only breaks urgency ties, because a great post
    whose peg died is worth less than a good post published while its peg is alive.

    What can still need a human is not the order but the SHAPE: a news-jack whose peg is
    dead by its slot is the wrong shape for the slot it earned. That is a rewrite of live
    creative, so this reports the cost and leaves the call.

    Returns [(item, date, slot_index, why)] so the caller can persist the assignment.
    """
    print("=" * 72)
    print("POSTING ORDER (most urgent first)\n")

    live, spent, ever = [], [], []
    for s, it, f, fmt, conf, job, why in rows:
        step = next_decay_step(f.get("news_peg_days"))
        dl = days_until(f.get("deadline"), anchor)
        if dl is not None and dl >= 0:
            # A cutoff outranks a peg: it expires hard rather than fading.
            live.append((s, it, f, fmt, job, dl, "deadline"))
        elif f.get("evergreen"):
            ever.append((s, it, f, fmt, job, None, "evergreen"))
        elif step is not None:
            live.append((s, it, f, fmt, job, step, "peg"))
        else:
            spent.append((s, it, f, fmt, job, None, "spent"))

    # Urgency first, score only to break it, id last so the result never depends on the
    # order items happen to sit in the file. Evergreen goes last: it holds its value.
    live.sort(key=lambda r: (r[5], -r[0], str(r[1].get("id"))))
    spent.sort(key=lambda r: (-r[0], str(r[1].get("id"))))
    ever.sort(key=lambda r: (-r[0], str(r[1].get("id"))))
    ordered = live + spent + ever

    # A day pinned by hand (post_day_locked) is kept. Everything else fills the remaining
    # weekday slots in urgency order, so an override never leaves a gap or a double booking.
    slots = weekdays_from(anchor, len(ordered))
    base = slots[0] if slots and slots[0] else None
    locked = {}
    for i, (s, it, f, fmt, job, step, kind) in enumerate(ordered):
        twin = it.get("linkedin") if isinstance(it.get("linkedin"), dict) else {}
        if twin.get("post_day_locked") and twin.get("post_day"):
            try:
                locked[i] = datetime.date.fromisoformat(twin["post_day"])
            except ValueError:
                pass
    free = [d for d in slots if d not in set(locked.values())]
    assigned, fi = [], 0
    for i in range(len(ordered)):
        if i in locked:
            assigned.append(locked[i])
        else:
            assigned.append(free[fi] if fi < len(free) else None)
            fi += 1

    plan, decayed, missed_dl = [], [], []
    for i, (s, it, f, fmt, job, step, kind) in enumerate(ordered):
        day = assigned[i]
        when = day.strftime("%a %d %b") if day else f"slot {i+1}"
        pin = "  (pinned)" if i in locked else ""
        cost = ""
        if kind == "deadline":
            urgency = f"hard deadline {f['deadline']}, {step}d out"
            left = days_until(f["deadline"], day.isoformat()) if day else step
            if left is not None and left < 0:
                cost = (f"   PAST ITS DEADLINE: ships {when}, cutoff was {f['deadline']}. "
                        f"The post is wrong, not weak.")
                missed_dl.append((it, when, f["deadline"]))
            elif left is not None:
                cost = f"   leaves the reader {left}d before the cutoff"
        elif kind == "peg":
            age_at_post = (f["news_peg_days"] or 0) + ((day - base).days if day and base else i)
            before, after = peg_decay(f["news_peg_days"]), (peg_decay(age_at_post) or 0.0)
            urgency = f"peg steps down in {step}d"
            if before is not None and before > after:
                cost = (f"   COST OF THIS SLOT: peg drops from {before:.1f} to {after:.1f} "
                        f"by {when} (age {age_at_post}d)")
                decayed.append((it, fmt, when, before, after))
        elif kind == "evergreen":
            urgency = "evergreen, no decay"
        else:
            urgency = "peg already spent, carried by the angle"

        print(f"{i+1}. {when} 9am   {it.get('id')}  [{fmt} / {job}]  score {s}{pin}")
        print(f"   {str(it.get('title'))[:66]}")
        print(f"   why this slot: {urgency}")
        if cost:
            print(cost)
        print()
        plan.append((it, day, i + 1, urgency))

    if decayed:
        print("SHAPE COST (the order is settled, this is about the post itself)\n")
        for it, fmt, when, before, after in decayed:
            print(f"  {it.get('id')} ships {when} with its peg at {after:.1f}, was {before:.1f}.")
        print("  A news-jack whose peg is spent is the wrong shape for its slot: the news is")
        print("  no longer the reason to stop scrolling. Either it moves up and the item above")
        print("  it takes the loss instead, or it gets rewritten as an authority post that")
        print("  stands on the analysis alone. That is a rewrite of live creative, so the")
        print("  selector prices it and leaves the call.")
        print()

    if missed_dl:
        print("MISSED DEADLINES (move these up or drop them)\n")
        for it, when, dl in missed_dl:
            print(f"  {it.get('id')} ships {when}, its cutoff was {dl}.")
        print("  A deadline post published after the deadline is not a weaker post, it is")
        print("  a wrong one. Pin it earlier with post_day_locked or cut it.")
        print()

    if ever:
        print(f"Evergreen items ({', '.join(r[1].get('id') for r in ever)}) are the buffer:")
        print(f"  they hold their value, so they absorb a slipped week or a hot drop.")
        print()

    return plan


def main():
    if "--weights" in sys.argv:
        print(json.dumps({"weights": WEIGHTS, "target_mix": TARGET_MIX,
                          "bands": {"short_max": SHORT_MAX, "dead": [DEAD_LO, DEAD_HI],
                                    "reach": [BAND_LO, BAND_HI], "hard_stop": HARD_STOP}}, indent=2))
        return

    wk = None
    if "--week" in sys.argv:
        wk = sys.argv[sys.argv.index("--week") + 1]
        if not os.path.isabs(wk):
            wk = os.path.join(RADAR, wk)
    wk = wk or latest_week()
    if not wk or not os.path.exists(wk):
        print("no week file found")
        return

    twin_cap = TWIN_CAP
    if "--twin-cap" in sys.argv:
        twin_cap = int(sys.argv[sys.argv.index("--twin-cap") + 1])

    d = json.load(open(wk))
    items = [dict(i, _kind="twin") for i in d.get("distribution", []) if i.get("linkedin")]
    items += [dict({"linkedin": t, **{k: v for k, v in t.items() if k != "linkedin"}},
                   _kind="solo") for t in d.get("linkedin", [])]

    n_twin = sum(1 for i in items if i["_kind"] == "twin")
    n_solo = len(items) - n_twin
    print(f"week {d.get('week')}   {n_twin} twin candidate(s), {n_solo} LinkedIn-only, "
          f"twin cap {twin_cap}\n")
    if not items:
        print("no LinkedIn posts in this week file.")
        return

    rows, undeclared_any = [], False
    for it in items:
        f, body, _ = features(it)
        fmt, conf = propose_format(it, f)
        job = FORMATS[fmt]
        s, why = score(f, fmt)
        if f["undeclared"]:
            undeclared_any = True
        rows.append((s, it, f, fmt, conf, job, why))

    for s, it, f, fmt, conf, job, why in sorted(rows, key=lambda r: -r[0]):
        lane = "twin" if it.get("_kind") == "twin" else "LinkedIn-only"
        print(f"[{s:>4}]  {it.get('id')}  {fmt}  ({job})  [{lane}]   confidence: {conf}")
        print(f"        {str(it.get('title'))[:72]}")
        print(f"        {f['chars']} chars = {f['band']}   units={f['units']}"
              f"   carousel_shaped={f['carousel_shaped']}")
        if why:
            print(f"        score: {', '.join(why)}")
        if f["undeclared"]:
            print(f"        UNDECLARED (not guessed): {', '.join(f['undeclared'])}")
        print()

    selected, cut = allocate(rows, twin_cap)
    jobs, fmts = {}, {}
    for s, it, f, fmt, conf, job, why in selected:
        jobs[job] = jobs.get(job, 0) + 1
        fmts[fmt] = fmts.get(fmt, 0) + 1

    print("=" * 72)
    print("WEEK VERDICT\n")

    cut_twins = [r for r in cut if r[1].get("_kind") == "twin"]
    cut_solos = [r for r in cut if r[1].get("_kind") != "twin"]
    if cut_twins:
        print(f"CUT FROM THE FEED ({len(cut_twins)}), still films and still ships elsewhere:")
        for s, it, f, fmt, conf, job, why in sorted(cut_twins, key=lambda r: -r[0]):
            print(f"  {it.get('id')}  score {s}  ({fmt})  {job} slots filled by higher scores")
        print("  A twin is a candidate, not an entitlement. TikTok, Reels, Shorts and")
        print("  YouTube still get these: reach is their job, the ICP is LinkedIn's.")
        print()
    if cut_solos:
        print(f"BANKED ({len(cut_solos)}), written and holding for a future week:")
        for s, it, f, fmt, conf, job, why in sorted(cut_solos, key=lambda r: -r[0]):
            print(f"  {it.get('id')}  score {s}  ({fmt})  {job} slot taken this week")
        print("  No video behind these, so nothing else ships them. They keep their value")
        print("  and fill the first week their job comes up short.")
        print()

    print(f"job mix     {dict(sorted(jobs.items()))}")
    print(f"target      {TARGET_MIX}")
    short_any = False
    for job, want in TARGET_MIX.items():
        got = jobs.get(job, 0)
        if got < want:
            short_any = True
            print(f"  SHORT on {job}: {got} of {want}. {JOB_WHY_SHORT.get(job, '')}")
            print(f"  COMMISSION a {job} post into the week file's linkedin[] lane. It cannot")
            print(f"  come from the video slate: the twin lane can only reshape what the show")
            print(f"  already wrote, and the show does not commission by feed job.")
            src = JOB_SOURCE.get(job)
            if src:
                for i, line in enumerate(textwrap.wrap(src, 70)):
                    print(f"  {'SOURCE: ' if i == 0 else '        '}{line}")
    if not short_any:
        print("  mix met.")
    print()

    # Relatability is the one leg research cannot fill, so it gets asked rather than
    # inferred. Asked cold the answer is always no, so the candidates come with it.
    if jobs.get("relatability", 0) < TARGET_MIX.get("relatability", 0):
        cands = relatability_candidates(d.get("week"))
        print("RELATABILITY: is there anything real to use this week?\n")
        print("  Only Alex can answer this. A confession needs a failure that actually")
        print("  happened, and inventing one is the single most punished move on the")
        print("  platform. If the honest answer is no, say so: the slot goes to a second")
        print("  authority post and the week ships 2/3/0 rather than a manufactured story.")
        print("  Note the format library caps confession at once a FORTNIGHT anyway, so an")
        print("  empty relatability week is the expected case, not a failure.\n")
        if cands:
            print(f"  From work-journal, {len(cands)} candidate(s) in the 10 days to "
                  f"{d.get('week')}:\n")
            for c in cands[:8]:
                tag = "seed " if c["kind"] == "seed" else "tension"
                print(f"    [{tag}] {c['day']}  {c['angle'][:88]}")
                if c.get("naming"):
                    print(f"             naming: {str(c['naming'])[:78]}")
            if len(cands) > 8:
                print(f"    ... and {len(cands) - 8} more in work-journal/")
            print()
            print("  Pick one, or say none. A seed carries the verbatim scene and a naming")
            print("  line stating what to abstract, so it is closer to ready than a tension.")
        else:
            print("  Nothing in work-journal for this window. Either the week was logged")
            print("  thin or there is genuinely nothing, and both mean the same thing here.")
        print()

    print(f"format spread  {dict(sorted(fmts.items()))}")
    if len(fmts) == 1:
        print(f"  MONOCULTURE: all {len(selected)} posts are {list(fmts)[0]}. {len(selected)} posts of one\n"
              f"  shape read as one post published {len(selected)} times. Reassign at least two.")
    print()

    dead = [it.get("id") for _, it, f, *_ in selected if f["band"] == "DEAD ZONE"]
    over = [it.get("id") for _, it, f, *_ in selected if f["band"] == "OVER HARD STOP"]
    inband = sum(1 for _, _, f, *_ in selected if f["band"] == "reach band")
    print(f"length      {inband} of {len(selected)} in the 1300-1900 reach band")
    if dead:
        print(f"  DEAD ZONE (600-1000 chars, wins neither dwell nor velocity): {', '.join(dead)}")
    if over:
        print(f"  OVER 2500 (reported ~35% engagement drop): {', '.join(over)}")
    print()

    # A playbook that names no moves is an essay with headings. Alex's line, 2026-08-11:
    # give people useful things they can actually apply themselves to win.
    weak = [(it.get("id"), f) for _, it, f, fmt, *_ in selected
            if fmt == "F1_playbook" and f["heads"] and f["moves"] < f["heads"]]
    if weak:
        print("playbook    a unit that does not open with an instruction is a DIAGNOSIS")
        for pid, f in weak:
            print(f"  {pid}: {f['moves']} of {f['heads']} units name a move the reader can run.")
        print("  A playbook earns its slot by being runnable, not by being right. Each unit")
        print("  wants an instruction, what it costs, who already proved it, and how the")
        print("  reader knows it worked. The show's companies are the PROOF, not the subject.")
        print("  Heuristic: it checks that a move was named, never whether it is a good move.")
        overclaimed = [pid for pid, f in weak if f.get("executable")]
        if overclaimed:
            print(f"  DECLARED executable but reads diagnostic: {', '.join(overclaimed)}.")
            print("  executable means the reader can run it from the post alone. Re-check it.")
        print()

    missed = [it.get("id") for _, it, f, *_ in selected if f["carousel_shaped"]]
    print(f"carousel    {len(missed)} of {len(selected)} are carousel-shaped (3+ headed units)")
    if missed:
        print(f"  Ship these as document posts, text as framing: {', '.join(missed)}")
        print(f"  This is the biggest lever in the file: ~6.60% vs ~2.00% engagement.")
    # Substance that WANTS to be a carousel but is written as prose. The restructure is a
    # judgment call on live creative, so this reports the opportunity and does not take it.
    latent = [it.get("id") for _, it, f, *_ in selected
              if f.get("ordering_claim") and not f["carousel_shaped"]]
    if latent:
        print(f"  LATENT: {', '.join(latent)} carries a sequence argument written as prose.")
        print(f"  One slide per step would make the ordering visible and unlock the 3x.")
        print(f"  Alex's call: that is a rewrite of live creative, not a mechanical fix.")
        print(f"  If yes, the tooling exists: linkedin-engine references/carousel-cards.md for")
        print(f"  the style, scripts/carousel.py to render from a spec. Depth cards must come")
        print(f"  from this item's own beats, never a fresh writing session.")
    if not missed and not latent:
        print(f"  Nothing in this week's substance is carousel-shaped. That is a BRIEF-stage")
        print(f"  gap, not a twin-stage one: no playbook or reorder was commissioned.")
    print()

    plan = schedule(selected, d.get("week"))

    # Persist the assignment. Without this the days live only in this terminal output and
    # the dashboard, which renders the week file, has nothing to show.
    #
    # The SHAPE is persisted too, as of 2026-08-11. Before that the selector computed a
    # format for every post, printed it, and wrote back only the day, so the twins kept
    # rendering the video's post_type and the dashboard showed five identical shapes on a
    # week the selector had already assigned four different ones. A proposal that is not
    # written down is a proposal nobody acts on.
    if "--no-write" not in sys.argv:
        written, pinned, marked = 0, 0, 0
        for s, it, f, fmt, conf, job, why in selected:
            twin = it.get("linkedin")
            if isinstance(twin, dict):
                twin["shape"] = fmt
                twin["job"] = job
                twin["twin_cut"] = False
                twin.pop("banked", None)
        # Losing a slot means different things in each lane. A cut TWIN still films and
        # still ships on every other platform, so nothing is lost. A cut SOLO has no video
        # behind it, so it carries to a future week instead. Same allocation, different
        # consequence, and collapsing them would tell Alex a written post had been binned.
        for s, it, f, fmt, conf, job, why in cut:
            twin = it.get("linkedin")
            if isinstance(twin, dict):
                twin["shape"] = fmt
                twin["job"] = job
                if it.get("_kind") == "twin":
                    twin["twin_cut"] = True
                    twin["cut_why"] = f"score {s}, {job} slots filled by higher-scoring posts"
                else:
                    twin["banked"] = True
                    twin["cut_why"] = (f"score {s}, {job} slot taken this week. Holds its "
                                       f"value, carries to a future week.")
                for k in ("post_day", "post_slot", "post_why"):
                    twin.pop(k, None)
                marked += 1
        for it, day, slot, why in plan:
            twin = it.get("linkedin")
            if not isinstance(twin, dict) or day is None:
                continue
            if twin.get("post_day_locked") and twin.get("post_day"):
                pinned += 1
                continue
            twin["post_day"] = day.isoformat()
            twin["post_slot"] = slot
            twin["post_why"] = why
            written += 1
        with open(wk, "w") as fh:
            json.dump(d, fh, indent=2)
            fh.write("\n")
        print(f"wrote shape + post_day to {written} post(s) in {os.path.basename(wk)}"
              f"{f', cut {marked}' if marked else ''}"
              f"{f', kept {pinned} pinned' if pinned else ''}.")
        print("  Pin a day against re-runs with \"post_day_locked\": true on the twin.")
        print("  Rebuild the dashboard to see the calendar: python3 build_dashboard.py")
        print()

    if undeclared_any:
        print("DECLARE THESE on the twin to make the selector deterministic:")
        print("  news_peg_days   age of the peg in days (full <=3, half 4-7, zero after)")
        print("  angle_unclaimed true if the STORY is saturated but your ANGLE is not")
        print("  arguable        true if a credible practitioner could disagree")
        print("  executable      true if the reader can run it from the post alone")
        print("  ordering_claim  true if the argument is the SEQUENCE, not the items")
        print("  friction_story  true if a testimony piece carries real failure")
        print("  linkedin_format overrides the proposal entirely")


if __name__ == "__main__":
    main()

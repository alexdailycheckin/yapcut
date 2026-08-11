#!/usr/bin/env python3
"""
The LinkedIn selector. Answers two questions the weekly routine otherwise answers by
accident: which SHAPE does each week's substance become on LinkedIn, and in what ORDER
does the week ship.

Why this exists. When `linkedin_twins` is on, each primary-lane script gets a twin. The
twin has historically inherited the video's `post_type`, which produces a week of
identical shapes: five posts of one shape read as one post published five times.
`references/post-types.md` picks the SCREEN shape for video. This picks the FEED shape
for text, from the same substance, using different rules, because the two surfaces do
not reward the same thing. The FYP rewards watch-through on a hook. The feed rewards
dwell, saves and early comment velocity.

What it does and does not do. It computes what is computable: character band,
enumeration shape, proof presence, job mix, shape monoculture, carousel opportunity,
posting order. It DECLARES what needs judgment rather than faking inference: whether a
claim is genuinely arguable, whether a list is an ordering argument, whether a story
carries real friction. Undeclared items are flagged, not guessed. A tool that pretends
to detect contrarianism with a regex is worse than one that asks.

Usage:
  python3 select_linkedin.py                       latest week in weeks/
  python3 select_linkedin.py --week weeks/2026-08-10.json
  python3 select_linkedin.py --dir ~/outlier-radar
  python3 select_linkedin.py --weights             show the scoring weights

Reads `facets` and `linkedin_twins` from radar-config.json when present.
"""

import glob
import json
import os
import re
import sys
import textwrap

# Character bands, from published platform studies (see references/linkedin-selector.md
# for sourcing and its limits). Characters, not words: characters are what the platform
# counts and what the fold and the 3,000 cap are measured in.
BAND_LO, BAND_HI, HARD_STOP, SHORT_MAX, DEAD_LO, DEAD_HI = 1300, 1900, 2500, 300, 600, 1000

# Target mix per 5-post week. Not a taste ratio: a portfolio.
# Follower growth = reach to non-followers x conversion to follow. Reach posts bring
# strangers, authority posts convert them and farm saves (a save reportedly drives about
# 5x the reach of a like), relatability retains. Drop a leg and the funnel starves.
#
# PLAYBOOK IS ITS OWN LEG as of 2.7. It used to sit inside "authority" next to teardowns,
# which meant a week could satisfy the mix with two analyses and ship nothing the reader
# could actually run. Splitting it makes the useful leg a requirement rather than a
# preference. Override the whole thing with "target_mix" in radar-config.json.
DEFAULT_TARGET_MIX = {"reach": 2, "playbook": 1, "authority": 1, "relatability": 1}

# How many of the week's video scripts may ALSO ship as LinkedIn twins.
#
# This cap is the reason the mix was previously unreachable. A twin was gated one-to-one
# to the video slate, so LinkedIn could only ever ship what the video side had already
# commissioned. If your week's videos are five teardowns, you got five teardown posts and
# no amount of reshaping at publish time could produce anything else.
#
# So a twin is a CANDIDATE, not an entitlement. Video scripts compete for slots against
# posts written for the feed alone, at most TWIN_CAP of them get through, and the rest
# ship as video only. Losing the twin costs nothing: the script still films and still
# goes out on every short-form platform. Override with "twin_cap" in radar-config.json.
DEFAULT_TWIN_CAP = 3

# Starting weights are PRIORS from published research, not from your own numbers.
# Replace them with your measured results once a dimension has enough posts behind it.
WEIGHTS = {
    "carousel_shaped": 30,   # document posts ~6.60% vs ~2.00% text-only. Biggest single lever.
    "has_verified_number": 20,
    "news_peg": 18,          # full at <=3 days, half at 4-7, zero after. See peg_decay.
    "angle_unclaimed": 12,   # a saturated STORY can still carry an unclaimed ANGLE
    "arguable": 15,          # comment velocity in the first 30-60min
    "executable": 15,        # save probability
    "in_lane": 10,           # topic authority
    "dead_zone_length": -20,
    "no_proof": -30,
}

# Shape -> the job that shape does. Job is derived from shape, not from the video's intent,
# because the same subject can do different jobs depending on how it is framed.
SHAPES = {
    "playbook": "playbook",      # moves the reader can run. Carousel-shaped.
    "reorder": "reach",          # the argument is the SEQUENCE, not the items. Carousel-shaped.
    "newsjack": "reach",         # borrowed attention from a live story
    "teardown": "authority",     # a subject diagnosed, standing on its own analysis
    "confession": "relatability",  # an admission that reads as bad news, then turns
    "short": "reach",            # one idea, under ~300 chars, wins on replies not dwell
}

JOB_WHY_SHORT = {
    "reach": "No acquisition engine, so the week only reaches existing followers.",
    "playbook": "Nothing the reader can run, so the week teaches without helping.",
    "authority": "Nothing farms saves, and a save reportedly drives about 5x a like.",
    "relatability": "Nothing human, so new visitors have no reason to follow rather than read.",
}

# Where each leg's substance comes from. Written down because getting this wrong is the
# most common way a week goes thin, and the failure is silent: every post is defensible
# on its own and the set still does one job four times.
JOB_SOURCE = {
    "reach": ("your weekly sweep. One subject, one live peg, one angle nobody else "
              "took."),
    "playbook": ("DEMAND, not supply. Find what your audience is measurably stuck on, "
                 "then build the thing that settles it. Three tests, and the third is "
                 "the one people skip: (1) they are stuck on it, with a real number "
                 "behind the claim, (2) the pain sits inside your niche, (3) the "
                 "CONSENSUS ANSWER IS WRONG and you can show it. Miss the third and you "
                 "wrote the post forty other people wrote that week. Pitch every move at "
                 "your READER'S OWN ALTITUDE: what they personally decide, delegate, "
                 "defend or stop funding, never a task they would hand to someone else."),
    "authority": ("your own back catalogue, cross-cut. The PATTERN across subjects you "
                  "have already covered rather than one subject on one peg, so it makes "
                  "no new factual claim and stays evergreen."),
    "relatability": ("you, and nothing else can supply it. A confession needs a failure "
                     "that actually happened. If you did not have one this week, say so "
                     "and let the slot go to another leg."),
}


def peg_decay(days):
    """A peg decays with SATURATION IN YOUR AUDIENCE'S FEED, not with the clock, and a
    B2B feed saturates slower than consumer media. A Friday earnings story posted Monday
    is on time, not late. A flat 48-hour cliff is too tight for this surface."""
    if days is None:
        return None
    if days <= 3:
        return 1.0
    if days <= 7:
        return 0.5
    return 0.0


def next_decay_step(days):
    """Days until this peg loses value again. That, not age, is what makes a post urgent:
    a 7-day peg expiring tomorrow outranks a 5-day peg with three days left."""
    if days is None:
        return None
    if days <= 3:
        return 4 - days
    if days <= 7:
        return 8 - days
    return None


def resolve_home():
    """Same resolution order as the rest of the skill: --dir, env, cwd, then skill root."""
    if "--dir" in sys.argv:
        return os.path.expanduser(sys.argv[sys.argv.index("--dir") + 1])
    env = os.environ.get("OUTLIER_RADAR_HOME")
    if env:
        return os.path.expanduser(env)
    if os.path.isdir(os.path.join(os.getcwd(), "weeks")):
        return os.getcwd()
    here = os.path.dirname(os.path.abspath(__file__))
    if os.path.isdir(os.path.join(here, "weeks")):
        return here
    return os.path.expanduser("~/outlier-radar")


def load_config(home):
    for p in (os.path.join(home, "radar-config.json"),
              os.path.join(os.path.dirname(os.path.abspath(__file__)), "radar-config.json")):
        if os.path.exists(p):
            try:
                return json.load(open(p))
            except Exception:
                pass
    return {}


def enumerated_units(body):
    """Count discrete headed units. This is what makes a post carousel-shaped."""
    n = 0
    for line in body.split("\n"):
        s = line.strip()
        if not s:
            continue
        if re.match(r"^\d+[\.\)]\s", s) or re.match(r"^[→↳•\-\*]\s", s):
            n += 1
        elif re.match(r"^[A-Z][A-Z \-/]{2,28}$", s):
            n += 1
    return n


def has_number(text):
    """A magnitude, not just any digit. Catches symbols, abbreviations, spelled-out
    magnitudes ("1.8 million") and ISO currency codes ("EUR2.26 billion")."""
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


# Verbs a reader can act on. Deliberately mundane: a playbook move is "list", "open",
# "write down", never "leverage" or "rethink". Extend it when a real post is flagged
# wrongly, never to make a weak post pass.
IMPERATIVES = {
    "add", "ask", "attach", "audit", "block", "book", "bring", "build", "call", "change",
    "check", "choose", "compare", "count", "cut", "draft", "export", "find", "fix", "get",
    "give", "go", "keep", "kill", "leave", "list", "map", "mark", "measure", "mine",
    "move", "name", "note", "open", "pick", "post", "pull", "put", "read", "record",
    "remove", "reply", "review", "run", "send", "set", "ship", "show", "start", "stop",
    "swap", "take", "test", "track", "watch", "write",
}


def playbook_moves(body):
    """How many headed units are followed by something the reader can actually run.

    The shape gate (3+ headed units) only proves a post is FORMATTED like a playbook. A
    post can pass it and still be a set of DIAGNOSES: true, useful to understand, and
    impossible to act on before Monday. This checks whether each unit opens with an
    instruction.

    It is a heuristic and it says so: it can tell whether a move was named, never whether
    it is a good move. That is still the difference between a playbook and an essay with
    headings.
    """
    lines = [l.strip() for l in body.split("\n") if l.strip()]
    heads = [i for i, l in enumerate(lines) if re.match(r"^[A-Z][A-Z \-/]{2,28}$", l)]
    moves = 0
    for i in heads:
        if i + 1 < len(lines):
            first = re.sub(r"^[^A-Za-z]+", "", lines[i + 1]).split()
            if first and first[0].lower().rstrip(",.") in IMPERATIVES:
                moves += 1
    return moves, len(heads)


def days_until(deadline, anchor):
    """Days from the week's anchor to a declared deadline. None if there isn't one.

    A DEADLINE INVERTS THE DECAY MODEL, which is why it needs its own field. A news peg
    loses value as it ages, so the sort races the clock downward. A dated cutoff your
    reader has to act before gets MORE urgent as it approaches, and the post is worthless
    the day after. Scored as news it looks half-decayed and drifts down the order.
    """
    import datetime
    if not deadline:
        return None
    try:
        return (datetime.date.fromisoformat(deadline)
                - datetime.date.fromisoformat(anchor)).days
    except (ValueError, TypeError):
        return None


def allocate(rows, target_mix, twin_cap, slots=5):
    """Fill the week's slots against the target mix. Returns (selected, cut).

    Two rules, in this order, and the order is the point.

    MIX FIRST. A slot belongs to a job before it belongs to a post, so the best reach post
    cannot take a slot the week owes to another leg. Ranking everything on one list and
    taking the top five is what produces a monoculture: in any given week the strongest
    items tend to be the same shape, so they win every slot and the week ships one post
    five times.

    TWINS COMPETE. Inside a job, a twin and a LinkedIn-only post are ranked on the same
    score with no bonus for having a video behind it. A twin that loses is CUT from the
    feed, not softened: it still films and still ships everywhere else.

    Leftover slots go to the best remaining candidates of any job, because an unfilled slot
    is worse than an imperfect mix.
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

    for job, want in target_mix.items():
        for r in by_job.get(job, []):
            if sum(1 for x in selected if x[5] == job) >= want:
                break
            if eligible(r):
                take(r)

    spare = sorted((r for r in rows if r not in selected),
                   key=lambda r: (-r[0], str(r[1].get("id"))))
    for r in spare:
        if len(selected) >= slots:
            break
        if eligible(r):
            take(r)

    return selected, [r for r in rows if r not in selected]


def features(item, facets):
    tw = item.get("linkedin") or {}
    body = tw.get("body") or ""
    units = enumerated_units(body)
    f = {
        "chars": len(body),
        "band": band(len(body)),
        "units": units,
        "carousel_shaped": units >= 3,
        "has_verified_number": bool(has_number(body) and item.get("sources")),
        "no_proof": not item.get("sources"),
        "in_lane": (item.get("facet") in facets) if facets else None,
    }
    # Declared-only fields. Absent means unknown, never assumed false.
    for k in ("news_peg_days", "angle_unclaimed", "arguable", "executable",
              "ordering_claim", "friction_story", "evergreen", "deadline"):
        f[k] = tw.get(k, item.get(k))
    f["moves"], f["heads"] = playbook_moves(body)
    f["peg_decay"] = peg_decay(f["news_peg_days"])
    # An evergreen item has no peg BY DESIGN, which is not the same state as a peg
    # nobody measured.
    need = ["arguable", "executable"] + ([] if f.get("evergreen") else ["news_peg_days"])
    f["undeclared"] = [k for k in need if f[k] is None]
    return f, body


def propose_shape(item, f):
    """Declared wins. Otherwise propose from substance, with confidence."""
    tw = item.get("linkedin") or {}
    if tw.get("linkedin_shape") in SHAPES:
        return tw["linkedin_shape"], "declared"
    if f.get("friction_story"):
        return "confession", "high"
    if f.get("peg_decay"):
        return "newsjack", "high" if f["peg_decay"] == 1.0 else "high: peg half-decayed"
    if f["carousel_shaped"] and f.get("ordering_claim"):
        return "reorder", "high"
    if f["carousel_shaped"]:
        return "playbook", "medium"
    if f["chars"] <= SHORT_MAX:
        return "short", "medium"
    if f.get("evergreen"):
        return "teardown", "high: evergreen, authority by design"
    if f.get("news_peg_days") is not None:
        return "teardown", f"medium: peg expired at {f['news_peg_days']}d, stands on its own"
    return "teardown", "low: prose, peg not declared and not enumerated"


def score(f):
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
    elif f.get("news_peg_days") is not None:
        why.append(f"news_peg({f['news_peg_days']}d) +0 expired")
    if f["band"] == "DEAD ZONE":
        s += WEIGHTS["dead_zone_length"]
        why.append(f"dead_zone_length {WEIGHTS['dead_zone_length']:+d}")
    return s, why


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
    """Post order by URGENCY (how fast an item loses value), not by score. Score only
    breaks ties, because a great post whose peg died is worth less than a good post
    published while its peg is alive."""
    print("=" * 72)
    print("POSTING ORDER (most urgent first)\n")

    live, spent, ever = [], [], []
    for s, it, f, shape, conf, job, why in rows:
        step = next_decay_step(f.get("news_peg_days"))
        dl = days_until(f.get("deadline"), anchor)
        if dl is not None and dl >= 0:
            # A cutoff outranks a peg: it expires hard rather than fading.
            live.append((s, it, f, shape, job, dl, "deadline"))
        elif f.get("evergreen"):
            ever.append((s, it, f, shape, job, None, "evergreen"))
        elif step is not None:
            live.append((s, it, f, shape, job, step, "peg"))
        else:
            spent.append((s, it, f, shape, job, None, "spent"))

    # id last so the order never depends on where items sit in the file.
    live.sort(key=lambda r: (r[5], -r[0], str(r[1].get("id"))))
    spent.sort(key=lambda r: (-r[0], str(r[1].get("id"))))
    ever.sort(key=lambda r: (-r[0], str(r[1].get("id"))))
    ordered = live + spent + ever
    days = weekdays_from(anchor, len(ordered))
    conflict = [r for r in live if r[6] == "peg" and r[5] <= 1]

    plan, missed_dl = [], []
    for i, (s, it, f, shape, job, step, kind) in enumerate(ordered):
        day = days[i]
        when = day.strftime("%a %d %b") if day else f"slot {i+1}"
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
        elif step is not None:
            age_at_post = (f["news_peg_days"] or 0) + ((day - days[0]).days if day else i)
            before, after = peg_decay(f["news_peg_days"]), peg_decay(age_at_post) or 0
            urgency = f"peg steps down in {step}d"
            if before - after > 0:
                cost = (f"   COST OF THIS SLOT: peg drops {before:.1f} to {after:.1f} "
                        f"by {when} (age {age_at_post}d)")
        elif f.get("evergreen"):
            urgency = "evergreen, no decay"
        else:
            urgency = "peg already spent, carried by the angle"

        print(f"{i+1}. {when}   {it.get('id')}  [{shape} / {job}]  score {s}")
        print(f"   {str(it.get('title'))[:66]}")
        print(f"   why this slot: {urgency}")
        if cost:
            print(cost)
        print()
        plan.append((it, day, i + 1, urgency))

    if missed_dl:
        print("MISSED DEADLINES (move these up or drop them)\n")
        for it, when, dl in missed_dl:
            print(f"  {it.get('id')} ships {when}, its cutoff was {dl}.")
        print("  A deadline post published after the deadline is not a weaker post, it is")
        print("  a wrong one. Pin it earlier with post_day_locked, or cut it.\n")

    if len(conflict) > 1:
        ids = ", ".join(r[1].get("id") for r in conflict)
        print(f"SLOT CONFLICT: {len(conflict)} items ({ids}) each lose peg value within a day,")
        print("  and there is one day-one slot. Options: double up on day one and accept a")
        print("  split audience, or take the peg loss on the lower scorer and publish it as")
        print("  an authority post instead. That is a judgment call, not a mechanical fix.\n")

    if ever:
        print(f"Evergreen items ({', '.join(r[1].get('id') for r in ever)}) are the buffer:")
        print("  they hold their value, so they absorb a slipped week or a hot drop.\n")

    return plan


def main():
    if "--weights" in sys.argv:
        print(json.dumps({"weights": WEIGHTS, "target_mix": DEFAULT_TARGET_MIX,
                          "twin_cap": DEFAULT_TWIN_CAP,
                          "bands": {"short_max": SHORT_MAX, "dead": [DEAD_LO, DEAD_HI],
                                    "reach": [BAND_LO, BAND_HI], "hard_stop": HARD_STOP}},
                         indent=2))
        return

    home = resolve_home()
    cfg = load_config(home)
    facets = [f for f in (cfg.get("facets") or []) if isinstance(f, str)]
    target_mix = cfg.get("target_mix") or DEFAULT_TARGET_MIX
    twin_cap = int(cfg.get("twin_cap", DEFAULT_TWIN_CAP))
    if "--twin-cap" in sys.argv:
        twin_cap = int(sys.argv[sys.argv.index("--twin-cap") + 1])

    if "--week" in sys.argv:
        wk = sys.argv[sys.argv.index("--week") + 1]
        if not os.path.isabs(wk):
            wk = os.path.join(home, wk)
    else:
        files = sorted(glob.glob(os.path.join(home, "weeks", "*.json")))
        wk = files[-1] if files else None
    if not wk or not os.path.exists(wk):
        print(f"no week file found under {home}/weeks/")
        return

    d = json.load(open(wk))
    # Two lanes. A twin rides on a video script; a solo is written for the feed alone and
    # lives in the week file's linkedin[] list. Both compete for the same five slots.
    items = [dict(i, _kind="twin") for i in d.get("distribution", []) if i.get("linkedin")]
    items += [dict({"linkedin": t, **{k: v for k, v in t.items() if k != "linkedin"}},
                   _kind="solo") for t in d.get("linkedin", [])]

    n_twin = sum(1 for i in items if i["_kind"] == "twin")
    print(f"week {d.get('week')}   {n_twin} twin candidate(s), "
          f"{len(items) - n_twin} LinkedIn-only, twin cap {twin_cap}\n")
    if not items:
        print("no LinkedIn posts in this week file.")
        if not cfg.get("linkedin_twins"):
            print("`linkedin_twins` is off in radar-config.json, so this is expected.")
        return

    rows, undeclared_any = [], False
    for it in items:
        f, _ = features(it, facets)
        shape, conf = propose_shape(it, f)
        job = SHAPES[shape]
        s, why = score(f)
        undeclared_any = undeclared_any or bool(f["undeclared"])
        rows.append((s, it, f, shape, conf, job, why))

    for s, it, f, shape, conf, job, why in sorted(rows, key=lambda r: -r[0]):
        lane = "twin" if it.get("_kind") == "twin" else "LinkedIn-only"
        print(f"[{s:>4}]  {it.get('id')}  {shape}  ({job})  [{lane}]   confidence: {conf}")
        print(f"        {str(it.get('title'))[:72]}")
        print(f"        {f['chars']} chars = {f['band']}   units={f['units']}"
              f"   carousel_shaped={f['carousel_shaped']}")
        if why:
            print(f"        score: {', '.join(why)}")
        if f["undeclared"]:
            print(f"        UNDECLARED (not guessed): {', '.join(f['undeclared'])}")
        print()

    selected, cut = allocate(rows, target_mix, twin_cap)
    jobs, shapes = {}, {}
    for s, it, f, shape, conf, job, why in selected:
        jobs[job] = jobs.get(job, 0) + 1
        shapes[shape] = shapes.get(shape, 0) + 1

    print("=" * 72)
    print("WEEK VERDICT\n")

    cut_twins = [r for r in cut if r[1].get("_kind") == "twin"]
    cut_solos = [r for r in cut if r[1].get("_kind") != "twin"]
    if cut_twins:
        print(f"CUT FROM THE FEED ({len(cut_twins)}), still films and ships elsewhere:")
        for s, it, f, shape, conf, job, why in sorted(cut_twins, key=lambda r: -r[0]):
            print(f"  {it.get('id')}  score {s}  ({shape})  {job} slots filled by higher scores")
        print("  A twin is a candidate, not an entitlement. Every short-form platform still")
        print("  gets these: reach is their job, your ICP is LinkedIn's.\n")
    if cut_solos:
        print(f"BANKED ({len(cut_solos)}), written and holding for a future week:")
        for s, it, f, shape, conf, job, why in sorted(cut_solos, key=lambda r: -r[0]):
            print(f"  {it.get('id')}  score {s}  ({shape})  {job} slot taken this week")
        print("  No video behind these, so nothing else ships them. They keep their value")
        print("  and fill the first week their job comes up short.\n")

    print(f"job mix     {dict(sorted(jobs.items()))}")
    print(f"target      {target_mix}")
    short_any = False
    for job, want in target_mix.items():
        got = jobs.get(job, 0)
        if got < want:
            short_any = True
            print(f"  SHORT on {job}: {got} of {want}. {JOB_WHY_SHORT.get(job, '')}")
            print(f"  COMMISSION a {job} post into the week file's linkedin[] lane. It cannot")
            print(f"  come from the video slate: the twin lane can only reshape what your")
            print(f"  video side already wrote.")
            src = JOB_SOURCE.get(job)
            if src:
                for i, line in enumerate(textwrap.wrap(src, 70)):
                    print(f"  {'SOURCE: ' if i == 0 else '        '}{line}")
    if not short_any:
        print("  mix met.")
    print()

    # A playbook that names no moves is an essay with headings.
    weak = [(it.get("id"), f) for _, it, f, shape, *_ in selected
            if shape == "playbook" and f["heads"] and f["moves"] < f["heads"]]
    if weak:
        print("playbook    a unit that does not open with an instruction is a DIAGNOSIS")
        for pid, f in weak:
            print(f"  {pid}: {f['moves']} of {f['heads']} units name a move the reader can run.")
        print("  A playbook earns its slot by being runnable, not by being right. Each unit")
        print("  wants an instruction, what it costs, who proved it, and how the reader knows")
        print("  it worked. Heuristic: it checks a move was NAMED, not whether it is good.")
        over = [pid for pid, f in weak if f.get("executable")]
        if over:
            print(f"  DECLARED executable but reads diagnostic: {', '.join(over)}. Re-check it.")
        print()

    print(f"shape spread  {dict(sorted(shapes.items()))}")
    if len(shapes) == 1:
        print(f"  MONOCULTURE: all {len(selected)} posts are {list(shapes)[0]}. {len(selected)} of one")
        print(f"  shape read as one post published {len(selected)} times. Reassign at least two.")
    print()

    dead = [it.get("id") for _, it, f, *_ in rows if f["band"] == "DEAD ZONE"]
    over = [it.get("id") for _, it, f, *_ in rows if f["band"] == "OVER HARD STOP"]
    inband = sum(1 for _, _, f, *_ in rows if f["band"] == "reach band")
    print(f"length      {inband} of {len(rows)} in the {BAND_LO}-{BAND_HI} reach band")
    if dead:
        print(f"  DEAD ZONE ({DEAD_LO}-{DEAD_HI} chars, wins neither dwell nor replies): "
              f"{', '.join(dead)}")
    if over:
        print(f"  OVER {HARD_STOP} (reported engagement falloff): {', '.join(over)}")
    print()

    shaped = [it.get("id") for _, it, f, *_ in selected if f["carousel_shaped"]]
    print(f"carousel    {len(shaped)} of {len(selected)} are carousel-shaped (3+ headed units)")
    if shaped:
        print(f"  Ship these as document posts, text as framing: {', '.join(shaped)}")
        print("  Biggest lever available: ~6.60% vs ~2.00% engagement.")
    latent = [it.get("id") for _, it, f, *_ in selected
              if f.get("ordering_claim") and not f["carousel_shaped"]]
    if latent:
        print(f"  LATENT: {', '.join(latent)} carries a sequence argument written as prose.")
        print("  One slide per step would make the ordering visible and unlock the 3x.")
        print("  That is a rewrite of live creative, so it is your call, not a mechanical fix.")
        print("  If yes: flag it Carousel on the dashboard, Export carousel queue, then run")
        print("  build_carousels.py. Card copy must come from this item's own beats, never a")
        print("  fresh writing session, or the cards carry claims the script never verified.")
    if not shaped and not latent:
        print("  Nothing this week is carousel-shaped. That is a BRIEF-stage gap, not a")
        print("  twin-stage one: no playbook or reorder was commissioned.")
    print()

    plan = schedule(selected, d.get("week"))

    # Persist. Before 2.7 the shape was computed, printed, and thrown away, so a twin kept
    # rendering the video's post_type and the dashboard showed a shape the selector had
    # already replaced. A proposal nobody writes down is a proposal nobody acts on.
    if "--no-write" not in sys.argv:
        written, pinned, marked = 0, 0, 0
        for s_, it, f, shape, conf, job, why in selected:
            tw = it.get("linkedin")
            if isinstance(tw, dict):
                tw["linkedin_shape"], tw["job"] = shape, job
                tw["twin_cut"] = False
                tw.pop("banked", None)
        # Losing a slot means different things per lane. A cut TWIN still films and ships
        # everywhere else, so nothing is lost. A cut SOLO has no video behind it and
        # carries to a future week instead.
        for s_, it, f, shape, conf, job, why in cut:
            tw = it.get("linkedin")
            if isinstance(tw, dict):
                tw["linkedin_shape"], tw["job"] = shape, job
                if it.get("_kind") == "twin":
                    tw["twin_cut"] = True
                    tw["cut_why"] = f"score {s_}, {job} slots filled by higher-scoring posts"
                else:
                    tw["banked"] = True
                    tw["cut_why"] = f"score {s_}, {job} slot taken. Carries to a future week."
                for k in ("post_day", "post_slot", "post_why"):
                    tw.pop(k, None)
                marked += 1
        for it, day, slot, why in plan:
            tw = it.get("linkedin")
            if not isinstance(tw, dict) or day is None:
                continue
            if tw.get("post_day_locked") and tw.get("post_day"):
                pinned += 1
                continue
            tw["post_day"], tw["post_slot"], tw["post_why"] = day.isoformat(), slot, why
            written += 1
        with open(wk, "w") as fh:
            json.dump(d, fh, indent=2)
            fh.write("\n")
        print(f"wrote shape + post_day to {written} post(s) in {os.path.basename(wk)}"
              f"{f', {marked} cut or banked' if marked else ''}"
              f"{f', kept {pinned} pinned' if pinned else ''}.")
        print("  Pin a day against re-runs with \"post_day_locked\": true on the post.")
        print("  Rebuild the dashboard to see the calendar: python3 build_dashboard.py\n")

    if undeclared_any:
        print("DECLARE THESE on the twin to make the selector deterministic:")
        print("  news_peg_days   age of the story in days (full <=3, half 4-7, zero after)")
        print("  angle_unclaimed true if the STORY is saturated but your ANGLE is not")
        print("  evergreen       true if the item has no news peg by design")
        print("  arguable        true if a credible practitioner could disagree")
        print("  executable      true if the reader can run it from the post alone")
        print("  ordering_claim  true if the argument is the SEQUENCE, not the items")
        print("  friction_story  true if it carries a real failure of your own")
        print("  deadline        ISO date the reader must act before; drives urgency")
        print("  linkedin_shape  overrides the proposal entirely "
              f"({', '.join(sorted(SHAPES))})")


if __name__ == "__main__":
    main()

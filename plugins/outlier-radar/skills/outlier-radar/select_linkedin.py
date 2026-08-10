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

# Character bands, from published platform studies (see references/linkedin-selector.md
# for sourcing and its limits). Characters, not words: characters are what the platform
# counts and what the fold and the 3,000 cap are measured in.
BAND_LO, BAND_HI, HARD_STOP, SHORT_MAX, DEAD_LO, DEAD_HI = 1300, 1900, 2500, 300, 600, 1000

# Target mix per 5-post week. Not a taste ratio: a portfolio.
# Follower growth = reach to non-followers x conversion to follow. Reach posts bring
# strangers, authority posts convert them and farm saves (a save reportedly drives about
# 5x the reach of a like), relatability retains. Drop a leg and the funnel starves.
TARGET_MIX = {"reach": 2, "authority": 2, "relatability": 1}

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
    "playbook": "authority",     # numbered repeatable system. Carousel-shaped.
    "reorder": "reach",          # the argument is the SEQUENCE, not the items. Carousel-shaped.
    "newsjack": "reach",         # borrowed attention from a live story
    "teardown": "authority",     # a subject diagnosed, standing on its own analysis
    "confession": "relatability",  # an admission that reads as bad news, then turns
    "short": "reach",            # one idea, under ~300 chars, wins on replies not dwell
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
              "ordering_claim", "friction_story", "evergreen"):
        f[k] = tw.get(k, item.get(k))
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
        if f.get("evergreen"):
            ever.append((s, it, f, shape, job, None))
        elif step is not None:
            live.append((s, it, f, shape, job, step))
        else:
            spent.append((s, it, f, shape, job, None))

    live.sort(key=lambda r: (r[5], -r[0]))
    spent.sort(key=lambda r: -r[0])
    ever.sort(key=lambda r: -r[0])
    ordered = live + spent + ever
    days = weekdays_from(anchor, len(ordered))
    conflict = [r for r in live if r[5] <= 1]

    for i, (s, it, f, shape, job, step) in enumerate(ordered):
        day = days[i]
        when = day.strftime("%a %d %b") if day else f"slot {i+1}"
        cost = ""
        if step is not None:
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

    if len(conflict) > 1:
        ids = ", ".join(r[1].get("id") for r in conflict)
        print(f"SLOT CONFLICT: {len(conflict)} items ({ids}) each lose peg value within a day,")
        print("  and there is one day-one slot. Options: double up on day one and accept a")
        print("  split audience, or take the peg loss on the lower scorer and publish it as")
        print("  an authority post instead. That is a judgment call, not a mechanical fix.\n")

    if ever:
        print(f"Evergreen items ({', '.join(r[1].get('id') for r in ever)}) are the buffer:")
        print("  they hold their value, so they absorb a slipped week or a hot drop.\n")


def main():
    if "--weights" in sys.argv:
        print(json.dumps({"weights": WEIGHTS, "target_mix": TARGET_MIX,
                          "bands": {"short_max": SHORT_MAX, "dead": [DEAD_LO, DEAD_HI],
                                    "reach": [BAND_LO, BAND_HI], "hard_stop": HARD_STOP}},
                         indent=2))
        return

    home = resolve_home()
    cfg = load_config(home)
    facets = [f for f in (cfg.get("facets") or []) if isinstance(f, str)]

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
    items = [i for i in d.get("distribution", []) if i.get("linkedin")]
    items += [{"linkedin": t, **{k: v for k, v in t.items() if k != "linkedin"}}
              for t in d.get("linkedin", [])]

    print(f"week {d.get('week')}   {len(items)} twins\n")
    if not items:
        print("no LinkedIn twins in this week file.")
        if not cfg.get("linkedin_twins"):
            print("`linkedin_twins` is off in radar-config.json, so this is expected.")
        return

    rows, jobs, shapes, undeclared_any = [], {}, {}, False
    for it in items:
        f, _ = features(it, facets)
        shape, conf = propose_shape(it, f)
        job = SHAPES[shape]
        s, why = score(f)
        jobs[job] = jobs.get(job, 0) + 1
        shapes[shape] = shapes.get(shape, 0) + 1
        undeclared_any = undeclared_any or bool(f["undeclared"])
        rows.append((s, it, f, shape, conf, job, why))

    for s, it, f, shape, conf, job, why in sorted(rows, key=lambda r: -r[0]):
        print(f"[{s:>4}]  {it.get('id')}  {shape}  ({job})   confidence: {conf}")
        print(f"        {str(it.get('title'))[:72]}")
        print(f"        {f['chars']} chars = {f['band']}   units={f['units']}"
              f"   carousel_shaped={f['carousel_shaped']}")
        if why:
            print(f"        score: {', '.join(why)}")
        if f["undeclared"]:
            print(f"        UNDECLARED (not guessed): {', '.join(f['undeclared'])}")
        print()

    print("=" * 72)
    print("WEEK VERDICT\n")
    print(f"job mix     {dict(sorted(jobs.items()))}")
    print(f"target      {TARGET_MIX}")
    gap = {
        "reach": "No acquisition engine, so the week only reaches existing followers.",
        "authority": "Nothing farms saves, and a save is worth about 5x a like in reach.",
        "relatability": "Nothing human, so new visitors have no reason to follow rather than read.",
    }
    for job, want in TARGET_MIX.items():
        got = jobs.get(job, 0)
        if got < want:
            print(f"  SHORT on {job}: {got} of {want}. {gap[job]}")
    print()

    print(f"shape spread  {dict(sorted(shapes.items()))}")
    if len(shapes) == 1:
        print(f"  MONOCULTURE: all {len(rows)} twins are {list(shapes)[0]}. {len(rows)} posts of one")
        print(f"  shape read as one post published {len(rows)} times. Reassign at least two.")
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

    shaped = [it.get("id") for _, it, f, *_ in rows if f["carousel_shaped"]]
    print(f"carousel    {len(shaped)} of {len(rows)} are carousel-shaped (3+ headed units)")
    if shaped:
        print(f"  Ship these as document posts, text as framing: {', '.join(shaped)}")
        print("  Biggest lever available: ~6.60% vs ~2.00% engagement.")
    latent = [it.get("id") for _, it, f, *_ in rows
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

    schedule(rows, d.get("week"))

    if undeclared_any:
        print("DECLARE THESE on the twin to make the selector deterministic:")
        print("  news_peg_days   age of the story in days (full <=3, half 4-7, zero after)")
        print("  angle_unclaimed true if the STORY is saturated but your ANGLE is not")
        print("  evergreen       true if the item has no news peg by design")
        print("  arguable        true if a credible practitioner could disagree")
        print("  executable      true if the reader can run it from the post alone")
        print("  ordering_claim  true if the argument is the SEQUENCE, not the items")
        print("  friction_story  true if it carries a real failure of your own")
        print("  linkedin_shape  overrides the proposal entirely "
              f"({', '.join(sorted(SHAPES))})")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Weekly LinkedIn intake. Alex pastes a feed table, this turns it into store rows.

The loop it serves (his 2026-08-11 directive): at some point each week he hands over the
activity-feed numbers, the engine studies them, and the LOCAL Radar gets small tuning
edits from what is working. This script is only the intake half. It never tunes anything;
it lands clean rows and prints what a human then has to decide.

Why it exists when log_perf.py --linkedin already logs LinkedIn: that mode asks one
input() per post. Pasting 20 rows into it is 80 prompts, so in practice the numbers do not
get logged, which is exactly how performance/ stayed empty for ten weeks.

Usage:
  python3 ingest_feed.py < table.md              dry run, proposes everything, writes nothing
  python3 ingest_feed.py --commit < table.md     writes performance.jsonl + post-meta stubs
  python3 ingest_feed.py --measured 2026-08-11 --commit < table.md

Input: the markdown table from the feed sweep, or loose pipe/tab rows. Tolerant of
thousands separators, en-dash and "-" for empty cells, footnote asterisks, and a leading
row number. Expected columns, in order:

  # | age | topic/hook | reactions | comments | reposts | impressions

RE-INGEST IS SAFE AND IS THE POINT. Ids are derived from post identity (matched Radar id,
or an `x-<postdate>-<row>` mint), never from the measurement, so handing over an
overlapping table appends a fresh dated measurement rather than a duplicate post.
log_perf.py keeps the latest `measured` per id.

Identity comes from ONE place: the `_aliases` map in post-meta.json, normalised topic text
-> post id. A row it does not cover is reported UNRESOLVED and not written, with a ranked
shortlist of plausible Radar posts to check against the week files. Resolving a row means
adding an alias, so each week's judgement is permanent and the same table always produces
the same ids. Two earlier attempts to auto-match on text similarity both shipped wrong
ids; see the note by RARE_DF.

Organic posts (Alex's own, no Radar id) get an `x-<postdate>-<row>` alias and need
dimensions in post-meta.json before they can be ranked: linkedin_format, job, medium,
repeatable, topic_class. Those are judgement calls a regex gets wrong, and a wrong
dimension is worse than a missing one.

Rows that are reshares of someone else's post are flagged, not logged: their counts are
the original author's aggregate, so they would corrupt every average they touch.
"""

import glob
import json
import math
import os
import re
import sys
from datetime import date, datetime, timedelta

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
PERF = os.path.join(RADAR, "performance", "performance.jsonl")
POSTMETA = os.path.join(RADAR, "performance", "post-meta.json")

MATURE_HOURS = 48

# Identity resolution, and the first version of this got it wrong in both directions, so
# the reasoning is worth keeping. Character-similarity between two short marketing phrases
# is noise: it matched "Everything in marketing works" to "Marketing's two religions" and
# "Steal the strategy" to the Moonshot teardown, while MISSING Domino's because norm()
# stripped the parenthetical that held the peg. A wrong match is worse than no match,
# because it silently welds one post's numbers onto another post's dimensions.
#
# The proper-noun version of that idea did better and still failed confidently: it took the
# pronoun "me" as a distinctive token, matched "Steal the strategy" on "strategy", and
# MISSED the real Apple twin while matching a different post on "search". Two rounds of
# threshold tuning both shipped wrong ids, so auto-assignment is gone rather than tuned a
# third time. Scoring now only RANKS A SHORTLIST for a human; the alias map below is the
# single resolution path. Determinism beats coverage here: an unresolved row costs one
# decision, a wrong id costs a corrupted dimension nobody will ever see.
RARE_DF = 3
SHORTLIST = 3


def _tok(t):
    return [w for w in t.split() if len(w) > 1]

AGE = re.compile(r"^(\d+)\s*(h|hr|hrs|hour|hours|d|day|days|w|wk|week|weeks|mo|month|months|y)$", re.I)
RESHARE = re.compile(r"\b(repost|reshare|shared)\b", re.I)


def parse_age(s):
    """-> (hours, precision). LinkedIn shows relative ages only, and coarsely: '1mo' is
    anything from 4 to 8 weeks. Precision is recorded so nothing downstream treats a
    month-granular date as a day-granular one."""
    s = (s or "").strip().lower().replace(" ", "")
    m = AGE.match(s)
    if not m:
        return None, None
    n, unit = int(m.group(1)), m.group(2)
    if unit.startswith("h"):
        return n, "hour"
    if unit.startswith("d"):
        return n * 24, "day"
    if unit.startswith("w"):
        return n * 168, "week"
    if unit.startswith("y"):
        return n * 8760, "year"
    return n * 720, "month"


def num(s):
    """'41,652' -> 41652. En dash, hyphen, empty, 'n/a' -> None. '(672)*' -> 672."""
    s = (s or "").strip()
    if not s or s in {"-", "–", "—", "n/a", "N/A", "——"}:
        return None
    d = re.sub(r"[^\d]", "", s)
    return int(d) if d else None


def norm(t):
    """Parentheticals are KEPT. Radar titles put the identifying peg in them ("How Domino's
    actually sells (six million views on a PlayStation)"), so stripping them threw away the
    only part that identifies the post."""
    t = (t or "").lower()
    t = re.sub(r"[^a-z0-9 ]", " ", t)
    stop = {"the", "a", "an", "of", "to", "and", "actually", "sells", "sell", "how",
            "my", "i", "your", "you", "it", "is", "in", "on", "for", "video", "doc",
            "just", "with", "that", "this", "from", "was", "not", "but", "all", "one"}
    return " ".join(w for w in t.split() if w not in stop and len(w) > 1)


def load_candidates():
    """Every Radar post that could own a pasted row: LinkedIn twins and solos. Keyed by
    id, valued by the strings worth matching against."""
    cands = {}
    for f in sorted(glob.glob(os.path.join(RADAR, "weeks", "*.json"))):
        if ".bak" in f:
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        for lane in ("distribution", "office"):
            for it in d.get(lane, []):
                tw = it.get("linkedin") or {}
                if tw.get("id"):
                    cands[tw["id"]] = [it.get("title"), tw.get("title"),
                                       it.get("text_hook"), tw.get("hook_arch")]
        for tw in d.get("linkedin", []):
            if tw.get("id"):
                cands[tw["id"]] = [tw.get("title"), tw.get("text_hook"), tw.get("hook_arch")]
    return {k: [norm(s) for s in v if s] for k, v in cands.items()}


def build_df(cands):
    """Document frequency per token across candidate posts, so 'domino' can outweigh
    'marketing'."""
    df = {}
    for pid, strings in cands.items():
        for w in {w for s in strings for w in _tok(s)}:
            df[w] = df.get(w, 0) + 1
    return df


def shortlist(topic, cands, df):
    """-> [(id, score, shared_rare_tokens)] ranked, at most SHORTLIST long. A SUGGESTION
    for a human, never an assignment. Requires a shared rare token so the list stays short
    enough to actually check."""
    q = set(_tok(norm(topic)))
    if not q:
        return None, 0.0, []
    n = max(len(cands), 1)
    idf = {w: math.log(n / max(df.get(w, 0), 1) + 1e-9) if df.get(w) else math.log(n + 1.0)
           for w in q}
    hits = []
    for pid, strings in cands.items():
        ctoks = {w for s in strings for w in _tok(s)}
        shared = q & ctoks
        if not shared:
            continue
        shared_rare = sorted(w for w in shared if df.get(w, 0) <= RARE_DF)
        if not shared_rare:
            continue                      # only common words in common: not evidence
        num_ = sum(idf[w] for w in shared)
        den = sum(idf[w] for w in q if df.get(w, 0)) or num_
        hits.append((pid, round(num_ / den, 3), shared_rare))
    hits.sort(key=lambda h: -h[1])
    return hits[:SHORTLIST]


def parse_table(text):
    rows = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or set(line) <= set("|-: "):
            continue
        cells = [c.strip() for c in (line.split("|") if "|" in line else line.split("\t"))]
        cells = [c for c in cells if c != ""]
        if len(cells) < 6:
            continue
        if cells[0].lower().startswith("#") or "impress" in line.lower():
            continue
        # Leading row number is optional.
        if re.fullmatch(r"\d{1,3}", cells[0]) and parse_age(cells[1])[0] is not None:
            rownum, age, topic, rest = cells[0], cells[1], cells[2], cells[3:]
        elif parse_age(cells[0])[0] is not None:
            rownum, age, topic, rest = str(len(rows) + 1), cells[0], cells[1], cells[2:]
        else:
            continue
        hours, precision = parse_age(age)
        rows.append({
            "row": int(rownum), "age_reported": age.strip(), "topic": topic,
            "age_hours": hours, "date_precision": precision,
            "reactions": num(rest[0] if len(rest) > 0 else None),
            "comments": num(rest[1] if len(rest) > 1 else None),
            "reposts": num(rest[2] if len(rest) > 2 else None),
            "impressions": num(rest[3] if len(rest) > 3 else None),
            "raw": line,
        })
    return rows


def main():
    commit = "--commit" in sys.argv
    measured = None
    if "--measured" in sys.argv:
        measured = sys.argv[sys.argv.index("--measured") + 1]
    measured = measured or date.today().isoformat()
    anchor = datetime.strptime(measured, "%Y-%m-%d").date()

    text = sys.stdin.read()
    rows = parse_table(text)
    if not rows:
        print("parsed 0 rows. Expected: # | age | topic | reactions | comments | reposts | impressions")
        return 1

    cands = load_candidates()
    meta = json.load(open(POSTMETA)) if os.path.exists(POSTMETA) else {}
    seen_ids = set()
    if os.path.exists(PERF):
        for l in open(PERF):
            if l.strip():
                seen_ids.add(json.loads(l).get("id"))

    print(f"measured {measured}   parsed {len(rows)} rows   "
          f"{len(cands)} Radar LinkedIn posts on disk\n")

    # The alias map is the store's memory of identity decisions. Checked before any
    # guessing, so a topic line resolved by hand once is deterministic every week after,
    # and re-ingesting an overlapping table can never split one post across two ids.
    aliases = meta.get("_aliases", {})
    df = build_df(cands)

    out, skipped, unresolved, taken = [], [], [], set()
    for r in rows:
        if r["impressions"] is None:
            skipped.append((r, "no impressions column"))
            continue
        if RESHARE.search(r["topic"]) and (r["reactions"] or 0) > 300:
            skipped.append((r, "reshare of someone else's post; counts are the original "
                               "author's aggregate, logging it would corrupt every average"))
            continue

        pid = aliases.get(norm(r["topic"]))
        if not pid:
            unresolved.append((r, shortlist(r["topic"], cands, df)))
            continue

        row = {"id": pid, "impressions": r["impressions"],
               "reactions": r["reactions"] or 0, "comments": r["comments"] or 0,
               "reposts": r["reposts"] or 0, "measured": measured,
               "age_reported": r["age_reported"], "age_hours": r["age_hours"],
               "mature": (r["age_hours"] or 0) >= MATURE_HOURS}
        out.append(row)
        tag = "re-measure" if pid in seen_ids else "new"
        mat = "" if row["mature"] else "  IMMATURE, stored not ranked"
        print(f"  {r['impressions']:>7,}  {r['age_reported']:>4}  {tag:<10} {pid:<22} "
              f"{r['topic'][:36]}{mat}")

    print()
    if skipped:
        print("EXCLUDED:")
        for r, why in skipped:
            print(f"  row {r['row']}  {r['topic'][:44]}\n      {why}")
        print()

    if unresolved:
        print(f"UNRESOLVED ({len(unresolved)}). NOT written, by design: a guessed identity")
        print("welds one post's numbers onto another post's dimensions, and nothing")
        print("downstream would ever show you it happened. Decide each one, then add it to")
        print('post-meta.json under "_aliases" as  "<normalised topic>": "<post id>".')
        for r, cand in unresolved:
            pdate = anchor - timedelta(hours=r["age_hours"] or 0)
            mint = f"x-{pdate.strftime('%Y%m%d')}-{r['row']}"
            print(f"\n  row {r['row']}  {r['impressions']:,}  {r['age_reported']}  {r['topic'][:46]}")
            print(f'      "{norm(r["topic"])}": "<id>"')
            if cand:
                print("      candidates, RANKED NOT CHOSEN, verify against the week file:")
                for pid, sc, rare in cand:
                    print(f"        {pid:<22} {sc:<6} shares {'+'.join(rare)}")
            else:
                print("      no Radar post shares a distinctive token")
            print(f"      if it is one of Alex's own posts, use: {mint}")
        print()

    if not commit:
        print("DRY RUN. Nothing written. Re-run with --commit to land these.")
        return 0

    with open(PERF, "a") as f:
        for row in out:
            f.write(json.dumps(row) + "\n")
    print(f"wrote {len(out)} rows -> {PERF}")
    if unresolved:
        print(f"{len(unresolved)} row(s) NOT written, still unresolved. Alias them and re-run.")
    print("\nnext: python3 scripts/log_perf.py --report")
    return 0


if __name__ == "__main__":
    sys.exit(main())

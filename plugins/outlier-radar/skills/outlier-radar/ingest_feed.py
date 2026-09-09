#!/usr/bin/env python3
"""
Weekly intake. The creator pastes a table, this turns it into store rows.

The loop it serves (a standing call from the creator, 2026-08-11): each week they hand over the
activity-feed numbers, the engine studies them, and the LOCAL Radar gets small tuning
edits from what is working. This script is only the intake half. It never tunes anything;
it lands clean rows and prints what a human then has to decide.

Why it exists when log_perf.py --linkedin already logs LinkedIn: that mode asks one
input() per post. Pasting 20 rows into it is 80 prompts, so in practice the numbers do not
get logged, which is exactly how performance/ stayed empty for ten weeks.

Three pastes (the TikTok and people paths were added 2026-09-09, audit Q1 items 9 and 12):

  LINKEDIN, the activity-feed table
    python3 ingest_feed.py < table.md              dry run, proposes everything, writes nothing
    python3 ingest_feed.py --commit < table.md     writes performance.jsonl
    python3 ingest_feed.py --measured 2026-08-11 --commit < table.md
    Expected columns, in order:  # | age | topic/hook | reactions | comments | reposts | impressions

  TIKTOK, the Studio content table (Analytics > Content, select all, copy)
    python3 ingest_feed.py --tiktok < studio.txt            dry run
    python3 ingest_feed.py --tiktok --commit < studio.txt
    Headers are matched by name, in any order: title, date, views, likes, comments, shares,
    avg watch time (12.3s or 0:12), watched full %, new followers, and the traffic-source
    columns (for you, following, search, profile, other) when present. Rows land with the
    Contract 5 retention fields: avg_watch_s, full_watch_pct, follows, source_split.

  PEOPLE, who engaged (one person per line: name, headline or role, company, url)
    python3 ingest_feed.py --people --kind comment_by --post d-20260907-3 < names.txt
    kinds: comment_by comment_on connect dm_sent dm_reply tag tag_reply invite request
    Upserts performance/people.jsonl. icp is true when the headline matches
    radar-config.json audience.icp_regex (default: growth|marketing|gtm|cmo|revenue|demand).
    Writes immediately (there is no identity guess to review); --dry-run previews.

RE-INGEST IS SAFE AND IS THE POINT. Ids are derived from post identity (matched Radar id,
or an `x-<postdate>-<row>` mint), never from the measurement, so handing over an
overlapping table appends a fresh dated measurement rather than a duplicate post.
log_perf.py keeps the latest `measured` per id.

Identity comes from ONE place: the `_aliases` map in post-meta.json, normalised topic text
-> post id. A row it does not cover is reported UNRESOLVED and not written, with a ranked
shortlist of plausible Radar posts to check against the week files. Resolving a row means
adding an alias, so each week's judgement is permanent and the same table always produces
the same ids. Two earlier attempts to auto-match on text similarity both shipped wrong
ids; see the note by RARE_DF. The TikTok path adds ONE deterministic shortcut: a caption
that normalises to exactly one Radar title or text_hook resolves, because that is the same
string, not a similarity.

Organic posts (the creator's own, no Radar id) get an `x-<postdate>-<row>` alias and need
dimensions in post-meta.json before they can be ranked: linkedin_format, job, medium,
repeatable, topic_class. Those are judgement calls a regex gets wrong, and a wrong
dimension is worse than a missing one.

Rows that are reshares of someone else's post are flagged, not logged: their counts are
the original author's aggregate, so they would corrupt every average they touch.
"""

import argparse
import glob
import json
import math
import os
import re
import sys
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yapcut_home import radar_home  # noqa: E402

RADAR = str(radar_home())      # consumes --dir; exits 2 with the places looked when none found
PERF = os.path.join(RADAR, "performance", "performance.jsonl")
POSTMETA = os.path.join(RADAR, "performance", "post-meta.json")
PEOPLE = os.path.join(RADAR, "performance", "people.jsonl")
CONFIG = os.path.join(RADAR, "radar-config.json")

MATURE_HOURS = 48
DEFAULT_ICP = r"growth|marketing|gtm|cmo|revenue|demand"
PEOPLE_KINDS = ("comment_by", "comment_on", "connect", "dm_sent", "dm_reply", "tag",
                "tag_reply", "invite", "request")

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
    """'41,652' -> 41652. '1.2K' -> 1200. '3.4M' -> 3400000. En dash, hyphen, empty, 'n/a' -> None.
    '(672)*' -> 672."""
    s = (s or "").strip()
    if not s or s in {"-", "–", "—", "n/a", "N/A", "——"}:
        return None
    m = re.match(r"^[^\d]*(\d[\d,]*\.?\d*)\s*([KkMmBb])?\b", s)
    if m and m.group(2):
        base = float(m.group(1).replace(",", ""))
        mult = {"k": 1e3, "m": 1e6, "b": 1e9}[m.group(2).lower()]
        return int(round(base * mult))
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


def week_files():
    for f in sorted(glob.glob(os.path.join(RADAR, "weeks", "*.json"))):
        if ".bak" in f or f.endswith(".gate.json"):
            continue
        try:
            yield f, json.load(open(f))
        except Exception:
            continue


def load_candidates():
    """Every Radar post that could own a pasted LinkedIn row: LinkedIn twins and solos.
    Keyed by id, valued by the strings worth matching against."""
    cands = {}
    for f, d in week_files():
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


def load_video_candidates():
    """Every Radar VIDEO script a TikTok caption could belong to. Returns (cands, exact)
    where exact maps a normalised title or text_hook to the ids that carry it."""
    cands, exact = {}, {}
    for f, d in week_files():
        for lane in ("distribution", "office"):
            for it in d.get(lane, []):
                if not it.get("id"):
                    continue
                strings = [it.get("title"), it.get("text_hook")]
                strings += [a for a in (it.get("text_hook_alts") or []) if isinstance(a, str)]
                sh = (it.get("spoken_hook") or "").split("\n")[0]
                if sh:
                    strings.append(sh)
                pc = it.get("post_copy") if isinstance(it.get("post_copy"), dict) else {}
                if pc.get("caption"):
                    strings.append(pc["caption"])
                cands[it["id"]] = [norm(s) for s in strings if s]
                for s in strings:
                    n = norm(s)
                    if n:
                        exact.setdefault(n, set()).add(it["id"])
    return cands, exact


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
        return []
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


# --- TikTok Studio -------------------------------------------------------------------------

TT_HEADERS = [
    # (field, [header substrings, lowercase]) checked in this order; first hit wins
    ("full_watch_pct", ["watched full", "watched the full", "full video", "completion", "watched in full", "full watch"]),
    ("avg_watch_s", ["avg watch", "average watch", "avg. watch", "average time watched", "avg time", "watch time"]),
    ("follows", ["new followers", "net followers", "followers", "follows"]),
    ("for_you", ["for you", "fyp"]),
    ("following", ["following"]),
    ("search", ["search"]),
    ("profile", ["profile"]),
    ("other", ["other", "sound", "hashtag"]),
    ("views", ["video views", "views", "plays"]),
    ("likes", ["likes", "hearts"]),
    ("comments", ["comments"]),
    ("shares", ["shares"]),
    ("date", ["post time", "posted", "publish", "date", "time"]),
    ("title", ["title", "video", "post", "caption", "description", "name"]),
]
TT_DEFAULT_ORDER = ["title", "date", "views", "likes", "comments", "shares",
                    "avg_watch_s", "full_watch_pct", "follows"]
SOURCE_FIELDS = ("for_you", "following", "search", "profile", "other")


def _split_cells(line):
    if "\t" in line:
        cells = line.split("\t")
    elif "|" in line:
        cells = line.strip().strip("|").split("|")
    else:
        return None
    return [c.strip() for c in cells]


def _header_map(cells):
    """column index -> field, or None when the line does not look like a header."""
    mapping, used = {}, set()
    for i, c in enumerate(cells):
        low = c.lower().strip()
        if not low:
            continue
        for field, keys in TT_HEADERS:
            if field in used:
                continue
            if any(k in low for k in keys):
                mapping[i] = field
                used.add(field)
                break
    known = set(mapping.values())
    return mapping if len(known & {"views", "likes", "comments", "title", "date"}) >= 3 else None


def parse_watch(s):
    """'12.3s' -> 12.3; '0:12' or '00:01:12' -> seconds; '12' -> 12.0."""
    s = (s or "").strip().lower()
    if not s or s in {"-", "–", "—", "n/a"}:
        return None
    if ":" in s:
        parts = [p for p in s.split(":") if p != ""]
        try:
            secs = 0.0
            for p in parts:
                secs = secs * 60 + float(p)
            return round(secs, 2)
        except ValueError:
            return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(m|min|minutes?)?\s*(?:(\d+(?:\.\d+)?)\s*s)?", s)
    if not m:
        return None
    if m.group(2):
        return round(float(m.group(1)) * 60 + float(m.group(3) or 0), 2)
    return round(float(m.group(1)), 2)


def parse_pct(s):
    s = (s or "").strip()
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return round(float(m.group(1)), 2) if m else None


def parse_date(s):
    """Best effort on the formats TikTok Studio shows. Returns ISO date or None."""
    s = (s or "").strip()
    if not s:
        return None
    s2 = re.sub(r"\s+\d{1,2}:\d{2}(:\d{2})?\s*(am|pm)?$", "", s, flags=re.I)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y",
                "%m/%d/%Y", "%d/%m/%Y", "%b %d %Y", "%d.%m.%Y", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s2, fmt).date().isoformat()
        except ValueError:
            continue
    m = re.match(r"^(\d{4}-\d{2}-\d{2})", s)
    return m.group(1) if m else None


def parse_tiktok(text):
    """-> (rows, note). Each row: title, posted, views, likes, comments, shares, avg_watch_s,
    full_watch_pct, follows, source_split."""
    lines = [l for l in text.splitlines() if l.strip()]
    mapping, start, note = None, 0, ""
    for i, l in enumerate(lines[:8]):
        cells = _split_cells(l)
        if cells:
            mapping = _header_map(cells)
            if mapping:
                start = i + 1
                break
    if not mapping:
        note = ("no header row recognised; assuming TikTok Studio's default column order: "
                + ", ".join(TT_DEFAULT_ORDER))
        mapping = {i: f for i, f in enumerate(TT_DEFAULT_ORDER)}
    rows = []
    for l in lines[start:]:
        cells = _split_cells(l)
        if not cells or len(cells) < 3:
            continue
        rec = {}
        for i, field in mapping.items():
            if i < len(cells):
                rec[field] = cells[i]
        title = (rec.get("title") or "").strip()
        if not title or title.lower() in ("title", "total", "totals"):
            continue
        row = {
            "row": len(rows) + 1, "title": title,
            "posted": parse_date(rec.get("date")), "date_raw": rec.get("date"),
            "views": num(rec.get("views")), "likes": num(rec.get("likes")),
            "comments": num(rec.get("comments")), "shares": num(rec.get("shares")),
            "avg_watch_s": parse_watch(rec.get("avg_watch_s")),
            "full_watch_pct": parse_pct(rec.get("full_watch_pct")),
            "follows": num(rec.get("follows")),
            "raw": l.strip(),
        }
        split = {}
        for f in SOURCE_FIELDS:
            v = parse_pct(rec.get(f)) if rec.get(f) else None
            if v is not None:
                split[f] = round(v / 100.0, 4) if v > 1.0 else round(v, 4)
        if split:
            row["source_split"] = split
        rows.append(row)
    return rows, note


def tiktok_main(a, text):
    measured = a.measured or date.today().isoformat()
    rows, note = parse_tiktok(text)
    if note:
        print(note)
    if not rows:
        print("parsed 0 rows. Paste TikTok Studio's content table (title, date, views, likes, "
              "comments, shares, avg watch time, watched full %, new followers).")
        return 1
    cands, exact = load_video_candidates()
    meta = json.load(open(POSTMETA)) if os.path.exists(POSTMETA) else {}
    aliases = meta.get("_aliases", {})
    df = build_df(cands)
    seen_ids = set()
    if os.path.exists(PERF):
        for l in open(PERF):
            if l.strip():
                seen_ids.add(json.loads(l).get("id"))
    print(f"measured {measured}   parsed {len(rows)} TikTok rows   {len(cands)} Radar video scripts on disk\n")

    out, unresolved = [], []
    for r in rows:
        n = norm(r["title"])
        pid = aliases.get(n)
        how = "alias"
        if not pid:
            hits = exact.get(n) or set()
            if len(hits) == 1:
                pid, how = next(iter(hits)), "exact title/hook"
        if not pid:
            unresolved.append((r, shortlist(r["title"], cands, df)))
            continue
        row = {"id": pid, "platform": "tiktok", "measured": measured}
        for k in ("views", "likes", "comments", "shares", "avg_watch_s", "full_watch_pct",
                  "follows", "posted", "source_split"):
            if r.get(k) is not None:
                row[k] = r[k]
        if r.get("posted"):
            try:
                age_h = (datetime.strptime(measured, "%Y-%m-%d").date()
                         - datetime.strptime(r["posted"], "%Y-%m-%d").date()).days * 24
                row["age_hours"] = age_h
                row["mature"] = age_h >= MATURE_HOURS
            except ValueError:
                pass
        out.append(row)
        tag = "re-measure" if pid in seen_ids else "new"
        fw = f"{r['full_watch_pct']:>5.1f}% full" if r.get("full_watch_pct") is not None else "     -    "
        aw = f"{r['avg_watch_s']:>5.1f}s" if r.get("avg_watch_s") is not None else "    - "
        print(f"  {r.get('views') or 0:>8,} views  {fw}  {aw}  {tag:<10} {pid:<20} "
              f"({how})  {r['title'][:34]}")

    print()
    if unresolved:
        print(f"UNRESOLVED ({len(unresolved)}). NOT written, by design: a guessed identity welds")
        print("one video's retention onto another video's dimensions. Decide each one, then add")
        print('it to post-meta.json under "_aliases" as  "<normalised caption>": "<radar id>".')
        for r, cand in unresolved:
            print(f"\n  row {r['row']}  {r.get('views') or 0:,} views  {r.get('posted') or r.get('date_raw') or '?'}  {r['title'][:50]}")
            print(f'      "{norm(r["title"])}": "<id>"')
            if cand:
                print("      candidates, RANKED NOT CHOSEN, verify against the week file:")
                for pid, sc, rare in cand:
                    print(f"        {pid:<22} {sc:<6} shares {'+'.join(rare)}")
            else:
                print("      no Radar script shares a distinctive token")
            pdate = (r.get("posted") or measured).replace("-", "")
            print(f"      if it is not a Radar script, use: x-{pdate}-{r['row']}")
        print()

    if not a.commit:
        print(f"DRY RUN. {len(out)} row(s) ready. Re-run with --commit to land them.")
        return 0
    if out:
        os.makedirs(os.path.dirname(PERF), exist_ok=True)
        with open(PERF, "a") as f:
            for row in out:
                f.write(json.dumps(row) + "\n")
    print(f"wrote {len(out)} rows -> {PERF}")
    if unresolved:
        print(f"{len(unresolved)} row(s) NOT written, still unresolved. Alias them and re-run.")
    print("\nnext: python3 log_perf.py --report")
    return 0


# --- people -----------------------------------------------------------------------------------

def icp_regex():
    try:
        cfg = json.load(open(CONFIG)) if os.path.exists(CONFIG) else {}
        pat = ((cfg.get("audience") or {}).get("icp_regex")) or DEFAULT_ICP
        return re.compile(pat, re.I)
    except (ValueError, re.error):
        return re.compile(DEFAULT_ICP, re.I)


URL = re.compile(r"https?://\S+")


def parse_people(text):
    """One person per line. Tab or ' | ' separated fields (name, headline or role, company,
    url), or a loose line: 'Name - Head of Growth at Viktor https://...'."""
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.lower().startswith(("name\t", "name |", "#")):
            continue
        url = None
        m = URL.search(line)
        if m:
            url = m.group(0).rstrip(".,;)")
            line = (line[:m.start()] + line[m.end():]).strip(" \t|-")
        if "\t" in line:
            parts = [p.strip() for p in line.split("\t")]
        elif " | " in line:
            parts = [p.strip() for p in line.split(" | ")]
        else:
            parts = [p.strip() for p in re.split(r"\s+-\s+", line, maxsplit=1)]
        parts = [p for p in parts if p]
        if not parts:
            continue
        name, headline, company = parts[0], (parts[1] if len(parts) > 1 else ""), (parts[2] if len(parts) > 2 else "")
        if headline and not company:
            m2 = re.match(r"^(.*?)\s+(?:at|@)\s+(.+)$", headline, re.I)
            if m2:
                headline, company = m2.group(1).strip(), m2.group(2).strip()
        out.append({"name": name, "role": headline, "company": company, "url": url})
    return out


def _people_key(p):
    url = (p.get("url") or "").strip().lower().rstrip("/")
    return ("url", url) if url else ("name", (p.get("name") or "").strip().casefold())


def load_people():
    latest = {}
    if os.path.exists(PEOPLE):
        for l in open(PEOPLE):
            l = l.strip()
            if not l:
                continue
            try:
                p = json.loads(l)
            except ValueError:
                continue
            k = _people_key(p)
            if k[1]:
                latest[k] = p
    return latest


def upsert_people(people, kind, post_id, at=None, dry=False):
    """Append-only upsert: the merged record is appended and readers take the newest per
    url (else name). Nothing is ever rewritten, so a mistaken paste is one more line to
    read past, not a lost history."""
    today = at or date.today().isoformat()
    icp = icp_regex()
    latest = load_people()
    written = []
    for p in people:
        k = _people_key(p)
        if not k[1]:
            continue
        # a name-only paste may refer to someone already stored under a url
        cur = latest.get(k)
        if cur is None and k[0] == "url":
            cur = latest.get(("name", (p.get("name") or "").casefold()))
        if cur is None and k[0] == "name":
            for kk, v in latest.items():
                if (v.get("name") or "").casefold() == k[1]:
                    cur = v
                    break
        rec = dict(cur) if cur else {"name": p["name"], "first_seen": today, "touches": []}
        for f in ("url", "role", "company"):
            if p.get(f) and not rec.get(f):
                rec[f] = p[f]
        if p.get("name") and not rec.get("name"):
            rec["name"] = p["name"]
        text = " ".join(str(rec.get(f) or "") for f in ("role", "company"))
        rec["icp"] = bool(icp.search(text)) if text.strip() else bool(rec.get("icp"))
        rec["last_seen"] = today
        touch = {"date": today, "kind": kind, "post_id": post_id}
        touches = [t for t in (rec.get("touches") or []) if isinstance(t, dict)]
        if touch not in touches:
            touches.append(touch)
        rec["touches"] = touches
        latest[_people_key(rec)] = rec
        written.append(rec)
        flag = "ICP" if rec["icp"] else "   "
        new = "new" if not cur else "seen"
        print(f"  {flag} {new:<4} {rec.get('name','')[:26]:<26} {str(rec.get('role') or '')[:30]:<30} "
              f"{str(rec.get('company') or '')[:18]:<18} touches={len(touches)}")
    if dry:
        print(f"\nDRY RUN. {len(written)} record(s) would be appended to {PEOPLE}")
        return 0
    if written:
        os.makedirs(os.path.dirname(PEOPLE), exist_ok=True)
        with open(PEOPLE, "a") as fh:
            for rec in written:
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    n_icp = sum(1 for r in written if r.get("icp"))
    print(f"\nupserted {len(written)} people ({n_icp} ICP) as {kind} on {post_id or '-'} -> {PEOPLE}")
    return 0


def people_main(a, text):
    if a.kind not in PEOPLE_KINDS:
        print(f"--kind must be one of: {', '.join(PEOPLE_KINDS)}")
        return 2
    people = parse_people(text)
    if not people:
        print("parsed 0 people. One per line: name, headline or role, company, url.")
        return 1
    print(f"{len(people)} people parsed, kind {a.kind}, post {a.post or '-'}\n")
    return upsert_people(people, a.kind, a.post, at=a.measured, dry=a.dry_run)


# --- LinkedIn ------------------------------------------------------------------------------

def linkedin_main(a, text):
    commit = a.commit
    measured = a.measured or date.today().isoformat()
    anchor = datetime.strptime(measured, "%Y-%m-%d").date()

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

    out, skipped, unresolved = [], [], []
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

        row = {"id": pid, "platform": "linkedin", "impressions": r["impressions"],
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
            print(f"      if it is one of the creator's own posts, use: {mint}")
        print()

    if not commit:
        print("DRY RUN. Nothing written. Re-run with --commit to land these.")
        return 0

    os.makedirs(os.path.dirname(PERF), exist_ok=True)
    with open(PERF, "a") as f:
        for row in out:
            f.write(json.dumps(row) + "\n")
    print(f"wrote {len(out)} rows -> {PERF}")
    if unresolved:
        print(f"{len(unresolved)} row(s) NOT written, still unresolved. Alias them and re-run.")
    print("\nnext: python3 log_perf.py --report")
    return 0


def main():
    ap = argparse.ArgumentParser(description="paste-fed intake; see the module docstring")
    ap.add_argument("--dir", help="workspace (consumed by yapcut_home when given)")
    ap.add_argument("--commit", action="store_true", help="write rows (LinkedIn and TikTok paths)")
    ap.add_argument("--measured", help="YYYY-MM-DD the numbers were read (default today)")
    ap.add_argument("--tiktok", action="store_true", help="parse a TikTok Studio content table")
    ap.add_argument("--people", action="store_true", help="parse a list of people who engaged")
    ap.add_argument("--kind", default="comment_by", help="touch kind for --people")
    ap.add_argument("--post", default=None, help="post id the people touched, for --people")
    ap.add_argument("--dry-run", action="store_true", help="--people: preview, write nothing")
    a = ap.parse_args()
    if a.measured and not re.match(r"^\d{4}-\d{2}-\d{2}$", a.measured):
        print("--measured wants YYYY-MM-DD")
        return 2
    text = sys.stdin.read()
    if a.tiktok:
        return tiktok_main(a, text)
    if a.people:
        return people_main(a, text)
    return linkedin_main(a, text)


if __name__ == "__main__":
    sys.exit(main())

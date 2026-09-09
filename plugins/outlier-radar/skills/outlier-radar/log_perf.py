#!/usr/bin/env python3
"""
The feedback loop. Ten weeks and 175 scripts ran with performance/ empty, because
logging was event-driven and optional. It is now neither.

Designed to take under a minute. Paste numbers, done.

Usage:
  python3 log_perf.py                    interactive: lists unlogged posted items, asks for views
  python3 log_perf.py --paste            paste "id views" lines (or just views, in order), Ctrl-D
  python3 log_perf.py --linkedin         log the LinkedIn twins: impressions, reactions, comments
  python3 log_perf.py --followers [<week> <delta> [icp_pct]]   follower delta, non-interactive
                                         when the three values are given
  python3 log_perf.py --due              what to re-measure: logged too early, now settled
  python3 log_perf.py --report           what is working, by mechanic / post_type / intent.
                                         Also writes performance/last-report.md

  Tracking, the state that used to live only in the browser (Contract 5, 2026-09-09):
  python3 log_perf.py --filmed <id> [--at YYYY-MM-DD] [--notes "..."]
  python3 log_perf.py --posted <id> <url> [--platform tiktok] [--at YYYY-MM-DD]
  python3 log_perf.py --ignore <id>
  python3 log_perf.py --import <export.json>   the dashboard's export: tracking + views

  Closing the loop:
  python3 log_perf.py --weights-out      performance/learned.json for select_linkedin.py
  python3 log_perf.py --edits <output_dir>   merge the editor's *.edit.json into post-meta

The LinkedIn lane was invisible to this script until 2026-08-10: load_items() read only
`distribution` and `office`, so the twins that constitution rule 2 ships unconditionally
every week were the one thing never measured. They are in scope now, and they carry their
own dimensions (linkedin_format, job, character band) because the feed rewards different
things than the FYP does.

WHAT CHANGED 2026-09-09 (audit Q1 items 2, 9, 12, 13, 14). Filmed, posted and ignored
state gets a home on disk (performance/tracking.jsonl, append-only) instead of browser
localStorage that never produced a file. Video rows may carry retention (avg_watch_s,
full_watch_pct, follows, source_split) and the report ranks by full-watch share when it
has it, because a 65-second length budget is a retention claim and views cannot confirm it.
The report opens with PEOPLE (returning vs new engagers, ICP share) above impressions,
because every prior metric measured reach and reach trains a creator to be broad. One
pre-registered question per week (the week file's `experiment` block) gets answered at
n=4 per arm instead of six passive dimensions that never clear it. And the loop closes:
--weights-out writes what the data says so the selector can read it.
"""

import argparse
import contextlib
import glob
import io
import json
import os
import re
import sys
from collections import defaultdict
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yapcut_home import radar_home  # noqa: E402

RADAR = str(radar_home())      # consumes --dir; exits 2 with the places looked when none found
PERFDIR = os.path.join(RADAR, "performance")
PERF = os.path.join(PERFDIR, "performance.jsonl")
FOLLOWERS = os.path.join(PERFDIR, "followers.jsonl")
POSTMETA = os.path.join(PERFDIR, "post-meta.json")
TRACKING = os.path.join(PERFDIR, "tracking.jsonl")
PEOPLE = os.path.join(PERFDIR, "people.jsonl")
LEARNED = os.path.join(PERFDIR, "learned.json")
LAST_REPORT = os.path.join(PERFDIR, "last-report.md")

# Below this, a bucket average is noise. At 5 posts a week the fine-grained dimensions
# take months to clear it, so the report shows the n and refuses to rank under it rather
# than dressing up a sample of two as a finding.
MIN_N = 4

# A LinkedIn post is still accruing impressions for days. The 2026-08-11 sweep logged one
# post at 3h (137 impressions) and one at 22h (326) next to month-old posts, and read them
# as underperformers; they were simply unfinished. Anything younger than this is stored but
# never ranked, because letting it into a bucket average teaches the engine that fresh
# posts are bad posts.
MATURE_HOURS = 48

# The age a post should be measured at for its number to mean anything. Impressions are
# still climbing at 48h; by a week they have essentially settled. Rows logged earlier are
# kept but flagged by --due so they get a second reading at a comparable age.
TARGET_HOURS = 168

TRACK_EVENTS = ("filmed", "posted", "ignored")
VIDEO_DIMS = ("post_type", "intent", "hook_family", "borrows", "tam", "plug", "hook_styles",
              "script_class", "proof_kind", "platform")
LI_DIMS = ("linkedin_format", "job", "medium", "origin", "char_band", "topic_class", "hook_arch")
# Boolean features the selector scores, derived here from the week file so learned.json
# can speak the selector's language (dim name == WEIGHTS key, value "true"/"false").
FEATURE_DIMS = ("carousel_shaped", "has_verified_number", "arguable", "executable", "in_lane",
                "angle_unclaimed", "news_peg", "dead_zone_length", "no_proof")


def band(n):
    if n is None:
        return None
    if n <= 300:
        return "short (<=300)"
    if 600 <= n <= 1000:
        return "DEAD ZONE (600-1000)"
    if 1300 <= n <= 1900:
        return "reach band (1300-1900)"
    if n > 2500:
        return "over hard stop (>2500)"
    return "off band"


# --- feature extraction for LinkedIn posts ---------------------------------------------
# Two small helpers mirrored from select_linkedin.py rather than imported: importing it
# would run its module-level workspace resolution a second time with --dir already
# consumed from argv. Keep them in step with the selector.

def _enumerated_units(body):
    n = 0
    for line in (body or "").split("\n"):
        s = line.strip()
        if not s:
            continue
        if re.match(r"^\d+[\.\)]\s", s) or re.match(r"^[→↳•\-\*]\s", s) \
                or re.match(r"^[A-Z][A-Z \-/]{2,28}$", s):
            n += 1
    return n


def _has_number(text):
    return bool(re.search(
        r"\d[\d,\.]*\s*(%|bn\b|m\b|k\b|x\b|million|billion|trillion|thousand)"
        r"|[$£€]\s?\d|\b(?:EUR|USD|GBP)\s?\d", text or "", re.I))


def post_features(post, parent):
    body = post.get("body") or ""
    sources = post.get("sources") or (parent or {}).get("sources")
    peg = post.get("news_peg_days", (parent or {}).get("news_peg_days"))
    f = {
        "carousel_shaped": _enumerated_units(body) >= 3,
        "has_verified_number": bool(_has_number(body) and sources),
        "no_proof": not sources,
        "in_lane": (parent or post).get("facet") in ("gtm-distribution", "organic"),
        "news_peg": peg is not None and peg <= 7,
        "dead_zone_length": 600 <= len(body) <= 1000,
    }
    for k in ("arguable", "executable", "angle_unclaimed"):
        v = post.get(k, (parent or {}).get(k))
        if isinstance(v, bool):
            f[k] = v
    return f


def _twin_meta(week, title, tw, parent=None):
    body = tw.get("body") or ""
    return {
        "week": week, "lane": "linkedin", "title": title, "platform": "linkedin",
        "linkedin_format": tw.get("linkedin_format") or tw.get("shape") or tw.get("type"),
        "job": tw.get("job"), "hook_arch": tw.get("hook_arch"),
        "chars": len(body), "char_band": band(len(body)),
        "carousel": tw.get("carousel"), "text_hook": title,
        "_features": post_features(tw, parent),
    }


def load_items():
    items = {}
    for f in sorted(glob.glob(os.path.join(RADAR, "weeks", "*.json"))):
        if f.endswith(".gate.json") or ".bak" in f:
            continue
        try:
            d = json.load(open(f))
        except Exception:
            continue
        week = d.get("week") or os.path.basename(f).replace(".json", "")
        for lane in ("distribution", "office"):
            for it in d.get(lane, []):
                if it.get("id"):
                    proof = it.get("proof") if isinstance(it.get("proof"), dict) else {}
                    items[it["id"]] = {
                        "week": week, "lane": lane, "title": it.get("title"),
                        "post_type": it.get("post_type"), "intent": it.get("intent"),
                        "borrows": it.get("borrows"), "hook_family": it.get("hook_family"),
                        "text_hook": it.get("text_hook"),
                        "tam": it.get("tam"), "plug": it.get("plug"),
                        "hook_styles": it.get("hook_styles"),
                        "script_class": it.get("script_class"),
                        "proof_kind": proof.get("kind"),
                        "platform": it.get("platform"),
                    }
                # The LinkedIn twin is a separate post with its own outcome.
                tw = it.get("linkedin") or {}
                if tw.get("id"):
                    items[tw["id"]] = _twin_meta(week, it.get("title"), tw, it)
        for tw in d.get("linkedin", []):
            if tw.get("id"):
                items[tw["id"]] = _twin_meta(week, tw.get("title"), tw)

    # The overlay. the creator's own organic posts have no Radar id and therefore no week-file
    # metadata, so without this they log as rows of "unknown" and the report learns nothing
    # from them. It also backfills dimensions the week files never carried (medium, origin,
    # repeatable) onto Radar twins without rewriting history.
    if os.path.exists(POSTMETA):
        over = json.load(open(POSTMETA))
        for pid, meta in over.items():
            if pid.startswith("_") or not isinstance(meta, dict):
                continue
            base = items.setdefault(pid, {"lane": "linkedin", "week": meta.get("post_date_approx")})
            base.update({k: v for k, v in meta.items() if v is not None})
            if base.get("chars") is not None:
                base["char_band"] = band(base["chars"])
            base.setdefault("text_hook", base.get("title"))
    return items


def _read_jsonl(path):
    rows = []
    if os.path.exists(path):
        for line in open(path):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except ValueError:
                    continue
    return rows


def load_logged():
    """Latest measurement per id wins. The file is append-only and posts get re-measured
    once they mature, so summing every row would double-count the re-measured ones."""
    latest = {}
    order = []
    for r in _read_jsonl(PERF):
        pid = r.get("id")
        if pid not in latest:
            order.append(pid)
        prev = latest.get(pid)
        if prev is None or (r.get("measured") or "") >= (prev.get("measured") or ""):
            latest[pid] = r
    return [latest[p] for p in order]


def append(rows, path=None):
    path = path or PERF
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"logged {len(rows)} -> {path}")


def _median(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _dim_values(meta, dim):
    """A row can sit in several buckets of one dimension (hook_styles is a list) or in a
    derived feature bucket ("true"/"false")."""
    if dim in FEATURE_DIMS:
        v = (meta.get("_features") or {}).get(dim)
        return [] if v is None else [str(bool(v)).lower()]
    v = meta.get(dim)
    if v is None:
        return ["unknown"]
    if isinstance(v, (list, tuple)):
        return [str(x) for x in v] or ["unknown"]
    return [str(v)]


def _by_dim(rows, items, dims, metric, label):
    """Rank each dimension by MEDIAN metric, never below MIN_N. Median, not mean: the
    2026-08-11 sweep held one post at 41,652 impressions against a median of 625, so any
    bucket containing it ranked first on the mean regardless of what else was in it. Mean
    is still printed, because a big gap between the two is itself the signal that a bucket
    is one lucky post."""
    dec = 2 if metric in ("_er", "full_watch_pct") else 0
    for dim in dims:
        buckets = defaultdict(list)
        for r in rows:
            if r.get(metric) is None:
                continue
            for v in _dim_values(items.get(r["id"], {}), dim):
                buckets[v].append(r[metric])
        ranked = sorted(buckets.items(), key=lambda kv: -_median(kv[1]))
        ready = [(k, v) for k, v in ranked if len(v) >= MIN_N]
        thin = [(k, v) for k, v in ranked if len(v) < MIN_N]
        print(f"-- {label} by {dim}")
        for k, v in ready[:10]:
            mean = sum(v) / len(v)
            skew = "  <- mean is one post, not a pattern" if mean > 2.5 * max(_median(v), 1e-9) else ""
            print(f"   {_median(v):>9,.{dec}f} med  {mean:>9,.{dec}f} avg  "
                  f"n={len(v):<3} {str(k)[:40]}{skew}")
        if thin:
            names = ", ".join(f"{str(k)[:22]}(n={len(v)})" for k, v in thin[:6])
            print(f"   below n={MIN_N}, not ranked: {names}")
        if not ready:
            print(f"   nothing has cleared n={MIN_N} yet. No weight changes from this dimension.")
        print()


def is_mature(r):
    if r.get("mature") is not None:
        return bool(r["mature"])
    h = r.get("age_hours")
    return True if h is None else h >= MATURE_HOURS


# --- people ----------------------------------------------------------------------------

def _people_key(p):
    url = (p.get("url") or "").strip().lower().rstrip("/")
    return ("url", url) if url else ("name", (p.get("name") or "").strip().casefold())


def load_people():
    """people.jsonl is append-only; the newest record per person (by url, else name) is the
    current one. Written by ingest_feed.py --people and lead-magnet-report/requests.py."""
    latest = {}
    for p in _read_jsonl(PEOPLE):
        k = _people_key(p)
        if k[1]:
            latest[k] = p
    return list(latest.values())


def relevance_line(today=None):
    """Who engaged this week, and how many of them are the ICP. Printed ABOVE reach because
    reach measures breadth and this measures whether the right people are coming back."""
    today = today or date.today()
    people = load_people()
    if not people:
        return ("relevance: no performance/people.jsonl yet. Paste this week's engagers:\n"
                "   python3 ingest_feed.py --people --kind comment_by --post <id> < names.txt")
    start = today - timedelta(days=7)
    engaged, returning, icp = [], [], 0
    for p in people:
        dates = sorted(t.get("date", "") for t in (p.get("touches") or []) if t.get("date"))
        recent = [d for d in dates if d >= start.isoformat()]
        if not recent:
            continue
        engaged.append(p)
        if p.get("icp"):
            icp += 1
        earlier = [d for d in dates if d < start.isoformat()]
        first = p.get("first_seen") or (dates[0] if dates else "")
        if earlier or (first and first < start.isoformat()):
            returning.append(p)
    if not engaged:
        return (f"relevance: {len(people)} people in the ledger, none touched in the last 7 days")
    share = round(100.0 * icp / len(engaged))
    return (f"relevance: {len(engaged)} engagers this week, {len(returning)} returning, "
            f"{len(engaged) - len(returning)} new, ICP share {share}%  "
            f"(ledger {len(people)} people)")


# --- the pre-registered question ---------------------------------------------------------

def newest_week_file():
    files = [f for f in sorted(glob.glob(os.path.join(RADAR, "weeks", "*.json")))
             if not f.endswith(".gate.json") and ".bak" not in f]
    return files[-1] if files else None


def question_block(rows):
    """One two-arm question per week, answered at n=4 per arm. Six passive dimensions will
    not clear n=4 for months; one pre-registered comparison can clear it in a fortnight."""
    wf = newest_week_file()
    if not wf:
        return ["this week's question: no week files"]
    try:
        d = json.load(open(wf))
    except Exception:
        return [f"this week's question: {os.path.basename(wf)} is not valid JSON"]
    ex = d.get("experiment")
    name = os.path.basename(wf)
    if not isinstance(ex, dict):
        return [f"this week's question: none pre-registered in {name}. Add an experiment "
                f"block {{dim, arms:{{a:[ids], b:[ids]}}, metric, question}} before the batch ships."]
    metric = ex.get("metric") or "impressions"
    latest = {r["id"]: r for r in rows}
    out = [f"this week's question ({name}): {ex.get('question', '?')}",
           f"   dim {ex.get('dim')}   metric {metric}"]
    arms = ex.get("arms") or {}
    stats = {}
    for arm in ("a", "b"):
        ids = arms.get(arm) or []
        vals = []
        for pid in ids:
            r = latest.get(pid)
            if not r or not is_mature(r):
                continue
            if metric == "_er" and r.get("impressions"):
                eng = (r.get("reactions", 0) or 0) + (r.get("comments", 0) or 0) + (r.get("reposts", 0) or 0)
                vals.append(round(100.0 * eng / r["impressions"], 2))
            elif r.get(metric) is not None:
                vals.append(r[metric])
        stats[arm] = (len(ids), vals)
        med = f"{_median(vals):,.1f}" if vals else "-"
        out.append(f"   arm {arm}: {len(ids)} post(s), {len(vals)} mature row(s), median {metric} {med}")
    na, nb = len(stats["a"][1]), len(stats["b"][1])
    if na >= 2 and nb >= 2:
        ma, mb = _median(stats["a"][1]), _median(stats["b"][1])
        lead = "a" if ma > mb else ("b" if mb > ma else "neither")
        if na >= MIN_N and nb >= MIN_N:
            out.append(f"   ANSWERED at n={MIN_N} per arm: arm {lead} leads "
                       f"({ma:,.1f} vs {mb:,.1f}). Write the block in tuning-log.md and pick next week's question.")
        else:
            out.append(f"   still open: arm {lead} leads so far ({ma:,.1f} vs {mb:,.1f}), "
                       f"needs {MIN_N} mature rows per arm (have {na} and {nb})")
    else:
        out.append(f"   still open: needs 2 mature rows per arm to compare, {MIN_N} to answer "
                   f"(have {na} and {nb})")
    return out


# --- the report ------------------------------------------------------------------------

def _report():
    rows = load_logged()
    print(relevance_line())
    print()
    for line in question_block(rows):
        print(line)
    print()
    if not rows:
        print("nothing logged yet. run: python3 log_perf.py")
        return
    items = load_items()

    vid = [r for r in rows if r.get("views") is not None or r.get("full_watch_pct") is not None]
    li = [r for r in rows if r.get("impressions") is not None]
    print(f"{len(rows)} logged: {len(vid)} video, {len(li)} LinkedIn\n")

    if vid:
        vals = [r["views"] for r in vid if r.get("views") is not None]
        if vals and len(set(vals)) == 1:
            print(f"WARNING: all {len(vals)} video rows have the same value ({vals[0]:,}). "
                  f"Zero variance means zero signal, so nothing below can be learned from. "
                  f"This is a placeholder dataset, not a measurement.\n")
        retained = [r for r in vid if r.get("full_watch_pct") is not None]
        if retained:
            # Retention outranks reach for a talking-head lane: the length budget and the
            # hook gates are retention claims, and views cannot confirm them.
            print(f"-- video by FULL-WATCH share ({len(retained)} rows carry it; views shown as reach)")
            for r in sorted(retained, key=lambda r: -r["full_watch_pct"])[:12]:
                meta = items.get(r["id"], {})
                aw = f"{r['avg_watch_s']:.1f}s" if r.get("avg_watch_s") is not None else "   -"
                print(f"   {r['full_watch_pct']:>5.1f}% full  {aw:>6} avg  {r.get('views') or 0:>8,} views  "
                      f"{r.get('follows') or 0:>4} follows  {r['id']}  "
                      f"{str(meta.get('text_hook') or meta.get('title') or '')[:36]}")
            print()
            _by_dim(retained, items, VIDEO_DIMS, "full_watch_pct", "video full-watch %")
        else:
            print("-- no retention on any video row yet. Paste TikTok Studio's content table:\n"
                  "   python3 ingest_feed.py --tiktok < studio.txt   (avg watch, watched full %, follows)\n")
        if vals:
            _by_dim([r for r in vid if r.get("views") is not None], items, VIDEO_DIMS, "views", "video views")
            med = sorted(vals)[len(vals) // 2]
            print(f"video median {med:,}  best {max(vals):,}")
            print("outliers (3x median), autopsy these and brief 3-4 variations:")
            hits = [r for r in sorted(vid, key=lambda r: -(r.get("views") or 0))
                    if (r.get("views") or 0) >= 3 * med]
            for r in hits:
                meta = items.get(r["id"], {})
                print(f"   {r['views']:>9,}  {r['id']}  {meta.get('text_hook') or meta.get('title')}")
            if not hits:
                print("   none.")
            print()

    if li:
        for r in li:
            eng = (r.get("reactions", 0) or 0) + (r.get("comments", 0) or 0) + (r.get("reposts", 0) or 0)
            r["_er"] = round(100.0 * eng / r["impressions"], 2) if r["impressions"] else 0.0

        green, immature = [r for r in li if is_mature(r)], [r for r in li if not is_mature(r)]
        if immature:
            print(f"-- held out as immature (<{MATURE_HOURS}h, still accruing; stored, not ranked)")
            for r in sorted(immature, key=lambda r: r.get("age_hours") or 0):
                meta = items.get(r["id"], {})
                print(f"   {r['impressions']:>9,}  {r.get('age_reported') or '?':>4}  "
                      f"{r['id']}  {str(meta.get('title') or '')[:44]}")
            print()

        # An unrepeatable post is history, not a lever. Two of the three top performers in
        # the 2026-08-11 sweep were one-off life events (a new job, a first sale); rank them
        # alongside formats and the engine "learns" to post more job announcements.
        rankable = [r for r in green if items.get(r["id"], {}).get("repeatable") is not False]
        dropped = len(green) - len(rankable)
        if dropped:
            print(f"-- {dropped} mature post(s) excluded from format ranking as unrepeatable "
                  f"one-off events (see post-meta.json)\n")

        # `carousel` is gone: the week files never set it, and `medium` (text/video/doc/
        # reshare) now carries the same information without a column of "unknown".
        _by_dim(rankable, items, LI_DIMS, "impressions", "LinkedIn impressions [mature+repeatable]")
        _by_dim(rankable, items, LI_DIMS, "_er", "LinkedIn engagement rate % [mature+repeatable]")

        vals = sorted(r["impressions"] for r in green)
        ers = sorted(r["_er"] for r in green)
        med = vals[len(vals) // 2]
        med_er = ers[len(ers) // 2]
        print(f"LinkedIn (mature, n={len(green)}) median impressions {med:,}  best {max(vals):,}")
        print(f"LinkedIn (mature, n={len(green)}) median ER {med_er}%  best {max(ers)}%")
        print("   Median, not mean: one outlier can carry a month. Check an ER claim against\n"
              "   this median before calling a post a standout.\n")
        print("outliers (3x median impressions), autopsy these:")
        for r in sorted(green, key=lambda r: -r["impressions"]):
            if r["impressions"] < 3 * med:
                continue
            meta = items.get(r["id"], {})
            flag = "" if meta.get("repeatable") is not False else "   [UNREPEATABLE EVENT]"
            print(f"   {r['impressions']:>9,}  ER {r['_er']:>5}%  {r['id']}  "
                  f"{str(meta.get('title') or meta.get('text_hook') or '')[:40]}{flag}")
        print()
    else:
        print("no LinkedIn rows yet. The twins ship weekly and are the ICP surface, so this\n"
              "is the gap that matters most: run  python3 log_perf.py --linkedin\n")

    if os.path.exists(FOLLOWERS):
        fr = _read_jsonl(FOLLOWERS)
        print("-- follower growth (the north star, ICP-weighted)")
        for r in fr[-8:]:
            share = r.get("icp_share_pct")
            icp = f"{share}% ICP" if share is not None else "ICP share not logged"
            qual = f"  ~{round(r['delta'] * share / 100)} ICP followers" if share is not None else ""
            print(f"   {r['week']}  {r['delta']:+d} followers   {icp}{qual}")
        print("\n   Raw delta is the vanity number. ICP-weighted delta is the one that\n"
              "   feeds the funnel: 200 followers at 20% growth-leader beats 500 at 2%.\n")
    else:
        print("no follower history. run: python3 log_perf.py --followers <week> <delta> [icp_pct]\n")

    tr = _read_jsonl(TRACKING)
    if tr:
        c = defaultdict(int)
        for e in tr:
            c[e.get("event")] += 1
        print(f"tracking: {c['filmed']} filmed, {c['posted']} posted, {c['ignored']} ignored events "
              f"({len({e.get('id') for e in tr})} ids) in performance/tracking.jsonl")
    else:
        print("tracking: no performance/tracking.jsonl yet. Mark work as it happens:\n"
              "   python3 log_perf.py --filmed <id>   --posted <id> <url>   --import <export.json>")


def report():
    """Print the report and write it to performance/last-report.md as well (Contract 5)."""
    buf = io.StringIO()

    class Tee(io.TextIOBase):
        def write(self, s):
            buf.write(s)
            return sys.__stdout__.write(s)

        def flush(self):
            sys.__stdout__.flush()

    with contextlib.redirect_stdout(Tee()):
        _report()
    os.makedirs(PERFDIR, exist_ok=True)
    with open(LAST_REPORT, "w", encoding="utf-8") as fh:
        fh.write(f"# Performance report, {datetime.now().isoformat(timespec='minutes')}\n\n")
        fh.write("Written by `python3 log_perf.py --report`. Regenerated on every run.\n\n```\n")
        fh.write(buf.getvalue())
        fh.write("```\n")
    print(f"\nwrote {LAST_REPORT}")


# --- learned weights -----------------------------------------------------------------------

def weights_out():
    """performance/learned.json: {dim: {value: {ratio, n}}} for every value past MIN_N.
    ratio = median metric for that value / mature median across the dimension's population.
    The selector multiplies a matching WEIGHTS entry by the "true" ratio, so a feature that
    measurably helps gets heavier and one that measurably hurts gets lighter. Nothing under
    MIN_N is written, because a ratio from two posts is a coin flip with a decimal point."""
    rows = load_logged()
    items = load_items()
    dims = {}
    pops = {}

    li = [r for r in rows if r.get("impressions") is not None and is_mature(r)
          and items.get(r["id"], {}).get("repeatable") is not False]
    if li:
        base = _median([r["impressions"] for r in li])
        pops["linkedin"] = {"metric": "impressions", "n": len(li), "median": base}
        for dim in LI_DIMS + FEATURE_DIMS:
            buckets = defaultdict(list)
            for r in li:
                for v in _dim_values(items.get(r["id"], {}), dim):
                    if v != "unknown":
                        buckets[v].append(r["impressions"])
            ready = {k: {"ratio": round(_median(v) / base, 3) if base else 1.0, "n": len(v)}
                     for k, v in buckets.items() if len(v) >= MIN_N}
            if ready:
                dims[dim] = ready

    vid = [r for r in rows if r.get("views") is not None or r.get("full_watch_pct") is not None]
    ret = [r for r in vid if r.get("full_watch_pct") is not None]
    metric = "full_watch_pct" if len(ret) >= MIN_N else "views"
    pool = [r for r in vid if r.get(metric) is not None]
    if pool:
        vals = [r[metric] for r in pool]
        base = _median(vals)
        pops["video"] = {"metric": metric, "n": len(pool), "median": base,
                         "zero_variance": len(set(vals)) == 1}
        if len(set(vals)) > 1:
            for dim in VIDEO_DIMS:
                buckets = defaultdict(list)
                for r in pool:
                    for v in _dim_values(items.get(r["id"], {}), dim):
                        if v != "unknown":
                            buckets[v].append(r[metric])
                ready = {k: {"ratio": round(_median(v) / base, 3) if base else 1.0, "n": len(v)}
                         for k, v in buckets.items() if len(v) >= MIN_N}
                if ready:
                    dims.setdefault(dim, {}).update(ready)

    out = {"generated": datetime.now().isoformat(timespec="seconds"),
           "source": "log_perf --weights-out", "min_n": MIN_N,
           "populations": pops, "dims": dims}
    os.makedirs(PERFDIR, exist_ok=True)
    with open(LEARNED, "w") as fh:
        json.dump(out, fh, indent=2)
        fh.write("\n")
    print(f"wrote {LEARNED}: {len(dims)} dimension(s) with a value past n={MIN_N}")
    for dim, vals in dims.items():
        for k, v in sorted(vals.items(), key=lambda kv: -kv[1]["ratio"]):
            print(f"   {dim:<22} {k:<28} ratio {v['ratio']:>6.3f}  n={v['n']}")
    if not dims:
        print("   nothing has cleared n=4 in any dimension. The selector keeps its priors.")
    if pops.get("video", {}).get("zero_variance"):
        print("   video rows have zero variance (placeholder values); no video dimension written.")


# --- tracking ----------------------------------------------------------------------------

def track(event, pid, at=None, link=None, notes=None, platform=None, quiet=False):
    if event not in TRACK_EVENTS:
        raise ValueError(f"event must be one of {TRACK_EVENTS}")
    row = {"id": pid, "event": event, "at": at or date.today().isoformat()}
    if link:
        row["link"] = link
    if notes:
        row["notes"] = notes
    if platform:
        row["platform"] = platform
    for e in _read_jsonl(TRACKING):
        if e.get("id") == pid and e.get("event") == event and e.get("link") == row.get("link") \
                and e.get("at") == row["at"]:
            if not quiet:
                print(f"already tracked: {pid} {event} {row['at']}")
            return False
    os.makedirs(PERFDIR, exist_ok=True)
    with open(TRACKING, "a") as fh:
        fh.write(json.dumps(row) + "\n")
    if not quiet:
        print(f"tracked {event}: {pid}" + (f"  {link}" if link else "") + f" -> {TRACKING}")
    return True


def import_export(path):
    """The dashboard's Export > Performance file, and the older shapes.

    build_dashboard.py writes {exported_at, source: "dashboard", weeks: [{week, items:
    [{id, title, lane, mechanic, facet, intent, value, qa, status, views, link, notes}]}]}.
    `source` and the dimension columns are ignored on purpose: the week files own the
    dimensions and load_items() reads them there. Also accepted: the raw `track` object
    ({id: {status, views, link, notes}}), that object under a `track`/`tracking` key, or a
    top-level `items` list. Filmed/posted/ignored become tracking events. A numeric `views`
    becomes a performance row dated by exported_at: `views` for a video lane, `impressions`
    for lane "linkedin", because that is what the dashboard's one number means on a post and
    the report splits video from LinkedIn on exactly that key."""
    data = json.load(open(path))
    recs = {}
    if isinstance(data, dict):
        inner = data.get("track") or data.get("tracking")
        if isinstance(inner, dict):
            recs = inner
        elif isinstance(data.get("weeks"), list):
            for wk in data["weeks"]:
                for it in (wk.get("items") if isinstance(wk, dict) else None) or []:
                    if isinstance(it, dict) and it.get("id"):
                        recs[it["id"]] = it
        elif isinstance(data.get("items"), list):
            for it in data["items"]:
                if isinstance(it, dict) and it.get("id"):
                    recs[it["id"]] = it.get("track") if isinstance(it.get("track"), dict) else it
        else:
            recs = {k: v for k, v in data.items() if isinstance(v, dict) and not k.startswith("_")}
    exported = data.get("exported_at", "")[:10] if isinstance(data, dict) else ""
    at = exported if re.match(r"^\d{4}-\d{2}-\d{2}$", exported or "") else date.today().isoformat()
    n_ev = n_rows = 0
    perf_rows = []
    n_li = 0
    for pid, rec in recs.items():
        if not isinstance(rec, dict):
            continue
        status = (rec.get("status") or "").strip().lower()
        link = (rec.get("link") or rec.get("url") or "").strip() or None
        notes = (rec.get("notes") or "").strip() or None
        lane = (rec.get("lane") or "").strip().lower()
        platform = rec.get("platform") or ("linkedin" if lane == "linkedin" else None)
        if status in TRACK_EVENTS:
            if status == "posted" and track("filmed", pid, at=at, notes=None, quiet=True):
                n_ev += 1
            if track(status, pid, at=at, link=link, notes=notes, platform=platform, quiet=True):
                n_ev += 1
        views = rec.get("views")
        if isinstance(views, str):
            views = re.sub(r"[^\d]", "", views)
        if views not in (None, "", False):
            try:
                metric = "impressions" if lane == "linkedin" else "views"
                row = {"id": pid, metric: int(views), "measured": at, "note": "dashboard export"}
                if platform:
                    row["platform"] = platform
                perf_rows.append(row)
                n_li += metric == "impressions"
            except (TypeError, ValueError):
                pass
    if perf_rows:
        have = {(r["id"], r.get("views"), r.get("impressions")) for r in _read_jsonl(PERF)}
        fresh = [r for r in perf_rows
                 if (r["id"], r.get("views"), r.get("impressions")) not in have]
        if fresh:
            append(fresh)
        n_rows = len(fresh)
    print(f"imported {len(recs)} record(s) from {os.path.basename(path)}: "
          f"{n_ev} new tracking event(s), {n_rows} new performance row(s)"
          + (f" ({n_li} LinkedIn, logged as impressions)" if n_li else ""))


def merge_edits(output_dir):
    """Contract 6: finalize.sh writes <name>.edit.json beside every finished cut. Merge the
    fields that join an edit to an outcome into post-meta.json by radar_id."""
    files = sorted(glob.glob(os.path.join(output_dir, "**", "*.edit.json"), recursive=True))
    if not files:
        print(f"no *.edit.json under {output_dir}")
        return 1
    meta = json.load(open(POSTMETA)) if os.path.exists(POSTMETA) else {}
    merged = skipped = 0
    for f in files:
        try:
            e = json.load(open(f))
        except Exception:
            skipped += 1
            continue
        rid = e.get("radar_id")
        if not rid or rid == "standalone":
            skipped += 1
            continue
        hook = e.get("hook") if isinstance(e.get("hook"), dict) else {}
        patch = {
            "hook_words": hook.get("words") if hook.get("words") is not None
            else (len(str(hook.get("text", "")).split()) if hook.get("text") else None),
            "duration_s": e.get("duration_s"),
            "receipts_n": len(e.get("accept_files") or []),
            "platform": e.get("platform"),
            "edit_name": e.get("name"),
            "edit_final": e.get("final"),
        }
        base = meta.setdefault(rid, {})
        if not isinstance(base, dict):
            skipped += 1
            continue
        base.update({k: v for k, v in patch.items() if v is not None})
        merged += 1
    os.makedirs(PERFDIR, exist_ok=True)
    with open(POSTMETA, "w") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print(f"merged {merged} edit record(s) into {POSTMETA}"
          + (f", skipped {skipped} (standalone or unreadable)" if skipped else ""))
    return 0


# --- the interactive paths -----------------------------------------------------------------

def log_linkedin():
    items = load_items()
    logged = {r["id"] for r in load_logged() if r.get("impressions") is not None}
    pending = sorted(i for i, m in items.items()
                     if m.get("lane") == "linkedin" and i not in logged)
    if not pending:
        print("no unlogged LinkedIn twins found.")
        return
    print("LinkedIn twin numbers. Blank impressions to skip an item, Ctrl-C to stop.")
    print("(Impressions and reactions/comments/reposts are on the post's analytics view.\n"
          " Saves and dwell are not exposed to authors, so they cannot be logged.)\n")
    rows = []
    for i in pending[-15:]:
        m = items[i]
        try:
            imp = input(f"{i}  {str(m.get('title'))[:58]}\n  impressions: ").strip()
            if not imp:
                continue
            rea = input("  reactions: ").strip()
            com = input("  comments: ").strip()
            rep = input("  reposts: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        def num(s):
            n = re.sub(r"[^\d]", "", s or "")
            return int(n) if n else 0
        rows.append({"id": i, "impressions": num(imp), "reactions": num(rea),
                     "comments": num(com), "reposts": num(rep),
                     "measured": date.today().isoformat(), "platform": "linkedin"})
    if rows:
        append(rows)
    else:
        print("nothing logged")


def due():
    """What to re-measure, and why this exists. The 2026-08-11 intake caught two posts at 3h
    and 22h, because the sweep ran whenever rather than at a fixed post age. A post measured
    at 3h and one measured at 4 weeks are not comparable numbers, so the store has to track
    which rows were taken too early and surface them once the post has actually settled.
    Comparable beats frequent: one measurement per post at ~7 days is worth more than three
    at random ages."""
    rows = [r for r in load_logged() if r.get("impressions") is not None]
    items = load_items()
    today = date.today()
    pending = []
    for r in rows:
        h, m = r.get("age_hours"), r.get("measured")
        if h is None or not m:
            continue
        if h >= TARGET_HOURS:
            continue                       # already measured at or past the target age
        posted = datetime.strptime(m, "%Y-%m-%d").date() - timedelta(hours=h)
        now_h = (today - posted).days * 24
        if now_h >= TARGET_HOURS:
            pending.append((r, posted, now_h))
    if not pending:
        print(f"nothing due. Every post is either measured at >= {TARGET_HOURS}h "
              f"({TARGET_HOURS // 24}d) or has not reached it yet.")
        return
    print(f"DUE FOR RE-MEASURE ({len(pending)}). Logged before {TARGET_HOURS // 24}d and now "
          f"past it, so the stored number understates them:\n")
    for r, posted, now_h in sorted(pending, key=lambda p: -p[2]):
        meta = items.get(r["id"], {})
        print(f"  {r['id']:<22} logged {r['impressions']:>7,} at {r.get('age_reported'):<4} "
              f"| posted ~{posted} | now ~{now_h // 24}d")
        print(f"     {str(meta.get('title') or meta.get('text_hook') or '')[:66]}")
    print("\nPull these from the feed and hand them over; the ingest will append a fresh\n"
          "dated measurement and log_perf keeps the latest per id.")


def log_followers(args):
    """--followers <week> <delta> [icp_pct] writes without prompting; with no arguments the
    three questions are asked, as before."""
    if args:
        week = args[0]
        delta = args[1] if len(args) > 1 else ""
        share = args[2] if len(args) > 2 else ""
    else:
        try:
            week = input("week (YYYY-MM-DD): ").strip()
            delta = input("net new followers this week: ").strip()
            share = input("ICP share of new followers %, from LinkedIn's follower demographics\n"
                          "  (blank if not checked): ").strip()
        except (EOFError, KeyboardInterrupt):
            return 1
    d = re.sub(r"[^\d\-]", "", delta or "")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", week or "") or not d:
        print("need a week (YYYY-MM-DD) and a delta: --followers 2026-09-07 42 [35]")
        return 2
    row = {"week": week, "delta": int(d)}
    s = re.sub(r"[^\d\.]", "", share or "")
    if s:
        row["icp_share_pct"] = float(s)
    os.makedirs(PERFDIR, exist_ok=True)
    with open(FOLLOWERS, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"logged -> {FOLLOWERS}: {row}")
    return 0


def log_views_interactive(paste):
    items = load_items()
    logged = {r["id"] for r in load_logged()}
    # The default flow is the video lane; twins have their own mode with their own metrics.
    pending = [i for i, m in items.items()
               if i not in logged and m.get("lane") != "linkedin"]
    pending.sort()

    if paste:
        print("paste lines: '<id> <views>' or just '<views>' in the order shown. Ctrl-D to end.")
        for i in pending[-20:]:
            print(f"  {i}  {items[i].get('text_hook')}")
        print("---")
        rows = []
        order = pending[-20:]
        n = 0
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            m = re.match(r"^(\S+)\s+([\d,]+)$", line)
            if m and m.group(1) in items:
                rows.append({"id": m.group(1), "views": int(m.group(2).replace(",", "")),
                             "measured": date.today().isoformat()})
            else:
                num = re.sub(r"[^\d]", "", line)
                if num and n < len(order):
                    rows.append({"id": order[n], "views": int(num),
                                 "measured": date.today().isoformat()})
                    n += 1
        append(rows)
        return

    print("Views for what you posted. Blank line to skip an item, Ctrl-C to stop.\n")
    rows = []
    for i in pending[-15:]:
        hook = items[i].get("text_hook") or items[i].get("title") or ""
        try:
            v = input(f"{i}  {hook[:60]}\n  views: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not v:
            continue
        num = re.sub(r"[^\d]", "", v)
        if num:
            rows.append({"id": i, "views": int(num), "measured": date.today().isoformat()})
    if rows:
        append(rows)
    else:
        print("nothing logged")


def main():
    ap = argparse.ArgumentParser(description="the performance loop; see the module docstring")
    ap.add_argument("--dir", help="workspace (consumed by yapcut_home when given)")
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--linkedin", action="store_true")
    ap.add_argument("--due", action="store_true")
    ap.add_argument("--paste", action="store_true")
    ap.add_argument("--followers", nargs="*", metavar="ARG",
                    help="<week> <delta> [icp_pct]; interactive when given no values")
    ap.add_argument("--filmed", metavar="ID")
    ap.add_argument("--posted", nargs=2, metavar=("ID", "URL"))
    ap.add_argument("--ignore", metavar="ID")
    ap.add_argument("--at", metavar="YYYY-MM-DD", help="date for --filmed/--posted/--ignore")
    ap.add_argument("--notes", default=None)
    ap.add_argument("--platform", default=None, help="tiktok | reels | shorts | linkedin | youtube")
    ap.add_argument("--import", dest="import_path", metavar="EXPORT.json")
    ap.add_argument("--weights-out", action="store_true")
    ap.add_argument("--edits", metavar="OUTPUT_DIR")
    a = ap.parse_args()

    if a.at and not re.match(r"^\d{4}-\d{2}-\d{2}$", a.at):
        print("--at wants YYYY-MM-DD")
        return 2

    items = None
    if a.filmed or a.posted or a.ignore:
        items = load_items()
        for pid in [a.filmed, a.ignore] + ([a.posted[0]] if a.posted else []):
            if pid and pid not in items and not pid.startswith("x-"):
                print(f"warning: {pid} is not an id in any week file (organic posts use x-<date>-<n>)")
    if a.filmed:
        track("filmed", a.filmed, at=a.at, notes=a.notes, platform=a.platform)
    if a.posted:
        track("filmed", a.posted[0], at=a.at, quiet=True)
        track("posted", a.posted[0], at=a.at, link=a.posted[1], notes=a.notes, platform=a.platform)
    if a.ignore:
        track("ignored", a.ignore, at=a.at, notes=a.notes)
    if a.import_path:
        import_export(a.import_path)
    if a.edits:
        return merge_edits(a.edits)
    if a.weights_out:
        weights_out()
    if a.followers is not None:
        return log_followers(a.followers)
    if a.report:
        report()
        return 0
    if a.linkedin:
        log_linkedin()
        return 0
    if a.due:
        due()
        return 0
    if a.filmed or a.posted or a.ignore or a.import_path or a.weights_out:
        return 0
    log_views_interactive(a.paste)
    return 0


if __name__ == "__main__":
    sys.exit(main())

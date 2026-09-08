#!/usr/bin/env python3
"""
The feedback loop. Ten weeks and 175 scripts ran with performance/ empty, because
logging was event-driven and optional. It is now neither.

Designed to take under a minute. Paste numbers, done.

Usage:
  python3 log_perf.py                    interactive: lists unlogged posted items, asks for views
  python3 log_perf.py --paste            paste "id views" lines (or just views, in order), Ctrl-D
  python3 log_perf.py --linkedin         log the LinkedIn twins: impressions, reactions, comments
  python3 log_perf.py --followers        log the week's follower delta and its ICP share
  python3 log_perf.py --due              what to re-measure: logged too early, now settled
  python3 log_perf.py --report           what is working, by mechanic / post_type / intent

The LinkedIn lane was invisible to this script until 2026-08-10: load_items() read only
`distribution` and `office`, so the twins that constitution rule 2 ships unconditionally
every week were the one thing never measured. They are in scope now, and they carry their
own dimensions (linkedin_format, job, character band) because the feed rewards different
things than the FYP does.
"""

import glob
import json
import os
import re
import sys
from collections import defaultdict
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
FOLLOWERS = os.path.join(RADAR, "performance", "followers.jsonl")
POSTMETA = os.path.join(RADAR, "performance", "post-meta.json")

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


def load_items():
    items = {}
    for f in sorted(glob.glob(os.path.join(RADAR, "weeks", "*.json"))):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        week = d.get("week") or os.path.basename(f).replace(".json", "")
        for lane in ("distribution", "office"):
            for it in d.get(lane, []):
                if it.get("id"):
                    items[it["id"]] = {
                        "week": week, "lane": lane, "title": it.get("title"),
                        "post_type": it.get("post_type"), "intent": it.get("intent"),
                        "borrows": it.get("borrows"), "hook_family": it.get("hook_family"),
                        "text_hook": it.get("text_hook"),
                    }
                # The LinkedIn twin is a separate post with its own outcome.
                tw = it.get("linkedin") or {}
                if tw.get("id"):
                    body = tw.get("body") or ""
                    items[tw["id"]] = {
                        "week": week, "lane": "linkedin", "title": it.get("title"),
                        "linkedin_format": tw.get("linkedin_format") or tw.get("type"),
                        "job": tw.get("job"), "hook_arch": tw.get("hook_arch"),
                        "chars": len(body), "char_band": band(len(body)),
                        "carousel": tw.get("carousel"), "text_hook": it.get("title"),
                    }
        for tw in d.get("linkedin", []):
            if tw.get("id"):
                body = tw.get("body") or ""
                items[tw["id"]] = {
                    "week": week, "lane": "linkedin", "title": tw.get("title"),
                    "linkedin_format": tw.get("linkedin_format") or tw.get("type"),
                    "job": tw.get("job"), "hook_arch": tw.get("hook_arch"),
                    "chars": len(body), "char_band": band(len(body)),
                    "carousel": tw.get("carousel"), "text_hook": tw.get("title"),
                }

    # The overlay. Alex's own organic posts have no Radar id and therefore no week-file
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


def load_logged():
    """Latest measurement per id wins. The file is append-only and posts get re-measured
    once they mature, so summing every row would double-count the re-measured ones."""
    latest = {}
    order = []
    if os.path.exists(PERF):
        for line in open(PERF):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            pid = r.get("id")
            if pid not in latest:
                order.append(pid)
            prev = latest.get(pid)
            if prev is None or (r.get("measured") or "") >= (prev.get("measured") or ""):
                latest[pid] = r
    return [latest[p] for p in order]


def append(rows):
    os.makedirs(os.path.dirname(PERF), exist_ok=True)
    with open(PERF, "a") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    print(f"logged {len(rows)} -> {PERF}")


def _median(v):
    s = sorted(v)
    n = len(s)
    return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2.0


def _by_dim(rows, items, dims, metric, label):
    """Rank each dimension by MEDIAN metric, never below MIN_N. Median, not mean: the
    2026-08-11 sweep held one post at 41,652 impressions against a median of 625, so any
    bucket containing it ranked first on the mean regardless of what else was in it. Mean
    is still printed, because a big gap between the two is itself the signal that a bucket
    is one lucky post."""
    dec = 2 if metric == "_er" else 0
    for dim in dims:
        buckets = defaultdict(list)
        for r in rows:
            meta = items.get(r["id"], {})
            buckets[meta.get(dim) or "unknown"].append(r[metric])
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


def report():
    rows = load_logged()
    if not rows:
        print("nothing logged yet. run: python3 log_perf.py")
        return
    items = load_items()

    vid = [r for r in rows if r.get("views") is not None]
    li = [r for r in rows if r.get("impressions") is not None]
    print(f"{len(rows)} logged: {len(vid)} video, {len(li)} LinkedIn\n")

    if vid:
        vals = [r["views"] for r in vid]
        if len(set(vals)) == 1:
            print(f"WARNING: all {len(vals)} video rows have the same value ({vals[0]:,}). "
                  f"Zero variance means zero signal, so nothing below can be learned from. "
                  f"This is a placeholder dataset, not a measurement.\n")
        _by_dim(vid, items, ("post_type", "intent", "hook_family", "borrows"), "views", "video")
        med = sorted(vals)[len(vals) // 2]
        print(f"video median {med:,}  best {max(vals):,}")
        print("outliers (3x median), autopsy these and brief 3-4 variations:")
        hits = [r for r in sorted(vid, key=lambda r: -r["views"]) if r["views"] >= 3 * med]
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

        def is_mature(r):
            if r.get("mature") is not None:
                return bool(r["mature"])
            h = r.get("age_hours")
            return True if h is None else h >= MATURE_HOURS

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
        dims = ("linkedin_format", "job", "medium", "origin", "char_band", "topic_class")
        _by_dim(rankable, items, dims, "impressions", "LinkedIn impressions [mature+repeatable]")
        _by_dim(rankable, items, dims, "_er", "LinkedIn engagement rate % [mature+repeatable]")

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
        fr = [json.loads(l) for l in open(FOLLOWERS) if l.strip()]
        print("-- follower growth (the north star, ICP-weighted)")
        for r in fr[-8:]:
            share = r.get("icp_share_pct")
            icp = f"{share}% ICP" if share is not None else "ICP share not logged"
            qual = f"  ~{round(r['delta'] * share / 100)} ICP followers" if share is not None else ""
            print(f"   {r['week']}  {r['delta']:+d} followers   {icp}{qual}")
        print("\n   Raw delta is the vanity number. ICP-weighted delta is the one that\n"
              "   feeds the funnel: 200 followers at 20% growth-leader beats 500 at 2%.\n")
    else:
        print("no follower history. run: python3 log_perf.py --followers\n")


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
                     "comments": num(com), "reposts": num(rep)})
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


def log_followers():
    try:
        week = input("week (YYYY-MM-DD): ").strip()
        delta = input("net new followers this week: ").strip()
        share = input("ICP share of new followers %, from LinkedIn's follower demographics\n"
                      "  (growth / marketing / GTM leaders; blank if not checked): ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    d = re.sub(r"[^\d\-]", "", delta or "")
    if not week or not d:
        print("need a week and a delta")
        return
    row = {"week": week, "delta": int(d)}
    s = re.sub(r"[^\d\.]", "", share or "")
    if s:
        row["icp_share_pct"] = float(s)
    os.makedirs(os.path.dirname(FOLLOWERS), exist_ok=True)
    with open(FOLLOWERS, "a") as f:
        f.write(json.dumps(row) + "\n")
    print(f"logged -> {FOLLOWERS}")


def main():
    if "--report" in sys.argv:
        report()
        return
    if "--linkedin" in sys.argv:
        log_linkedin()
        return
    if "--due" in sys.argv:
        due()
        return
    if "--followers" in sys.argv:
        log_followers()
        return

    items = load_items()
    logged = {r["id"] for r in load_logged()}
    # The default flow is the video lane; twins have their own mode with their own metrics.
    pending = [i for i, m in items.items()
               if i not in logged and m.get("lane") != "linkedin"]
    pending.sort()

    if "--paste" in sys.argv:
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
                rows.append({"id": m.group(1), "views": int(m.group(2).replace(",", ""))})
            else:
                num = re.sub(r"[^\d]", "", line)
                if num and n < len(order):
                    rows.append({"id": order[n], "views": int(num)})
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
            rows.append({"id": i, "views": int(num)})
    if rows:
        append(rows)
    else:
        print("nothing logged")


if __name__ == "__main__":
    main()

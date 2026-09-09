#!/usr/bin/env python3
"""requests.py: the comment-gate request ledger for the lead magnet.

WHY. The gate earns a comment from a self-identified buyer who names a category, and the
promise is a DM the same day. Without a ledger "same day" is unenforceable, and the audit of
2026-09-09 found exactly that (Q1 item 26): references/distribution.md said let the comments
choose the queue, no file recorded a commenter or a DM, and issue 03's category came from the
sector plan because no intake existed.

WHAT IT WRITES. Two append-only files in the workspace, never rewritten:
  issues/<slug>/requests.jsonl    one event per line:
                                  {event: request | dm_sent, issue, commenter, url, category,
                                   post, at}
  performance/people.jsonl        the shared people ledger (Contract 5): the commenter is
                                  upserted with a touch of kind `request` on add and `dm_sent`
                                  on dm-sent, so the same person shows up in log_perf.py's
                                  relevance line next to everyone who commented on a post.

THE QUEUE is the requests file read in order: each category asked for is a future issue.

Usage:
  python3 requests.py add --issue <slug> --commenter "<name>" --category "<what they asked for>"
                          [--url <profile>] [--post <post id or url>] [--at YYYY-MM-DD] [--dir <ws>]
  python3 requests.py dm-sent --issue <slug> --commenter "<name>" [--url <profile>] [--at ...]
  python3 requests.py list [--issue <slug>]                every request with its DM state
  python3 requests.py --due [--issue <slug>] [--hours 24]  requests past the deadline with no DM
  python3 requests.py queue                                categories asked for, in order, unbuilt

The DM itself is three lines, by hand, never automated (references/distribution.md):
  Here is the sheet you asked for: [link or attachment].
  The one line I would look at first for [their category]: [one finding from the report].
  If you want the version for your own category, say which one and it goes in the queue.

Exit codes (Contract 1): 0 ok, 1 when --due finds overdue requests (a to-do, not a defect),
2 on a usage error or when no workspace can be found.
"""
import argparse
import datetime
import json
import os
import re
import sys

# The resolver lives in the sibling skill. realpath locates THIS file through any symlink,
# then ../outlier-radar is the Radar skill inside the same plugin: never used to locate the
# workspace itself (see yapcut_home.py for why).
HERE = os.path.dirname(os.path.realpath(__file__))
RADAR_SKILL = os.path.normpath(os.path.join(HERE, "..", "outlier-radar"))
if not os.path.exists(os.path.join(RADAR_SKILL, "yapcut_home.py")):
    sys.stderr.write(f"yapcut_home.py not found at {RADAR_SKILL}. lead-magnet-report ships beside "
                     "outlier-radar in the same plugin; do not copy this skill out on its own.\n")
    sys.exit(2)
sys.path.insert(0, RADAR_SKILL)
from yapcut_home import radar_home  # noqa: E402

HOME = radar_home()          # consumes --dir; exits 2 with the places looked when none found
PEOPLE = HOME / "performance" / "people.jsonl"
CONFIG = HOME / "radar-config.json"
DEFAULT_ICP = r"growth|marketing|gtm|cmo|revenue|demand"
EVENTS = ("request", "dm_sent")


def today():
    return datetime.date.today().isoformat()


def _read_jsonl(path):
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                continue
    return rows


def _append(path, row):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def slug_ok(s):
    return bool(re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", s or ""))


def requests_path(issue):
    return HOME / "issues" / issue / "requests.jsonl"


def issues():
    root = HOME / "issues"
    if not root.is_dir():
        return []
    return sorted(p.name for p in root.iterdir() if (p / "requests.jsonl").exists())


def person_key(name, url):
    u = (url or "").strip().lower().rstrip("/")
    return ("url", u) if u else ("name", (name or "").strip().casefold())


def fold(issue_slugs):
    """Latest state per (issue, person): the request row plus dm_sent_at when a DM was logged."""
    state = {}
    for issue in issue_slugs:
        for r in _read_jsonl(requests_path(issue)):
            k = (issue,) + person_key(r.get("commenter"), r.get("url"))
            if r.get("event") == "request":
                cur = state.setdefault(k, dict(r))
                if cur is not r:
                    for f in ("url", "category", "post"):
                        if r.get(f) and not cur.get(f):
                            cur[f] = r[f]
                cur.setdefault("requested_at", r.get("at"))
            elif r.get("event") == "dm_sent":
                cur = state.get(k)
                if cur is None:
                    # a DM logged without a request row: record it so --due never nags for it
                    cur = state.setdefault(k, {"issue": issue, "commenter": r.get("commenter"),
                                               "url": r.get("url"), "category": None,
                                               "requested_at": None})
                cur["dm_sent_at"] = r.get("at")
    return state


# --- the people ledger (Contract 5), the same shape ingest_feed.py --people writes -----------

def icp_regex():
    try:
        cfg = json.load(open(CONFIG)) if CONFIG.exists() else {}
        return re.compile(((cfg.get("audience") or {}).get("icp_regex")) or DEFAULT_ICP, re.I)
    except (ValueError, re.error):
        return re.compile(DEFAULT_ICP, re.I)


def upsert_person(name, url, kind, post_id, at, role=None, company=None):
    """Append-only upsert: readers take the newest record per url (else name)."""
    latest = {}
    for p in _read_jsonl(PEOPLE):
        k = person_key(p.get("name"), p.get("url"))
        if k[1]:
            latest[k] = p
    k = person_key(name, url)
    cur = latest.get(k)
    if cur is None:
        for v in latest.values():
            if (v.get("name") or "").casefold() == (name or "").casefold():
                cur = v
                break
    rec = dict(cur) if cur else {"name": name, "first_seen": at, "touches": []}
    for f, v in (("url", url), ("role", role), ("company", company)):
        if v and not rec.get(f):
            rec[f] = v
    text = " ".join(str(rec.get(f) or "") for f in ("role", "company"))
    rec["icp"] = bool(icp_regex().search(text)) if text.strip() else bool(rec.get("icp"))
    rec["last_seen"] = at
    touch = {"date": at, "kind": kind, "post_id": post_id}
    touches = [t for t in (rec.get("touches") or []) if isinstance(t, dict)]
    if touch not in touches:
        touches.append(touch)
    rec["touches"] = touches
    _append(PEOPLE, rec)
    return rec, cur is None


# --- commands -------------------------------------------------------------------------------

def cmd_add(a):
    if not slug_ok(a.issue):
        print("--issue wants a slug: letters, digits, . _ - (the issues/<slug>/ folder name)")
        return 2
    if not a.commenter or not a.category:
        print("add needs --commenter and --category (what they asked for; it becomes the queue)")
        return 2
    at = a.at or today()
    row = {"event": "request", "issue": a.issue, "commenter": a.commenter.strip(),
           "url": (a.url or "").strip() or None, "category": a.category.strip(),
           "post": a.post, "at": at}
    _append(requests_path(a.issue), row)
    rec, new = upsert_person(row["commenter"], row["url"], "request", a.post or a.issue, at,
                             role=a.role, company=a.company)
    print(f"request logged: {row['commenter']} asked for {row['category']!r} on issue {a.issue} ({at})")
    print(f"  -> {requests_path(a.issue).relative_to(HOME)}")
    print(f"  -> {PEOPLE.relative_to(HOME)}: {'new' if new else 'seen'} person, "
          f"{'ICP' if rec.get('icp') else 'not ICP by headline'}, {len(rec['touches'])} touch(es)")
    print("  DM them today, then: python3 requests.py dm-sent --issue "
          f"{a.issue} --commenter \"{row['commenter']}\"")
    return 0


def cmd_dm_sent(a):
    if not slug_ok(a.issue) or not a.commenter:
        print("dm-sent needs --issue <slug> and --commenter \"<name>\"")
        return 2
    at = a.at or today()
    state = fold([a.issue])
    k = (a.issue,) + person_key(a.commenter, a.url)
    match = state.get(k)
    if match is None:
        for kk, v in state.items():
            if kk[0] == a.issue and (v.get("commenter") or "").casefold() == a.commenter.strip().casefold():
                match = v
                break
    if match is None:
        print(f"warn: no request from {a.commenter!r} on issue {a.issue}; logging the DM anyway")
    url = (a.url or (match or {}).get("url") or "").strip() or None
    row = {"event": "dm_sent", "issue": a.issue, "commenter": a.commenter.strip(), "url": url,
           "at": at}
    _append(requests_path(a.issue), row)
    upsert_person(row["commenter"], url, "dm_sent", (match or {}).get("post") or a.issue, at)
    print(f"dm_sent logged: {row['commenter']} on issue {a.issue} ({at})")
    return 0


def cmd_list(a):
    slugs = [a.issue] if a.issue else issues()
    state = fold(slugs)
    if not state:
        print("no requests logged" + (f" for issue {a.issue}" if a.issue else "") +
              ". Log one: python3 requests.py add --issue <slug> --commenter \"<name>\" --category \"<x>\"")
        return 0
    print(f"{'issue':<18}{'requested':<12}{'commenter':<26}{'DM':<12}category")
    for k in sorted(state, key=lambda k: (k[0], state[k].get("requested_at") or "")):
        r = state[k]
        dm = r.get("dm_sent_at") or "-"
        print(f"{k[0][:17]:<18}{(r.get('requested_at') or '-'):<12}{(r.get('commenter') or '')[:25]:<26}"
              f"{dm:<12}{(r.get('category') or '')[:50]}")
    n_open = sum(1 for r in state.values() if not r.get("dm_sent_at"))
    print(f"\n{len(state)} request(s), {n_open} without a DM")
    return 0


def cmd_due(a):
    slugs = [a.issue] if a.issue else issues()
    state = fold(slugs)
    cutoff = datetime.datetime.now() - datetime.timedelta(hours=a.hours)
    due = []
    for r in state.values():
        if r.get("dm_sent_at") or not r.get("requested_at"):
            continue
        try:
            when = datetime.datetime.fromisoformat(r["requested_at"])
        except ValueError:
            continue
        if when.hour == 0 and when.minute == 0 and len(r["requested_at"]) == 10:
            when = when.replace(hour=12)      # a bare date: treat the request as midday
        if when <= cutoff:
            due.append((when, r))
    if not due:
        n_open = sum(1 for r in state.values() if not r.get("dm_sent_at"))
        print(f"nothing overdue: {n_open} request(s) waiting under {a.hours}h, "
              f"{len(state) - n_open} answered")
        return 0
    due.sort(key=lambda t: t[0])
    print(f"{len(due)} request(s) older than {a.hours}h with no DM:")
    for when, r in due:
        age_h = int((datetime.datetime.now() - when).total_seconds() // 3600)
        print(f"  {r['issue']:<18}{r.get('requested_at'):<12}{age_h:>4}h  {(r.get('commenter') or '')[:26]:<27}"
              f"{(r.get('category') or '')[:40]}")
    print("Send the three-line DM, then log it: python3 requests.py dm-sent --issue <slug> --commenter \"<name>\"")
    return 1


def cmd_queue(a):
    slugs = [a.issue] if a.issue else issues()
    state = fold(slugs)
    built = set(issues())
    seen, rows = set(), []
    for r in sorted(state.values(), key=lambda r: r.get("requested_at") or ""):
        c = (r.get("category") or "").strip()
        if not c or c.casefold() in seen:
            continue
        seen.add(c.casefold())
        n = sum(1 for x in state.values() if (x.get("category") or "").strip().casefold() == c.casefold())
        rows.append((r.get("requested_at"), c, n, re.sub(r"[^a-z0-9]+", "-", c.lower()).strip("-") in built))
    if not rows:
        print("the queue is empty: no category has been asked for yet")
        return 0
    print("the queue, in the order it was asked for (a built issue is marked):")
    for at, c, n, done in rows:
        print(f"  {at or '-':<12}{'built' if done else '     ':<7}{n:>2} ask(s)  {c}")
    return 0


def main():
    argv = sys.argv[1:]
    if "--due" in argv:
        argv = ["due"] + [x for x in argv if x != "--due"]
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir", help="workspace (consumed by yapcut_home when given)")
    sub = ap.add_subparsers(dest="cmd")
    for name in ("add", "dm-sent", "list", "due", "queue"):
        sp = sub.add_parser(name)
        sp.add_argument("--issue")
        sp.add_argument("--commenter")
        sp.add_argument("--url")
        sp.add_argument("--category")
        sp.add_argument("--post", help="post id or url the comment landed on")
        sp.add_argument("--role", help="commenter's headline, for the ICP flag")
        sp.add_argument("--company")
        sp.add_argument("--at", help="YYYY-MM-DD or ISO datetime (default now)")
        sp.add_argument("--hours", type=float, default=24.0)
    a = ap.parse_args(argv)
    if not a.cmd:
        ap.print_help()
        return 2
    if a.at and not re.match(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}(:\d{2})?)?$", a.at):
        print("--at wants YYYY-MM-DD or YYYY-MM-DDTHH:MM")
        return 2
    return {"add": cmd_add, "dm-sent": cmd_dm_sent, "list": cmd_list, "due": cmd_due,
            "queue": cmd_queue}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())

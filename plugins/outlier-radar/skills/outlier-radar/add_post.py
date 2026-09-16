#!/usr/bin/env python3
"""add_post.py: register a post the weekly routine did not commission.

    python3 add_post.py --body post.md --title "..." --assets carousels/<slug>/

The selector writes `linkedin[]` from the week's measured sweep. Anything made outside
that run (a deck built from a one-off question, a reaction to something that landed
mid-week) has no way into the week file, so it never reaches the schedule, never reaches
the dashboard, and never gets tracked. It then competes for the same posting slots as the
commissioned work while being invisible to every tool that reasons about the week.

This is the one supported door for that. It appends a schema-valid item to `linkedin[]`
and nothing else: it does not reorder the lane, does not touch the selector's
declarations, and does not pretend the post was selected. `selector_note` records that a
human put it there, so a later read of the week can tell commissioned work from ad-hoc.

Writing the record by hand instead is the failure this replaces. A `linkedin[]` item has
25 fields and the dashboard is keyed on `id`; a near-miss does not error, it renders a
card with no tracking or drops out of the lane silently.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from yapcut_home import radar_home  # noqa: E402

QA_VALUES = ("passed", "pending-approval")
ID_RE = re.compile(r"^(d|o|li|li-tw)-\d{8}-\d+$")


def die(msg):
    print(f"add_post.py: {msg}", file=sys.stderr)
    sys.exit(2)


def newest_week(ws):
    """weeks/*.json minus the gate stamps beside them, newest by filename."""
    files = sorted(f for f in glob.glob(os.path.join(ws, "weeks", "*.json"))
                   if not f.endswith(".gate.json"))
    if not files:
        die(f"no weeks/*.json in {ws}")
    return files[-1]


def next_id(week, stamp):
    """li-YYYYMMDD-N, N the first free index. Ids are never reused, so this scans
    every lane in the file rather than just linkedin[]."""
    used = set()
    for lane in ("linkedin", "gtm_linkedin", "distribution", "office", "food"):
        for item in week.get(lane) or []:
            if isinstance(item, dict):
                if item.get("id"):
                    used.add(str(item["id"]))
                twin = item.get("linkedin")
                if isinstance(twin, dict) and twin.get("id"):
                    used.add(str(twin["id"]))
    n = 1
    while f"li-{stamp}-{n}" in used:
        n += 1
    return f"li-{stamp}-{n}"


def rel_to_ws(ws, path):
    """Store the assets path relative to the workspace when it sits inside it, so a
    week file survives the workspace moving. Absolute otherwise."""
    ap = os.path.abspath(os.path.expanduser(path))
    wa = os.path.abspath(ws)
    return os.path.relpath(ap, wa) if ap.startswith(wa + os.sep) else ap


def main():
    argv = sys.argv[1:]
    ws = str(radar_home(argv))  # consumes --dir; exits 2 naming the places it looked

    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", help="workspace (consumed by yapcut_home when given)")
    ap.add_argument("--body", required=True, metavar="FILE",
                    help="the post text; '-' reads stdin")
    ap.add_argument("--title", default=None, help="what the calendar cell should say")
    ap.add_argument("--assets", default=None, metavar="PATH",
                    help="folder or file the dashboard links to")
    ap.add_argument("--week", default=None, metavar="FILE",
                    help="week file to append to (default: the newest)")
    ap.add_argument("--type", default="text", dest="ptype",
                    help="format label shown on the card: text, document, single image")
    ap.add_argument("--shape", default=None,
                    help="feed shape. select_linkedin.py owns this field; leave it off "
                         "for a post it did not select")
    ap.add_argument("--job", default=None, help="the job this post does")
    ap.add_argument("--source", action="append", default=[], metavar="SRC",
                    help="repeatable; at least one is required by the schema")
    ap.add_argument("--post-day", default=None, metavar="YYYY-MM-DD")
    ap.add_argument("--qa", default="pending-approval", choices=QA_VALUES)
    ap.add_argument("--note", default=None, help="why this post exists")
    ap.add_argument("--id", default=None, help="override the generated id")
    a = ap.parse_args(argv)

    if not a.source:
        die("--source is required at least once (the schema requires source or sources[])")

    body = sys.stdin.read() if a.body == "-" else None
    if body is None:
        if not os.path.exists(a.body):
            die(f"no such body file: {a.body}")
        with open(a.body, encoding="utf-8") as fh:
            body = fh.read()
    body = body.strip()
    if not body:
        die("body is empty")

    week_path = a.week or newest_week(ws)
    if not os.path.isabs(week_path):
        cand = os.path.join(ws, week_path)
        week_path = cand if os.path.exists(cand) else week_path
    if not os.path.exists(week_path):
        die(f"no such week file: {week_path}")
    with open(week_path, encoding="utf-8") as fh:
        week = json.load(fh)

    stamp = (a.post_day or dt.date.today().isoformat()).replace("-", "")
    pid = a.id or next_id(week, stamp)
    if not ID_RE.match(pid):
        die(f"id {pid!r} does not match the preferred shape li-YYYYMMDD-N")
    if any(str(p.get("id")) == pid for p in week.get("linkedin") or []):
        die(f"id {pid} is already in {os.path.basename(week_path)}; ids are never reused")

    item = {
        "id": pid,
        "title": a.title or body.split("\n", 1)[0][:80],
        "type": a.ptype,
        "body": body,
        "qa": a.qa,
        "sources": list(a.source),
        "selector_note": a.note or "Added outside the weekly sweep with add_post.py.",
    }
    if a.shape:
        item["shape"] = a.shape
    if a.job:
        item["job"] = a.job
    if a.post_day:
        item["post_day"] = a.post_day
    if a.assets:
        target = os.path.abspath(os.path.expanduser(a.assets))
        if not os.path.exists(target):
            die(f"--assets path does not exist: {target}")
        item["assets"] = rel_to_ws(ws, a.assets)

    week.setdefault("linkedin", []).append(item)
    with open(week_path, "w", encoding="utf-8") as fh:
        json.dump(week, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    print(f"added {pid} to {os.path.basename(week_path)} linkedin[] "
          f"(now {len(week['linkedin'])} posts)")
    if a.assets:
        print(f"  assets: {item['assets']}")
    print(f"  title:  {item['title']}")
    print("Rebuild the page with build_dashboard.py to see it.")


if __name__ == "__main__":
    main()

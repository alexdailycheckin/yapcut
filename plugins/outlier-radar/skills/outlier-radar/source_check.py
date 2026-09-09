#!/usr/bin/env python3
"""source_check.py: open every source URL and prove the words are actually on the page.

WHY THIS EXISTS.

A source gate is a promise until something checks it. A run writes "every number carries
a source URL" in its method block, and nothing anywhere confirms that the URL says what
the label claims. That gap has been exercised: a batch shipped asserting it had cut
everything unverifiable, and three fabricated claims were sitting underneath that
sentence. A quote attributed to a named executive that appears nowhere in the cited
interview. A second quote a post called "verbatim" that misquotes the document. A product
feature, described concretely enough to be filmed, that does not exist on the vendor's
page or anywhere else.

All three were found by a human opening 55 pages by hand. None was catchable by any other
gate, because a well-formed invented quote satisfies every check that looks at shape
rather than at the source.

HOW IT WORKS, and the design is deliberately stupid so it cannot be argued with.

A `sources[]` entry may carry `must_contain`, a list of literal strings that HAVE to
appear on the page. This opens the page in real Chrome (the same CDP path capture_gate
uses, because many outlets refuse curl), normalises whitespace and curly quotes, and
looks for each string. Either the words are on the page or they are not. No judgement, no
model, no interpretation.

Three outcomes per claim, kept separate because they need different fixes:

  FOUND        the page says it.
  NOT_FOUND    the page loaded and the words are not there. The fabrication case, and a
               hard failure.
  UNREACHABLE  the page did not load, 404'd, redirected away, or served a bot wall. Not a
               fabrication, but the receipt is dead and needs a source swap.

Sources with no `must_contain` report as UNCHECKED. That is the point: an unverified
source should be visibly unverified rather than silently assumed.

WHAT IT CANNOT DO, stated plainly so nobody over-trusts it:
  * it cannot tell whether a real sentence was read out of context
  * it cannot check arithmetic. An invented interval between two real dates is false by
    subtraction rather than by any missing string, and this will wave it through
  * it only catches paraphrase drift when the claim is entered verbatim, which is exactly
    why quotes should be entered verbatim

Usage:
  python3 source_check.py --week weeks/<date>.json [--dir <workspace>]
  python3 source_check.py --week weeks/<date>.json --json out.json
  python3 source_check.py --week weeks/<date>.json --item d-<date>-3
  python3 source_check.py --url https://example.com --contains "some words"

Exit codes (Contract 1, 2026-09-09): 2 on any NOT_FOUND, UNREACHABLE, DATE MISMATCH or
STALE FRESHNESS (a dead or false receipt); 1 when something is UNCHECKED, undated or only
weakly dated (proven nothing yet, a warning); 0 when every claim was found. UNREACHABLE
stays a failure on purpose: the receipt is dead whatever the reason, and the fix is a
source swap, not a retry.
"""
import argparse
import datetime
import json
import os
import pathlib
import re
import sys

# realpath here locates SIBLING modules through the workspace symlink; it is never used
# to locate the workspace itself (see yapcut_home.py for why).
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cdp import Browser  # noqa: E402
from yapcut_home import radar_home  # noqa: E402

HOME = radar_home(required=False)   # consumes --dir; only used to find a relative --week

PAGE_JS = r"""(() => {
  // The page's OWN machine-readable publication date, in priority order. This is
  // read rather than guessed: every source below is something the publisher put
  // there deliberately for machines, so it is evidence in the same sense the
  // claim strings are. Prose datelines are NOT parsed, because "last updated
  // Tuesday" is not a date and a regex over body text finds every date on the
  // page including the ones in the comments.
  const pick = [];
  for (const el of document.querySelectorAll('script[type="application/ld+json"]')) {
    try {
      // Only a date hanging off an article-ish @type is trustworthy. A
      // datePublished on some other node (an Organization, a breadcrumb, a
      // sidebar ItemList) may belong to a different page entirely.
      const ARTICLE = /article|blogposting|newsarticle|webpage|report|scholarly|posting/i;
      const walk = (o) => {
        if (!o || typeof o !== 'object') return;
        if (Array.isArray(o)) { o.forEach(walk); return; }
        const ty = JSON.stringify(o['@type'] || '');
        const strong = ARTICLE.test(ty);
        for (const k of ['datePublished', 'dateCreated', 'uploadDate']) {
          if (typeof o[k] === 'string') {
            pick.push([(strong ? 'ld:' : 'ld-untyped:') + k, o[k]]);
          }
        }
        Object.values(o).forEach(walk);
      };
      walk(JSON.parse(el.textContent));
    } catch (e) { /* one malformed block must not lose the others */ }
  }
  const metas = [
    'meta[property="article:published_time"]', 'meta[name="article:published_time"]',
    'meta[name="citation_publication_date"]', 'meta[name="citation_date"]',
    'meta[property="og:published_time"]', 'meta[name="pubdate"]',
    'meta[name="publish-date"]', 'meta[name="date"]', 'meta[name="DC.date.issued"]',
    'meta[itemprop="datePublished"]',
  ];
  for (const sel of metas) {
    const el = document.querySelector(sel);
    if (el && el.content) pick.push([sel, el.content]);
  }
  const t = document.querySelector('time[datetime]');
  if (t) pick.push(['time[datetime]', t.getAttribute('datetime')]);
  return {
    finalUrl: location.href,
    title: (document.title || '').trim(),
    text: (document.body ? document.body.innerText : '').replace(/\s+/g, ' '),
    dates: pick
  };
})()"""

# Same markers capture_gate refuses on. A bot wall that happens to contain the claim
# string would otherwise read as a pass.
WALL = [
    "just a moment", "verifying you are human", "checking your browser",
    "enable javascript and cookies", "attention required", "access denied",
    "are you a robot", "unusual traffic", "ddos protection",
    "page not found", "404 error", "no longer available",
    "sign up | linkedin", "join linkedin", "your privacy choices",
]


# ---------------------------------------------------------------------------
# DATES. Added 2026-08-31 after a batch shipped calling a February 2025 campaign
# "the most copied campaign of the year", and, worse, ran a head-to-head between
# two experiments 18 months apart that straddled a ranking-model replacement.
# Neither error was catchable by anything here: source_check proved every claim
# string was on its page, and a string being present says nothing about WHEN the
# page was published. 32 green checks produced total confidence in a stale claim.
#
# Two hard failures only, and age by itself is deliberately NOT one of them. A
# wildcard tears down an old subject on purpose, so "this source is old" is a
# fact to display, never a defect. What fails is claiming freshness you do not
# have, and declaring a date the page contradicts.
# ---------------------------------------------------------------------------

# Phrases that assert the SUBJECT is current. Kept tight on purpose: bare "just"
# and bare "now" are ordinary adverbs ("it's just maths", "right now I'd argue")
# and matching them would fire on every script in the batch. Each entry here
# only makes sense if the thing being described is recent.
FRESH_CLAIMS = [
    "of the year", "this year's", "this week", "last week", "this month",
    "just shipped", "just launched", "just announced", "just added",
    "just released", "just published", "just dropped",
    "breaking", "as of today",
    "the latest", "newly released", "brand new",
]
# Removed on the first run of this gate, per the rule that the list gets loosened
# when it flags a real post wrongly and never to let a weak one through:
# "days ago", "hours ago" and "yesterday" describe the CREATOR's timeline far more
# often than the subject's. A day-in-the-life script saying "a post I wrote 9 days
# ago" makes no claim at all about how fresh its sources are, and it was flagged.
#
# "this week" and "this month" are KEPT despite the same risk, because they are the
# highest-value catches in the list and the cost is asymmetric. A false positive
# costs one reworded hook. A miss costs a batch asserting a stale story is current,
# which is the failure this gate exists for. Reword the line rather than loosening
# these two.

# A freshness claim is only a lie if the newest thing behind it is genuinely old.
# 45 days is a month and a half: long enough that a slow-moving story stays legal,
# short enough that "this week" cannot mean last quarter.
FRESH_MAX_AGE_DAYS = 45

# How far a declared date may sit from the page's own before it is a mismatch
# rather than a rounding difference. Timezones and "published vs updated" move a
# date by a day; 3 days absorbs that and nothing more.
DATE_TOLERANCE_DAYS = 3

SHIPPING_FIELDS = ("text_hook", "spoken_hook", "script")


def parse_date(v):
    """A date out of a machine-readable field, or None. Deliberately narrow."""
    if not isinstance(v, str):
        return None
    v = v.strip()
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", v)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    m = re.search(r"(\d{4})/(\d{2})/(\d{2})", v)
    if m:
        try:
            return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        except ValueError:
            return None
    return None


def url_date(url):
    """A /2026/08/20/ style path date. Not a guess: wire services and most news
    CMSs put the publication date in the path, and it is the only date available
    on pages that ship no metadata at all."""
    m = re.search(r"/(20\d{2})/(\d{1,2})/(\d{1,2})(?:/|$)", url or "")
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


# A date is only as good as the field it came from, and the difference decides
# whether a disagreement is a fabrication or just a page with poor metadata.
#
# STRONG: the publisher stated this article's publication date for machines.
# WEAK:   a date that is on the page but may not be THIS article's. Learned the
#         hard way on the first run: buffer.com ships no article metadata at all,
#         and its only <time> elements are a related-posts sidebar, so the gate
#         read a neighbouring article's date and called a correct declaration a
#         mismatch. A bare <time> is also very often an "updated" stamp.
STRONG_DATE = re.compile(
    r"^(ld:(datePublished|dateCreated|uploadDate)"
    r"|meta\[(property|name)=\"article:published_time\"\]"
    r"|meta\[name=\"citation_(publication_)?date\"\]"
    r"|meta\[itemprop=\"datePublished\"\]"
    r"|meta\[property=\"og:published_time\"\])"
)


def page_date(info, url):
    """(date, where_it_came_from, strong?) or (None, '', False). Strong fields win
    outright; a weak date is still reported, flagged as weak."""
    weak = None
    for where, raw in (info.get("dates") or []):
        d = parse_date(raw)
        if not (d and datetime.date(2000, 1, 1) < d <= datetime.date.today()):
            continue
        if STRONG_DATE.match(where):
            return d, where, True
        if weak is None:
            weak = (d, where, False)
    if weak:
        return weak
    d = url_date(url)
    if d:
        return d, "url path", False
    return None, "", False


def fresh_claims_in(item):
    """Which freshness phrases the viewer actually receives, and where."""
    hits = []
    texts = [(f, item.get(f) or "") for f in SHIPPING_FIELDS]
    tw = item.get("linkedin") or {}
    texts.append(("linkedin.body", tw.get("body") or ""))
    for field, text in texts:
        low = norm(text)
        for phrase in FRESH_CLAIMS:
            if phrase in low:
                hits.append((field, phrase))
    return hits


def norm(s: str) -> str:
    """Whitespace and quote-mark normalisation. Curly quotes, non-breaking spaces and
    line wrapping are formatting, not content, and a claim should not fail on them."""
    s = (s or "")
    s = s.replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    s = s.replace(" ", " ").replace("‑", "-").replace("–", "-")
    s = s.replace("—", "-").replace("‐", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def wall_hit(text: str, title: str) -> str:
    low = norm(title + " " + text[:1500])
    for m in WALL:
        if m in low:
            return m
    return ""


def check_page(page, url: str, claims):
    try:
        loaded = page.goto(url, settle=3.0, timeout=45)
        info = page.eval(PAGE_JS)
    except Exception as e:
        return {"state": "UNREACHABLE", "detail": f"load error: {repr(e)[:120]}",
                "results": [{"claim": c, "state": "UNREACHABLE"} for c in claims]}
    if not isinstance(info, dict):
        return {"state": "UNREACHABLE", "detail": "no DOM",
                "results": [{"claim": c, "state": "UNREACHABLE"} for c in claims]}
    text = info.get("text") or ""
    w = wall_hit(text, info.get("title") or "")
    if w or len(text) < 200:
        return {"state": "UNREACHABLE",
                "detail": f"wall or empty page ({w or 'body under 200 chars'})",
                "finalUrl": info.get("finalUrl"),
                "results": [{"claim": c, "state": "UNREACHABLE"} for c in claims]}
    hay = norm(text)
    out = []
    for c in claims:
        out.append({"claim": c, "state": "FOUND" if norm(c) in hay else "NOT_FOUND"})
    pd, pd_where, pd_strong = page_date(info, info.get("finalUrl") or url)
    return {"state": "OK", "detail": "", "finalUrl": info.get("finalUrl"),
            "loaded": loaded, "results": out,
            "page_date": pd.isoformat() if pd else None,
            "page_date_from": pd_where, "page_date_strong": pd_strong}


def iter_sources(week):
    for lane in ("distribution", "office", "linkedin"):
        for it in week.get(lane) or []:
            for i, s in enumerate(it.get("sources") or []):
                if isinstance(s, dict) and s.get("url"):
                    yield it["id"], i, s, it


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week")
    ap.add_argument("--item", help="only this item id")
    ap.add_argument("--url", help="one-off check")
    ap.add_argument("--contains", action="append", default=[],
                    help="with --url: a string that must be on the page")
    ap.add_argument("--json")
    ap.add_argument("--fresh-max-age", type=int, default=FRESH_MAX_AGE_DAYS,
                    help="days a freshness claim may sit behind its newest source")
    ap.add_argument("--dir", help="workspace (consumed by yapcut_home when given first)")
    a = ap.parse_args()
    today = datetime.date.today()

    jobs = []
    if a.url:
        jobs.append(("adhoc", 0, {"url": a.url, "must_contain": a.contains}, {}))
    elif a.week:
        wpath = pathlib.Path(a.week)
        if not wpath.exists() and HOME is not None and not wpath.is_absolute():
            alt = HOME / a.week
            if alt.exists():
                wpath = alt
        if not wpath.exists():
            print(f"no week file at {wpath}")
            sys.exit(2)
        week = json.loads(wpath.read_text(encoding="utf-8"))
        for iid, idx, s, item in iter_sources(week):
            if a.item and iid != a.item:
                continue
            jobs.append((iid, idx, s, item))
    else:
        sys.exit("need --week or --url")

    checked = unchecked = found = notfound = unreachable = 0
    date_mismatch = date_unknown = date_weak_conflict = 0
    ages = {}          # item id -> [(age_days, url)] for every dated claim source
    items_by_id = {}   # item id -> the item, for the freshness gate
    report = []
    with Browser(width=1440, height=2200) as b:
        page = b.page()
        for iid, idx, s, item in jobs:
            items_by_id.setdefault(iid, item)
            claims = [c for c in (s.get("must_contain") or []) if c]
            url = s["url"]
            if not claims:
                unchecked += 1
                report.append({"item": iid, "source": idx, "url": url,
                               "state": "UNCHECKED"})
                print(f"[UNCHECKED] {iid} sources[{idx}]  {url[:80]}")
                print("            no must_contain, so nothing here is proven")
                continue
            checked += 1
            r = check_page(page, url, claims)
            r.update({"item": iid, "source": idx, "url": url})
            report.append(r)
            if r["state"] == "UNREACHABLE":
                unreachable += len(claims)
                print(f"[UNREACHABLE] {iid} sources[{idx}]  {url[:80]}")
                print(f"              {r['detail']}. Receipt is dead, needs a swap.")
                continue
            for res in r["results"]:
                if res["state"] == "FOUND":
                    found += 1
                    print(f"[FOUND] {iid} sources[{idx}]  \"{res['claim'][:70]}\"")
                else:
                    notfound += 1
                    print(f"[NOT FOUND] {iid} sources[{idx}]  {url[:70]}")
                    print(f"            claimed: \"{res['claim'][:100]}\"")
                    print(f"            the page loaded and does not contain this.")
            pd = parse_date(r.get("page_date"))
            declared = parse_date(s.get("published"))
            strong = bool(r.get("page_date_strong"))
            if pd:
                age = (today - pd).days
                tag = "" if strong else "  WEAK FIELD"
                print(f"            [DATE] published {pd.isoformat()} "
                      f"({age}d old, from {r.get('page_date_from')}){tag}")
                # Only a strong date may drive the freshness verdict. A weak one
                # might belong to another article on the page.
                if strong:
                    ages.setdefault(iid, []).append((age, url))
                elif declared:
                    ages.setdefault(iid, []).append(((today - declared).days, url))
                if declared and abs((declared - pd).days) > DATE_TOLERANCE_DAYS:
                    if strong:
                        date_mismatch += 1
                        print(f"            [DATE MISMATCH] the source declares "
                              f"{declared.isoformat()}, the page states "
                              f"{pd.isoformat()}. One of the two is wrong.")
                    else:
                        date_weak_conflict += 1
                        print(f"            [DATE UNCONFIRMED] declared "
                              f"{declared.isoformat()}, and the only machine date on "
                              f"the page is {pd.isoformat()} from a weak field. That "
                              f"date may belong to another article or be an update "
                              f"stamp, so the declaration stands. Confirm by eye.")
            else:
                date_unknown += 1
                if declared:
                    ages.setdefault(iid, []).append(((today - declared).days, url))
                print(f"            [DATE UNKNOWN] the page publishes no "
                      f"machine-readable date. "
                      + ("Falling back to the declared date."
                         if declared else "Declare `published` on this source."))

    # ---- the freshness gate -------------------------------------------------
    # Age is never a defect on its own. Claiming freshness you do not have is.
    stale_fresh = []
    for iid, item in items_by_id.items():
        hits = fresh_claims_in(item)
        if not hits:
            continue
        dated = ages.get(iid) or []
        if not dated:
            print(f"\n[FRESHNESS UNKNOWN] {iid} says "
                  f"{', '.join(repr(p) for _, p in hits[:3])} and not one of its "
                  f"sources published a machine-readable date. Cannot judge.")
            continue
        newest = min(age for age, _ in dated)
        if newest > a.fresh_max_age:
            stale_fresh.append((iid, hits, newest))
            print(f"\n[STALE FRESHNESS] {iid}")
            for field, phrase in hits[:4]:
                print(f"                  {field} says {phrase!r}")
            print(f"                  newest source behind it is {newest}d old "
                  f"(limit {a.fresh_max_age}d)")
            print(f"                  Either drop the freshness language or state "
                  f"the real date in the script.")

    print(f"\n{found} found, {notfound} NOT FOUND, {unreachable} unreachable, "
          f"{unchecked} unchecked ({checked} sources carried claims)")
    print(f"{date_mismatch} date mismatch, {date_weak_conflict} unconfirmed, "
          f"{date_unknown} undated page(s), {len(stale_fresh)} stale freshness claim(s)")
    if date_mismatch:
        print("\nDATE MISMATCH is the fabrication case for dates. The page states a "
              "different publication date than the source declares. Fix whichever is "
              "wrong; a figure quoted under the wrong year is a false claim even when "
              "the number itself is real.")
    if stale_fresh:
        print("\nSTALE FRESHNESS is how a February 2025 campaign became \"the most "
              "copied campaign of the year\" in an August 2026 batch. An old subject is "
              "completely legal, and wildcards exist for exactly that. Saying it is "
              "recent when it is not is the failure.")
    if notfound:
        print("\nNOT FOUND is the fabrication case. The page rendered and the words are "
              "not on it. Cut the claim or fix the source; do not soften it.")
    if unchecked:
        print(f"\n{unchecked} sources prove nothing yet. Add must_contain to each one "
              f"and this becomes real coverage rather than a promise.")
    if a.json:
        pathlib.Path(a.json).write_text(json.dumps(report, indent=2, ensure_ascii=False),
                                        encoding="utf-8")
        print(f"wrote {a.json}")
    n_fail = notfound + unreachable + date_mismatch + len(stale_fresh)
    n_warn = unchecked + date_unknown + date_weak_conflict
    rc = 2 if n_fail else (1 if n_warn else 0)
    print(f"source_check: {n_fail} fail, {n_warn} warn -> rc {rc}")
    sys.exit(rc)


if __name__ == "__main__":
    main()

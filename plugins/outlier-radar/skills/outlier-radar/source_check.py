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
  python3 scripts/source_check.py --week weeks/<date>.json
  python3 scripts/source_check.py --week weeks/<date>.json --json out.json
  python3 scripts/source_check.py --week weeks/<date>.json --item d-<date>-3
  python3 scripts/source_check.py --url https://example.com --contains "some words"
"""
import argparse
import json
import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cdp import Browser  # noqa: E402

PAGE_JS = r"""(() => ({
  finalUrl: location.href,
  title: (document.title || '').trim(),
  text: (document.body ? document.body.innerText : '').replace(/\s+/g, ' ')
}))()"""

# Same markers capture_gate refuses on. A bot wall that happens to contain the claim
# string would otherwise read as a pass.
WALL = [
    "just a moment", "verifying you are human", "checking your browser",
    "enable javascript and cookies", "attention required", "access denied",
    "are you a robot", "unusual traffic", "ddos protection",
    "page not found", "404 error", "no longer available",
    "sign up | linkedin", "join linkedin", "your privacy choices",
]


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
    return {"state": "OK", "detail": "", "finalUrl": info.get("finalUrl"),
            "loaded": loaded, "results": out}


def iter_sources(week):
    for lane in ("distribution", "office", "linkedin"):
        for it in week.get(lane) or []:
            for i, s in enumerate(it.get("sources") or []):
                if isinstance(s, dict) and s.get("url"):
                    yield it["id"], i, s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week")
    ap.add_argument("--item", help="only this item id")
    ap.add_argument("--url", help="one-off check")
    ap.add_argument("--contains", action="append", default=[],
                    help="with --url: a string that must be on the page")
    ap.add_argument("--json")
    a = ap.parse_args()

    jobs = []
    if a.url:
        jobs.append(("adhoc", 0, {"url": a.url, "must_contain": a.contains}))
    elif a.week:
        week = json.loads(pathlib.Path(a.week).read_text(encoding="utf-8"))
        for iid, idx, s in iter_sources(week):
            if a.item and iid != a.item:
                continue
            jobs.append((iid, idx, s))
    else:
        sys.exit("need --week or --url")

    checked = unchecked = found = notfound = unreachable = 0
    report = []
    with Browser(width=1440, height=2200) as b:
        page = b.page()
        for iid, idx, s in jobs:
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

    print(f"\n{found} found, {notfound} NOT FOUND, {unreachable} unreachable, "
          f"{unchecked} unchecked ({checked} sources carried claims)")
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
    sys.exit(1 if (notfound or unreachable) else 0)


if __name__ == "__main__":
    main()

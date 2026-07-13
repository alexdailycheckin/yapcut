#!/usr/bin/env python3
"""Receipts gate: every named brand and every stat should have something on
screen while it is spoken (PiP evidence insert, counter, or source tag).

The retention tool cannot see this: jump cuts register as visual events, so a
bare talking head that name-drops six companies and four numbers can pass the
pattern-interrupt budget with zero receipts. This scans the cut transcript for
claim moments (brand-cased words mid-sentence, digits, money, percentages,
scale words) and checks each against the overlays JSON windows.

Usage:
  python3 pip_coverage.py --words .yap_build/w_<out>.json \
      [--overlays .yap_build/<out>_overlays.json] [--slack 2.0] [--strict] \
      [--corrections .yap_build/<out>_corrections.json]

--corrections: the caption fixes are applied to the transcript BEFORE claim
detection, so a garble fixed to a brand ("cloud" -> Claude) correctly demands
its receipt and a fixed-away false noun ("Ferguson" -> "first and") stops
demanding one.

Default is a report (exit 0/1) so unscripted quick cuts stay cheap; --strict
(or wiring via brand-config "pip_strict": true) makes uncovered claims fatal.
Exit codes: 0 all covered / no claims, 1 uncovered claims (report),
2 uncovered claims under --strict.
"""
import argparse
import json
import re
import sys

STOP = {"i", "im", "ive", "id", "ill", "ai", "ok", "okay", "pov", "diy",
        "asap", "tv", "b2b", "b2c", "qa", "faq", "us", "uk", "eu", "ceo",
        "cfo", "cmo", "vp", "gtm", "icp", "roi", "seo", "aeo", "ugc", "cta",
        "ceos", "cmos", "cfos", "vps"}
SCALE = {"million", "billion", "thousand", "hundred", "percent", "%", "$", "€", "£"}
SENT_END = re.compile(r"[.!?]\s*$")


def tokens(words_json: str, corrections: str = "") -> list:
    d = json.load(open(words_json))
    out = []
    for s in d.get("transcription", []):
        t = s.get("text", "").strip()
        if not t:
            continue
        o = s["offsets"]
        out.append([o["from"] / 1000.0, o["to"] / 1000.0, t])
    if corrections:
        try:
            c = json.load(open(corrections))
        except Exception:
            return out
        drop = set(c.get("drop", []))
        fix = {int(k): v for k, v in c.get("fix", {}).items()}
        out = [[a, b, fix.get(i, t)] for i, (a, b, t) in enumerate(out)
               if i not in drop]
    return out


def claim_moments(toks: list) -> list:
    """[(start, end, label)] merged claim windows."""
    hits = []
    sentence_start = True
    for s, e, t in toks:
        word = re.sub(r"[^A-Za-z0-9$%€£]", "", t)
        if not word:
            if SENT_END.search(t):
                sentence_start = True
            continue
        low = word.lower()
        is_stat = (bool(re.search(r"\d", word)) or low in SCALE) and low not in STOP
        is_brand = (word[0].isupper() and not sentence_start
                    and low not in STOP and len(word) > 1)
        if is_stat or is_brand:
            hits.append([s, e, word])
        sentence_start = bool(SENT_END.search(t))
    merged = []
    for h in hits:
        if merged and h[0] - merged[-1][1] <= 1.0:
            merged[-1][1] = h[1]
            merged[-1][2] += f" {h[2]}"
        else:
            merged.append(h[:])
    return merged


def overlay_windows(path: str) -> list:
    try:
        items = json.loads(open(path).read())
    except Exception:
        return []
    return [(float(i.get("start", 0)), float(i.get("end", 0)))
            for i in items if isinstance(i.get("start"), (int, float))]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", required=True)
    ap.add_argument("--overlays", default="")
    ap.add_argument("--slack", type=float, default=2.0,
                    help="an overlay within this many seconds covers the claim")
    ap.add_argument("--strict", action="store_true")
    ap.add_argument("--corrections", default="",
                    help="caption corrections json, applied before detection")
    a = ap.parse_args()

    claims = claim_moments(tokens(a.words, a.corrections))
    if not claims:
        print("pip_coverage: no brand/stat claims detected")
        return 0
    wins = overlay_windows(a.overlays) if a.overlays else []

    uncovered = []
    for s, e, label in claims:
        ok = any(ws - a.slack <= e and we + a.slack >= s for ws, we in wins)
        mark = "ok " if ok else "MISS"
        print(f"  [{mark}] {s:6.2f}-{e:6.2f}s  {label}")
        if not ok:
            uncovered.append((s, e, label))

    if uncovered:
        print(f"pip_coverage: {len(uncovered)}/{len(claims)} claims have no "
              "receipt on screen. Screenshot the real thing into "
              ".yap_build/evidence/, add a pip/counter/source window to "
              "<out>_overlays.json at those timestamps, recompose.")
        return 2 if a.strict else 1
    print(f"pip_coverage: all {len(claims)} claims covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())

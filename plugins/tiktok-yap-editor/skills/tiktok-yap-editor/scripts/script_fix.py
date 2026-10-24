#!/usr/bin/env python3
"""Caption fixes from the script: the creator's words, in the script's case and punctuation.

On a scripted take the script is the best spelling of what was said. On 2026-10-23 a cut's
transcript came back lowercase with no punctuation and "fineman" for Feynman, "combination
logs" for combination locks; every recut brought the same garbles back, and the caption gate
failed each time until the agent wrote three one-off scripts (punct_fix, capfix, adlibs) to
restore them by hand. This is that step, run by yapfull.sh after every transcript:

  - every cut word the script also says (difflib over the bare letters) takes the script's
    form: case, punctuation, apostrophes
  - a mis-heard word sitting where the script has a similar word (same number of words on both
    sides, similarity 0.6 or more, never just an inflection: "notice" for "noticed" is how it
    was said) takes the script's word; two cut words that join into one script word
    ("fine man" for "Feynman") become that word
  - a word after a sentence end is capitalised, and "i", "i'm", "i've", "i'll", "i'd" are "I"

What it never does: touch a word after the opinion slot starts (the script says nothing about
the creator's own take, so only the "I" forms apply there), touch a number, or override a fix
or drop someone wrote by hand. Its own entries carry "by": "script" and are rewritten on every
run, so a re-cut never leaves a stale one. A word the script does not have stays exactly as
heard, and the caption gate still makes a person rule on it.

Usage: script_fix.py --words w_<out>.json --script <out>_script.txt
                     --corrections <out>_corrections.json [--free-from <opinion start s>]
Exit 0 always (a missing script is a no-op); prints every word it replaced.
"""
import argparse, difflib, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import words as ywords  # noqa: E402
from yaplib import script as yscript  # noqa: E402

MIN_RATIO = 0.6
I_FORMS = {"i": "I", "i'm": "I'm", "i've": "I've", "i'll": "I'll", "i'd": "I'd"}
QUOTES = "\"'“”‘’()"


def bare(t):
    return re.sub(r"[^a-z0-9$%]", "", (t or "").lower())


def core_and_tail(t):
    m = re.match(r"^(.*?)([.,?!:;]*)$", t)
    return m.group(1), m.group(2)


SUFFIXES = ("ing", "ed", "es", "s", "d", "er", "ly")


def stem(w):
    for s in SUFFIXES:
        if len(w) - len(s) >= 3 and w.endswith(s):
            return w[:-len(s)]
    return w


def similar(a, b):
    """A garble of the script word, not another word the creator chose."""
    a, b = bare(a), bare(b)
    if len(a) < 3 or len(b) < 3 or re.search(r"\d", a + b) or a == b:
        return False
    if stem(a) == stem(b) or a.startswith(b) or b.startswith(a):
        return False                     # an inflection: "notice" said for "noticed", "surveys" for "surveyed"
    return difflib.SequenceMatcher(None, a, b).ratio() >= MIN_RATIO


def script_words(path):
    return [w.strip(QUOTES) for w in open(path, encoding="utf-8").read().split() if w.strip(QUOTES)]


def plan(words, script, locked, free=None):
    """{index: new form} and {index} to drop, for the cut words before `free`."""
    n = len(words) if free is None else sum(1 for w in words if w[0] < free)
    cut = [w[2] for w in words[:n]]
    sm = difflib.SequenceMatcher(None, [bare(x) for x in cut], [bare(x) for x in script], autojunk=False)
    fix, drop, swapped = {}, set(), []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal":
            for k in range(i2 - i1):
                fix[i1 + k] = script[j1 + k]
        elif op == "replace" and i2 - i1 == j2 - j1 <= 3:
            for k in range(i2 - i1):
                if similar(cut[i1 + k], script[j1 + k]):
                    fix[i1 + k] = script[j1 + k]
                    swapped.append((cut[i1 + k], script[j1 + k]))
        elif op == "replace" and i2 - i1 == 2 and j2 - j1 == 1:
            if similar(cut[i1] + cut[i1 + 1], script[j1]):
                fix[i1] = script[j1]; drop.add(i1 + 1)
                swapped.append((f"{cut[i1]} {cut[i1 + 1]}", script[j1]))
    # sentence starts, then the first-person forms everywhere (the opinion slot too)
    out = [fix.get(i, w[2]) for i, w in enumerate(words)]
    prev_end = True
    for i in range(n):
        if i in drop:
            continue
        w = out[i]
        if prev_end and w[:1].isalpha() and w[:1].islower() and i not in locked:
            out[i] = w[0].upper() + w[1:]
        prev_end = w.endswith((".", "?", "!"))
    for i, w in enumerate(out):
        c, tail = core_and_tail(w)
        if c.lower() in I_FORMS and c != I_FORMS[c.lower()]:
            out[i] = I_FORMS[c.lower()] + tail
    fixes = {i: out[i] for i in range(len(words))
             if out[i] != words[i][2] and i not in locked and i not in drop}
    return fixes, {i for i in drop if i not in locked}, swapped


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--words", required=True)
    ap.add_argument("--script", required=True)
    ap.add_argument("--corrections", required=True)
    ap.add_argument("--free-from", type=float, default=None)
    a = ap.parse_args()
    if not os.path.isfile(a.script) or not yscript.load(a.script):
        print("script_fix: no script, nothing to restore")
        return
    words = ywords.load_words(a.words)
    try:
        corr = json.load(open(a.corrections, encoding="utf-8"))
    except (OSError, ValueError):
        corr = {}
    raw_fix = corr.get("fix", {}) if isinstance(corr.get("fix"), dict) else {}
    raw_drop = corr.get("drop", {})
    if isinstance(raw_drop, list):     # the legacy list form, kept as hand drops
        raw_drop = {str(v["index"] if isinstance(v, dict) else v):
                    ({"from": v["from"]} if isinstance(v, dict) and v.get("from") else {}) for v in raw_drop}
    hand_fix = {k: v for k, v in raw_fix.items() if not (isinstance(v, dict) and v.get("by") == "script")}
    hand_drop = {k: v for k, v in raw_drop.items() if not (isinstance(v, dict) and v.get("by") == "script")}
    locked = {int(k) for k in list(hand_fix) + list(hand_drop) if not str(k).startswith("_")}
    fixes, drops, swapped = plan(words, script_words(a.script), locked, a.free_from)
    new_fix = dict(hand_fix)
    new_fix.update({str(i): {"from": words[i][2], "to": to, "by": "script"} for i, to in fixes.items()})
    new_drop = dict(hand_drop)
    new_drop.update({str(i): {"from": words[i][2], "by": "script"} for i in drops})
    corr["fix"] = dict(sorted(new_fix.items(), key=lambda kv: int(kv[0]) if kv[0].lstrip("-").isdigit() else -1))
    corr["drop"] = dict(sorted(new_drop.items(), key=lambda kv: int(kv[0]) if kv[0].lstrip("-").isdigit() else -1))
    json.dump(corr, open(a.corrections, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    print(f"script_fix: {len(fixes)} word(s) take the script's form ({len(swapped)} mis-heard), "
          f"{len(drops)} joined, {len(locked)} hand entr{'y' if len(locked) == 1 else 'ies'} kept"
          + (f"; the opinion slot from {a.free_from:g}s keeps its own words" if a.free_from is not None else ""))
    for frm, to in swapped:
        print(f"  {frm!r} -> {to!r}")


if __name__ == "__main__":
    main()

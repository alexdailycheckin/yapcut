#!/usr/bin/env python3
"""Caption-garble gate: diff the BURNED captions against the source script.

Whisper mishears brand names and fast phrases, then the caption engine burns
the mishear verbatim: Arc -> "ARK", Rdio -> "Radio", Claude -> "clod",
ChatGPT -> "chatgbt", "Being first and" -> "Ferguson". A human eyeballing 500
caption events misses these; a vocabulary diff does not. For any scripted run
(the creator read a written script), save that script next to the build and
this gate refuses to ship a caption word the script never contained.

Numbers and money are folded to words on BOTH sides before comparing, so a
script "fifteen dollars" matches captions "$15" and "1,600" matches itself.

Creators ad-lib connective words on camera ("of these tools" for "of the
tools"), so the gate is an ADJUDICATION list, not a dumb equality: every
unknown word must be either fixed (corrections.json, real garble) or accepted
(<out>_capqa_ok.json, harmless ad-lib) before the build passes. Review takes
seconds because the list is ~15 words, and nothing brand-shaped slips.

Usage:
  python3 caption_qa.py --ass .yap_build/cap_<out>.ass \
      --script .yap_build/<out>_script.txt [--brand brand-config.json] \
      [--accept-file .yap_build/<out>_capqa_ok.json]

accept-file: JSON list of reviewed-ok caption words, e.g. ["these","tools"].
Exit codes: 0 clean, 2 = unreviewed caption words (build-gating).
For each offender it prints the closest script word: garble -> fix it in
<out>_corrections.json and re-run yapfull with YAP_FROM_CUT=1; ad-lib ->
append the word to the accept-file and re-run.
"""
import argparse
import difflib
import json
import re
import sys

ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight",
        "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen",
        "sixteen", "seventeen", "eighteen", "nineteen"]
TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy",
        "eighty", "ninety"]
SYMBOLS = {"$": " dollars ", "%": " percent ", "€": " euros ", "£": " pounds ",
           "&": " and ", "+": " plus "}
# folding digits emits glue words english scripts phrase differently
# ("a hundred" vs "one hundred"); never flag the glue. "plus" is the CTA
# spark glyph yapfull itself prepends to the handle, pipeline-authored.
GLUE = {"one", "a", "and", "zero", "oh", "plus"}


def int_words(n: int) -> list:
    if n == 0:
        return ["zero"]
    out = []
    for div, name in ((10 ** 9, "billion"), (10 ** 6, "million"), (1000, "thousand")):
        if n >= div:
            out += int_words(n // div) + [name]
            n %= div
    if n >= 100:
        out += [ONES[n // 100], "hundred"]
        n %= 100
    if n >= 20:
        out.append(TENS[n // 10])
        n %= 10
    if n:
        out.append(ONES[n])
    return [w for w in out if w]


def canon(text: str) -> list:
    """Text -> canonical comparison words (symbols worded, digits worded)."""
    for sym, word in SYMBOLS.items():
        text = text.replace(sym, word)
    out = []
    for w in re.findall(r"[A-Za-z0-9']+", text.lower()):
        w = re.sub(r"'s$", "", w).replace("'", "")
        if not w:
            continue
        for part in re.findall(r"\d+|[a-z]+", w):
            out += int_words(int(part)) if part.isdigit() else [part]
    return out


def caption_words(ass_path: str) -> list:
    """Unique display words from Cap-style dialogue, tags stripped.

    Overlay-rendered events (counter tick frames, source lower-thirds) reuse
    the Cap style but sit in the upper 2/3 of frame; spoken-word captions and
    the CTA block sit low. Position is the discriminator: skip \\pos y < 1150
    so a counter ticking 0 -> $9M never trips the script diff."""
    words, seen = [], set()
    for line in open(ass_path, encoding="utf-8", errors="ignore"):
        if not line.startswith("Dialogue:") or ",Cap," not in line:
            continue
        text = line.split(",,", 1)[-1]
        m = re.search(r"\\pos\(\s*[\d.]+\s*,\s*([\d.]+)\s*\)", text)
        if m and float(m.group(1)) < 1150:
            continue
        text = re.sub(r"\{[^}]*\}", "", text).replace("\\N", " ").strip()
        for w in re.findall(r"[A-Za-z0-9'$%€£&+]+", text):
            if w.lower() not in seen:
                seen.add(w.lower())
                words.append(w)
    return words


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ass", required=True)
    ap.add_argument("--script", required=True, help="the verbatim source script")
    ap.add_argument("--brand", default="", help="brand-config.json: handle and "
                    "contact lines are allowlisted (the CTA block is Cap-styled)")
    ap.add_argument("--accept-file", default="",
                    help="JSON list of reviewed-ok ad-lib words")
    ap.add_argument("--overlays", default="",
                    help="overlays json: counter values/labels and source-tag "
                    "text are burned as caption-styled events, allowlist them")
    a = ap.parse_args()

    vocab = set(canon(open(a.script, encoding="utf-8").read())) | GLUE
    if a.brand:
        try:
            c = json.load(open(a.brand))
            extra = " ".join([c.get("handle", "")] + c.get("contact_lines", []))
            vocab |= set(canon(extra))
        except Exception:
            pass
    if a.accept_file:
        try:
            for w in json.load(open(a.accept_file)):
                vocab |= set(canon(str(w)))
        except FileNotFoundError:
            pass
    if a.overlays:
        try:
            for o in json.load(open(a.overlays)):
                for k in ("text", "label", "value"):
                    if o.get(k):
                        vocab |= set(canon(str(o[k])))
        except FileNotFoundError:
            pass

    caps = caption_words(a.ass)
    bad = []
    for i, w in enumerate(caps):
        folded = canon(w)
        if not folded:
            continue
        ok = all(f in vocab for f in folded) or "".join(folded) in vocab
        if not ok:
            # a hyphenated script word renders as two caption events
            # ("bi" + "directional" for "bidirectional"): join with a neighbour
            for j in (i - 1, i + 1):
                if 0 <= j < len(caps):
                    pair = canon(caps[j]) + folded if j < i else folded + canon(caps[j])
                    if "".join(pair) in vocab:
                        ok = True
                        break
        if not ok:
            bad.append((w, folded))

    if not bad:
        print("caption_qa: burned captions match the script")
        return 0
    print(f"caption_qa: {len(bad)} caption word(s) the script never contained:")
    pool = sorted(vocab)
    for w, folded in bad:
        near = difflib.get_close_matches(folded[0], pool, n=1, cutoff=0.5)
        hint = f"  (script has: {near[0]})" if near else ""
        print(f"  {w!r}{hint}")
    print("Adjudicate each: real garble -> fix in <out>_corrections.json "
          "(word index from the build w_<out>.json) and re-run with "
          "YAP_FROM_CUT=1; harmless ad-lib -> add to the accept-file.")
    return 2


if __name__ == "__main__":
    sys.exit(main())

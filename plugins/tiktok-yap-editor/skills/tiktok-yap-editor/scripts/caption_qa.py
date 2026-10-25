#!/usr/bin/env python3
"""Caption-garble gate: diff the BURNED captions against the source script.

Whisper mishears brand names and fast phrases, then the caption engine burns
the mishear verbatim: Arc -> "ARK", Rdio -> "Radio", Claude -> "clod",
ChatGPT -> "chatgbt", "Being first and" -> "Ferguson". A human eyeballing 500
caption events misses these; a vocabulary diff does not. For any scripted run
(the creator read a written script), save that script next to the build and
this gate refuses to ship a caption word the script never contained, unless it
is plainly an ad-lib.

Numbers and money are folded to words on BOTH sides before comparing, so a
script "fifteen dollars" matches captions "$15" and "1,600" matches itself.

Creators ad-lib on camera ("bear with me, I have an opinion"), and until 3.9.0 every
ad-libbed word was a decision: 80 on the 2026-10-25 Warhound cut, 78 of them ordinary
words. Now an ad-lib that is an ordinary English word in its ordinary spelling (the
system dictionary with inflections, a short modern list, and the creator's own lexicon
of every word they ever accepted or scripted, yaplib/lexicon.py) is accepted and printed
for the line audit. What still needs a ruling is what can be a garble: a word in no
dictionary, a capitalised word mid-sentence (whisper's sign that it heard a name), a
number the script never said, and a dash, which nothing clears.

Usage:
  python3 caption_qa.py --ass .yap_build/cap_<out>.ass \\
      --script .yap_build/<out>_script.txt [--brand brand-config.json] \\
      [--accept-file .yap_build/<out>_capqa_ok.json] [--words w_<out>.json --corrections <out>_corrections.json]

accept-file: JSON list of reviewed-ok caption words, e.g. ["these","tools"].
--words and --corrections let the gate see sentence starts (a capitalised word that starts a
sentence is not a name) and learn the creator's lexicon as it passes.
Exit codes: 0 clean, 2 = unreviewed caption words (build-gating). A caption
word carrying an em dash or an en dash (U+2014 / U+2013) is always flagged: the
dash ban is a hard rule on screen, and no accept-file can clear it.
For each offender it prints the closest script word: garble -> fix it in
<out>_corrections.json and re-run yapfull with YAP_FROM_CUT=1; ad-lib ->
append the word to the accept-file and re-run.
"""
import argparse
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import lexicon as ylex  # noqa: E402
from yaplib import words as ywords  # noqa: E402

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


def _ass_secs(t):
    h, m, sec = t.strip().split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


def caption_words(ass_path: str, free_from=None) -> list:
    """Unique display words from Cap-style dialogue, tags stripped.

    Overlay-rendered events (counter tick frames, source lower-thirds) reuse
    the Cap style but sit in the upper 2/3 of frame; spoken-word captions and
    the CTA block sit low. Position is the discriminator: skip \\pos y < 1150
    so a counter ticking 0 -> $9M never trips the script diff."""
    words, seen = [], set()
    for line in open(ass_path, encoding="utf-8", errors="ignore"):
        if not line.startswith("Dialogue:") or ",Cap," not in line:
            continue
        if free_from is not None:
            # the opinion slot: the take is unscripted, so nothing after it starts is diffed
            try:
                if _ass_secs(line.split(",")[1]) >= free_from:
                    continue
            except (IndexError, ValueError):
                pass
        text = line.split(",,", 1)[-1]
        m = re.search(r"\\pos\(\s*[\d.]+\s*,\s*([\d.]+)\s*\)", text)
        if m and float(m.group(1)) < 1150:
            continue
        text = re.sub(r"\{[^}]*\}", "", text).replace("\\N", " ").strip()
        for w in re.findall(r"[A-Za-z0-9'$%€£&+\u2013\u2014]+", text):
            if w.lower() not in seen:
                seen.add(w.lower())
                words.append(w)
    return words


def sentence_starts(words_path, corrections_path=""):
    """Lowercase forms of the words that begin a sentence in the cut: the first word and every
    word after one ending in . ? or !. A capitalised caption word among them is not a name."""
    if not words_path or not os.path.isfile(words_path):
        return None
    ws = [list(w) for w in ywords.load_words(words_path)]
    if corrections_path and os.path.isfile(corrections_path):
        ws = [list(w) for w in ywords.apply_corrections(ws, corrections_path, warn=False)]
    out, prev_end = set(), True
    for _s, _e, t in ws:
        core = re.sub(r"^[^A-Za-z0-9]+", "", t)
        if prev_end and core:
            out.add(core.lower().strip(".,!?;:\"'"))
        prev_end = t.rstrip().endswith((".", "?", "!"))
    return out


def judge(caps, vocab, starts, learned_words):
    """(garbles [(word, folded)], adlibs [word]) among the caption words not in vocab."""
    garbles, adlibs = [], []
    for i, w in enumerate(caps):
        if ywords.has_dash(w):
            garbles.append((w, ["<em/en dash on screen: banned, no accept-file clears it>"]))
            continue
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
        if ok:
            continue
        # an inflection of a script word ("Warhounds" when the script says warhound) is the script
        if any(b in vocab for b in ylex.bases(w)):
            continue
        core = re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9']+$", "", w)
        if re.search(r"\d", w):
            garbles.append((w, folded))                                     # a number the script never said
        elif core[:1].isupper() and not (starts is not None and core.lower().strip(".,!?;:\"'") in starts) \
                and not (starts is None and ylex.is_word(w, learned_words)):
            garbles.append((w, folded))                                     # capitalised mid-sentence: a name
        elif ylex.is_word(w, learned_words):
            adlibs.append(w)
        else:
            garbles.append((w, folded))
    return garbles, adlibs


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
    ap.add_argument("--free-from", type=float, default=None,
                    help="seconds into the cut where the unscripted opinion slot starts: captions "
                    "from there on are the creator's own take and are not diffed (3.6.0)")
    ap.add_argument("--words", default="", help="w_<out>.json: lets the gate see sentence starts")
    ap.add_argument("--corrections", default="", help="<out>_corrections.json, applied to --words")
    ap.add_argument("--no-lexicon", action="store_true",
                    help="flag every word the script lacks, as before 3.9.0")
    a = ap.parse_args()

    script_text = open(a.script, encoding="utf-8").read()
    vocab = set(canon(script_text)) | GLUE
    if a.brand:
        try:
            c = json.load(open(a.brand))
            extra = " ".join([c.get("handle", "")] + c.get("contact_lines", []))
            vocab |= set(canon(extra))
        except Exception:
            pass
    accepted = []
    if a.accept_file:
        try:
            accepted = [str(w) for w in json.load(open(a.accept_file))]
            for w in accepted:
                vocab |= set(canon(w))
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

    caps = caption_words(a.ass, a.free_from)
    learned_words = set() if a.no_lexicon else ylex.learned()
    starts = sentence_starts(a.words, a.corrections)
    if a.no_lexicon:
        garbles, adlibs = [], []
        for i, w in enumerate(caps):
            g, ad = judge([w], vocab, None, set())
            garbles += g; garbles += [(x, canon(x)) for x in ad]
    else:
        garbles, adlibs = judge(caps, vocab, starts, learned_words)

    if adlibs:
        print(f"caption_qa: {len(adlibs)} ad-lib word(s) accepted as ordinary English (read them in the line audit): "
              + ", ".join(adlibs))
    if not garbles:
        print("caption_qa: burned captions match the script" + (" plus the ad-libs above" if adlibs else ""))
        # the creator's lexicon grows with every pass: the script's own words and the hand-accepted ones
        if not a.no_lexicon:
            n = ylex.learn([w for w in re.findall(r"[A-Za-z][A-Za-z'\u2019]*", script_text)] + accepted)
            if n:
                print(f"  lexicon: {n} new word(s) learned")
        return 0
    print(f"caption_qa: {len(garbles)} caption word(s) the script never contained and no dictionary explains:")
    pool = sorted(vocab)
    for w, folded in garbles:
        if folded and folded[0].startswith("<"):
            print(f"  {w!r}  {folded[0]}")
            continue
        near = difflib.get_close_matches(folded[0], pool, n=1, cutoff=0.5)
        hint = f"  (script has: {near[0]})" if near else ""
        print(f"  {w!r}{hint}")
    print("Adjudicate each: real garble -> fix in <out>_corrections.json "
          "(word index from the build w_<out>.json) and re-run with "
          "YAP_FROM_CUT=1; harmless ad-lib -> add to the accept-file.")
    return 2


if __name__ == "__main__":
    sys.exit(main())

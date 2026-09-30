"""whisper word-JSON loaders. One definition of "a word" for the whole editor.

Input is whisper-cli -oj output: {"transcription":[{"offsets":{"from":ms,"to":ms},
"text":"..."}]}. Two flavours of that file exist in a build:

  -ml 1 -sow -dtw   caption words: one token per word, punctuation glued on.
                    load_words() reads these. Index == build_ass.py word index
                    (non-empty tokens only), which is what corrections.json,
                    stutter_check drop lists and pip_coverage all key on.
  -ml 1 (no -sow)   punct-separate tokens, used by gap_check only: pause time
                    parks inside '.' tiles, so speech_tokens() skips them and
                    the gap shows up between real words.
"""
import json
import os
import re
import sys


def read_words_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def load_words(path, offset=0.0):
    """[(start_s, end_s, text), ...] for every NON-EMPTY token, in order.
    Index in this list is the canonical word index. offset shifts every time
    (restart_scan windows)."""
    d = read_words_json(path)
    out = []
    for s in d.get("transcription", []):
        t = (s.get("text") or "").strip()
        if not t:
            continue
        o = s["offsets"]
        out.append((o["from"] / 1000.0 + offset, o["to"] / 1000.0 + offset, t))
    return out


def load_corrections(path):
    """{'drop': {int: expected|None}, 'fix': {int: (to, expected|None)}} from a corrections
    json; empty when the file is missing or blank. Keys starting with "_" are notes.

    Two forms per entry, mixable in one file:
      "fix":  {"12": "ChatGPT"}                          legacy, applied blind
      "fix":  {"12": {"from": "chat", "to": "ChatGPT"}}  applied only while word 12 is "chat"
      "drop": [13]                                       legacy, applied blind
      "drop": {"13": {"from": "-"}}                      applied only while word 13 is "-"
    """
    empty = {"drop": {}, "fix": {}}
    if not path:
        return empty
    try:
        c = json.load(open(path, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return empty
    drop, fix = {}, {}
    raw_drop = c.get("drop", [])
    if isinstance(raw_drop, dict):
        for k, v in raw_drop.items():
            if str(k).startswith("_"):
                continue
            drop[int(k)] = v.get("from") if isinstance(v, dict) else (v if isinstance(v, str) else None)
    else:
        for v in raw_drop:
            if isinstance(v, dict):
                drop[int(v["index"])] = v.get("from")
            else:
                drop[int(v)] = None
    for k, v in c.get("fix", {}).items():
        if str(k).startswith("_"):
            continue
        fix[int(k)] = (v["to"], v.get("from")) if isinstance(v, dict) else (v, None)
    return {"drop": drop, "fix": fix}


def _core(t):
    return re.sub(r"^[^A-Za-z0-9$%]+|[^A-Za-z0-9$%]+$", "", (t or "").strip()).lower()


def same_word(a, b):
    """The word a correction expects versus the word at its index now. Whisper glues
    punctuation on and changes case between runs, so compare the core too."""
    return (a or "").strip() == (b or "").strip() or _core(a) == _core(b)


def apply_corrections(words, corrections_path, warn=True):
    """Apply drop/fix by ORIGINAL index and return the new list (shorter when
    words were dropped).

    An entry that names the word it expects ("from") is applied only while that word is
    still at its index. Indices go stale on any re-cut: on 2026-09-30 a drop computed for a
    stray "-" token deleted the word "software" after a re-transcription. A stale entry is
    skipped and reported, with where the expected word sits now when it is close by."""
    c = load_corrections(corrections_path)
    if not c["drop"] and not c["fix"]:
        return list(words)
    stale = []

    def ok(kind, i, expected):
        if expected is None:
            return True
        now = words[i][2] if 0 <= i < len(words) else None
        if now is not None and same_word(expected, now):
            return True
        near = [j for j in range(max(0, i - 6), min(len(words), i + 7))
                if j != i and same_word(expected, words[j][2])]
        stale.append(f"{kind} #{i} expects {expected!r} but the word there is "
                     + (f"{now!r}" if now is not None else "past the end")
                     + (f"; {expected!r} is at #{min(near, key=lambda j: abs(j - i))} now" if near else ""))
        return False

    drop = {i for i, exp in c["drop"].items() if ok("drop", i, exp)}
    fix = {i: to for i, (to, exp) in c["fix"].items() if ok("fix", i, exp)}
    if stale and warn:
        sys.stderr.write(f"corrections: {len(stale)} stale entr{'y' if len(stale) == 1 else 'ies'} "
                         f"in {os.path.basename(corrections_path)} skipped (the cut changed; "
                         "re-derive the index from the fresh w_<out>.json):\n"
                         + "".join(f"  {m}\n" for m in stale))
    return [(w[0], w[1], fix.get(i, w[2])) for i, w in enumerate(words) if i not in drop]


def drop_entries(words, indices):
    """{"<i>": {"from": word}} for indices into words: the drop form that survives a re-cut
    (stutter_check --emit-corrections writes it)."""
    return {str(i): {"from": words[i][2]} for i in sorted(indices) if 0 <= i < len(words)}


_SPEECH = re.compile(r"[A-Za-z0-9]")
_BRACKETED = re.compile(r"^[\[(].*[\])]$")


def speech_tokens(path, offset=0.0):
    """Punct-separate flavour: (start, end, text) for spoken tokens only.
    Punctuation tiles and whisper's [BLANK_AUDIO]-style markers are skipped so
    their span counts as gap."""
    out = []
    for st, en, t in load_words(path, offset):
        if not _SPEECH.search(t) or _BRACKETED.match(t):
            continue
        out.append((st, en, t))
    return out


DASHES = ("\u2014", "\u2013")   # em dash, en dash: banned on screen everywhere


def has_dash(text):
    return any(d in (text or "") for d in DASHES)

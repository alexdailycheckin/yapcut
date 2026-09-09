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
import re


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
    """{'drop': set(int), 'fix': {int: str}} from a corrections json; empty
    when the file is missing or blank."""
    if not path:
        return {"drop": set(), "fix": {}}
    try:
        c = json.load(open(path, encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"drop": set(), "fix": {}}
    return {"drop": set(int(i) for i in c.get("drop", [])),
            "fix": {int(k): v for k, v in c.get("fix", {}).items()}}


def apply_corrections(words, corrections_path):
    """Apply drop/fix by ORIGINAL index and return the new list (shorter when
    words were dropped)."""
    c = load_corrections(corrections_path)
    if not c["drop"] and not c["fix"]:
        return list(words)
    return [(w[0], w[1], c["fix"].get(i, w[2])) for i, w in enumerate(words)
            if i not in c["drop"]]


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

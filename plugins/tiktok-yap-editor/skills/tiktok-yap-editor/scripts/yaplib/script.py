"""The take's script as evidence: what the creator meant to say, read by every repetition
detector and by the caption fixer (3.8.0).

On 2026-10-23 every one of five scripted cuts failed a gate on its first pass, and the agent's
own read was that none of them was a real problem with the takes: the detectors flagged repeats
the script itself contains ("They poke at it, they make a joke about it, they poke at it again")
and the caption gate flagged a transcript that came back lowercase with "fineman" for Feynman.
Each flag cost a decision and a re-run, and three of five shipped with YAP_ALLOW_STUTTER=1,
which silenced every repetition detector at once. The script was in .yap_build the whole time.

The rule the detectors share: a repeat the script itself says the same number of times, close
together, is the script, not a restart. A restart is the creator saying something MORE times
than the script does, so a restart of a scripted repeat ("they poke at it" three times where the
script has it twice) still gates. Words after the opinion slot starts are the creator's own take
and the script settles nothing there.
"""
import json
import os
import re


def norm(t):
    """The detectors' token form (stutter_check.norm): lowercase letters, digits, apostrophes."""
    return re.sub(r"[^a-z0-9']", "", (t or "").lower().replace("’", "'"))


def _skel(t):
    return re.sub(r"[aeiou]", "", t)


def alike(a, b):
    """Two normalised tokens that are the same word as whisper might hear it: equal, the same
    consonant skeleton ("belt"/"built", stutter_check.same), or one an inflection of the other
    ("notice"/"noticed": the script says "They noticed. ... They notice.")."""
    if a == b:
        return True
    if not a or not b:
        return False
    sa, sb = _skel(a), _skel(b)
    if len(sa) >= 3 and sa == sb:
        return True
    short, long_ = sorted((a, b), key=len)
    return len(short) >= 4 and long_.startswith(short) and len(long_) - len(short) <= 2


def tokens(text):
    """Normalised script tokens, in order."""
    return [k for k in (norm(w) for w in (text or "").split()) if k]


def load(path):
    """Script tokens from <out>_script.txt, or None when there is no script (unscripted take)."""
    if not path or not os.path.isfile(path):
        return None
    toks = tokens(open(path, encoding="utf-8").read())
    return toks or None


def free_from(path):
    """Seconds into the cut where the opinion slot starts (<out>_opinion.json), else None."""
    if not path or not os.path.isfile(path):
        return None
    try:
        v = json.load(open(path)).get("start")
        return float(v) if v not in (None, "") else None
    except (OSError, ValueError, AttributeError, TypeError):
        return None


def positions(script, phrase):
    """Every index where the script says phrase (a list of normalised tokens)."""
    n = len(phrase)
    if not script or not n:
        return []
    return [i for i in range(len(script) - n + 1)
            if all(alike(script[i + k], phrase[k]) for k in range(n))]


def says_twice_near(script, phrase, within):
    """The script says phrase twice with the second start at most `within` tokens after the
    first: the shape of a written restart ("a chatbot when they're lonely. A chatbot is")."""
    p = positions(script, phrase)
    return any(0 < b - a <= within for a, b in zip(p, p[1:]))


def says_run(script, word, n):
    """The script says word n times in a row ("No, no, no.")."""
    return bool(positions(script, [word] * n))


def count(script, phrase):
    """How many times the script says phrase, non-overlapping."""
    out, last = 0, -1
    for i in positions(script, phrase):
        if i > last:
            out, last = out + 1, i + len(phrase) - 1
    return out

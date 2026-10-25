"""Pauses the envelope cannot see, found and proven from word transcripts (3.8.1).

On the 2026-10-23 terrace takes the wind sat at -24 to -28 dB and the voice at -22 to -25, so
no level gate could tell a pause from a word: one clause kept seven pauses (3.9s after
"cabinets"), and the dead-air gate, reading a punct-separate transcript whose token spans run
across wind, called the cut clean. The aligned word transcript (transcribe.sh --words,
align_words.py) does have the gaps; the agent split that clause by hand at exactly those times.
yapcut.py cuts them and gap_check.py measures them, both through this module.
"""
import json
import os
import re
import subprocess
import tempfile

from . import rules
from . import words as ywords

WG = rules.get("cut")["word_gaps"]
SCRIPTS = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def spoken(words):
    """The words of a load_words() list that are speech, not punctuation or [markers]."""
    return [w for w in words if re.search(r"[A-Za-z0-9]", w[2]) and not w[2].startswith("[")]


def word_gap_candidates(words, min_gap=WG["min_gap_s"]):
    """(last word end, next word start, last word, next word) for every gap of min_gap or
    more between two spoken words of an aligned transcript."""
    toks = spoken(words)
    return [(x[1], y[0], x[2], y[2]) for x, y in zip(toks, toks[1:]) if y[0] - x[1] >= min_gap]


def aligned_words(wav, base):
    """transcribe.sh --words on a 16 kHz wav into <base>.json; the scratch it leaves is removed."""
    subprocess.run(["bash", os.path.join(SCRIPTS, "transcribe.sh"), wav, base, "--words"], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for junk in (base + ".wav", base + ".full.json"):
        if os.path.exists(junk):
            os.remove(junk)
    return ywords.load_words(base + ".json")


def span_words(wav, t0, t1):
    """Aligned words of a span of a take, on the take's clock. Neither the whole take nor one
    clause hears every pause: on the terrace take the whole-take transcript read 123.3 to 135.2
    as one gap, swallowing "...and if this is you, congratulations." and the pause after it,
    which that clause alone heard; and the 41s Feynman clause alone heard one of the six pauses
    the whole take did. yapcut.py takes candidates from both and lets GapConfirm decide. Cached
    beside the take's audio as <clip>.spans.json, keyed by span, remade when the audio is newer."""
    cache = wav[:-4] + ".spans.json"
    model = os.path.basename(ywords.whisper_model())
    try:
        d = json.load(open(cache))
        if d.get("model") != model or os.path.getmtime(cache) < os.path.getmtime(wav):
            d = {}
    except (OSError, ValueError):
        d = {}
    key = f"{t0:.3f}-{t1:.3f}"
    if key not in d.get("spans", {}):
        with tempfile.TemporaryDirectory(prefix="wspan_") as td:
            w = os.path.join(td, "in.wav")
            subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}",
                            "-i", wav, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", w], check=True)
            words = [(a + t0, b + t0, t) for a, b, t in aligned_words(w, os.path.join(td, "x"))]
        d.setdefault("spans", {})[key] = words
        d["model"] = model
        json.dump(d, open(cache, "w"), indent=0)
    return [tuple(x) for x in d["spans"][key]]


class GapConfirm:
    """confirm(src, e1, s2): is a gap the full transcript hears real? Two windows of the audio
    around it, at different offsets, are re-transcribed the same way (window times do not
    drift). The gap is real when both hear the next word start where the full transcript does
    (within confirm_edge_s) and neither hears a word START inside it.

    Starts, not ends: a window drags a sentence's last word into the pause after it (on the
    2026-10-23 terrace take "cabinets" ended at 79.29 in the full take and at 80.95 in a window
    with 1.5s of context), which only shrinks a gap. A start inside a gap is the dangerous case,
    a gap made of spoken words the full transcript dropped: the same take read 7.9s of lines as
    a gap, and both windows heard the words. A confirmed gap keeps the full transcript's times,
    as the hand splits did. Decisions are cached in `cache` (json), keyed by source and times."""

    def __init__(self, wavs, cache):
        self.wavs, self.path = wavs, cache
        model = os.path.basename(ywords.whisper_model())
        try:
            d = json.load(open(cache))
        except (OSError, ValueError):
            d = {}
        self.d = d if d.get("model") == model and d.get("v") == 4 else {"model": model, "v": 4}

    def window_words(self, src, t0, t1):
        with tempfile.TemporaryDirectory(prefix="wgap_") as td:
            w = os.path.join(td, "w.wav")
            subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-ss", f"{t0:.3f}", "-to", f"{t1:.3f}",
                            "-i", self.wavs[src], "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", w], check=True)
            return [(a + t0, b + t0, t) for a, b, t in spoken(aligned_words(w, os.path.join(td, "x")))]

    @staticmethod
    def real(words, e1, s2):
        edge = WG["confirm_edge_s"]
        return (any(x[0] < e1 for x in words)
                and any(abs(x[0] - s2) <= edge for x in words)
                and not any(e1 + 0.1 < x[0] < s2 - edge for x in words))

    def _grid_words(self, src, a, b):
        """A grid window's words, transcribed once per take and kept in the cache: every gap inside it
        shares the one transcription, on this cut and on any re-cut of the same take."""
        key = f"win:{os.path.basename(src)}@{a:.3f}-{b:.3f}"
        if key not in self.d:
            self.d[key] = self.window_words(src, a, b)
        return [tuple(x) for x in self.d[key]]

    def _windows(self, src, e1, s2):
        """Two windows that each hear the gap with at least 0.75 x confirm_pad_s of context on both
        sides, starting at different offsets. Grid windows first (3.8.2): whisper pads every input to
        30s, so on 2026-10-25 a 6s window took 6.6s and a 24s one 10.4s, and a take's per-gap windows
        (two for each of 47 pauses on a 3-minute episode) cost about twice what one 28s window every
        8s does. A gap too long for two grid windows to hold falls back to the per-gap windows."""
        pad = WG["confirm_pad_s"]
        ctx = pad * 0.75
        L, S = WG.get("confirm_window_s", 28.0), WG.get("confirm_stride_s", 8.0)
        wins = []
        k = max(0, int((s2 + ctx - L) // S))
        while k * S <= e1 - ctx and len(wins) < 2:
            a = k * S
            if a + L >= s2 + ctx:
                wins.append(self._grid_words(src, a, a + L))
            k += 1
        for lead, tail in ((pad, pad), (pad * 1.5, pad * 0.75))[len(wins):]:
            wins.append(self.window_words(src, max(0.0, e1 - lead), s2 + tail))
        return wins

    def __call__(self, src, e1, s2):
        key = f"{os.path.basename(src)}@{e1:.3f}-{s2:.3f}"
        if key not in self.d:
            wins = self._windows(src, e1, s2)
            ok = all(self.real(w, e1, s2) for w in wins)
            self.d[key] = [e1, s2] if ok else None
            if not ok:
                # the full transcript can drop spoken lines and report them as one long gap (on
                # the terrace take 123.3 to 135.2 held "...and if this is you, congratulations."
                # and the real 1.2s pause after it): the windows' own gaps inside it, proven by
                # the same check on both windows, stand in for it
                inner = []
                for w in wins:
                    for a, b, t1, t2 in word_gap_candidates(w):
                        if e1 - 0.1 <= a and b <= s2 + 0.1 and all(self.real(x, a, b) for x in wins) \
                                and not any(abs(a - i[0]) < 0.3 and abs(b - i[1]) < 0.3 for i in inner):
                            inner.append([a, b, t1, t2])
                self.d[key + "/inner"] = inner
            if self.path:
                json.dump(self.d, open(self.path, "w"), indent=0)
        return tuple(self.d[key]) if self.d[key] else None

    def inner(self, src, e1, s2):
        """Gaps inside a rejected candidate that both windows prove, as (e1, s2, w1, w2)."""
        self(src, e1, s2)
        return [tuple(x) for x in self.d.get(f"{os.path.basename(src)}@{e1:.3f}-{s2:.3f}/inner", [])]

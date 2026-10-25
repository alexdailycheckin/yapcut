"""One take, read once: its audio, its words, its runs of speech and what it says twice (3.9.0).

Everything the clause plan is written from, cached beside the take's audio in <workdir>/audio/
so yapprep.py, clauses_from_script.py and yapcut.py read the same files:

  <stem>.wav          16 kHz mono (yapcut's own extract)
  <stem>.spans.json   aligned words by span (yaplib/gaps.py's cache; the whole take is the
                      "0.000-<dur>" span, which is why yapcut's word-gap pass finds it made)
  <stem>.take.json    the whole take's words with the lines whisper dropped filled back in,
                      its runs of speech and its repeats

Whisper drops lines on a long file (on the 2026-10-23 terrace take it read 123.3s to 135.2s
as one gap over "and if this is you, congratulations"). A run of speech the microphone hears
with no word inside it is decoded on its own and its words put back, so the transcript the
plan is written from is complete.
"""
import json
import os
import subprocess
import tempfile

from . import envelope as yenv
from . import gaps as ygaps
from . import repeats as yrep
from . import rules
from . import words as ywords

C = rules.get("cut")
RA = rules.get("repetition")["acoustic"]


def stem_of(src):
    return os.path.splitext(os.path.basename(src))[0]


def wav_of(src, workdir):
    """The take's 16 kHz mono wav in <workdir>/audio/, made when missing or older than the take."""
    d = os.path.join(workdir, "audio")
    os.makedirs(d, exist_ok=True)
    wav = os.path.join(d, stem_of(src) + ".wav")
    if not os.path.isfile(wav) or (os.path.isfile(src) and os.path.getmtime(wav) < os.path.getmtime(src)):
        subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", src, "-vn", "-ar", "16000", "-ac", "1",
                        "-c:a", "pcm_s16le", wav], check=True)
    return wav


def runs_of(dbs, silence_db, min_silence_s):
    """Runs of speech [(start, end)] between the envelope's silences (yapcut's silences(), inverted)."""
    hop = yenv.HOP
    sil, st = [], None
    for i, v in enumerate(dbs):
        t = round(i * hop, 3)
        if v < silence_db:
            if st is None:
                st = t
        elif st is not None:
            if t - st >= min_silence_s:
                sil.append((st, t))
            st = None
    t = round(len(dbs) * hop, 3)
    if st is not None and t - st >= min_silence_s:
        sil.append((st, t))
    runs, cur = [], 0.0
    for s, e in sil:
        if s > cur:
            runs.append((cur, s))
        cur = e
    if cur < t:
        runs.append((cur, t))
    return runs


def _fill_dropped(wav, words, runs, voice_db):
    """Runs of speech (0.5s or more, as loud as the voice) with no word inside them are lines the
    whole-take decode dropped: decode each one alone and put its words back, in order."""
    env = None
    missing = []
    for a, b in runs:
        if b - a < 0.5:
            continue
        if any(w[0] < b and w[1] > a for w in words):
            continue
        if env is None:
            env = yenv.of_file(wav)
        if yenv.peak(env, a, b) < voice_db - 10:
            continue
        missing.append((max(0.0, a - 0.15), b + 0.15))
    if not missing:
        return words, 0
    out = list(words)
    for a, b in missing:
        try:
            out += ygaps.span_words(wav, a, b)
        except subprocess.CalledProcessError as e:
            print(f"  take: could not decode the run {a:.2f}-{b:.2f}s ({e})", flush=True)
    return sorted(out, key=lambda w: w[0]), len(missing)


def _fix_stacked(wav, words):
    """Whisper's long-file decode sometimes stacks a whole line's words inside a few hundredths of
    a second (on the 2026-10-25 Warhound take twenty words sat between 132.06 and 132.74). A run
    of four or more words whose starts are within 0.05s of each other is re-decoded in a window
    around it (window times do not drift) and the words put back. Returns (words, runs fixed)."""
    out, fixed, i = [], 0, 0
    n = len(words)
    while i < n:
        j = i
        while j + 1 < n and words[j + 1][0] - words[j][0] < 0.05:
            j += 1
        if j - i + 1 >= 4:
            a = max(0.0, (words[i - 1][1] if i > 0 else max(0.0, words[i][0] - 0.5)) - 0.3)
            b = (words[j + 1][0] if j + 1 < n else words[j][1] + 0.5) + 0.3
            # the stacked words' true span may run past the next word's start (their times are not
            # even monotonic): the window runs to the word after the next one, and never under 1.5s
            if j + 2 < n:
                b = max(b, words[j + 2][0])
            b = max(b, a + 1.5)
            try:
                fresh = [w for w in ygaps.span_words(wav, a, b) if a <= w[0] < b]
            except subprocess.CalledProcessError as e:
                print(f"  take: could not re-decode {a:.2f}-{b:.2f}s ({e}); its words stay as they are", flush=True)
                out += words[i:j + 1]
                i = j + 1
                continue
            out = [w for w in out if w[0] < a]
            out += fresh
            k = j + 1
            while k < n and words[k][0] < b:
                k += 1
            i = k
            fixed += 1
            continue
        out.append(words[i])
        i += 1
    return sorted(out, key=lambda w: w[0]), fixed


def read(src, workdir, silence_db=None, min_silence_s=None, refresh=False):
    """{"src", "wav", "dur", "words": [(s, e, text)], "runs": [(a, b)], "repeats": [dict], "filled": n,
    "floor", "voice"} for one take, from the cache when the audio is unchanged."""
    wav = wav_of(src, workdir)
    cache = wav[:-4] + ".take.json"
    model = os.path.basename(ywords.whisper_model())
    sdb = C["silence_db"] if silence_db is None else silence_db
    msl = C["min_silence_s"] if min_silence_s is None else min_silence_s
    key = {"model": model, "silence_db": sdb, "min_silence_s": msl, "v": 2}
    if not refresh and os.path.isfile(cache) and os.path.getmtime(cache) >= os.path.getmtime(wav):
        try:
            d = json.load(open(cache))
            if d.get("key") == key:
                d["words"] = [tuple(w) for w in d["words"]]
                d["runs"] = [tuple(r) for r in d["runs"]]
                return d
        except (OSError, ValueError, KeyError):
            pass
    env = yenv.of_file(wav)
    dur = yenv.duration_s(env)
    floor = yenv.floor_of(env)
    voice = yenv.speech_level(env, floor)
    runs = runs_of(env, sdb, msl)
    words = ygaps.span_words(wav, 0.0, dur)
    words, restacked = _fix_stacked(wav, words)
    words, filled = _fill_dropped(wav, words, runs, voice)
    reps = [e.as_dict() for e in yrep.find_file(wav, max_lag=RA["take_max_lag_s"])]
    d = {"key": key, "src": os.path.abspath(src), "wav": wav, "dur": round(dur, 3), "words": words, "runs": runs,
         "repeats": reps, "filled": filled, "restacked": restacked, "floor": round(floor, 1), "voice": round(voice, 1)}
    json.dump(d, open(cache, "w"), indent=0)
    d["words"] = [tuple(w) for w in words]
    return d


def said(words, a, b):
    """The words whose span touches [a, b], as text."""
    return " ".join(w[2] for w in words if w[0] < b and w[1] > a)


def starting(words, a, b):
    """The words that start inside [a, b), as text (a word's end is loose; its start is not)."""
    return " ".join(w[2] for w in words if a <= w[0] < b)


def transcript_text(take, gap_s=0.6):
    """The take as readable text: a [m:ss.s] mark and a new line at every pause of gap_s or more."""
    out, last = [], None
    for s, e, t in take["words"]:
        if last is None or s - last >= gap_s:
            m, sec = divmod(s, 60)
            out.append(f"\n[{int(m)}:{sec:04.1f}] ")
        out.append(t)
        last = e
    return " ".join(out).replace("\n ", "\n").strip() + "\n"

"""The take's loudness over time, the series every level decision in the cutter reads.

Median-smoothed RMS in dB: 30 ms windows at a 10 ms hop, a 5-tap median (cut.envelope in
rules.json). yapcut.py computed this in a per-sample Python loop, the slowest step of a cut on
a long take; this is the same series in numpy (the integer sums are exact, so the values match
to the last bit), shared with the dead-air gate since 3.9.0, which uses it to tell a pause the
microphone can see from one only the words can.
"""
import math
import wave

import numpy as np

from . import rules

C = rules.get("cut")
E = C["envelope"]
HOP = C["envelope"]["hop_s"]


def read_wav(path):
    """(int16 samples, rate) of a mono 16-bit wav."""
    w = wave.open(path, "rb")
    try:
        if w.getsampwidth() != 2 or w.getnchannels() != 1:
            raise ValueError(f"{path}: want mono 16-bit PCM")
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16), w.getframerate()
    finally:
        w.close()


def of_samples(sm, fr):
    """The envelope of int16 samples at rate fr: a Python list of dB values, one per hop."""
    win, hop, h = int(E["window_s"] * fr), int(HOP * fr), E["median_taps"] // 2
    n = (len(sm) - win + hop - 1) // hop if len(sm) > win else 0   # range(0, len - win, hop)
    if n <= 0:
        return []
    x = sm.astype(np.int64)
    sq = np.concatenate([[0], np.cumsum(x * x)])
    starts = np.arange(n) * hop
    s = sq[starts + win] - sq[starts]
    r = np.sqrt(s / win) / 32768.0
    with np.errstate(divide="ignore"):
        raw = np.where(r > 0, 20.0 * np.log10(np.where(r > 0, r, 1.0)), E["zero_db"])
    if h <= 0 or n < 2:
        return raw.tolist()
    # the same median as yapcut's: over the taps that exist at the edges
    cols = []
    for d in range(-h, h + 1):
        c = np.full(n, np.nan)
        if d >= 0:
            c[:n - d] = raw[d:]
        else:
            c[-d:] = raw[:n + d]
        cols.append(c)
    stack = np.stack(cols)
    med = np.nanmedian(stack, axis=0)
    # nanmedian averages the two middle values on an even count; yapcut takes the upper one
    cnt = np.sum(~np.isnan(stack), axis=0)
    even = cnt % 2 == 0
    if even.any():
        srt = np.sort(stack, axis=0)            # NaNs sort last
        upper = srt[(cnt // 2), np.arange(n)]
        med = np.where(even, upper, med)
    return med.tolist()


def of_file(path):
    sm, fr = read_wav(path)
    return of_samples(sm, fr)


def floor_of(dbs):
    """The take's pause floor: the cut.floor percentile of the frames above digital silence."""
    F = C["floor"]
    vals = sorted(d for d in dbs if d > F["ignore_below_db"])
    return vals[int(F["percentile"] * len(vals))] if vals else F["fallback_db"]


def quietest(dbs, pct=2.0):
    """The level the take or cut drops to between words: a low percentile of the frames above
    digital silence (2nd by default), the room tone of a cut whose pauses are already gone."""
    vals = [d for d in dbs if d > E["zero_db"] + 1.0]        # only digital silence is left out
    return float(np.percentile(vals, pct)) if vals else C["floor"]["fallback_db"]


def speech_level(dbs, floor):
    """The median level of the frames that are clearly voice (well above the floor)."""
    on = [d for d in dbs if d > floor + 12.0]
    return float(np.median(on)) if on else floor + 20.0


def quiet(dbs, t0, t1, level, frac=0.85):
    """True when at least `frac` of the frames in [t0, t1] sit under `level` dB: a pause the
    microphone can see, no whisper needed to prove it."""
    a, b = int(round(t0 / HOP)), int(round(t1 / HOP))
    seg = dbs[max(0, a):max(a + 1, min(len(dbs), b))]
    return bool(seg) and sum(1 for d in seg if d < level) >= frac * len(seg)


def longest_quiet(dbs, t0, t1, level):
    """The longest stretch inside [t0, t1] whose frames all sit under `level` dB, in seconds."""
    a, b = int(round(t0 / HOP)), int(round(t1 / HOP))
    best = run = 0
    for d in dbs[max(0, a):min(len(dbs), b)]:
        run = run + 1 if d < level else 0
        best = max(best, run)
    return best * HOP


def peak(dbs, t0, t1):
    a, b = int(round(t0 / HOP)), int(round(t1 / HOP))
    seg = dbs[max(0, a):max(a + 1, min(len(dbs), b))]
    return max(seg) if seg else -99.0


def duration_s(dbs):
    return len(dbs) * HOP


def _self_check():
    """Byte-for-byte agreement with the Python loop yapcut.py carried until 3.9.0."""
    import random
    rng = random.Random(3)
    sm = np.array([int(rng.gauss(0, 3000)) for _ in range(16000 * 2)], dtype=np.int16)
    fr = 16000
    win, hop, h = int(E["window_s"] * fr), int(HOP * fr), E["median_taps"] // 2
    raw_db = []
    for i in range(0, len(sm) - win, hop):
        c = sm[i:i + win].tolist()
        r = math.sqrt(sum(x * x for x in c) / len(c)) / 32768.0
        raw_db.append(20 * math.log10(r) if r > 0 else E["zero_db"])
    n = len(raw_db)
    ref = [sorted(raw_db[max(0, i - h):min(n, i + h + 1)])[(min(n, i + h + 1) - max(0, i - h)) // 2] for i in range(n)]
    got = of_samples(sm, fr)
    assert len(got) == len(ref), (len(got), len(ref))
    worst = max(abs(a - b) for a, b in zip(got, ref))
    assert worst < 1e-9, worst
    return worst


if __name__ == "__main__":
    print("envelope matches the loop to", _self_check())

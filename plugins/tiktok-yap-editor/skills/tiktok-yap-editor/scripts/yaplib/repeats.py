"""Repeats heard in the audio itself, before any transcript (3.9.0).

A restart is the same words said twice by the same voice, seconds apart, through the same mic
in the same room. Two passes of one phrase leave two stretches of audio whose spectral shape
lines up frame for frame: a ridge of high similarity at one lag. That ridge is cheap to find
(a self-similarity over MFCC frames, numpy, about a second for a five-minute take), and it
does not depend on what whisper chose to write down. The cross-window restart scan used to
decode every 0.45s of a cut in 1.1s and 1.6s whisper windows to find the restarts whisper's
long transcript tidies away: 500 to 900 decodes per video, 13 to 30 minutes of GPU, and on
the 2026-10-25 batch a prescan lane that ran a half hour ahead of each video. Now this finds
the candidate stretches and the scan decodes only the windows around them.

What it is good at: a stall ("we must we must"), a re-attempt ("it's the same bet we made.
it's the same bet we made at"), a deliberate repeat ("I love Claude. I love Claude.") and a
scripted callback all land here, because all four are the same audio twice. Which of those
each one is stays with the detectors that read words (stutter_check, restart_scan, xwin_scan)
and the person who listens. A miss is a phrase said twice so differently that the spectra do
not line up (a whisper then a shout); the rate of speech may differ by up to about a quarter.

    from yaplib import repeats
    evs = repeats.find(pcm_int16)           # [Repeat(t0, t1, lag, score)]: pass 1 is t0..t1,
                                            # pass 2 starts lag seconds later
    repeats.find_file("cut.wav", max_lag=3.5)

Every number lives in rules.json under repetition.acoustic.
"""
import math
import wave

import numpy as np

from . import rules

A = rules.get("repetition")["acoustic"]
RATE = 16000
HOP = int(RATE * A["hop_s"])            # 160 samples, 10 ms
WIN = int(RATE * A["window_s"])         # 400 samples, 25 ms
NFFT = 512
NMEL = 40
NCEP = 20


class Repeat:
    __slots__ = ("t0", "t1", "lag", "lag1", "score")

    def __init__(self, t0, t1, lag, lag1, score):
        self.t0, self.t1, self.lag, self.lag1, self.score = t0, t1, lag, lag1, score

    @property
    def dur(self):
        return self.t1 - self.t0

    @property
    def pass2(self):
        """(start, end) of the second pass in the same timeline."""
        return (self.t0 + self.lag, self.t1 + self.lag1)

    @property
    def span(self):
        """The audio both passes live in: (start of pass 1, end of pass 2)."""
        return (self.t0, self.t1 + self.lag1)

    def __repr__(self):
        return (f"Repeat({self.t0:.2f}-{self.t1:.2f}s again at {self.pass2[0]:.2f}s, "
                f"lag {self.lag:.2f}s, score {self.score:.1f})")

    def as_dict(self):
        return {"t0": round(self.t0, 3), "t1": round(self.t1, 3), "lag": round(self.lag, 3),
                "again": round(self.pass2[0], 3), "score": round(self.score, 2)}


def read_pcm(path):
    """int16 mono samples of a 16 kHz wav (anything else is rejected: the callers decode with ffmpeg)."""
    w = wave.open(path, "rb")
    try:
        if w.getframerate() != RATE or w.getnchannels() != 1 or w.getsampwidth() != 2:
            raise ValueError(f"{path}: want 16 kHz mono s16, got {w.getframerate()} Hz, "
                             f"{w.getnchannels()} ch, {w.getsampwidth() * 8}-bit")
        return np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    finally:
        w.close()


def _mel_filterbank():
    def hz2mel(f):
        return 2595.0 * math.log10(1.0 + f / 700.0)

    def mel2hz(m):
        return 700.0 * (10.0 ** (m / 2595.0) - 1.0)
    lo, hi = hz2mel(60.0), hz2mel(7600.0)
    pts = mel2hz(np.linspace(lo, hi, NMEL + 2))
    bins = np.floor((NFFT + 1) * pts / RATE).astype(int)
    fb = np.zeros((NMEL, NFFT // 2 + 1), dtype=np.float32)
    for m in range(NMEL):
        a, b, c = bins[m], bins[m + 1], bins[m + 2]
        if b <= a:
            b = a + 1
        if c <= b:
            c = b + 1
        fb[m, a:b] = (np.arange(a, b) - a) / (b - a)
        fb[m, b:c] = (c - np.arange(b, c)) / (c - b)
    return fb


def _dct_matrix():
    n = np.arange(NMEL)
    k = np.arange(NCEP + 1)[:, None]
    m = np.cos(math.pi * k * (2 * n + 1) / (2 * NMEL)) * math.sqrt(2.0 / NMEL)
    m[0] /= math.sqrt(2.0)
    return m.astype(np.float32)


def features(pcm):
    """(cepstra (N, NCEP) float32, speech mask (N,) bool, energy dB (N,)) at 10 ms frames."""
    x = pcm.astype(np.float32) / 32768.0
    if len(x) < WIN + HOP:
        return np.zeros((0, NCEP), np.float32), np.zeros(0, bool), np.zeros(0, np.float32)
    x = np.concatenate([x[:1], x[1:] - 0.97 * x[:-1]])          # pre-emphasis
    n = 1 + (len(x) - WIN) // HOP
    idx = np.arange(WIN)[None, :] + HOP * np.arange(n)[:, None]
    frames = x[idx] * np.hamming(WIN).astype(np.float32)[None, :]
    energy = 10.0 * np.log10(np.mean(frames * frames, axis=1) + 1e-10)
    spec = np.abs(np.fft.rfft(frames, NFFT, axis=1)) ** 2
    with np.errstate(all="ignore"):                             # Accelerate's BLAS raises FP flags it never acts on
        mel = np.log(spec @ _mel_filterbank().T + 1e-8)
        cep = (mel @ _dct_matrix().T)[:, 1:NCEP + 1]
    floor = np.percentile(energy, 10)
    speech = energy > floor + A["speech_over_floor_db"]
    if speech.mean() < 0.2:                                      # a take that is mostly quiet: keep what moves
        speech = energy > floor + A["speech_over_floor_db"] / 2
    if speech.any():
        cep = cep - cep[speech].mean(axis=0)                     # cepstral mean over the voice
    return cep.astype(np.float32), speech, energy.astype(np.float32)


def _ridges(sim, speech, min_lag, step_every):
    """Local-alignment ridge tracking over sim[lag, frame] (0 outside speech): a score that grows
    by (sim - base) along a ridge, may step one lag every `step_every` frames (a quarter of rate
    drift), and resets at zero. Returns the best score per frame, its lag, and where its ridge
    started (frame, lag)."""
    L, N = sim.shape
    base = A["similarity_base"]
    R = np.zeros(L, np.float32)
    start = np.zeros(L, np.int64)
    lag0 = np.arange(L, dtype=np.int64)
    best = np.zeros(N, np.float32)
    best_lag = np.zeros(N, np.int64)
    best_start = np.zeros(N, np.int64)
    best_lag0 = np.zeros(N, np.int64)
    pad = np.float32(-1e9)
    for i in range(N):
        if step_every and i % step_every == 0:
            up = np.concatenate([R[1:], [pad]])
            dn = np.concatenate([[pad], R[:-1]])
            choice = np.argmax(np.stack([R, up, dn]), axis=0)
            src = np.arange(L) + np.where(choice == 1, 1, np.where(choice == 2, -1, 0))
            src = np.clip(src, 0, L - 1)
            R, start, lag0 = R[src], start[src], lag0[src]
        s = sim[:, i] - base
        fresh = R <= 0
        start = np.where(fresh, i, start)
        lag0 = np.where(fresh, np.arange(L), lag0)
        R = np.maximum(0, R + s)
        k = int(np.argmax(R))
        best[i], best_lag[i], best_start[i], best_lag0[i] = R[k], k, start[k], lag0[k]
    return best, best_lag, best_start, best_lag0


def find(pcm, max_lag=None, min_lag=None):
    """Repeats in 16 kHz int16 mono audio: [Repeat], earliest first, pass 1 before pass 2."""
    max_lag = A["max_lag_s"] if max_lag is None else max_lag
    min_lag = A["min_lag_s"] if min_lag is None else min_lag
    cep, speech, _e = features(pcm)
    N = len(cep)
    k0, k1 = int(round(min_lag / A["hop_s"])), int(round(max_lag / A["hop_s"]))
    if N < k0 + int(A["min_run_s"] / A["hop_s"]) + 2:
        return []
    k1 = min(k1, N - 2)
    F = cep / (np.linalg.norm(cep, axis=1, keepdims=True) + 1e-6)
    L = k1 - k0 + 1
    sim = np.zeros((L, N), np.float32)
    for j, k in enumerate(range(k0, k1 + 1)):
        s = np.sum(F[:-k] * F[k:], axis=1)
        s[~(speech[:-k] & speech[k:])] = 0.0
        sim[j, :N - k] = s
    # a little smoothing along time so one odd frame does not break a ridge
    w = int(A["smooth_frames"])
    if w > 1:
        kern = np.ones(w, np.float32) / w
        sim = np.apply_along_axis(lambda r: np.convolve(r, kern, mode="same"), 1, sim)
    best, lag, start, lag0 = _ridges(sim, speech, k0, int(A["lag_step_every_frames"]))
    thr = A["event_score"]
    hop = A["hop_s"]
    nov = np.concatenate([np.zeros(2, np.float32), 1.0 - np.sum(F[2:] * F[:-2], axis=1)])
    out = []
    i = 0
    while i < N:
        if best[i] <= thr:
            i += 1
            continue
        j = i
        while j < N and best[j] > thr:
            j += 1
        peak = i + int(np.argmax(best[i:j]))
        a, b = int(start[peak]), peak + 1
        ka, kb = sorted((int(lag0[peak]), int(lag[peak])))
        t0, t1 = a * hop, peak * hop + A["window_s"]
        if t1 - t0 >= A["min_run_s"]:
            # the ridge must belong to this lag: stationary sound (wind, a fan, a held vowel) is as
            # similar to itself a tenth of a second off as on the ridge, a repeated phrase is not
            on = _mean_sim(F, a, b, range(max(0, ka - 2), kb + 3), k0, L)
            off = _mean_sim(F, a, b, list(range(ka - 12, ka - 7)) + list(range(kb + 8, kb + 13)), k0, L)
            spec = on - off
            novelty = float(nov[a:b].mean())
            if spec >= A["min_specificity"] and novelty >= A["min_novelty"]:
                out.append(Repeat(t0, t1, (ka + k0) * hop if lag0[peak] <= lag[peak] else (kb + k0) * hop,
                                  (lag[peak] + k0) * hop, float(best[peak])))
        i = j
    return _merge(out)


def _mean_sim(F, a, b, lags, k0, L):
    """The best mean frame similarity of F[a:b] against itself `lag` frames later, over `lags`
    (lag indices relative to k0)."""
    best = -1.0
    N = len(F)
    for kk in lags:
        k = kk + k0
        if k <= 0 or b + k > N:
            continue
        best = max(best, float(np.mean(np.sum(F[a:b] * F[a + k:b + k], axis=1))))
    return best


def _merge(evs):
    """Events whose pass-1 spans overlap and whose lags are within a few frames are one repeat;
    the longer run wins."""
    evs = sorted(evs, key=lambda e: (e.t0, -e.score))
    out = []
    for e in evs:
        for o in out:
            if e.t0 <= o.t1 and e.t1 >= o.t0 and abs(e.lag - o.lag) <= A["merge_lag_s"]:
                if e.score > o.score:
                    o.t0, o.t1, o.lag, o.lag1, o.score = e.t0, e.t1, e.lag, e.lag1, e.score
                else:
                    o.t0, o.t1 = min(o.t0, e.t0), max(o.t1, e.t1)
                break
        else:
            out.append(Repeat(e.t0, e.t1, e.lag, e.lag1, e.score))
    return sorted(out, key=lambda e: e.t0)


def find_file(path, max_lag=None, min_lag=None):
    return find(read_pcm(path), max_lag=max_lag, min_lag=min_lag)


def spans_of(evs, pad):
    """Merged [(lo, hi)] of audio the repeats live in, padded: the windows a scan decodes."""
    spans = sorted((max(0.0, e.span[0] - pad), e.span[1] + pad) for e in evs)
    out = []
    for lo, hi in spans:
        if out and lo <= out[-1][1]:
            out[-1] = (out[-1][0], max(out[-1][1], hi))
        else:
            out.append((lo, hi))
    return out

#!/usr/bin/env python3
"""Word times for captions: whisper.cpp's DTW alignment, checked against the voice.

    python3 align_words.py <whisper -ojf json> <out words json> [<16 kHz mono wav>]

transcribe.sh --words runs whisper with `-ml 1 -sow -nfa -dtw <preset> -ojf` and hands the full
JSON here. The output keeps the -oj shape every caller reads (transcription[].text and
offsets.from/to in ms), so nothing downstream changes.

Why: until 3.7.7 the words file carried whisper's per-segment offsets, never the DTW times.
`-oj` does not include them, nothing read `t_dtw`, and since whisper.cpp turned flash attention
on by default DTW did not even run. On fast speech the segment offsets stack three words inside
80 ms ("taken a new" at 9.06, 9.09, 9.14), so a caption group pops up whole and its highlight
jumps across all three at once. On the 2026-10-11 batch DTW cut those stacks from 9 to 23 a
video to 2 to 5 on six videos of seven.

DTW lands about 60 ms after the voice (LAG). It also drifts late on a sentence's trailing word,
into the pause after it. With the wav, a word that starts in silence is moved: back to whisper's
own start when that one is on the voice, back to just before the voice ended when the voice
stopped within 0.45 s, or forward to where the voice comes back. A move never comes closer than
GUARD to a neighbour, so it cannot reorder or stack words.
"""
import array
import json
import math
import sys
import wave

LAG = 0.06    # s, DTW's mean lateness against voice onsets on the 2026-10-11 batch
GUARD = 0.12  # s, the closest a moved word may come to its neighbours' starts
MIN = 0.08    # s, the shortest word
HOP = 0.01    # s, envelope frame


def envelope(path):
    """Per-10 ms speech flags: frame level above the take's 10th-percentile floor + 15 dB."""
    w = wave.open(path)
    if w.getsampwidth() != 2 or w.getnchannels() != 1:
        return None
    rate = w.getframerate()
    a = array.array("h", w.readframes(w.getnframes()))
    hop = int(rate * HOP)
    db = []
    for i in range(0, len(a) - hop + 1, hop):
        s = sum(x * x for x in a[i:i + hop]) / hop
        db.append(10 * math.log10(s / (32768.0 ** 2) + 1e-18))
    if not db:
        return None
    s = sorted(db)                       # 10th percentile, interpolated
    k = (len(s) - 1) * 0.10
    floor = s[int(k)] + (s[min(int(k) + 1, len(s) - 1)] - s[int(k)]) * (k - int(k))
    return [d > floor + 15 for d in db]


def align(full, sp=None):
    segs = [s for s in full.get("transcription", []) if (s.get("text") or "").strip()]
    seg_t0 = [s["offsets"]["from"] / 1000.0 for s in segs]
    t0 = []
    for s, st in zip(segs, seg_t0):
        toks = [x for x in s.get("tokens", []) if not x["text"].startswith("[_") and x.get("t_dtw", -1) >= 0]
        t0.append(max(0.0, toks[0]["t_dtw"] / 100.0 - LAG) if toks else st)
    for i in range(1, len(t0)):
        t0[i] = max(t0[i], t0[i - 1] + 0.01)

    if sp:
        def quiet(a, b):
            i0 = int(a / HOP)
            return not any(sp[i0:max(i0 + 1, int(b / HOP))])

        # voice onsets: speech after at least 150 ms of quiet
        ons = [k * HOP for k in range(15, len(sp)) if sp[k] and not any(sp[k - 15:k])]
        for i in range(len(t0)):
            lo = t0[i - 1] + GUARD if i else 0.0
            hi = t0[i + 1] - GUARD if i + 1 < len(t0) else float("inf")
            if not quiet(t0[i], t0[i] + 0.10):
                # the voice came back after a pause up to 0.3 s before this word: DTW is late, start there
                back = [o for o in ons if -0.3 <= o - t0[i] < 0 and lo <= o <= hi]
                if back:
                    t0[i] = back[-1]
                continue
            if not quiet(seg_t0[i], seg_t0[i] + 0.10) and lo <= seg_t0[i] <= hi:
                t0[i] = seg_t0[i]                       # whisper's own start is on the voice
                continue
            b = int(t0[i] / HOP)
            while b > 0 and not sp[b]:
                b -= 1
            if t0[i] - b * HOP <= 0.45 and b * HOP - 0.25 > lo - GUARD and b * HOP > lo:  # a trailing word stamped after the voice stopped
                t0[i] = max(lo, b * HOP - 0.25)
                continue
            j = int(t0[i] / HOP)
            while j < len(sp) and not sp[j]:
                j += 1
            if 0 < j * HOP - t0[i] <= 0.3 and lo <= j * HOP <= hi:
                t0[i] = j * HOP                         # forward to where the voice comes back

    out = []
    for i, s in enumerate(segs):
        end = s["offsets"]["to"] / 1000.0
        nxt = t0[i + 1] if i + 1 < len(segs) else max(end, t0[i] + 0.3)
        t1 = nxt if nxt - t0[i] < 0.9 else min(nxt, max(end, t0[i] + 0.25) + 0.1)
        t1 = max(t1, t0[i] + MIN)
        out.append({"timestamps": {}, "offsets": {"from": int(round(t0[i] * 1000)), "to": int(round(t1 * 1000))},
                    "text": s["text"]})
    return out


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    full = json.load(open(sys.argv[1], encoding="utf-8"))
    sp = envelope(sys.argv[3]) if len(sys.argv) > 3 else None
    words = align(full, sp)
    json.dump({"model": full.get("model"), "params": full.get("params"), "result": full.get("result"),
               "aligned": {"source": "dtw", "lag_s": LAG, "voice_checked": sp is not None},
               "transcription": words}, open(sys.argv[2], "w", encoding="utf-8"), indent=0)


if __name__ == "__main__":
    main()

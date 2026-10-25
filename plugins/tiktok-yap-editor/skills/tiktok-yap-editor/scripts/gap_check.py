#!/usr/bin/env python3
"""Dead-air gate: measure the pauses that actually SURVIVED the cut.

Why this exists: silence detection cannot prove a cut is tight. Room tone sits
above any -dB threshold (a fan/AC take reports zero silence while holding a
1.3s hole), so the only honest measure is the transcript: the gap between one
spoken word ending and the next beginning. If this gate fails, the cut stage never
saw the pauses; that is the noisy-take symptom, see SKILL.md 6b: measure the
real floor, raise --silence-db, re-cut.

THE ALIGNED PATH (3.9.0, the one both modes use). The cut's own aligned word transcript
(w_<out>.json, DTW-timed and checked against the voice, which yapfull already makes) names
every gap of 0.6s or more between two spoken words. Each one is then proven, cheapest proof
first:
  - the microphone: on a take whose room tone sits well under the voice, the cut's envelope
    (yaplib/envelope.py) says how long the stretch under the floor really is; that is the
    gap, measured, and no whisper runs. A transcript gap the envelope cannot find is the
    words' loose end times, not a pause.
  - the words: on a noisy take (wind, a fan, room tone as loud as the voice) two window
    re-transcriptions at different offsets must both hear the next word where the transcript
    does and no word starting inside the gap (yaplib/gaps.py, the same proof yapcut.py cuts
    by, cached in gapcheck_w_<out>.json so a rerun on the same cut decodes nothing).
Until 3.9.0 the gate also transcribed the whole cut a second time with punctuation as
separate tokens and re-transcribed three windows per candidate; on the 2026-10-23 terrace
take that transcript ran its token spans across the wind and called the cut clean, which is
why the aligned path was added, and the second transcript was never needed again.

THE LEGACY PATH runs with no --aligned: whisper -ml 1 with punctuation as separate tokens,
where pause time parks inside '.' tiles, and three windows per candidate.

Usage:
  python3 gap_check.py --video cut.mp4 --aligned w_<out>.json [--fail 0.8] [--warn 0.6] [--lead 0.8] [--allow "6.9,41.2"]
  python3 gap_check.py --video cut.mp4 [--words no_sow_words.json]      (legacy)

--allow: comma-separated timestamps (s) of deliberate beats to permit (+/-0.3s).
Exit codes: 0 clean, 1 warnings only, 2 dead air found (build-gating).
"""
import argparse
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import media, rules  # noqa: E402

D = rules.get("dead_air")   # the thresholds the phone's dead-air gate reads too
from yaplib import words as ywords  # noqa: E402
from yaplib import whisper as ywhisper  # noqa: E402


def transcribe_punct_separate(video: str, t0: float = None, t1: float = None) -> str:
    """16k mono extract + whisper -ml 1 (NO -sow): punct tokens stay separate.
    Pass t0/t1 to transcribe just a window (window timings do not drift)."""
    model = ywords.whisper_model()
    td = tempfile.mkdtemp(prefix="gapchk_")
    wav = os.path.join(td, "a.wav")
    out = os.path.join(td, "w")
    cmd = ["ffmpeg", "-nostdin", "-y"]
    if t0 is not None:
        cmd += ["-ss", f"{max(0.0, t0):.3f}", "-to", f"{t1:.3f}"]
    cmd += ["-i", video, "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
            wav, "-hide_banner", "-loglevel", "error"]
    subprocess.run(cmd, check=True)
    ywhisper.run(["whisper-cli", "-m", model, "-f", wav, "-ml", "1", "-oj", "-of", out],
                 check=True, capture_output=True, text=True)
    return out + ".json"


def window_max_gap(video: str, e1: float, s2: float) -> float:
    """Corroborate a candidate gap by re-transcribing a tight window at three
    start offsets and taking the largest inter-speech-token gap near the
    candidate (the legacy path's proof)."""
    best = 0.0
    for off in (0.0, 0.37, 0.83):
        t0 = max(0.0, e1 - 1.5 - off)
        toks = speech_tokens(transcribe_punct_separate(video, t0, s2 + 1.5 + off))
        for a, b in zip(toks, toks[1:]):
            if t0 + b[0] > e1 - 0.6 and t0 + a[1] < s2 + 0.6:
                best = max(best, b[0] - a[1])
    return best


def speech_tokens(words_json: str) -> list:
    """(start, end, text) for real spoken tokens; punctuation tiles are skipped
    so their span counts as gap (whisper parks pause time inside '.' tokens).
    One definition of a token for the whole editor: yaplib.words."""
    return ywords.speech_tokens(words_json)


def cut_wav(video, aligned):
    """The 16 kHz mono wav of the cut: the one transcribe.sh left beside the aligned words, else a fresh decode."""
    wav = aligned[:-5] + ".wav" if aligned else ""
    if wav and os.path.isfile(wav):
        return wav
    wav = os.path.join(tempfile.mkdtemp(prefix="gapchk_"), "cut.wav")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", video, "-vn", "-ar", "16000",
                    "-ac", "1", "-c:a", "pcm_s16le", wav], check=True)
    return wav


def aligned_gate(a, allow, dur):
    from yaplib import envelope as yenv
    from yaplib import gaps as ygaps
    words = ywords.load_words(a.aligned)
    toks = ygaps.spoken(words)
    if not toks:
        print("gap_check: no speech found, refusing to pass silence")
        return 2
    wav = cut_wav(a.video, a.aligned)
    env = yenv.of_file(wav)
    # a cut has almost no pause left, so its 20th percentile sits inside the words' decay: the
    # quietest frames (the 2nd percentile, three seconds of a two-minute cut) are its room tone
    floor = yenv.quietest(env)
    voice = yenv.speech_level(env, floor)
    mic_sees = voice - floor >= D["mic_separation_db"]
    level = voice - D["pause_under_voice_db"]
    print(f"  room {floor:.1f} dB, voice {voice:.1f} dB: "
          + ("the microphone sees the pauses" if mic_sees else "noisy, pauses are proven by words"))
    confirm = ygaps.GapConfirm({a.video: wav}, os.path.join(os.path.dirname(os.path.abspath(a.aligned)),
                                                           "gapcheck_" + os.path.basename(a.aligned)))
    fails, warns = [], []
    lead = toks[0][0]
    if lead > a.lead:
        g = yenv.longest_quiet(env, 0.0, lead, level) if mic_sees else lead
        if g > a.lead:
            fails.append((0.0, lead, "<start>", toks[0][2]))
    for e1, s2, t1, t2 in ygaps.word_gap_candidates(words, a.warn):
        if any(abs(e1 - t) <= 0.3 for t in allow):
            print(f"  allowed beat: {s2 - e1:.2f}s @ {e1:.2f}s  (...{t1} | {t2}...)")
            continue
        g = s2 - e1
        if mic_sees:
            # the measured pause: the longest stretch under the floor around the transcript's gap
            # (a word's end time is loose by a few tenths; the microphone is not)
            g = yenv.longest_quiet(env, e1 - 0.15, s2 + 0.15, level)
            how = "measured by the microphone"
            if g < a.warn:
                continue
        elif yenv.quiet(env, e1, s2, level):
            how = "the microphone hears nothing"
        elif confirm(a.video, e1, s2):
            how = "window-confirmed"
        else:
            print(f"  not a pause @ {e1:.2f}s: a window heard words inside the {g:.2f}s the transcript "
                  f"left (...{t1} | {t2}...)")
            continue
        if g >= a.fail:
            fails.append((e1, s2, t1, t2))
            print(f"  DEAD AIR: {g:.2f}s @ {e1:.2f}s ({how})  (...{t1} | {t2}...)")
        else:
            warns.append((e1, s2, t1, t2))
            print(f"  warn: {g:.2f}s gap @ {e1:.2f}s ({how})  (...{t1} | {t2}...)")
    tail = dur - toks[-1][1]
    if dur and tail > D["tail_warn_s"]:
        warns.append((toks[-1][1], dur, toks[-1][2], "<end>"))
        print(f"  warn: {tail:.2f}s after the last word")
    return verdict(fails, warns, len(toks), a)


def verdict(fails, warns, nwords, a):
    if fails:
        print(f"gap_check: {len(fails)} dead-air gap(s) survived the cut. "
              "Read the cut log's 'word gaps:' line first (yapcut.py cuts proven word gaps "
              "since 3.8.1; a gap it rejected heard speech in a window). Otherwise measure the "
              "pause floor, raise --silence-db (SKILL.md, Noisy takes), re-cut. Deliberate beat? --allow <t>.")
        return 2
    if warns:
        print(f"gap_check: {len(warns)} borderline gap(s), listen before shipping")
        return 1
    print(f"gap_check: clean ({nwords} words, no gap >= {a.warn}s)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--words", help="pre-made PUNCT-SEPARATE word json (no -sow); "
                    "omit to let the gate transcribe the video itself (legacy path)")
    ap.add_argument("--fail", type=float, default=D["fail_s"],
                    help="a surviving gap this long is dead air (exit 2)")
    ap.add_argument("--warn", type=float, default=D["warn_s"],
                    help="gaps between warn and fail are printed for the ear pass")
    ap.add_argument("--lead", type=float, default=D["first_word_max_s"],
                    help="max silence before the first word (cold-open rule)")
    ap.add_argument("--aligned", default="",
                    help="the cut's aligned word json (w_<out>.json): the gate reads its gaps and proves each")
    ap.add_argument("--allow", default="",
                    help="comma-separated gap timestamps to permit (+/-0.3s)")
    a = ap.parse_args()

    allow = [float(x) for x in a.allow.split(",") if x.strip()]
    dur = media.probe_duration(a.video)
    if a.aligned and os.path.isfile(a.aligned):
        return aligned_gate(a, allow, dur)

    words_json = a.words or transcribe_punct_separate(a.video)
    toks = speech_tokens(words_json)
    if not toks:
        print("gap_check: no speech found, refusing to pass silence")
        return 2

    fails, warns = [], []

    lead = toks[0][0]
    if lead > a.lead:
        fails.append((0.0, lead, "<start>", toks[0][2]))

    for (s1, e1, t1), (s2, e2, t2) in zip(toks, toks[1:]):
        g = s2 - e1
        if g < a.warn:
            continue
        if any(abs(e1 - t) <= 0.3 for t in allow):
            print(f"  allowed beat: {g:.2f}s @ {e1:.2f}s  (...{t1} | {t2}...)")
            continue
        (fails if g >= a.fail else warns).append((e1, s2, t1, t2))

    tail = dur - toks[-1][1]
    if dur and tail > D["tail_warn_s"]:
        warns.append((toks[-1][1], dur, toks[-1][2], "<end>"))

    for e1, s2, t1, t2 in warns:
        print(f"  warn: {s2 - e1:.2f}s gap @ {e1:.2f}s  (...{t1} | {t2}...)")

    confirmed = []
    for e1, s2, t1, t2 in fails:
        g = window_max_gap(a.video, e1, s2)
        if g >= a.fail * 0.9:
            confirmed.append((e1, s2, t1, t2))
            print(f"  DEAD AIR: {s2 - e1:.2f}s @ {e1:.2f}s (window-confirmed "
                  f"{g:.2f}s)  (...{t1} | {t2}...)")
        else:
            print(f"  drift artifact @ {e1:.2f}s: full-file said "
                  f"{s2 - e1:.2f}s, window measured {g:.2f}s, not gating")
    return verdict(confirmed, warns, len(toks), a)


if __name__ == "__main__":
    sys.exit(main())

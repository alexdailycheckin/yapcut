#!/usr/bin/env bash
# Transcribe one clip with whisper.cpp, producing word-level timestamps.
# Usage: transcribe.sh <video> <out_prefix> [--words]
#   default  : sentence-level .txt + .json (use for reading/story-shaping)
#   --words  : word-level, timed by DTW and checked against the voice (use for caption sync)
#
# Caption timing (3.7.7): whisper.cpp's per-segment offsets stack fast words inside 80 ms, so a
# caption group pops up whole. DTW gives each word its own time, but only with flash attention
# off (-nfa; whisper.cpp turned it on by default and DTW then silently does nothing), and only in
# the full JSON (-ojf). align_words.py reads that, corrects DTW's lateness against the wav and
# writes the usual -oj shape, so every caller reads the same file as before.
#
# Model: ggml-large-v3-turbo when present (it hears names, plurals and punctuation the small model
# misses: "rebuilt" for "rebuild", "calendar" for "count"), else ggml-small.en. $WHISPER_MODEL
# overrides. The restart scanners use the same model (yaplib.words.whisper_model).
set -euo pipefail
VIDEO="$1"; OUT="$2"; MODE="${3:-}"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
# one model for every transcript in a run (yaplib.words.whisper_model): $WHISPER_MODEL, else
# large-v3-turbo, else small.en; the DTW preset follows its file name
MODEL="$(cd "$SCRIPTS" && python3 -c 'from yaplib import words as w; print(w.whisper_model())')"
DTW="$(cd "$SCRIPTS" && python3 -c 'import sys; from yaplib import words as w; print(w.dtw_preset(sys.argv[1]))' "$MODEL")"
WAV="${OUT}.wav"

ffmpeg -nostdin -y -i "$VIDEO" -ar 16000 -ac 1 -c:a pcm_s16le "$WAV" \
  -hide_banner -loglevel error

if [ "$MODE" = "--words" ]; then
  # a failed run must leave nothing behind: on 2026-10-29 align_words.py read the .full.json an
  # earlier run left and captioned a cut with the previous cut's words
  rm -f "${OUT}.full.json" "${OUT}.json"
  # -ml 1 -sow = one token per segment (word-level); -dtw = accurate alignment
  WARGS=(-m "$MODEL" -f "$WAV" -ml 1 -sow -nfa -dtw "$DTW" -ojf -of "${OUT}.full")
  WLOG="${OUT}.whisper.log"
  # the braces send bash's own "Abort trap: 6" report into the log with whisper's stderr
  if ! { whisper-cli "${WARGS[@]}"; } 2>"$WLOG" >/dev/null; then
    # whisper-cli 1.9.0 aborts in DTW's median filter under beam search on some cuts (exit 134,
    # filter_width < a->ne[2]); padding the audio does not help, greedy decoding does (2026-10-29)
    echo "whisper-cli failed with beam search ($(grep -m1 -E 'ASSERT|error' "$WLOG" || tail -1 "$WLOG")): fell back to greedy (-bs 1 -bo 1)"
    rm -f "${OUT}.full.json"
    { whisper-cli "${WARGS[@]}" -bs 1 -bo 1; } 2>"$WLOG" >/dev/null || {
      rc=$?; echo "whisper-cli failed greedy too (exit $rc): see $WLOG" >&2; exit "$rc"; }
  fi
  rm -f "$WLOG"
  python3 "$SCRIPTS/align_words.py" "${OUT}.full.json" "${OUT}.json" "$WAV"
  echo "word-level timestamps: ${OUT}.json ($(basename "$MODEL"), DTW $DTW)"
else
  whisper-cli -m "$MODEL" -f "$WAV" -otxt -oj -of "$OUT" 2>/dev/null >/dev/null
  echo "transcript: ${OUT}.txt  (json: ${OUT}.json)"
fi

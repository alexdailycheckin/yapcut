#!/usr/bin/env bash
# make_fixture.sh <outdir>
#
# Deterministic 12s vertical stand-in for the editor tests. Same machine, same
# inputs, same bytes: lavfi test patterns for the picture, macOS `say` for the
# speech (fixed voice and rate), seeded pink noise for the room, no clock, no
# random. Writes into <outdir>:
#   fixture.mp4         1080x1920 30fps H.264 + 48 kHz stereo AAC, 12.0s. Three
#                       patterns (testsrc2, smptehdbars, rgbtestsrc) switch INSIDE
#                       the first and the last speech run, never at a pause, so the
#                       retention gate sees two real visual events that survive the
#                       cut and are not joins.
#   fixture_speech.wav  the bare speech track, 48 kHz mono, padded to 12s
# The pink noise sits near -52 dBFS, a quiet real room: the seam gate calls any
# 15ms window under -65 dB a splice hole, and a fixture with no room at all would
# fail every join the cutter makes (measured: amplitude 0.003 gave a -68 dB floor).
#   clauses.json        one clause spanning the whole fixture (yapcut cuts the pauses)
#   script.txt          the verbatim spoken text (the caption gate reads it)
#   fixture.json        what was generated: speech source, runs, change points
#
# The speech has two 0.9s pauses ([[slnc 900]]) so the cutter has real joins to
# make. Without `say` (Linux), FIXTURE_SPEECH=<wav or aiff> supplies the speech;
# with neither, a sine stand-in is rendered and the gates that need words
# (dead air, captions) will not pass: the smoke test says so and stops.
set -euo pipefail
OUT="${1:?usage: make_fixture.sh <outdir>}"
mkdir -p "$OUT"; OUT="$(cd "$OUT" && pwd)"
DUR=12
SCRIPT_TEXT='This is the smoke test clip for the editor. It has three short lines with a pause after each one. The cut should remove both pauses and keep every word.'
SAY_TEXT='This is the smoke test clip for the editor. [[slnc 900]] It has three short lines with a pause after each one. [[slnc 900]] The cut should remove both pauses and keep every word.'
VOICE="${FIXTURE_VOICE:-Samantha}"; RATE=185

SOURCE=""
if [ -n "${FIXTURE_SPEECH:-}" ]; then
  [ -f "$FIXTURE_SPEECH" ] || { echo "make_fixture: FIXTURE_SPEECH not found: $FIXTURE_SPEECH"; exit 2; }
  SRC="$FIXTURE_SPEECH"; SOURCE="FIXTURE_SPEECH=$FIXTURE_SPEECH"
elif command -v say >/dev/null 2>&1; then
  SRC="$OUT/_speech.aiff"
  if say -v "$VOICE" -r "$RATE" -o "$SRC" "$SAY_TEXT" 2>/dev/null; then
    SOURCE="say -v $VOICE -r $RATE"
  else
    say -r "$RATE" -o "$SRC" "$SAY_TEXT"; SOURCE="say (default voice) -r $RATE"
  fi
else
  SRC="$OUT/_speech.wav"; SOURCE="sine stand-in (no words: the speech gates will not pass)"
  echo "make_fixture: no macOS say and no FIXTURE_SPEECH; rendering a sine stand-in" >&2
  ffmpeg -nostdin -y -f lavfi -i "aevalsrc=0.3*sin(2*PI*220*t)*lt(mod(t\,4)\,3):d=$DUR:s=48000" \
    -ac 1 -c:a pcm_s16le "$SRC" -hide_banner -loglevel error
fi

# the speech track: 48 kHz mono, silence-padded to DUR
ffmpeg -nostdin -y -i "$SRC" -af "apad" -t "$DUR" -ar 48000 -ac 1 -c:a pcm_s16le \
  "$OUT/fixture_speech.wav" -hide_banner -loglevel error

# speech runs from the energy (silencedetect), then the two picture-change points:
# the middle of the first run and the middle of the last run
SIL="$(ffmpeg -nostdin -i "$OUT/fixture_speech.wav" -af "silencedetect=noise=-40dB:d=0.4" -f null - 2>&1 \
       | grep -o 'silence_\(start\|end\): [0-9.]*' | tr '\n' ' ' || true)"
read -r C1 C2 RUNS <<<"$(python3 - "$SIL" "$DUR" <<'PY'
import re, sys, json
s, dur = sys.argv[1], float(sys.argv[2])
starts = [float(x) for x in re.findall(r"silence_start: ([0-9.]+)", s)]
ends = [float(x) for x in re.findall(r"silence_end: ([0-9.]+)", s)]
if len(starts) > len(ends):
    ends.append(dur)                       # silence running to EOF has no end line
runs, cur = [], 0.0
for a, b in zip(starts, ends):
    if a - cur >= 0.3:
        runs.append((round(cur, 2), round(a, 2)))
    cur = b
if dur - cur >= 0.3:
    runs.append((round(cur, 2), round(dur, 2)))
if len(runs) >= 2:
    c1 = (runs[0][0] + runs[0][1]) / 2
    c2 = (runs[-1][0] + runs[-1][1]) / 2
else:
    c1, c2 = dur * 0.25, dur * 0.75
print(f"{c1:.2f} {c2:.2f} {json.dumps(runs).replace(' ', '')}")
PY
)"
D2="$(python3 -c "print(round($C2 - $C1, 2))")"
D3="$(python3 -c "print(round($DUR - $C2, 2))")"

# picture: three lavfi patterns concatenated at C1 and C2; audio: speech + seeded
# pink noise (a room, so no pause ever reads as digital silence to the seam gate)
ffmpeg -nostdin -y \
  -f lavfi -i "testsrc2=s=1080x1920:r=30:d=$C1" \
  -f lavfi -i "smptehdbars=s=1080x1920:r=30:d=$D2" \
  -f lavfi -i "rgbtestsrc=s=1080x1920:r=30:d=$D3" \
  -i "$OUT/fixture_speech.wav" \
  -f lavfi -i "anoisesrc=color=pink:seed=42:amplitude=0.02:r=48000:d=$DUR" \
  -filter_complex "[0:v][1:v][2:v]concat=n=3:v=1:a=0,format=yuv420p[v];[3:a][4:a]amix=inputs=2:duration=first:normalize=0,aformat=channel_layouts=stereo[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset veryfast -crf 18 -r 30 -pix_fmt yuv420p \
  -video_track_timescale 30000 -c:a aac -ar 48000 -ac 2 -b:a 192k -t "$DUR" \
  "$OUT/fixture.mp4" -hide_banner -loglevel error

printf '%s\n' "$SCRIPT_TEXT" > "$OUT/script.txt"
python3 - "$OUT" "$DUR" "$SOURCE" "$C1" "$C2" "$RUNS" <<'PY'
import json, sys
out, dur, source, c1, c2, runs = sys.argv[1:7]
json.dump([{"src": f"{out}/fixture.mp4", "start": 0.0, "end": float(dur), "label": "all"}],
          open(f"{out}/clauses.json", "w"), indent=1)
json.dump({"duration_s": float(dur), "speech_source": source, "speech_runs": json.loads(runs),
           "picture_changes_s": [float(c1), float(c2)],
           "patterns": ["testsrc2", "smptehdbars", "rgbtestsrc"], "noise": "pink seed=42 amplitude=0.02"},
          open(f"{out}/fixture.json", "w"), indent=1)
PY
rm -f "$OUT/_speech.aiff" "$OUT/_speech.wav"
echo "fixture -> $OUT/fixture.mp4  (speech: $SOURCE; runs $RUNS; picture changes at ${C1}s and ${C2}s)"

#!/usr/bin/env bash
# libass-era final pass: burn a generated .ass caption file onto the cut,
# normalize loudness, and re-encode to clean constant-frame-rate 30fps.
# This replaces compose.sh (the Pillow PNG-overlay path) when ffmpeg has libass.
#
# Usage: compose_ass.sh <cut.mp4> <captions.ass> <out.mp4>
#
# Three jobs in one pass:
# - ass=  burns the styled subtitle file (one pass, no PNG frames). Needs an
#         ffmpeg built WITH libass; preflight.py asserts it. Fonts are resolved
#         by fontconfig from the family name in the .ass (Montserrat/Anton/etc),
#         so the font must be installed (the font casks, or system fonts).
# - loudnorm to -14 LUFS: TikTok normalizes toward ~-14; raw phone audio (~-22)
#         sounds thin against the feed. loudnorm resamples internally (its
#         output hits 96/192kHz), so -ar 48000 pins the export back to normal.
# - re-encode CFR 30fps: a concat of copied streams (from cut.py) can play black
#         in QuickTime due to irregular timestamps; this clean pass fixes it.
set -euo pipefail
CUT="$1"; ASS="$2"; OUT="$3"

# ass filter wants the path escaped (colons/commas break the filter parser).
ASS_ESC=$(printf '%s' "$ASS" | sed -e 's/\\/\\\\/g' -e "s/'/\\\\'/g" -e 's/:/\\:/g')

# setpts=N/(30*TB) RENUMBERS every frame onto a gapless 30fps grid BEFORE the
# ass burn. yapcut's segment video is concat-demuxed with -c copy, which leaves
# a small timestamp gap at every join; the video accumulates those gaps while
# the single continuous PCM->AAC audio has none, so the PICTURE drifts later than
# the voice, worst at the end (measured +0.23s on the Jun 29/Jul 5 v4 re-cuts).
# A plain fps=30 here HONORS those gappy PTS and preserves the drift; renumbering
# by frame index discards them and re-locks video to the gapless audio+captions.
# LOUDNESS: two-pass, not one. Single-pass loudnorm runs in dynamic mode and
# needs runway to converge, so it UNDER-SHOOTS on short clips: a 17s celebration
# clip with a loud transient (a gong at 0.7s) measured -17.6 LUFS against the
# -14 target, which is thin in the feed, exactly what this filter exists to
# prevent. Pass 1 measures, pass 2 applies a linear gain from those numbers, and
# alimiter guards the ceiling when the linear gain would push a transient over.
# Falls back to the old single-pass filter if measurement fails for any reason.
# Why not loudnorm's own linear mode: it REFUSES a linear gain that would breach
# TP and silently reverts to dynamic, which is the under-shoot above. A raw take
# whose loudest moment is a percussive spike (gong, clap, laugh burst) has no
# headroom left (measured input_tp -0.34 dBTP), so the only way to reach -14 is
# to gain first and let the limiter absorb that spike, which is inaudible on a
# transient and is what makes the voice sit forward in the feed.
#
# THE GAIN CEILING IS NOT A ROUND NUMBER YOU PICK (fixed 2026-08-28). It used to
# be a flat min(12.0), and that clamp silently ate the target on every single
# take the creator shoots: their lav records around -28 LUFS, so reaching -14 needs about
# +14.5dB, the clamp gave 12, and the whole 08-24 batch shipped 2 to 3dB thin
# (-15.9 to -16.8 against -14). The Aug 17 batch did too, at -16.2 to -17.7, so
# it had been quietly wrong for weeks. The rail it was trying to be, do not
# amplify a take that is silence, belongs on the INPUT (is there speech here at
# all), not on the gain. And the arithmetic is no longer trusted: the limiter
# does real work at these gains, so pass 2 renders the audio and MEASURES it,
# then pass 3 corrects the residue. Landing on target is verified, not assumed.
LIM="alimiter=limit=0.841:attack=5:release=60:level=disabled"
measure_i() {   # integrated LUFS of $CUT through filter chain $1
  ffmpeg -nostdin -i "$CUT" -af "$1,ebur128=framelog=quiet" -f null - 2>&1 \
    | awk '/Integrated loudness/{f=1} f&&/I:/{print $2; exit}' || true
}
G1=$(ffmpeg -nostdin -i "$CUT" -af "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json" \
       -f null - 2>&1 | python3 -c '
import sys,json,re
t=sys.stdin.read()
m=re.findall(r"\{[^{}]*input_i[^{}]*\}",t,re.S)
if not m: sys.exit(1)
d=json.loads(m[-1])
try: i=float(d["input_i"])
except Exception: sys.exit(1)
if i!=i or i in (float("inf"),float("-inf")): sys.exit(1)
# Guard the INPUT, not the gain: below -45 LUFS there is no speech to lift,
# only room tone, so refuse to amplify it into noise. Above that, allow the
# gain the take actually needs (a phone lav routinely wants +14 or +15).
if i < -45.0: sys.exit(1)
print(f"{max(-6.0,min(24.0,-14.0-i)):.2f}")
' 2>/dev/null) || G1=""

AF=""
if [ -n "$G1" ]; then
  L2=$(measure_i "volume=${G1}dB,$LIM")
  GF=$(python3 -c "
import sys
try: l=float('$L2')
except Exception: sys.exit(1)
g=float('$G1')
if l==l and abs(l)!=float('inf'):
    g=max(-6.0,min(24.0,g+max(-3.0,min(3.0,-14.0-l))))   # correct the limiter's residue
print(f'{g:.2f}')" 2>/dev/null) || GF="$G1"
  [ -n "$GF" ] || GF="$G1"
  printf '  loudness: %sdB then corrected to %sdB (pass-2 measured %s LUFS)\n' "$G1" "$GF" "${L2:-n/a}"
  AF="volume=${GF}dB,$LIM"
fi
[ -n "$AF" ] || { AF="loudnorm=I=-14:TP=-1.5:LRA=11"; echo "  (loudnorm measure failed, single-pass fallback)"; }

ffmpeg -nostdin -y -i "$CUT" \
  -vf "setpts=N/(30*TB),ass='${ASS_ESC}',setsar=1,format=yuv420p" \
  -af "$AF" -ar 48000 \
  -c:v libx264 -preset medium -crf 16 -r 30 -vsync cfr \
  -video_track_timescale 30000 -c:a aac -b:a 192k -movflags +faststart \
  "$OUT" -hide_banner -loglevel error

echo "wrote $OUT"
echo "--- QA: loudness (target ~-14 LUFS) ---"
ffmpeg -nostdin -i "$OUT" -af ebur128=peak=true -f null - 2>&1 \
  | grep -A1 "Integrated loudness" | tail -2
ffprobe -v error -show_entries format=duration:stream=r_frame_rate \
  -select_streams v:0 -of default=noprint_wrappers=1 "$OUT"

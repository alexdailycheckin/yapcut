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
# the single continuous PCM->AAC audio has none, so the PICTURE drifts later
# than the voice, worst at the end. A plain fps=30 here HONORS those gappy PTS
# and preserves the drift; renumbering by frame index discards them and
# re-locks video to the gapless audio+captions.
ffmpeg -nostdin -y -i "$CUT" \
  -vf "setpts=N/(30*TB),ass='${ASS_ESC}',setsar=1,format=yuv420p" \
  -af "loudnorm=I=-14:TP=-1.5:LRA=11" -ar 48000 \
  -c:v libx264 -preset medium -crf 18 -r 30 -vsync cfr \
  -video_track_timescale 30000 -c:a aac -b:a 192k -movflags +faststart \
  "$OUT" -hide_banner -loglevel error

echo "wrote $OUT"
echo "--- QA: loudness (target ~-14 LUFS) ---"
ffmpeg -nostdin -i "$OUT" -af ebur128=peak=true -f null - 2>&1 \
  | grep -A1 "Integrated loudness" | tail -2
ffprobe -v error -show_entries format=duration:stream=r_frame_rate \
  -select_streams v:0 -of default=noprint_wrappers=1 "$OUT"

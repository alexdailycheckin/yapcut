#!/usr/bin/env bash
# Promote the approved video to output/ and delete all working files.
#
# Usage: finalize.sh <approved_final.mp4> <footage_dir> <clean-name>
#   e.g. finalize.sh .yap_build/final.mp4 "/path/Creator YAP" yap-world-is-changing
#
# The rule (the creator's): the deliverable folder holds ONLY the one finished video.
# All intermediates (audio, segs, capframes, transcripts, rough/tight cuts,
# earlier final versions) live under <footage_dir>/.yap_build/ and are removed
# here. Run this only after the creator has signed off on the cut and captions, because
# it throws the working files away.
set -euo pipefail
FINAL="$1"; FOOTAGE="$2"; NAME="${3:-yap-final}"
OUT="$FOOTAGE/output"

mkdir -p "$OUT"
# keep output/ to a single deliverable: clear old finals first
rm -f "$OUT"/*.mp4
cp "$FINAL" "$OUT/$NAME.mp4"
rm -rf "$FOOTAGE/.yap_build"

echo "delivered: $OUT/$NAME.mp4"
echo "removed working dir: $FOOTAGE/.yap_build"
ls -la "$OUT"

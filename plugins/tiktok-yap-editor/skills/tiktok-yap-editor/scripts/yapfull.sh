#!/usr/bin/env bash
# Full per-clip pipeline (Mode A): single-pass cut -> gates -> brand captions ->
# CTA contact block -> compose -> gates on the finished file. Creator-agnostic:
# brand comes from brand-config.json via yaplib/brand.py, gates from gates.sh.
#
# Usage:
#   yapfull.sh <workdir> <clauses.json> <out.mp4> "<hook|line2>" "<hookword>" \
#              [brand-config.json] [corrections.json]
#
# Brand resolution (yaplib/brand.py): arg > <workdir>/brand-config.json >
#   <workspace>/brand-config.json > scripts/brand-config.default.json.
#   No skill-root fallback.
# Env:
#   YAP_PLATFORM=tiktok|reels|shorts|linkedin  (default tiktok). Picks that
#       platform's hook animation and length band from brand-config `platforms`;
#       any platform other than tiktok suffixes the output: <out>.<platform>.mp4.
#   YAP_FROM_CUT=1   skip the cut and reuse $WD/full_<base>.mp4 (caption fixes,
#       platform variants, hook variants: seconds instead of minutes)
#   YAP_CUT_BASE=<base>  name of the cut to reuse when <out> differs from it
#       (hook_variant.sh sets this so clip-b.mp4 composes from full_clip.mp4)
#   HOOK_SECS=5.0    how long the burned hook stays up
#   YAP_SCRIPT=<path>  verbatim script for the caption gate (default $WD/<base>_script.txt)
#   plus the gate overrides documented in gates.sh.
# Writes $WD/<final-base>_gates.json (every gate's rc, hook, platform, paths);
# finalize.sh turns that into the edit record.
set -euo pipefail
WD="$1"; CLAUSES="$2"; OUT="$3"; HOOK="$4"; HOOKWORD="${5:-}"; CFG="${6:-}"; CORR="${7:-}"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
source "$SCRIPTS/gates.sh"
mkdir -p "$WD"

eval "$(python3 "$SCRIPTS/yaplib/brand.py" --shell --workdir "$WD" ${CFG:+--brand "$CFG"})"
CFG="$BRANDCFG"
echo "brand: $CFG  platform: $PLATFORM  hook_anim: $HANIM  hook_style: $HSTYLE"

OUTBASE="$(basename "${OUT%.*}")"
CUTBASE="${YAP_CUT_BASE:-$OUTBASE}"
if [ "$PLATFORM" != "tiktok" ]; then OUT="${OUT%.*}.${PLATFORM}.mp4"; fi
FINALBASE="$(basename "${OUT%.*}")"
CUT="$WD/full_${CUTBASE}.mp4"
WORDS="$WD/w_${CUTBASE}.json"
KEEPS="$WD/keeps_full_${CUTBASE}.json"
ASS="$WD/cap_${FINALBASE}.ass"
[ -n "$CORR" ] || CORR="$WD/${CUTBASE}_corrections.json"
[ -f "$CORR" ] || echo '{}' > "$CORR"
# optional per-clip extra overlays (source tags, number count-ups, pips):
# always passed quoted, empty string when absent so paths with spaces are safe
OVRFILE="$WD/${CUTBASE}_overlays.json"; [ -f "$OVRFILE" ] || OVRFILE=""
STUTOK="$WD/${CUTBASE}_stutter_ok.json"
CAPOK="$WD/${CUTBASE}_capqa_ok.json"
SCRIPTFILE="${YAP_SCRIPT:-$WD/${CUTBASE}_script.txt}"
HOOK_SECS="${HOOK_SECS:-5.0}"

gates_init "$WD/${FINALBASE}_gates.json" "$PLATFORM" "$OUT"
gate_meta_json paths "$(python3 -c 'import json,sys; print(json.dumps(dict(zip(sys.argv[1::2], sys.argv[2::2]))))' \
  clauses "$CLAUSES" cut "$CUT" words "$WORDS" keeps "$KEEPS" ass "$ASS" corrections "$CORR" \
  overlays "$OVRFILE" script "$SCRIPTFILE" stutter_ok "$STUTOK" capqa_ok "$CAPOK" brand "$CFG")"

# 0. HOOK WORDS GATE, before any rendering: a hook that needs shrinking to fit
# is a hook the muted viewer cannot read in one fixation.
gate_hook_words "$HOOK" "$HOOKWORD" "$HANIM" "$HSTYLE" "$HOOK_SECS"

# 1. single-pass cut (clean CFR, dead-air, tight tails, anti-stutter crop-alt)
if [ "${YAP_FROM_CUT:-0}" != "1" ]; then
  python3 "$SCRIPTS/yapcut.py" --clauses "$CLAUSES" --workdir "$WD" --out "$CUT" \
    --silence-db -42 --auto-floor --head-trim --padr 0.12 --padl 0.10 --min-gap 0.55 --min-seg 0.45 --d 0.10
else
  [ -f "$CUT" ] || { echo "YAP_FROM_CUT=1 but no cut at $CUT"; exit 2; }
  echo "reusing cut: $CUT"
fi
echo "--- blackdetect (cut) ---"
ffmpeg -nostdin -i "$CUT" -vf "blackdetect=d=0.02:pic_th=0.95" -an -f null - 2>&1 \
  | grep -i black_start || echo "  NO black frames"
DUR=$(python3 "$SCRIPTS/yaplib/media.py" duration "$CUT")
echo "--- dur: $DUR ---"

# 2. word-timed transcript of the cut (reused on YAP_FROM_CUT=1 when present:
# the cut did not change, so neither did its words)
if [ "${YAP_FROM_CUT:-0}" = "1" ] && [ -s "$WORDS" ]; then
  echo "reusing transcript: $WORDS"
else
  bash "$SCRIPTS/transcribe.sh" "$CUT" "$WD/w_${CUTBASE}" --words >/dev/null 2>&1
fi

# 2b. REPETITION GATE: two detectors (transcript + windowed audio scan). MEDIUM
# is a decision, not a note: unlisted MEDIUM fails, list judged ones in $STUTOK.
gate_stutter_restart "$WORDS" "$CUT" "$STUTOK"

# 2c. DEAD-AIR GATE: pauses that survived the cut, transcript-measured.
gate_dead_air "$CUT"

# 3. captions + hook in the brand style, then the CTA contact block
python3 "$SCRIPTS/build_ass.py" --words "$WORDS" --out "$ASS" \
  --preset minimal --font "$CFONT" --caps "$CCASE" --accent none --active-scale 112 \
  --hook-y 430 --hook "$HOOK" --hook-secs "$HOOK_SECS" --hook-anim "$HANIM" --hook-style "$HSTYLE" \
  --hook-spark "$HOOKWORD" --accent-hex "$ACCENT" --overlays "$OVRFILE" --corrections "$CORR"
python3 "$SCRIPTS/cta_block.py" --ass "$ASS" --dur "$DUR" --handle "$HANDLE" --contact "$CONTACT" \
  --font "$HFONT" --accent "$ACCENT" --base "$BASE" --ink "$INK" --lead 9.7

# 3b. CAPTION GATE (scripted runs): no burned word the script never said.
gate_caption "$ASS" "$SCRIPTFILE" "$CFG" "$OVRFILE" "$CAPOK"

# 4. compose: burn captions, loudness to -14 (measured, corrected, verified), clean CFR
bash "$SCRIPTS/compose_ass.sh" "$CUT" "$ASS" "$OUT"

# 4a. burn image PiPs (logos, article/headline screenshots). libass cannot
# composite raster, so build_ass only drew the text overlays; the `pip` entries
# are burned here so they never silently drop. Real screenshots/logos only.
if [ -n "$OVRFILE" ] && [ -f "$OVRFILE" ]; then
  python3 "$SCRIPTS/burn_pips.py" --video "$OUT" --overlays "$OVRFILE" --workdir "$WD" \
    --meta "$ASS.meta.json" --out "$OUT.pips.mp4"
  [ -f "$OUT.pips.mp4" ] && mv "$OUT.pips.mp4" "$OUT"
fi
ffmpeg -nostdin -i "$OUT" -vf "blackdetect=d=0.02:pic_th=0.95" -an -f null - 2>&1 \
  | grep -i black_start || echo "  FINAL: NO black frames"

# 4b-4e. gates on the FINISHED file
gate_seam "$KEEPS" "$OUT"
gate_receipts "$WORDS" "$OVRFILE" "$CORR" "$PIPSTRICT"
gate_retention "$OUT" "$OVRFILE" "$ASS" "$DUR" "$KEEPS"
gate_drift "$OUT"
gate_frame0 "$ASS" "$HOOK"
FDUR=$(python3 "$SCRIPTS/yaplib/media.py" duration "$OUT")
gate_length "$FDUR" "$PLATFORM" "$PLATFORM_LEN_MIN" "$PLATFORM_LEN_MAX"
gate_meta_json duration_s "$FDUR"
gate_meta finished_at "$(date +%Y-%m-%dT%H:%M:%S)"
echo "gates -> $GATES_JSON"
echo "DONE -> $OUT"

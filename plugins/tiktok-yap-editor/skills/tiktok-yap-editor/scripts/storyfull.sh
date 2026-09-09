#!/usr/bin/env bash
# VO-storytelling finisher (Mode B). Takes the picture-locked timeline + the
# voiceover the creator recorded to the guide, lays the VO in (ducking the
# clips' natural sound under it), word-captions the VO, adds the brand hook +
# handle/CTA, mixes the SFX/music bed, composes, and runs the SAME gate ladder
# as yapfull.sh (gates.sh). Brand via yaplib/brand.py, same resolution as Mode A.
#
# Usage:
#   storyfull.sh <workdir> <picture.mp4> <vo.(m4a|wav)|-> <out.mp4> \
#                "<hook|line2>" "<hookword>" [sfx.json] [brand-config] [corrections]
#                [vo_offset_seconds]
#   vo = "-"  -> no external VO; keep the picture's own audio (e.g. talking b-roll).
# Env: YAP_PLATFORM, YAP_FROM_CUT=1 (reuse picvo_<base>.mp4), HOOK_SECS, YAP_SCRIPT,
#      and every gate override in gates.sh. The seam gate applies only when a
#      keeps file exists for this base (a Mode A cut reused as picture).
set -euo pipefail
WD="$1"; PIC="$2"; VO="$3"; OUT="$4"; HOOK="${5:-}"; HOOKWORD="${6:-}"
SFX="${7:-}"; CFG="${8:-}"; CORR="${9:-}"; VOFF="${10:-0}"
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
PV="$WD/picvo_${CUTBASE}.mp4"
WORDS="$WD/w_${CUTBASE}.json"
KEEPS="$WD/keeps_full_${CUTBASE}.json"; [ -f "$KEEPS" ] || KEEPS=""
ASS="$WD/cap_${FINALBASE}.ass"
CAPPED="$WD/capped_${FINALBASE}.mp4"
[ -n "$CORR" ] || CORR="$WD/${CUTBASE}_corrections.json"
[ -f "$CORR" ] || echo '{}' > "$CORR"
OVRFILE="$WD/${CUTBASE}_overlays.json"; [ -f "$OVRFILE" ] || OVRFILE=""
STUTOK="$WD/${CUTBASE}_stutter_ok.json"
CAPOK="$WD/${CUTBASE}_capqa_ok.json"
SCRIPTFILE="${YAP_SCRIPT:-$WD/${CUTBASE}_script.txt}"
HOOK_SECS="${HOOK_SECS:-5.0}"

gates_init "$WD/${FINALBASE}_gates.json" "$PLATFORM" "$OUT"
gate_meta_json paths "$(python3 -c 'import json,sys; print(json.dumps(dict(zip(sys.argv[1::2], sys.argv[2::2]))))' \
  picture "$PIC" vo "$VO" picvo "$PV" words "$WORDS" keeps "$KEEPS" ass "$ASS" corrections "$CORR" \
  overlays "$OVRFILE" script "$SCRIPTFILE" stutter_ok "$STUTOK" capqa_ok "$CAPOK" sfx "$SFX" brand "$CFG")"

# 0. HOOK WORDS GATE
gate_hook_words "$HOOK" "$HOOKWORD" "$HANIM" "$HSTYLE" "$HOOK_SECS"

# 1. lay the VO over the picture (VO leads; clips' natural sound ducks under it).
# A picture with no audio stream (a silent export) takes the VO as-is.
if [ "${YAP_FROM_CUT:-0}" = "1" ] && [ -f "$PV" ]; then
  echo "reusing picture+VO: $PV"
elif [ "$VO" = "-" ] || [ -z "$VO" ]; then
  cp "$PIC" "$PV"
elif python3 "$SCRIPTS/yaplib/media.py" has-audio "$PIC"; then
  ffmpeg -nostdin -y -i "$PIC" -ss "$VOFF" -i "$VO" -filter_complex \
    "[1:a]asplit=2[vo][key];[0:a]volume=-24dB[nat];\
     [nat][key]sidechaincompress=threshold=0.02:ratio=10:attack=15:release=250[duck];\
     [duck][vo]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95[a]" \
    -map 0:v -map "[a]" -c:v copy -c:a aac -ar 48000 -ac 2 -b:a 192k \
    "$PV" -hide_banner -loglevel error
else
  ffmpeg -nostdin -y -i "$PIC" -ss "$VOFF" -i "$VO" -map 0:v -map 1:a -shortest \
    -c:v copy -c:a aac -ar 48000 -ac 2 -b:a 192k "$PV" -hide_banner -loglevel error
fi
DUR=$(python3 "$SCRIPTS/yaplib/media.py" duration "$PV")
echo "--- picture+VO dur: $DUR ---"

# 2. word-timed transcript of the VO track
if [ "${YAP_FROM_CUT:-0}" = "1" ] && [ -s "$WORDS" ]; then
  echo "reusing transcript: $WORDS"
else
  bash "$SCRIPTS/transcribe.sh" "$PV" "$WD/w_${CUTBASE}" --words >/dev/null 2>&1
fi

# 2b/2c. REPETITION + DEAD-AIR GATES on the VO
gate_stutter_restart "$WORDS" "$PV" "$STUTOK"
gate_dead_air "$PV"

# 3. captions + hook in the brand style, then the CTA contact block
python3 "$SCRIPTS/build_ass.py" --words "$WORDS" --out "$ASS" \
  --preset minimal --font "$CFONT" --caps "$CCASE" --accent none --active-scale 112 \
  --hook-y 430 --hook "$HOOK" --hook-secs "$HOOK_SECS" --hook-anim "$HANIM" --hook-style "$HSTYLE" \
  --hook-spark "$HOOKWORD" --accent-hex "$ACCENT" --overlays "$OVRFILE" --corrections "$CORR"
python3 "$SCRIPTS/cta_block.py" --ass "$ASS" --dur "$DUR" --handle "$HANDLE" --contact "$CONTACT" \
  --font "$HFONT" --accent "$ACCENT" --base "$BASE" --ink "$INK" --lead 6.0

# 3b. CAPTION GATE (scripted runs)
gate_caption "$ASS" "$SCRIPTFILE" "$CFG" "$OVRFILE" "$CAPOK"

# 4. compose: burn captions, loudness to -14, clean CFR re-encode
bash "$SCRIPTS/compose_ass.sh" "$PV" "$ASS" "$CAPPED"

# 4a. PiPs, if any
if [ -n "$OVRFILE" ] && [ -f "$OVRFILE" ]; then
  python3 "$SCRIPTS/burn_pips.py" --video "$CAPPED" --overlays "$OVRFILE" --workdir "$WD" \
    --meta "$ASS.meta.json" --out "$CAPPED.pips.mp4"
  [ -f "$CAPPED.pips.mp4" ] && mv "$CAPPED.pips.mp4" "$CAPPED"
fi

# 5. SFX + music bed (optional): mix last so it rides the final audio
if [ -n "$SFX" ] && [ -f "$SFX" ]; then
  python3 "$SCRIPTS/sfxmix.py" --in "$CAPPED" --sfx "$SFX" --out "$OUT"
else
  cp "$CAPPED" "$OUT"
fi

# 6. gates on the FINISHED file (same ladder as Mode A)
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

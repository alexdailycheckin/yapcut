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
#       platform variants, hook variants: seconds instead of minutes). Its transcript is
#       reused only while it was made from this exact cut (w_<base>.json.cut holds the cut's
#       hash): on 2026-10-24 a sped-up re-cut was gated against the old 1x words.
#   YAP_SPEED=1.1    play the cut faster with the pitch kept (setpts + atempo), after the cut
#       and before its transcript; keeps_full_<base>.json is rescaled for the seam gate and the
#       1x cut and keeps stay as full_<base>.1x.mp4 / keeps_full_<base>.1x.json. Remembered in
#       full_<base>.mp4.speed, so a YAP_FROM_CUT=1 rerun picks it up.
#   YAP_CUT_ARGS="--min-gap 0.3 --silence-db -38"  extra yapcut.py flags for this cut (a format
#       that cuts pauses tighter than rules.json); recorded in the gates json
#   YAP_CUT_BASE=<base>  name of the cut to reuse when <out> differs from it
#       (hook_variant.sh sets this so clip-b.mp4 composes from full_clip.mp4)
#   HOOK_SECS=5.0    how long the burned hook stays up
#   YAP_SCRIPT=<path>  verbatim script for the caption gate (default $WD/<base>_script.txt);
#       missing, the caption gate fails unless YAP_UNSCRIPTED=1
#   plus the gate overrides documented in gates.sh.
#
# THE ORDER (3.9.0). Everything a person has to rule on comes first and at once: the hook's
# length, the repeats the transcript shows, the caption words the script never said. The
# build stops after those three with every decision printed, so one rerun carries them all
# (on 2026-10-25 the Anthropic episode took six). The slow audio scans, the dead-air gate and
# the compose run after, and each one is cached on the cut: a rerun with YAP_FROM_CUT=1 whose
# captions did not change skips the compose and the file gates read their caches, so it is
# seconds, not minutes.
#
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
HOOK_SECS="${HOOK_SECS:-$(python3 "$SCRIPTS/yaplib/rules.py" get hook.seconds)}"

gates_init "$WD/${FINALBASE}_gates.json" "$PLATFORM" "$OUT"
gate_meta_json paths "$(python3 -c 'import json,sys; print(json.dumps(dict(zip(sys.argv[1::2], sys.argv[2::2]))))' \
  clauses "$CLAUSES" cut "$CUT" words "$WORDS" keeps "$KEEPS" ass "$ASS" corrections "$CORR" \
  overlays "$OVRFILE" script "$SCRIPTFILE" stutter_ok "$STUTOK" capqa_ok "$CAPOK" brand "$CFG")"

# every decision gate below is deferred: the build stops after the last of them (gates_settle)
gates_defer

# 0. HOOK WORDS GATE, before any rendering: a hook that needs shrinking to fit
# is a hook the muted viewer cannot read in one fixation.
gate_hook_words "$HOOK" "$HOOKWORD" "$HANIM" "$HSTYLE" "$HOOK_SECS"

# 1. single-pass cut (clean CFR, dead-air, tight tails, anti-stutter crop-alt)
FRESH_CUT=0
if [ "${YAP_FROM_CUT:-0}" != "1" ]; then
  # every cut number comes from rules.json (cut.*); YAP_CUT_ARGS is the per-format exception
  # shellcheck disable=SC2086
  python3 "$SCRIPTS/yapcut.py" --clauses "$CLAUSES" --workdir "$WD" --out "$CUT" ${YAP_CUT_ARGS:-}
  FRESH_CUT=1
  rm -f "$CUT.speed"
  if [ -n "${YAP_SPEED:-}" ] && [ "${YAP_SPEED}" != "1" ]; then
    mv "$CUT" "${CUT%.mp4}.1x.mp4"; cp "$KEEPS" "${KEEPS%.json}.1x.json"
    ffmpeg -nostdin -y -v error -i "${CUT%.mp4}.1x.mp4" \
      -filter_complex "[0:v]setpts=PTS/${YAP_SPEED},fps=30[v];[0:a]atempo=${YAP_SPEED}[a]" \
      -map "[v]" -map "[a]" -c:v libx264 -crf 14 -preset medium -pix_fmt yuv420p \
      -color_primaries bt709 -color_trc bt709 -colorspace bt709 -c:a aac -b:a 256k \
      -movflags +faststart "$CUT"
    python3 - "$KEEPS" "$YAP_SPEED" <<'PY2'
import json, sys
p, s = sys.argv[1], float(sys.argv[2]); k = json.load(open(p))
for x in k:   # source a, and b = a + the keep's length in the faster cut (what seam_qa adds up)
    x["b"] = round(x["a"] + (x["b"] - x["a"]) / s, 3)
json.dump(k, open(p, "w"), indent=1)
PY2
    echo "$YAP_SPEED" > "$CUT.speed"
    echo "speed: ${YAP_SPEED}x (1x cut kept as $(basename "${CUT%.mp4}.1x.mp4"))"
  fi
else
  [ -f "$CUT" ] || { echo "YAP_FROM_CUT=1 but no cut at $CUT"; exit 2; }
  echo "reusing cut: $CUT"
  [ -f "$CUT.speed" ] && export YAP_SPEED="$(cat "$CUT.speed")"
fi
export YAP_SPEED="${YAP_SPEED:-1}"
gate_meta_json cut "$(python3 -c 'import json,sys; print(json.dumps({"speed": float(sys.argv[1]), "args": sys.argv[2]}))' "$YAP_SPEED" "${YAP_CUT_ARGS:-}")"
[ "$FRESH_CUT" = 1 ] && black_check "$CUT" "cut"
DUR=$(python3 "$SCRIPTS/yaplib/media.py" duration "$CUT")
echo "--- dur: $DUR ---"

# 2. word-timed transcript of the cut, reused only while it was made from this exact cut
CUTSIG="$(python3 -c 'import hashlib,sys
h = hashlib.sha1()
with open(sys.argv[1], "rb") as f:
    for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
print(h.hexdigest())' "$CUT")"
if [ "${YAP_FROM_CUT:-0}" = "1" ] && [ -s "$WORDS" ] && [ "$(cat "$WORDS.cut" 2>/dev/null)" = "$CUTSIG" ]; then
  echo "reusing transcript: $WORDS"
else
  [ -s "$WORDS" ] && [ "${YAP_FROM_CUT:-0}" = "1" ] && echo "transcript is from another cut: re-transcribing"
  bash "$SCRIPTS/transcribe.sh" "$CUT" "$WD/w_${CUTBASE}" --words >/dev/null 2>&1
  echo "$CUTSIG" > "$WORDS.cut"
fi

# 2a. caption words from the script: its case, punctuation and spelling for every word the
# script also says (script_fix.py; hand entries in the corrections file always win)
if [ -f "$SCRIPTFILE" ] && [ "${YAP_UNSCRIPTED:-0}" != "1" ]; then
  OPFREE=()
  OPJ="$WD/${CUTBASE}_opinion.json"
  if [ -f "$OPJ" ]; then
    OPT=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("start",""))' "$OPJ" 2>/dev/null || true)
    [ -n "$OPT" ] && OPFREE=(--free-from "$OPT")
  fi
  python3 "$SCRIPTS/script_fix.py" --words "$WORDS" --script "$SCRIPTFILE" --corrections "$CORR" \
    ${OPFREE[@]+"${OPFREE[@]}"}
fi

# 2b. REPETITION GATE, the transcript half: MEDIUM is a decision, not a note: an unlisted
# MEDIUM fails, list judged ones in $STUTOK. The audio half runs after the decisions.
gate_stutter_transcript "$WORDS" "$STUTOK" "$SCRIPTFILE"

# 3. captions + hook in the brand style, then the CTA contact block
python3 "$SCRIPTS/build_ass.py" --words "$WORDS" --out "$ASS" \
  --preset minimal --font "$CFONT" --caps "$CCASE" --accent none \
  --hook "$HOOK" --hook-secs "$HOOK_SECS" --hook-anim "$HANIM" --hook-style "$HSTYLE" \
  --hook-spark "$HOOKWORD" --accent-hex "$ACCENT" --overlays "$OVRFILE" --corrections "$CORR"
gate_hook_drawn "$ASS.meta.json"
python3 "$SCRIPTS/cta_block.py" --ass "$ASS" --dur "$DUR" --handle "$HANDLE" --contact "$CONTACT" \
  --font "$HFONT" --accent "$ACCENT" --base "$BASE" --ink "$INK" --lead 9.7

# 3b. CAPTION GATE (scripted runs): no burned word the script never said.
gate_caption "$ASS" "$SCRIPTFILE" "$CFG" "$OVRFILE" "$CAPOK" "$WORDS" "$CORR"

# every decision is on the screen: stop here if any gate above went red
gates_settle

# 2c. REPETITION GATE, the audio half (cached on the cut and on the takes' windows)
gate_stutter_audio "$WORDS" "$CUT" "$STUTOK" "$KEEPS" "$SCRIPTFILE"

# 2d. DEAD-AIR GATE: pauses that survived the cut, measured by the microphone or the words.
gate_dead_air "$CUT" "$WORDS"

# 4. compose: burn captions, loudness to -14 (measured, corrected, verified), clean CFR.
# Skipped when the cut, the captions and the overlays are the ones the file was made from.
SIG="$(compose_sig "$CUTSIG" "$ASS" "$OVRFILE")"
if [ -f "$OUT" ] && [ "$(cat "$OUT.sig" 2>/dev/null)" = "$SIG" ]; then
  echo "reusing composed file: $OUT (cut, captions and overlays unchanged)"
  FRESH_OUT=0
else
  rm -f "$OUT.sig"
  bash "$SCRIPTS/compose_ass.sh" "$CUT" "$ASS" "$OUT"
  # 4a. burn image PiPs (logos, article/headline screenshots). libass cannot
  # composite raster, so build_ass only drew the text overlays; the `pip` entries
  # are burned here so they never silently drop. Real screenshots/logos only.
  if [ -n "$OVRFILE" ] && [ -f "$OVRFILE" ]; then
    python3 "$SCRIPTS/burn_pips.py" --video "$OUT" --overlays "$OVRFILE" --workdir "$WD" \
      --meta "$ASS.meta.json" --out "$OUT.pips.mp4"
    [ -f "$OUT.pips.mp4" ] && mv "$OUT.pips.mp4" "$OUT"
  fi
  echo "$SIG" > "$OUT.sig"
  FRESH_OUT=1
fi
[ "$FRESH_OUT" = 1 ] && black_check "$OUT" "final"

# 4b-4e. gates on the FINISHED file
gate_seam "$KEEPS" "$OUT"
gate_receipts "$WORDS" "$OVRFILE" "$CORR" "$PIPSTRICT"
gate_retention "$OUT" "$OVRFILE" "$ASS" "$DUR" "$KEEPS" "$WD/scenes_${FINALBASE}.json"
gate_drift "$OUT"
gate_frame0 "$ASS" "$HOOK"
FDUR=$(python3 "$SCRIPTS/yaplib/media.py" duration "$OUT")
gate_length "$FDUR" "$PLATFORM" "$PLATFORM_LEN_MIN" "$PLATFORM_LEN_MAX"
gate_meta_json duration_s "$FDUR"
gate_meta finished_at "$(date +%Y-%m-%dT%H:%M:%S)"
echo "gates -> $GATES_JSON"
echo "DONE -> $OUT"

#!/usr/bin/env bash
# gates.sh: the gate ladder, sourced by yapfull.sh (Mode A) and storyfull.sh
# (Mode B) so both orchestrators run the SAME checks with the SAME exit-code
# contract. Before this file storyfull was a 99-line fork with zero gates.
#
# Contract 1 (2026-09-09): every gate returns 0 pass, 1 warnings only, 2 FAIL.
# The orchestrator fails the build on 2 only; 1 prints and continues. Every
# gate's rc is recorded in "$GATES_JSON" ({"gates": {name: rc}}), null when a
# gate does not apply to this build. finalize.sh copies that block into the
# edit record, so a shipped file always carries the results it passed on.
#
# Override env vars are unchanged from the old yapfull.sh:
#   YAP_ALLOW_LONG_HOOK=1  hook over 9 words is a warning, not a fail
#   YAP_ALLOW_STUTTER=1    a deliberate rhetorical repeat
#   YAP_ALLOW_GAPS="6.9,41.2" | =1   permit those beats / skip the dead-air gate
#   YAP_ALLOW_CAPTIONS=1   skip the caption garble gate
#   YAP_ALLOW_SEAM=1       override seam holes (justify with seam_evidence.py first)
#   YAP_ALLOW_STATIC=1     override the retention gate (deliberate slow burn)
#   YAP_PIP_STRICT=1       receipts gate fatal regardless of brand-config
# An override never records 0: the gate it silenced is recorded as 1 (warning),
# because the build shipped without that check passing on its own.
#
# Requires from the caller: SCRIPTS (this directory). Call gates_init first.

GATE_NAMES="hook_words stutter_restart dead_air caption seam receipts retention drift frame0 length"

gates_init() {                       # gates_init <gates_json> <platform> <out>
  GATES_JSON="$1"
  python3 - "$GATES_JSON" "$2" "$3" <<'PY'
import json, sys, datetime
p, plat, out = sys.argv[1:4]
json.dump({"gates": {}, "platform": plat, "out": out,
           "started_at": datetime.datetime.now().isoformat(timespec="seconds")},
          open(p, "w"), indent=1)
PY
}

gate_record() {                      # gate_record <name> <rc|null>
  python3 - "$GATES_JSON" "$1" "$2" <<'PY'
import json, sys
p, name, rc = sys.argv[1:4]
d = json.load(open(p))
d.setdefault("gates", {})[name] = None if rc == "null" else int(rc)
json.dump(d, open(p, "w"), indent=1)
PY
}

gate_meta() {                        # gate_meta <key> <string value>
  python3 - "$GATES_JSON" "$1" "$2" <<'PY'
import json, sys
p, k, v = sys.argv[1:4]
d = json.load(open(p)); d[k] = v; json.dump(d, open(p, "w"), indent=1)
PY
}

gate_meta_json() {                   # gate_meta_json <key> '<json value>'
  python3 - "$GATES_JSON" "$1" "$2" <<'PY'
import json, sys
p, k, v = sys.argv[1:4]
d = json.load(open(p)); d[k] = json.loads(v); json.dump(d, open(p, "w"), indent=1)
PY
}

# gate_finish <name> <rc> "<fail message>": records, fails the build on 2.
gate_finish() {
  local name="$1" rc="$2" msg="${3:-}"
  gate_record "$name" "$rc"
  case "$rc" in
    2) echo "GATE $name FAILED (rc 2). ${msg}"; echo "  gates so far: $GATES_JSON"; exit 2 ;;
    1) echo "gate $name: WARN (rc 1), continuing" ;;
    0) echo "gate $name: ok" ;;
    null) echo "gate $name: not applicable" ;;
  esac
}

# --- hook words: count BEFORE the cut, all lines. >9 fails, >7 warns. ---------
gate_hook_words() {                  # gate_hook_words "<hook|line2>" "<spark>" <anim> <style> <secs>
  local hook="$1" spark="${2:-}" anim="${3:-none}" style="${4:-outline}" secs="${5:-5.0}"
  local n rc=0
  n=$(python3 -c 'import sys; print(len(" ".join(sys.argv[1].split("|")).split()))' "$hook")
  echo "--- gate hook_words: $n word(s) ---"
  if [ "$n" -gt 9 ]; then
    if [ "${YAP_ALLOW_LONG_HOOK:-0}" = "1" ]; then
      echo "  hook is $n words (limit 9), allowed by YAP_ALLOW_LONG_HOOK=1"; rc=1
    else
      echo "  hook is $n words. The burned hook is read in one fixation by a muted"
      echo "  viewer; the aug 24 batch ran 6 to 8 words, aug 30 ran 9 to 13 and the"
      echo "  editor shrank them to fit. Cut it to 7, or YAP_ALLOW_LONG_HOOK=1."
      rc=2
    fi
  elif [ "$n" -gt 7 ]; then
    echo "  hook is $n words: over the 7-word target, under the 9-word limit"; rc=1
  fi
  python3 - "$GATES_JSON" "$hook" "$n" "$spark" "$anim" "$style" "$secs" <<'PY'
import json, sys
p, hook, n, spark, anim, style, secs = sys.argv[1:8]
d = json.load(open(p))
d["hook"] = {"text": hook, "words": int(n), "anim": anim, "style": style,
             "spark": spark, "secs": float(secs)}
json.dump(d, open(p, "w"), indent=1)
PY
  gate_finish hook_words "$rc" "Shorten the hook (7 words is the target)."
}

# --- repetition: transcript detector AND windowed audio scan -------------------
gate_stutter_restart() {             # gate_stutter_restart <words.json> <video> <accept-file>
  local words="$1" video="$2" accept="$3" r1=0 r2=0 rc=0
  echo "--- gate stutter_restart ---"
  [ -f "$accept" ] || echo '[]' > "$accept"
  python3 "$SCRIPTS/stutter_check.py" --words "$words" --accept-file "$accept" || r1=$?
  python3 "$SCRIPTS/restart_scan.py" --video "$video" --accept-file "$accept" || r2=$?
  rc=$(( r1 > r2 ? r1 : r2 ))
  if [ "$rc" -eq 2 ] && [ "${YAP_ALLOW_STUTTER:-0}" = "1" ]; then
    echo "  repetition findings overridden by YAP_ALLOW_STUTTER=1"; rc=1
  fi
  gate_finish stutter_restart "$rc" "A real restart: cut it via the clause plan. A deliberate repeat: add its printed key to $(basename "$accept")."
}

# --- dead air: pauses that survived the cut (transcript-measured) --------------
gate_dead_air() {                    # gate_dead_air <video>
  local video="$1" rc=0
  echo "--- gate dead_air ---"
  if [ "${YAP_ALLOW_GAPS:-0}" = "1" ]; then
    echo "  skipped by YAP_ALLOW_GAPS=1"; rc=1
  else
    python3 "$SCRIPTS/gap_check.py" --video "$video" --allow "${YAP_ALLOW_GAPS:-}" || rc=$?
  fi
  gate_finish dead_air "$rc" "The cut is not tight: measure the floor, raise --silence-db, re-cut (SKILL.md 6b)."
}

# --- caption garble: burned words vs the script ---------------------------------
gate_caption() {                     # gate_caption <cap.ass> <script.txt> <brand.json> <overlays|""> <accept-file>
  local ass="$1" script="$2" brand="$3" ovr="$4" accept="$5" rc=0
  echo "--- gate caption ---"
  if [ ! -f "$script" ]; then
    echo "  SKIPPED: no script at $script (unscripted yap). Scripted runs save the verbatim script there."; rc=1
  elif [ "${YAP_ALLOW_CAPTIONS:-0}" = "1" ]; then
    echo "  skipped by YAP_ALLOW_CAPTIONS=1"; rc=1
  else
    python3 "$SCRIPTS/caption_qa.py" --ass "$ass" --script "$script" --brand "$brand" \
      --overlays "$ovr" --accept-file "$accept" || rc=$?
  fi
  gate_finish caption "$rc" "Garbles -> $(basename "${accept%_capqa_ok.json}")_corrections.json + YAP_FROM_CUT=1; ad-libs -> $(basename "$accept")."
}

# --- seam: splice holes and clicks at every join -------------------------------
gate_seam() {                        # gate_seam <keeps.json|""> <video>
  local keeps="$1" video="$2" rc=0
  echo "--- gate seam ---"
  if [ -z "$keeps" ] || [ ! -f "$keeps" ]; then
    echo "  not applicable: no keeps file (no audio joins in this build)"
    gate_finish seam null; return 0
  fi
  python3 "$SCRIPTS/seam_qa.py" --keeps "$keeps" --video "$video" || rc=$?
  if [ "$rc" -eq 2 ]; then
    if [ "${YAP_ALLOW_SEAM:-0}" = "1" ]; then
      echo "  seam failures overridden by YAP_ALLOW_SEAM=1 (justify with seam_evidence.py: short runs, no clicks)"; rc=1
    else
      echo "  If this mic gates to silence, measure first:"
      echo "    python3 $SCRIPTS/seam_evidence.py \"$video\" \"$keeps\""
    fi
  fi
  gate_finish seam "$rc" "Splice hole at a join."
}

# --- receipts: every spoken brand/stat wants something on screen ---------------
gate_receipts() {                    # gate_receipts <words.json> <overlays|""> <corrections> <strict 0|1>
  local words="$1" ovr="$2" corr="$3" strict="$4" rc=0
  echo "--- gate receipts (strict=$strict) ---"
  [ "${YAP_PIP_STRICT:-0}" = "1" ] && strict=1
  if [ "$strict" = "1" ]; then
    python3 "$SCRIPTS/pip_coverage.py" --words "$words" --overlays "$ovr" --corrections "$corr" --strict || rc=$?
  else
    python3 "$SCRIPTS/pip_coverage.py" --words "$words" --overlays "$ovr" --corrections "$corr" || rc=$?
  fi
  gate_finish receipts "$rc" "Add evidence PiPs/counters at the MISS timestamps."
}

# --- retention: re-hook + pattern-interrupt budget, joins do not count ---------
gate_retention() {                   # gate_retention <video> <overlays|""> <cap.ass> <duration> <keeps|"">
  local video="$1" ovr="$2" ass="$3" dur="$4" keeps="${5:-}" rc=0 hookend maxgap
  hookend=$(python3 "$SCRIPTS/yaplib/ass.py" hook-end "$ass" 2>/dev/null || echo 2.5)
  # 5s budget for short form, 6s once the video is 60s+ (a longer video may breathe)
  maxgap=$(python3 -c 'import sys; print("6.0" if float(sys.argv[1]) >= 60 else "5.0")' "$dur")
  echo "--- gate retention (hook-end ${hookend}s, max-gap ${maxgap}s) ---"
  if [ "${YAP_ALLOW_STATIC:-0}" = "1" ]; then
    echo "  skipped by YAP_ALLOW_STATIC=1 (deliberate slow burn)"; rc=1
  else
    local args=(--video "$video" --hook-end "$hookend" --max-gap "$maxgap")
    [ -n "$ovr" ] && [ -f "$ovr" ] && args+=(--overlays "$ovr")
    [ -n "$keeps" ] && [ -f "$keeps" ] && args+=(--keeps "$keeps")
    python3 "$SCRIPTS/retention_check.py" "${args[@]}" || rc=$?
  fi
  gate_finish retention "$rc" "Fill the static stretches (PiP/counter/punch-in)."
}

# --- drift: the picture and the voice must be the same length ------------------
gate_drift() {                       # gate_drift <video>
  local rc=0
  echo "--- gate drift ---"
  python3 "$SCRIPTS/yaplib/media.py" drift "$1" || rc=$?
  gate_finish drift "$rc" "Never retime the final; fix the cut."
}

# --- frame zero: the full first hook line is on screen at 0.00 -----------------
gate_frame0() {                      # gate_frame0 <cap.ass> "<hook|line2>"
  local rc=0
  echo "--- gate frame0 ---"
  python3 "$SCRIPTS/yaplib/ass.py" frame0 "$1" "$2" || rc=$?
  if [ "$rc" -eq 3 ]; then gate_finish frame0 null; return 0; fi
  gate_finish frame0 "$rc" "The muted feed judges frame zero on the burned hook."
}

# --- length: inside the platform's band, else a warning ------------------------
gate_length() {                      # gate_length <duration> <platform> <min> <max>
  local dur="$1" plat="$2" lo="$3" hi="$4" rc=0
  echo "--- gate length (${plat}: ${lo}-${hi}s) ---"
  rc=$(python3 -c 'import sys
d, lo, hi = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
if d < lo: print(f"  {d:.1f}s is under the {sys.argv[4]} band ({lo:.0f}-{hi:.0f}s)"); print(1)
elif d > hi: print(f"  {d:.1f}s is over the {sys.argv[4]} band ({lo:.0f}-{hi:.0f}s)"); print(1)
else: print(f"  {d:.1f}s inside the {sys.argv[4]} band"); print(0)' "$dur" "$lo" "$hi" "$plat" | tee /dev/stderr | tail -1)
  gate_finish length "$rc"
}

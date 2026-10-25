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
# DECISIONS AT ONCE (3.9.0). The gates that ask a person for a ruling (the hook's length,
# a repeat the transcript shows, a caption word the script never said) all read the
# transcript, which exists a minute into the build. Until 3.9.0 the first of them to fail
# stopped the build, and the next failure was found on the rerun: on 2026-10-25 the
# Anthropic episode went through six runs for four decisions. Between gates_defer and
# gates_settle a failing gate is recorded and printed, and the build goes on to the next
# decision gate; gates_settle then exits 2 with every decision listed. The slow audio
# scans and the compose come after, so a rerun with the decisions in costs nothing twice.
#
# Override env vars are unchanged from the old yapfull.sh:
#   YAP_ALLOW_LONG_HOOK=1  hook over 9 words is a warning, not a fail
#   YAP_ALLOW_STUTTER=1    a deliberate rhetorical repeat
#   YAP_ALLOW_GAPS="6.9,41.2" | =1   permit those beats / skip the dead-air gate
#   YAP_ALLOW_CAPTIONS=1   skip the caption garble gate
#   YAP_UNSCRIPTED=1       the take had no script: the caption gate has nothing to diff (without it
#                          a missing <out>_script.txt fails the gate)
#   YAP_ALLOW_SEAM=1       override seam holes (justify with seam_evidence.py first)
#   YAP_ALLOW_STATIC=1     override the retention gate (deliberate slow burn)
#   YAP_PIP_STRICT=1       receipts gate fatal regardless of brand-config
# An override never records 0: the gate it silenced is recorded as 1 (warning),
# because the build shipped without that check passing on its own.
#
# Requires from the caller: SCRIPTS (this directory). Call gates_init first.

GATE_NAMES="hook_words stutter_restart dead_air caption seam receipts retention drift frame0 length"
GATE_DEFER=0
GATES_DEFERRED=""

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

gate_meta_get() {                    # gate_meta_get <dotted.key> -> prints the value ("" when missing)
  python3 - "$GATES_JSON" "$1" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
for k in sys.argv[2].split("."):
    d = d.get(k) if isinstance(d, dict) else None
print("" if d is None else d)
PY
}

# gate_hook_drawn <cap.ass.meta.json>: the hook style build_ass actually drew. gate_hook_words
# records the brand's style before the render, and a minimal hook whose later line is longer
# than line 1 is drawn as outline, so the edit record takes the drawn one from the sidecar.
gate_hook_drawn() {
  python3 - "$GATES_JSON" "$1" <<'PY'
import json, os, sys
p, m = sys.argv[1:3]
st = json.load(open(m)).get("hook_style") if os.path.isfile(m) else None
d = json.load(open(p))
if st and d.get("hook") and d["hook"].get("style") != st:
    d["hook"]["style_asked"] = d["hook"].get("style"); d["hook"]["style"] = st
    json.dump(d, open(p, "w"), indent=1)
PY
}

# gates_defer / gates_settle: between them a red gate is recorded and the ladder goes on, so
# every decision is on the screen at once; settle exits 2 if any gate went red.
gates_defer() { GATE_DEFER=1; GATES_DEFERRED=""; }
gates_settle() {
  GATE_DEFER=0
  if [ -n "$GATES_DEFERRED" ]; then
    echo "DECISIONS NEEDED (${GATES_DEFERRED// /, }): every ruling the build needs is printed above."
    echo "  Make them all, then rerun once (YAP_FROM_CUT=1 reuses the cut and its transcript; the scans and the compose are cached)."
    echo "  gates so far: $GATES_JSON"
    exit 2
  fi
}

# gate_finish <name> <rc> "<fail message>": records, fails the build on 2 (or defers it).
gate_finish() {
  local name="$1" rc="$2" msg="${3:-}"
  gate_record "$name" "$rc"
  case "$rc" in
    2) echo "GATE $name FAILED (rc 2). ${msg}"
       if [ "$GATE_DEFER" = "1" ]; then
         GATES_DEFERRED="${GATES_DEFERRED:+$GATES_DEFERRED }$name"
         echo "  (the other decision gates run first; the build stops after them)"
       else
         echo "  gates so far: $GATES_JSON"; exit 2
       fi ;;
    1) echo "gate $name: WARN (rc 1), continuing" ;;
    0) echo "gate $name: ok" ;;
    null) echo "gate $name: not applicable" ;;
  esac
}

# --- hook words: count BEFORE the cut, all lines. >9 fails, >7 warns. ---------
gate_hook_words() {                  # gate_hook_words "<hook|line2>" "<spark>" <anim> <style> <secs>
  local hook="$1" spark="${2:-}" anim="${3:-none}" style="${4:-outline}" secs="${5:-5.0}"
  local n rc=0 max warn
  max=$(python3 "$SCRIPTS/yaplib/rules.py" get hook.max_words)
  warn=$(python3 "$SCRIPTS/yaplib/rules.py" get hook.warn_words)
  n=$(python3 -c 'import sys; print(len(" ".join(sys.argv[1].split("|")).split()))' "$hook")
  echo "--- gate hook_words: $n word(s) ---"
  if [ "$n" -gt "$max" ]; then
    if [ "${YAP_ALLOW_LONG_HOOK:-0}" = "1" ]; then
      echo "  hook is $n words (limit $max), allowed by YAP_ALLOW_LONG_HOOK=1"; rc=1
    else
      echo "  hook is $n words. The burned hook is read in one fixation by a muted"
      echo "  viewer; the aug 24 batch ran 6 to 8 words, aug 30 ran 9 to 13 and the"
      echo "  editor shrank them to fit. Cut it to $warn, or YAP_ALLOW_LONG_HOOK=1."
      rc=2
    fi
  elif [ "$n" -gt "$warn" ]; then
    echo "  hook is $n words: over the $warn-word target, under the $max-word limit"; rc=1
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

# --- repetition: transcript detector first, the two audio scans after the decisions --------
# Three detectors, one gate, one accept-file. stutter_check.py reads the transcript (seconds);
# restart_scan.py reads 6s windows and xwin_scan.py reads 1.1s and 1.6s windows around what
# the audio itself says twice (minutes). 3.8.0: all three read the script (<out>_script.txt)
# and settle a repeat the script says itself; the accept-file takes {"key", "why"} entries that
# clear a HIGH, so one deliberate callback no longer needs YAP_ALLOW_STUTTER=1 (which silences
# all three). 3.9.0: the transcript half runs with the other decision gates and the audio half
# after them, so a repeat and a caption garble are both on the screen before the first rerun.
_stutter_args() {                    # sets SARGS (script, opinion slot) for the detectors
  local accept="$1" script="${2:-}" op t
  SARGS=()
  op="${accept%_stutter_ok.json}_opinion.json"
  if [ -f "$op" ]; then
    t=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("start",""))' "$op" 2>/dev/null || true)
    [ -n "$t" ] && SARGS=(--free-from "$t")
  fi
  [ -n "$script" ] && [ -f "$script" ] && SARGS=(--script "$script" ${SARGS[@]+"${SARGS[@]}"})
}

gate_stutter_transcript() {          # gate_stutter_transcript <words.json> <accept-file> [script.txt]
  local words="$1" accept="$2" script="${3:-}" r1=0
  echo "--- gate stutter_restart (the transcript) ---"
  [ -f "$accept" ] || echo '[]' > "$accept"
  _stutter_args "$accept" "$script"
  python3 "$SCRIPTS/stutter_check.py" --words "$words" --accept-file "$accept" ${SARGS[@]+"${SARGS[@]}"} || r1=$?
  gate_meta_json repetition "{\"stutter_check\": $r1}"
  if [ "$r1" -eq 2 ] && [ "${YAP_ALLOW_STUTTER:-0}" = "1" ]; then
    echo "  repetition findings overridden by YAP_ALLOW_STUTTER=1"; r1=1
  fi
  gate_finish stutter_restart "$r1" "A real restart: cut it via the clause plan. A deliberate repeat: add its printed key to $(basename "$accept") ({\"key\": ..., \"why\": ...} for a HIGH)."
}

gate_stutter_audio() {               # gate_stutter_audio <words.json> <video> <accept-file> [keeps.json] [script.txt]
  local words="$1" video="$2" accept="$3" keeps="${4:-}" script="${5:-}" r1 r2=0 r3=0 rc=0 base wd
  local kargs=()
  echo "--- gate stutter_restart (the audio) ---"
  [ -f "$accept" ] || echo '[]' > "$accept"
  base="$(basename "${accept%_stutter_ok.json}")"; wd="$(dirname "$accept")"
  _stutter_args "$accept" "$script"
  r1="$(gate_meta_get repetition.stutter_check)"; r1="${r1:-0}"
  [ -n "$keeps" ] && [ -f "$keeps" ] && kargs=(--keeps "$keeps" --speed "${YAP_SPEED:-1}" --workdir "$wd")
  python3 "$SCRIPTS/restart_scan.py" --video "$video" --accept-file "$accept" \
    --cache "$wd/restart_${base}.json" ${SARGS[@]+"${SARGS[@]}"} || r2=$?
  # yapbatch prescans the take windows in a background lane; wait for this video's, so the two
  # never decode the same windows (the marker appears even when the prescan failed)
  if [ -n "${YAP_XWIN_WAIT:-}" ] && [ ! -e "$YAP_XWIN_WAIT" ]; then
    echo "  waiting for the take prescan ($(basename "$YAP_XWIN_WAIT"))"
    local waited=0
    while [ ! -e "$YAP_XWIN_WAIT" ] && [ "$waited" -lt 3600 ]; do sleep 2; waited=$((waited + 2)); done
  fi
  python3 "$SCRIPTS/xwin_scan.py" --video "$video" --words "$words" --accept-file "$accept" \
    --cache "$wd/xwin_${base}.json" --store-dir "$wd/xwin_src" \
    ${kargs[@]+"${kargs[@]}"} ${SARGS[@]+"${SARGS[@]}"} || r3=$?
  gate_meta_json repetition "{\"stutter_check\": $r1, \"restart_scan\": $r2, \"xwin_scan\": $r3}"
  rc=$(( r1 > r2 ? r1 : r2 )); rc=$(( r3 > rc ? r3 : rc ))
  if [ "$rc" -eq 2 ] && [ "${YAP_ALLOW_STUTTER:-0}" = "1" ]; then
    echo "  repetition findings overridden by YAP_ALLOW_STUTTER=1"; rc=1
  fi
  gate_finish stutter_restart "$rc" "A real restart: cut it via the clause plan. A deliberate repeat: add its printed key to $(basename "$accept") ({\"key\": ..., \"why\": ...} for a HIGH)."
}

gate_stutter_restart() {             # the 3.8.x entry point: both halves in one go
  gate_stutter_transcript "$1" "$3" "${5:-}"
  gate_stutter_audio "$1" "$2" "$3" "${4:-}" "${5:-}"
}

# --- dead air: pauses that survived the cut (transcript-measured) --------------
gate_dead_air() {                    # gate_dead_air <video> [aligned words.json]
  local video="$1" aligned="${2:-}" rc=0 al=()
  echo "--- gate dead_air ---"
  [ -n "$aligned" ] && [ -f "$aligned" ] && al=(--aligned "$aligned")
  if [ "${YAP_ALLOW_GAPS:-0}" = "1" ]; then
    echo "  skipped by YAP_ALLOW_GAPS=1"; rc=1
  else
    python3 "$SCRIPTS/gap_check.py" --video "$video" --allow "${YAP_ALLOW_GAPS:-}" ${al[@]+"${al[@]}"} || rc=$?
  fi
  gate_finish dead_air "$rc" "The cut is not tight: read the cut log's word gaps line, then measure the floor, raise --silence-db, re-cut (SKILL.md, Noisy takes)."
}

# --- caption garble: burned words vs the script ---------------------------------
gate_caption() {                     # gate_caption <cap.ass> <script.txt> <brand.json> <overlays|""> <accept-file> [words.json] [corrections.json]
  local ass="$1" script="$2" brand="$3" ovr="$4" accept="$5" words="${6:-}" corr="${7:-}" rc=0 wargs=()
  echo "--- gate caption ---"
  [ -n "$words" ] && [ -f "$words" ] && wargs=(--words "$words")
  [ -n "$corr" ] && [ -f "$corr" ] && wargs+=(--corrections "$corr")
  if [ ! -f "$script" ]; then
    # a missing script used to be read as "unscripted" and passed with a warning: on 2026-10-11 seven
    # scripted videos shipped unchecked that way. Unscripted is now something the run says, not a guess.
    if [ "${YAP_UNSCRIPTED:-0}" = "1" ]; then
      echo "  skipped: YAP_UNSCRIPTED=1 (no script exists for this take)"; rc=1
    else
      echo "  no script at $script. Save the verbatim script there (the words read on camera, no labels),"
      echo "  or set YAP_UNSCRIPTED=1 when there is no script."; rc=2
    fi
  elif [ "${YAP_ALLOW_CAPTIONS:-0}" = "1" ]; then
    echo "  skipped by YAP_ALLOW_CAPTIONS=1"; rc=1
  else
    # the opinion slot (3.6.0): <out>_opinion.json {"start": seconds in the cut} marks where the
    # creator's unscripted take begins; captions from there on are theirs and are not diffed
    local op="${accept%_capqa_ok.json}_opinion.json" free=()
    if [ -f "$op" ]; then
      local t; t=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("start",""))' "$op" 2>/dev/null || true)
      [ -n "$t" ] && free=(--free-from "$t") && echo "  opinion slot from ${t}s: the take is unscripted, not diffed"
    fi
    python3 "$SCRIPTS/caption_qa.py" --ass "$ass" --script "$script" --brand "$brand" \
      --overlays "$ovr" --accept-file "$accept" ${free[@]+"${free[@]}"} ${wargs[@]+"${wargs[@]}"} || rc=$?
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
gate_retention() {                   # gate_retention <video> <overlays|""> <cap.ass> <duration> <keeps|""> [scene-cache.json]
  local video="$1" ovr="$2" ass="$3" dur="$4" keeps="${5:-}" cache="${6:-}" rc=0 hookend maxgap
  hookend=$(python3 "$SCRIPTS/yaplib/ass.py" hook-end "$ass" 2>/dev/null || echo 2.5)
  # 5s budget for short form, 6s once the video is 60s+ (a longer video may breathe);
  # the numbers are rules.json retention.*
  maxgap=$(python3 - "$SCRIPTS/yaplib/rules.py" "$dur" <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("rules", sys.argv[1]); r = importlib.util.module_from_spec(spec); spec.loader.exec_module(r)
R = r.get("retention")
print(R["max_static_long_s"] if float(sys.argv[2]) >= R["long_video_s"] else R["max_static_s"])
PY
)
  echo "--- gate retention (hook-end ${hookend}s, max-gap ${maxgap}s) ---"
  if [ "${YAP_ALLOW_STATIC:-0}" = "1" ]; then
    echo "  skipped by YAP_ALLOW_STATIC=1 (deliberate slow burn)"; rc=1
  else
    local args=(--video "$video" --hook-end "$hookend" --max-gap "$maxgap")
    [ -n "$ovr" ] && [ -f "$ovr" ] && args+=(--overlays "$ovr")
    [ -n "$keeps" ] && [ -f "$keeps" ] && args+=(--keeps "$keeps")
    [ -n "$cache" ] && args+=(--cache "$cache")
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

# --- black frames: the canary from the old concat path, one full decode ---------
black_check() {                      # black_check <file> <label>
  echo "--- blackdetect ($2) ---"
  ffmpeg -nostdin -i "$1" -vf "blackdetect=d=0.02:pic_th=0.95" -an -f null - 2>&1 \
    | grep -i black_start || echo "  NO black frames"
}

# --- compose signature: the compose is skipped when nothing it reads has changed (3.9.0) -------
# compose_sig <cut-hash> <cap.ass> <overlays|""> -> prints a hash of the cut, the captions, every
# overlay entry and the files it points at, and the loudness rules.
compose_sig() {
  python3 - "$1" "$2" "${3:-}" "$SCRIPTS/../rules.json" <<'PY'
import hashlib, json, os, sys
cutsig, ass, ovr, rules = sys.argv[1:5]
h = hashlib.sha1(cutsig.encode())
h.update(open(ass, "rb").read())
if ovr and os.path.isfile(ovr):
    h.update(open(ovr, "rb").read())
    try:
        for o in json.load(open(ovr)):
            f = o.get("file")
            if f:
                f = f if os.path.isabs(f) else os.path.join(os.path.dirname(os.path.abspath(ovr)), f)
                st = os.stat(f) if os.path.isfile(f) else None
                h.update(f"{f}:{st.st_size if st else 0}:{st.st_mtime if st else 0}".encode())
    except (ValueError, OSError):
        pass
h.update(json.dumps(json.load(open(rules)).get("loudness"), sort_keys=True).encode())
h.update(b"compose-v1")
print(h.hexdigest())
PY
}

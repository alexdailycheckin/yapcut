#!/usr/bin/env bash
# editor_smoke.sh: end-to-end smoke of the tiktok-yap-editor scripts on the
# synthetic fixture from make_fixture.sh. No personal footage, no personal
# brand config, no personal library: it runs in a temp dir with an EMPTY
# workspace ($YAPCUT_HOME) so the shipped default brand config wins.
#
# What runs, in order, and what is asserted:
#   1. yapfull.sh  (Mode A) on the fixture with a 4-word hook
#        rc 0; 1080x1920; video-audio drift under 0.112s; integrated loudness
#        within 1 LU of -14 LUFS; 48000 Hz; a Hook event carrying the full first
#        hook line from 0.00 (frame zero); the gates json lists EVERY gate in
#        gates.sh with no rc 2; platform tiktok; hook words 4.
#   2. hook_variant.sh  hook B on the same cut, no re-cut
#        rc 0; <out>-b.mp4 exists and passes the same file checks; <base>_hooks.json
#        carries both hooks.
#   3. storyfull.sh  (Mode B) picture = the yapfull cut with its audio stripped
#      (a silent export, the Mode B case), VO = that cut's speech track, so the VO
#      carries no dead air the cutter already removed and the seam gate applies
#        rc 0; same file checks; the same gate list with no rc 2.
#   4. finalize.sh --standalone with a throwaway footage library whose record
#      for the fixture points at a stale path
#        the edit record exists with radar_id standalone, gates and duration;
#        the library record is re-pathed by hash and stamped used_in.
# Prints the elapsed time; the target is under 60 seconds on an Apple Silicon Mac.
#
# Usage: bash tests/editor_smoke.sh   [KEEP_TMP=1 keeps the temp dir]
set -uo pipefail
T0=$(date +%s)
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$REPO/plugins/tiktok-yap-editor/skills/tiktok-yap-editor/scripts"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/yapsmoke.XXXXXX")"; TMP="$(cd "$TMP" && pwd -P)"
export YAPCUT_HOME="$TMP/ws"; mkdir -p "$YAPCUT_HOME"
unset OUTLIER_RADAR_HOME LEAD_MAGNET_HOME YAP_PLATFORM YAP_LIBRARY YAP_FROM_CUT YAP_CUT_BASE YAP_SCRIPT 2>/dev/null || true
FAILS=0
pass() { echo "  PASS  $*"; }
fail() { echo "  FAIL  $*"; FAILS=$((FAILS + 1)); }
TSTEP=$T0
step() { local now; now=$(date +%s); echo; echo "=== $* ===  (+$((now - TSTEP))s since the previous step)"; TSTEP=$now; }
run_logged() {   # run_logged <log> <cmd...>: rc in RC, tail of the log on failure
  local log="$1"; shift
  "$@" > "$log" 2>&1; RC=$?
  if [ "$RC" -ne 0 ]; then echo "  command failed (rc $RC): $*"; echo "  --- last 40 lines of $log ---"; tail -40 "$log"; fi
  return 0
}
# gate names from gates.sh itself, so this test cannot drift from the ladder
GATE_NAMES="$(sed -n 's/^GATE_NAMES="\(.*\)"$/\1/p' "$SCRIPTS/gates.sh")"
[ -n "$GATE_NAMES" ] || { echo "cannot read GATE_NAMES from gates.sh"; exit 2; }

check_final() {   # check_final <label> <final.mp4> <gates.json> <cap.ass> "<hook>" <platform> <hook_words>
  python3 - "$SCRIPTS" "$GATE_NAMES" "$@" <<'PY'
import json, os, re, subprocess, sys
scripts, gate_names, label, final, gates_p, ass_p, hook, platform, hook_words = sys.argv[1:10]
sys.path.insert(0, scripts)
from yaplib import media, ass as yass
fails = []
def check(cond, msg):
    print(("  PASS  " if cond else "  FAIL  ") + f"[{label}] " + msg)
    if not cond: fails.append(msg)
check(os.path.isfile(final), f"final exists: {final}")
if os.path.isfile(final):
    st = media.probe_streams(final)
    check(st.get("video", {}).get("width") == media.W and st.get("video", {}).get("height") == media.H,
          f"canvas {st.get('video', {}).get('width')}x{st.get('video', {}).get('height')} is {media.W}x{media.H}")
    d = media.drift(final)
    check(abs(d) < media.DRIFT_LIMIT_FINAL, f"drift {d:+.3f}s under {media.DRIFT_LIMIT_FINAL}s")
    check(st.get("audio", {}).get("sample_rate") == 48000, f"audio {st.get('audio', {}).get('sample_rate')} Hz is 48000")
    r = subprocess.run(["ffmpeg", "-nostdin", "-i", final, "-af", "ebur128=framelog=quiet", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"I:\s+(-?[0-9.]+) LUFS", r.stderr)
    lufs = float(m.group(1)) if m else None
    check(lufs is not None and abs(lufs + 14.0) <= 1.0, f"loudness {lufs} LUFS within 1 LU of -14")
    print(f"        duration {media.probe_duration(final):.2f}s")
if hook:
    rc, msg = yass.frame0_check(ass_p, hook)
    check(rc == 0, f"frame zero: {msg}")
check(os.path.isfile(gates_p), f"gates json exists: {gates_p}")
if os.path.isfile(gates_p):
    g = json.load(open(gates_p))
    gates = g.get("gates", {})
    missing = [n for n in gate_names.split() if n not in gates]
    check(not missing, f"gates json lists every gate ({len(gate_names.split())}): missing {missing or 'none'}")
    failed = [n for n, rc in gates.items() if rc == 2]
    check(not failed, f"no gate recorded rc 2: {failed or 'none'}")
    check(g.get("platform") == platform, f"platform recorded: {g.get('platform')} == {platform}")
    check(str((g.get("hook") or {}).get("words")) == hook_words, f"hook words recorded: {(g.get('hook') or {}).get('words')} == {hook_words}")
    print("        gates: " + ", ".join(f"{k}={v}" for k, v in gates.items()))
sys.exit(1 if fails else 0)
PY
  [ $? -eq 0 ] || FAILS=$((FAILS + 1))
}

step "fixture"
FX="$TMP/fixture"
run_logged "$TMP/fixture.log" bash "$REPO/tests/make_fixture.sh" "$FX"
if [ "$RC" -ne 0 ]; then echo "fixture failed"; exit 2; fi
cat "$TMP/fixture.log" | tail -1
if grep -q "sine stand-in" "$FX/fixture.json"; then
  echo "no speech source (macOS say or FIXTURE_SPEECH): the speech gates cannot pass on a sine tone. Stopping."; exit 2
fi
WD="$TMP/build"; mkdir -p "$WD"; cp "$FX/script.txt" "$WD/fixture_script.txt"
HOOK="SMOKE TEST HOOK LINE"; SPARK="HOOK"

step "1. yapfull.sh (Mode A)"
FINAL="$TMP/fixture.mp4"
run_logged "$TMP/yapfull.log" bash "$SCRIPTS/yapfull.sh" "$WD" "$FX/clauses.json" "$FINAL" "$HOOK" "$SPARK"
if [ "$RC" -eq 0 ]; then pass "yapfull rc 0"; else fail "yapfull rc $RC"; fi
grep -E "^(auto-floor|head-trim|[0-9]+ segments|joins:|  loudness:)" "$TMP/yapfull.log" | sed 's/^/        /'
check_final yapfull "$FINAL" "$WD/fixture_gates.json" "$WD/cap_fixture.ass" "$HOOK" tiktok 4

step "2. hook_variant.sh (hook B on the same cut)"
# 2 and 3 are independent once the cut exists but run one after the other on
# purpose: side by side they contend for the GPU (whisper) and x264 and take
# longer in total (measured 55s parallel vs 43s sequential on an M4).
HOOKB="SECOND HOOK VARIANT"
run_logged "$TMP/variant.log" bash "$SCRIPTS/hook_variant.sh" "$WD" "$FX/clauses.json" "$FINAL" "$HOOKB" "VARIANT"
echo "$RC" > "$TMP/variant.rc"
report_rc() {   # report_rc <label> <log> <rcfile>
  local rc; rc="$(cat "$3" 2>/dev/null || echo 99)"
  if [ "$rc" = "0" ]; then pass "$1 rc 0"; else fail "$1 rc $rc"; fi
}
report_rc hook_variant "$TMP/variant.log" "$TMP/variant.rc"
grep -q "reusing cut" "$TMP/variant.log" && pass "variant reused the cut (no re-cut)" || fail "variant did not reuse the cut"
check_final variant "$TMP/fixture-b.mp4" "$WD/fixture-b_gates.json" "$WD/cap_fixture-b.ass" "$HOOKB" tiktok 3
python3 - "$WD/fixture_hooks.json" "$HOOK" "$HOOKB" <<'PY2' || FAILS=$((FAILS + 1))
import json, sys
p, a, b = sys.argv[1:4]
try:
    hooks = json.load(open(p))
except Exception as e:
    print(f"  FAIL  hooks json unreadable: {e}"); sys.exit(1)
texts = [h.get("text") for h in hooks]
ok = a in texts and b in texts and all(h.get("out") and h.get("platform") for h in hooks)
print(("  PASS  " if ok else "  FAIL  ") + f"hooks json carries both hooks with out + platform: {texts}")
sys.exit(0 if ok else 1)
PY2
step "3. storyfull.sh (Mode B: silent picture + VO)"
WD2="$TMP/story"; mkdir -p "$WD2"
cp "$WD/keeps_full_fixture.json" "$WD2/"; cp "$FX/script.txt" "$WD2/fixture_script.txt"
ffmpeg -nostdin -y -i "$WD/full_fixture.mp4" -an -c:v copy "$WD2/picture.mp4" -hide_banner -loglevel error
ffmpeg -nostdin -y -i "$WD/full_fixture.mp4" -vn -c:a aac -b:a 192k "$TMP/fixture_vo.m4a" -hide_banner -loglevel error
STORY="$TMP/fixture-story.mp4"
run_logged "$TMP/storyfull.log" env YAP_CUT_BASE=fixture bash "$SCRIPTS/storyfull.sh" "$WD2" "$WD2/picture.mp4" "$TMP/fixture_vo.m4a" "$STORY" "$HOOK" "$SPARK"
echo "$RC" > "$TMP/storyfull.rc"
report_rc storyfull "$TMP/storyfull.log" "$TMP/storyfull.rc"
check_final storyfull "$STORY" "$WD2/fixture-story_gates.json" "$WD2/cap_fixture-story.ass" "$HOOK" tiktok 4
python3 -c 'import json,sys; g=json.load(open(sys.argv[1]))["gates"]; sys.exit(0 if g.get("seam") in (0,1) else 1)' "$WD2/fixture-story_gates.json" \
  && pass "storyfull seam gate applied (keeps file for the reused cut)" || fail "storyfull seam gate did not apply"

step "4. finalize.sh --standalone + footage library reconcile"
LIB="$TMP/lib"; mkdir -p "$LIB"
HASH="$(python3 -c 'import sys,pathlib; sys.path.insert(0, sys.argv[1]); import library; print(library.clip_hash(pathlib.Path(sys.argv[2])))' "$SCRIPTS" "$FX/fixture.mp4")"
printf '{"id":"%s","path":"%s","source_folder":"old-location","duration_s":12.0,"kind":"test","tags":{"topics":["smoke"]},"moments":[],"hooks":[],"used_in":[],"posted":false}\n' \
  "$HASH" "$FX/old-location/fixture.mp4" > "$LIB/library.jsonl"
run_logged "$TMP/finalize.log" env YAP_LIBRARY="$LIB" bash "$SCRIPTS/finalize.sh" "$FINAL" "$FX" fixture --standalone --workdir "$WD" --out-dir "$TMP/out"
if [ "$RC" -eq 0 ]; then pass "finalize rc 0"; else fail "finalize rc $RC"; fi
python3 - "$TMP/out/fixture.edit.json" "$LIB/library.jsonl" "$FX/fixture.mp4" <<'PY' || FAILS=$((FAILS + 1))
import json, os, sys
rec_p, lib_p, real = sys.argv[1:4]
bad = 0
def check(c, m):
    global bad
    print(("  PASS  " if c else "  FAIL  ") + m); bad += (not c)
try:
    r = json.load(open(rec_p))
    check(r.get("radar_id") == "standalone", "edit record radar_id standalone")
    check(bool(r.get("gates")) and all(v != 2 for v in r["gates"].values()), f"edit record carries gates: {sorted(r.get('gates', {}))}")
    check(isinstance(r.get("duration_s"), float) and r["duration_s"] > 0, f"edit record duration_s {r.get('duration_s')}")
    check(r.get("clauses") and r.get("script"), "edit record links clauses + script")
except Exception as e:
    check(False, f"edit record unreadable: {e}")
try:
    lib = [json.loads(l) for l in open(lib_p) if l.strip()]
    rec = lib[0]
    check(os.path.abspath(rec["path"]) == os.path.abspath(real), f"library record re-pathed by hash: {rec['path']}")
    check("missing_since" not in rec, "library record not stamped missing")
    check("fixture" in rec.get("used_in", []), f"library record used_in {rec.get('used_in')}")
except Exception as e:
    check(False, f"library unreadable: {e}")
sys.exit(1 if bad else 0)
PY
grep -E "^(REPATH|reconcile:|stamped|edit record|delivered)" "$TMP/finalize.log" | sed 's/^/        /'

step "done"
ELAPSED=$(( $(date +%s) - T0 ))
echo
if [ "$ELAPSED" -le 60 ]; then echo "elapsed ${ELAPSED}s (budget 60s)"; else echo "elapsed ${ELAPSED}s: OVER the 60s budget"; fi
if [ "${KEEP_TMP:-0}" = "1" ]; then echo "kept $TMP"; else rm -rf "$TMP"; fi
if [ "$FAILS" -eq 0 ]; then echo "SMOKE OK"; exit 0; else echo "SMOKE FAILED ($FAILS)"; exit 1; fi

#!/usr/bin/env bash
# xwin_restart.sh: xwin_scan.py must catch a known restart before a zero from it means anything.
#
# macOS `say` speaks "It's the same bet we made." then, 0.22s later, the full line again: the
# shape that shipped on 2026-09-30 because the whole-cut transcript read both passes as one.
# TTS is clean enough that whisper usually hears both passes over the whole clip, so the test
# builds the transcript the real take produced: the same word list with the first pass taken
# out. Asserted:
#   1. the restart is MEDIUM and the scan exits 2 (a decision, not a note)
#   2. its printed key in the accept-file clears it: exit 0, and the cached decodes are reused
#   3. the transcript that hears both passes makes it LOW (stutter_check owns that case): exit 0
#   4. the same line said once has no MEDIUM: exit 0
# Needs `say`, whisper-cli and a model; skips (exit 0 with a note) without `say`.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
SCRIPTS="$REPO/plugins/tiktok-yap-editor/skills/tiktok-yap-editor/scripts"
command -v say >/dev/null 2>&1 || { echo "  skip xwin_restart: no macOS say"; exit 0; }
T="$(mktemp -d "${TMPDIR:-/tmp}/xwin.XXXXXX")"
trap 'rm -rf "$T"' EXIT
FAILS=0
ok()  { echo "  ok   $1"; }
bad() { echo "  FAIL $1"; FAILS=$((FAILS + 1)); }
LINE="It's the same bet we made at the company, where the team does the work and the software makes them fast."
say -v Samantha -r 185 -o "$T/restart.aiff" "It's the same bet we made. [[slnc 220]] $LINE" 2>/dev/null \
  || say -r 185 -o "$T/restart.aiff" "It's the same bet we made. [[slnc 220]] $LINE"
say -v Samantha -r 185 -o "$T/once.aiff" "$LINE" 2>/dev/null || say -r 185 -o "$T/once.aiff" "$LINE"
for n in restart once; do
  ffmpeg -nostdin -y -v error -i "$T/$n.aiff" -af "adelay=300|300,apad=pad_dur=0.5" -ar 48000 -ac 1 "$T/$n.wav"
  bash "$SCRIPTS/transcribe.sh" "$T/$n.wav" "$T/w_$n" --words >/dev/null
done
# the merged transcript: drop every word before the second "It's"
python3 - "$T/w_restart.json" "$T/w_merged.json" <<'PY'
import json, re, sys
d = json.load(open(sys.argv[1])); segs = d["transcription"]
idx = [i for i, s in enumerate(segs) if re.sub(r"[^a-z']", "", s.get("text", "").lower()) == "it's"]
if len(idx) < 2:
    sys.exit(f"whisper did not hear two passes over the TTS clip ({len(idx)} 'It's'); cannot build the merged case")
d["transcription"] = segs[idx[1]:]
json.dump(d, open(sys.argv[2], "w"))
PY
[ $? = 0 ] || { bad "could not build the merged transcript"; exit 2; }

python3 "$SCRIPTS/xwin_scan.py" --video "$T/restart.wav" --words "$T/w_merged.json" \
  --accept-file "$T/ok.json" --cache "$T/xwin_restart.json" >"$T/1.log" 2>&1
rc=$?
if [ "$rc" = 2 ] && grep -q "\[MEDIUM\]" "$T/1.log"; then ok "the known restart is MEDIUM and exits 2"; else bad "the known restart was not caught (rc $rc)"; cat "$T/1.log"; fi
python3 - "$T/1.log" "$T/ok.json" <<'PY'
import json, re, sys
log = open(sys.argv[1]).read()
keys = json.loads(log[log.rindex("["):]) if "need a decision" in log else []
json.dump(keys, open(sys.argv[2], "w"))
PY
python3 "$SCRIPTS/xwin_scan.py" --video "$T/restart.wav" --words "$T/w_merged.json" \
  --accept-file "$T/ok.json" --cache "$T/xwin_restart.json" >"$T/2.log" 2>&1
rc=$?
if [ "$rc" = 0 ] && grep -q "cached" "$T/2.log"; then ok "its printed key clears it, from the cached decodes"; else bad "accept-file or cache did not work (rc $rc)"; cat "$T/2.log"; fi
python3 "$SCRIPTS/xwin_scan.py" --video "$T/restart.wav" --words "$T/w_restart.json" \
  --cache "$T/xwin_restart.json" >"$T/3.log" 2>&1
rc=$?
if [ "$rc" = 0 ] && ! grep -q "\[MEDIUM\]" "$T/3.log"; then ok "a transcript that hears both passes leaves it LOW"; else bad "both-passes transcript still gated (rc $rc)"; cat "$T/3.log"; fi
python3 "$SCRIPTS/xwin_scan.py" --video "$T/once.wav" --words "$T/w_once.json" >"$T/4.log" 2>&1
rc=$?
if [ "$rc" = 0 ]; then ok "the line said once has no MEDIUM"; else bad "false MEDIUM on a clean line (rc $rc)"; cat "$T/4.log"; fi
# 3.8.0, keeps mode: the windows come from the source take and the joins from the cut. The same
# restart must still be MEDIUM when the cut keeps it whole, and when a join splits its two passes
# (the cut is the same audio either way: the keeps meet at the pause). A rerun decodes nothing.
python3 - "$T/w_restart.json" "$T/restart.wav" "$T" <<'PY'
import json, re, sys
segs = json.load(open(sys.argv[1]))["transcription"]
its = [s for s in segs if re.sub(r"[^a-z']", "", s.get("text", "").lower()) == "it's"]
made = [s for s in segs if s["offsets"]["to"] <= its[1]["offsets"]["from"]][-1]
mid = round((made["offsets"]["to"] + its[1]["offsets"]["from"]) / 2000.0, 3)
import wave
w = wave.open(sys.argv[2]); dur = w.getnframes() / w.getframerate(); w.close()
json.dump([{"src": sys.argv[2], "a": 0.0, "b": round(dur, 3)}], open(f"{sys.argv[3]}/keeps1.json", "w"))
json.dump([{"src": sys.argv[2], "a": 0.0, "b": mid}, {"src": sys.argv[2], "a": mid, "b": round(dur, 3)}],
          open(f"{sys.argv[3]}/keeps2.json", "w"))
PY
for k in 1 2; do
  python3 "$SCRIPTS/xwin_scan.py" --video "$T/restart.wav" --words "$T/w_merged.json" --keeps "$T/keeps$k.json" \
    --cache "$T/xk$k.json" --store-dir "$T/xwin_src" >"$T/k$k.log" 2>&1
  rc=$?
  label=$([ "$k" = 1 ] && echo "kept whole" || echo "split by a join")
  if [ "$rc" = 2 ] && grep -q "\[MEDIUM\]" "$T/k$k.log"; then ok "keeps mode: the restart $label is MEDIUM"; else bad "keeps mode missed the restart $label (rc $rc)"; cat "$T/k$k.log"; fi
done
python3 "$SCRIPTS/xwin_scan.py" --video "$T/restart.wav" --words "$T/w_merged.json" --keeps "$T/keeps2.json" \
  --cache "$T/xk2.json" --store-dir "$T/xwin_src" >"$T/k3.log" 2>&1
grep -q " 0 decoded" "$T/k3.log" && ok "a rerun decodes nothing" || { bad "the rerun decoded windows again"; cat "$T/k3.log"; }
[ "$FAILS" = 0 ] || exit 2

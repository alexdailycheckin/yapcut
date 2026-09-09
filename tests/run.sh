#!/usr/bin/env bash
# tests/run.sh: the repo's only test harness. Three stages, no creator footage involved.
#
#   tests/run.sh          all stages (the editor stage cuts a synthetic clip; ~30-60s)
#   tests/run.sh --fast   stages 2 and 3 only (radar gates + dashboard), a few seconds;
#                         wired into release.sh and usable from the pre-commit hook
#
# Every regression in CHANGELOG.md before 3.5.0 was found by watching a shipped video or a
# broken dashboard, weeks late. This pins the contracts instead: exit codes, the example week
# passing its own gates, the dashboard rendering cards.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RADAR="$ROOT/plugins/outlier-radar/skills/outlier-radar"
FAST=0; [ "${1:-}" = "--fast" ] && FAST=1
fails=0
ok()   { echo "  ok   $1"; }
bad()  { echo "  FAIL $1"; fails=$((fails+1)); }

# Stage 1: the editor on a synthetic fixture (Mode A, Mode B, a hook variant).
if [ "$FAST" = 0 ]; then
  echo "[1] editor smoke"
  if [ -x "$ROOT/tests/editor_smoke.sh" ]; then
    if "$ROOT/tests/editor_smoke.sh" >/tmp/yapcut-editor-smoke.log 2>&1; then ok "editor_smoke.sh"; else bad "editor_smoke.sh (see /tmp/yapcut-editor-smoke.log)"; tail -20 /tmp/yapcut-editor-smoke.log; fi
  else
    bad "tests/editor_smoke.sh missing"
  fi
fi

# Stage 2: the radar gates on the bundled example week, in a throwaway workspace.
echo "[2] radar gates on the example week"
WS="$(mktemp -d /tmp/yapcut-ws.XXXXXX)"
mkdir -p "$WS/weeks" "$WS/performance" "$WS/voice-corpus"
cp "$RADAR/radar-config.example.json" "$WS/radar-config.json"
cp "$RADAR/weeks/0000-00-00-example.json" "$WS/weeks/"
for s in check_fidelity.py hook_lint.py spoken_lint.py; do
  python3 "$RADAR/$s" --help >/dev/null 2>&1 && ok "$s --help" || bad "$s --help"
done
python3 "$RADAR/radar_gate.py" --week "$WS/weeks/0000-00-00-example.json" --dir "$WS" --skip source,visual --allow-unvalidated >/tmp/yapcut-gate.log 2>&1
rc=$?
if [ "$rc" = 0 ]; then ok "radar_gate.py on the example week (rc 0)"; elif [ "$rc" = 1 ]; then ok "radar_gate.py on the example week (rc 1, warnings only)"; else bad "radar_gate.py on the example week rc $rc"; tail -15 /tmp/yapcut-gate.log; fi
[ -f "$WS/weeks/0000-00-00-example.gate.json" ] && ok "gate stamp written" || bad "no gate stamp"
# exit contract: an illegal qa value must be rc 2
python3 - "$WS" <<'PY'
import json, sys, os
ws = sys.argv[1]; p = os.path.join(ws, "weeks", "0000-00-00-example.json"); d = json.load(open(p))
d["distribution"][0]["qa"] = "pre-qa"; json.dump(d, open(os.path.join(ws, "weeks", "0000-00-00-bad.json"), "w"))
PY
python3 "$RADAR/check_fidelity.py" --dir "$WS" --week "$WS/weeks/0000-00-00-bad.json" --schema-only >/dev/null 2>&1
[ $? = 2 ] && ok "illegal qa value exits 2" || bad "illegal qa value did not exit 2"
rm -f "$WS/weeks/0000-00-00-bad.json"
# no workspace: exit 2, never the skill folder
( cd /tmp && env -u YAPCUT_HOME -u OUTLIER_RADAR_HOME -u LEAD_MAGNET_HOME HOME=/tmp/yapcut-nohome python3 "$RADAR/yapcut_home.py" >/dev/null 2>&1 ); [ $? = 2 ] && ok "no workspace exits 2" || bad "no workspace did not exit 2"

# Stage 3: the dashboard builds and renders cards.
echo "[3] dashboard"
python3 "$RADAR/build_dashboard.py" --dir "$WS" >/tmp/yapcut-dash.log 2>&1 && ok "build_dashboard.py" || { bad "build_dashboard.py"; tail -5 /tmp/yapcut-dash.log; }
[ -s "$WS/dashboard.html" ] && ok "dashboard.html written ($(wc -c <"$WS/dashboard.html" | tr -d ' ') bytes)" || bad "dashboard.html missing"
grep -q 'id="weeks-data"' "$WS/dashboard.html" && ok "weeks embedded as JSON" || bad "weeks-data block missing"
node --check "$RADAR/dashboard/app.js" >/dev/null 2>&1 && ok "app.js parses" || bad "app.js does not parse"
python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$RADAR/build_dashboard.py" && ok "build_dashboard.py parses" || bad "build_dashboard.py does not parse"
rm -rf "$WS"

echo
[ "$fails" = 0 ] && { echo "ALL GREEN"; exit 0; } || { echo "$fails failure(s)"; exit 2; }

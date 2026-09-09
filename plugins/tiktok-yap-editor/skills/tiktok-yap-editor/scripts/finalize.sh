#!/usr/bin/env bash
# Promote the approved video to output/<footage-folder-name>/ and WRITE THE EDIT
# RECORD. The old finalize did `rm -f output/*.mp4` and `rm -rf .yap_build`:
# it deleted the decision record and nothing joined a cut to a Radar id or a
# post (audit Q1 item 15). Finals now accumulate per run folder, .yap_build is
# kept unless --wipe, and every shipped file gets <name>.edit.json (Contract 6).
#
# Usage:
#   finalize.sh <final.mp4> <footage_dir> <name> (--radar-id <id> | --standalone)
#               [--wipe] [--pillar P] [--episode N] [--workdir WD] [--out-dir DIR]
#               [--cover cover.jpg] [--post-url URL]
#   e.g. finalize.sh .yap_build/clip.mp4 "/ws/input/aug 30" tesla --radar-id d-20260830-3
#
# Output dir, first hit wins: --out-dir | $YAP_OUTPUT_ROOT/<footage-folder-name> |
#   <workspace>/output/<footage-folder-name> (workspace = yaplib.home, required=False)
#   | <footage_dir>/output (no workspace: the legacy location).
# Then, when reachable: the footage library is stamped (library.py mark-used for
# every clip in clauses.json, then reconcile --roots <footage_dir>), and the Radar
# tracking log gets a `filmed` event (log_perf.py --filmed <id>) when that flag
# exists in the installed log_perf.py; otherwise the command is printed to run.
set -euo pipefail
usage() { sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
[ $# -ge 3 ] || usage
FINAL="$1"; FOOTAGE="$2"; NAME="$3"; shift 3
RADAR_ID=""; STANDALONE=0; WIPE=0; PILLAR=""; EPISODE=""; WD=""; OUTDIR=""; COVER=""; POST_URL=""
while [ $# -gt 0 ]; do
  case "$1" in
    --radar-id) RADAR_ID="$2"; shift 2 ;;
    --standalone) STANDALONE=1; shift ;;
    --wipe) WIPE=1; shift ;;
    --pillar) PILLAR="$2"; shift 2 ;;
    --episode) EPISODE="$2"; shift 2 ;;
    --workdir) WD="$2"; shift 2 ;;
    --out-dir) OUTDIR="$2"; shift 2 ;;
    --cover) COVER="$2"; shift 2 ;;
    --post-url) POST_URL="$2"; shift 2 ;;
    -h|--help) usage ;;
    *) echo "finalize: unknown argument $1"; usage ;;
  esac
done
if [ -z "$RADAR_ID" ] && [ "$STANDALONE" != "1" ]; then
  echo "finalize: refuse. Every shipped edit joins a Radar item or says it does not:"
  echo "  pass --radar-id <id> (the week-file item this cut films) or --standalone."
  exit 2
fi
[ -f "$FINAL" ] || { echo "finalize: no such final: $FINAL"; exit 2; }
[ -d "$FOOTAGE" ] || { echo "finalize: no such footage dir: $FOOTAGE"; exit 2; }
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
[ -n "$WD" ] || WD="$FOOTAGE/.yap_build"
[ -n "$RADAR_ID" ] || RADAR_ID="standalone"
FOLDER="$(basename "$FOOTAGE")"
HOME_DIR="$(python3 -c 'import sys,os; sys.path.insert(0, sys.argv[1]); from yaplib.home import radar_home; h = radar_home(argv=[], required=False); print(h or "")' "$SCRIPTS")"

if [ -z "$OUTDIR" ]; then
  if [ -n "${YAP_OUTPUT_ROOT:-}" ]; then OUTDIR="$YAP_OUTPUT_ROOT/$FOLDER"
  elif [ -n "$HOME_DIR" ]; then OUTDIR="$HOME_DIR/output/$FOLDER"
  else OUTDIR="$FOOTAGE/output"; fi
fi
mkdir -p "$OUTDIR"
DEST="$OUTDIR/$NAME.mp4"
if [ "$(cd "$(dirname "$FINAL")" && pwd)/$(basename "$FINAL")" != "$(cd "$OUTDIR" && pwd)/$NAME.mp4" ]; then
  cp "$FINAL" "$DEST"
fi
echo "delivered: $DEST"

# the cover: --cover, else <outdir>/<name>.jpg if the cover step already put it there
if [ -n "$COVER" ] && [ -f "$COVER" ]; then
  [ "$(cd "$(dirname "$COVER")" && pwd)/$(basename "$COVER")" = "$(cd "$OUTDIR" && pwd)/$NAME.jpg" ] || cp "$COVER" "$OUTDIR/$NAME.jpg"
  [ -f "$COVER.meta.json" ] && cp "$COVER.meta.json" "$OUTDIR/$NAME.jpg.meta.json" || true
fi
COVERPATH=""; [ -f "$OUTDIR/$NAME.jpg" ] && COVERPATH="$OUTDIR/$NAME.jpg"

# the gates json yapfull/storyfull wrote for THIS output
FINALBASE="$(basename "${FINAL%.*}")"
GATES="$WD/${FINALBASE}_gates.json"
[ -f "$GATES" ] || { GATES="$WD/${NAME}_gates.json"; }
[ -f "$GATES" ] || echo "finalize: WARNING no gates json at $WD/${FINALBASE}_gates.json; the record will carry no gate results"

RECORD="$OUTDIR/$NAME.edit.json"
python3 - "$RECORD" "$NAME" "$RADAR_ID" "$FOOTAGE" "$DEST" "$GATES" "$COVERPATH" "$PILLAR" "$EPISODE" "$POST_URL" "$WD" "$SCRIPTS" <<'PY'
import json, os, sys, datetime
(record, name, radar_id, footage, final, gates_p, cover_p, pillar, episode,
 post_url, wd, scripts) = sys.argv[1:13]
sys.path.insert(0, scripts)
from yaplib import media
g = {}
if gates_p and os.path.isfile(gates_p):
    g = json.load(open(gates_p))
paths = g.get("paths", {})
def p_or_none(k):
    v = paths.get(k) or ""
    return os.path.abspath(v) if v and os.path.exists(v) else None
hook = g.get("hook") or {"text": "", "words": 0, "anim": None, "style": None, "spark": ""}
hook = {k: hook.get(k) for k in ("text", "words", "anim", "style", "spark")}
cutbase = None
if paths.get("cut"):
    cutbase = os.path.basename(paths["cut"])[len("full_"):-4]
hooks = []
hp = os.path.join(wd, f"{cutbase}_hooks.json") if cutbase else ""
if hp and os.path.isfile(hp):
    try: hooks = json.load(open(hp))
    except json.JSONDecodeError: hooks = []
accept = [p for p in (p_or_none("stutter_ok"), p_or_none("capqa_ok"), p_or_none("corrections")) if p]
receipts_n = 0
ov = p_or_none("overlays")
if ov:
    try: receipts_n = len([o for o in json.load(open(ov)) if o.get("type") in ("pip", "counter", "source")])
    except Exception: receipts_n = 0
cover = None
if cover_p:
    cover = {"frame_t": None, "path": os.path.abspath(cover_p)}
    mp = cover_p + ".meta.json"
    if os.path.isfile(mp):
        try: cover["frame_t"] = json.load(open(mp)).get("frame_t")
        except Exception: pass
try:
    dur = float(g.get("duration_s") or media.probe_duration(final))
except Exception:
    dur = None
rec = {
    "name": name, "radar_id": radar_id, "footage_dir": os.path.abspath(footage),
    "final": os.path.abspath(final), "duration_s": dur,
    "platform": g.get("platform") or "tiktok",
    "hook": hook, "hook_words": hook.get("words"),
    "hooks": hooks if len(hooks) > 1 else [],
    "clauses": p_or_none("clauses"), "script": p_or_none("script"),
    "overlays": ov, "receipts_n": receipts_n, "accept_files": accept,
    "gates": g.get("gates", {}), "gates_json": os.path.abspath(gates_p) if gates_p and os.path.isfile(gates_p) else None,
    "cover": cover, "pillar": pillar or None,
    "episode": int(episode) if episode.isdigit() else (episode or None),
    "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
    "post_url": post_url or None,
}
json.dump(rec, open(record, "w"), indent=1, ensure_ascii=False)
print(f"edit record: {record}")
fails = [k for k, v in rec["gates"].items() if v == 2]
if fails:
    print(f"finalize: WARNING the gates json records FAILED gates: {', '.join(fails)}")
PY

# footage library: stamp used_in and reconcile paths, when a library is reachable
LIBDIR="${YAP_LIBRARY:-}"
[ -n "$LIBDIR" ] || { [ -n "$HOME_DIR" ] && [ -d "$HOME_DIR/footage-library" ] && LIBDIR="$HOME_DIR/footage-library"; } || true
if [ -n "$LIBDIR" ] && [ -d "$LIBDIR" ]; then
  CLAUSES="$(python3 -c 'import json,sys,os; g=json.load(open(sys.argv[1])) if os.path.isfile(sys.argv[1]) else {}; print(g.get("paths",{}).get("clauses",""))' "$GATES" 2>/dev/null || true)"
  if [ -n "$CLAUSES" ] && [ -f "$CLAUSES" ]; then
    python3 -c 'import json,sys,os; print("\n".join(sorted({os.path.splitext(os.path.basename(c["src"]))[0] for c in json.load(open(sys.argv[1]))})))' "$CLAUSES" \
    | while IFS= read -r stem; do
        [ -n "$stem" ] && YAP_LIBRARY="$LIBDIR" python3 "$SCRIPTS/library.py" mark-used "$stem" --edit "$NAME" || true
      done
  else
    echo "library: no clauses path in the gates json, nothing to mark-used"
  fi
  YAP_LIBRARY="$LIBDIR" python3 "$SCRIPTS/library.py" reconcile --roots "$FOOTAGE" || echo "library: reconcile failed (non-fatal)"
else
  echo "library: no footage library reachable (set YAP_LIBRARY or create <workspace>/footage-library); skipped"
fi

# Radar tracking: a `filmed` event for the item this cut films
if [ "$RADAR_ID" != "standalone" ]; then
  LOGPERF=""
  for cand in "${RADAR_SCRIPTS:-}/log_perf.py" \
              "$SCRIPTS/../../../../outlier-radar/skills/outlier-radar/log_perf.py" \
              "$SCRIPTS"/../../../../../outlier-radar/*/skills/outlier-radar/log_perf.py \
              "$HOME"/.claude/plugins/cache/yapcut/outlier-radar/*/skills/outlier-radar/log_perf.py; do
    [ -f "$cand" ] && { LOGPERF="$cand"; break; }
  done
  if [ -n "$LOGPERF" ]; then
    if python3 "$LOGPERF" --help </dev/null 2>&1 | grep -q -- '--filmed' || grep -q -- '--filmed' "$LOGPERF"; then
      python3 "$LOGPERF" --filmed "$RADAR_ID" ${POST_URL:+--link "$POST_URL"} || echo "log_perf --filmed failed (non-fatal)"
    else
      echo "log_perf.py has no --filmed yet; when it lands, run:"
      echo "  python3 \"$LOGPERF\" --filmed $RADAR_ID"
    fi
  else
    echo "log_perf.py not reachable (set RADAR_SCRIPTS); run later: python3 log_perf.py --filmed $RADAR_ID"
  fi
fi

if [ "$WIPE" = "1" ]; then
  rm -rf "$WD"; echo "wiped working dir: $WD"
else
  echo "kept working dir: $WD (--wipe removes it)"
fi
ls -la "$OUTDIR"

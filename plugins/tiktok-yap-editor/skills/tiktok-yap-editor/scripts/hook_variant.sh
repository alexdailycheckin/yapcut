#!/usr/bin/env bash
# Second hook on the SAME cut. One hook slot per video meant TikTok, Reels and
# Shorts all got the identical file; this re-composes from the existing cut
# (YAP_FROM_CUT=1, no re-cut, seconds) with hook B and records both hooks so
# they can be posted against the same radar id and compared.
#
# Usage:
#   hook_variant.sh <workdir> <clauses.json> <outA.mp4> "<hook B|line2>" "<spark B>" [brand-config]
# Writes <outA-dir>/<baseA>-b.mp4 (platform suffix follows YAP_PLATFORM, like yapfull)
# and appends both hooks to $WD/<baseA>_hooks.json as [{text, out, platform}].
set -euo pipefail
WD="$1"; CLAUSES="$2"; OUTA="$3"; HOOKB="$4"; SPARKB="${5:-}"; CFG="${6:-}"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
BASEA="$(basename "${OUTA%.*}")"
DIRA="$(dirname "$OUTA")"
# outA may carry a platform suffix (clip.linkedin.mp4): the cut base is the
# part before it, and the variant inherits that platform.
PLAT="${YAP_PLATFORM:-}"
CUTBASE="$BASEA"
if [[ "$BASEA" == *.* ]]; then
  cand="${BASEA##*.}"
  if [ -f "$WD/full_${BASEA%.*}.mp4" ]; then CUTBASE="${BASEA%.*}"; PLAT="${PLAT:-$cand}"; fi
fi
[ -f "$WD/full_${CUTBASE}.mp4" ] || { echo "no cut at $WD/full_${CUTBASE}.mp4 (run yapfull first)"; exit 2; }

OUTB="$DIRA/${CUTBASE}-b.mp4"
# the platform goes through env: a NAME=value word produced by a parameter
# expansion is a command name to bash, not an assignment (rc 127 on linkedin)
YAP_FROM_CUT=1 YAP_CUT_BASE="$CUTBASE" env ${PLAT:+YAP_PLATFORM="$PLAT"} \
  bash "$SCRIPTS/yapfull.sh" "$WD" "$CLAUSES" "$OUTB" "$HOOKB" "$SPARKB" ${CFG:+"$CFG"}

# the real output name (yapfull adds the platform suffix for non-tiktok)
PLATNAME="${PLAT:-tiktok}"
if [ "$PLATNAME" != "tiktok" ]; then OUTB="${OUTB%.*}.${PLATNAME}.mp4"; fi

python3 - "$WD" "$BASEA" "$CUTBASE" "$OUTA" "$OUTB" "$HOOKB" "$PLATNAME" <<'PY'
import json, os, sys
wd, basea, cutbase, outa, outb, hookb, plat = sys.argv[1:8]
hooks_path = os.path.join(wd, f"{cutbase}_hooks.json")
try:
    hooks = json.load(open(hooks_path))
except (FileNotFoundError, json.JSONDecodeError):
    hooks = []
def add(text, out):
    if not text:
        return
    for h in hooks:
        if h.get("out") == os.path.abspath(out):
            h["text"] = text; h["platform"] = plat; return
    hooks.append({"text": text, "out": os.path.abspath(out), "platform": plat})
# hook A from its own gates json (written by yapfull)
ga = os.path.join(wd, f"{basea}_gates.json")
try:
    add(json.load(open(ga)).get("hook", {}).get("text", ""), outa)
except (FileNotFoundError, json.JSONDecodeError):
    print(f"hook_variant: no gates json for A at {ga}; recording B only")
add(hookb, outb)
json.dump(hooks, open(hooks_path, "w"), indent=1, ensure_ascii=False)
print(f"hooks -> {hooks_path} ({len(hooks)} variant(s))")
PY
echo "VARIANT -> $OUTB"

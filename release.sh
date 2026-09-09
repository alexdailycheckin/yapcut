#!/usr/bin/env bash
# release.sh: the one release command. Releases used to be six hand steps across two repos and
# three got skipped on 2026-09-09 (no changelog for 3.4.6, README eight releases stale, the
# author's own machine one release behind his push).
#
#   ./release.sh <plugin> <version> "<one-line note>"
#
# Refuses on a dirty tree or a HEAD behind origin. Sets the version in plugin.json and the
# marketplace's top-level version, checks the CHANGELOG carries an entry for the version,
# rewrites the README "What's new" header from it, runs the privacy gate in --history mode and
# the fast tests, commits, tags, pushes, then updates the local marketplace clone and the
# installed plugin and relinks the workspace engine.
set -euo pipefail
cd "$(dirname "$0")"
PLUGIN="${1:-}"; VERSION="${2:-}"; NOTE="${3:-}"; SKIP_HISTORY="${4:-}"
[ -n "$PLUGIN" ] && [ -n "$VERSION" ] && [ -n "$NOTE" ] || { echo "usage: ./release.sh <plugin> <version> \"<note>\" [--skip-history]"; exit 1; }
[ -d "plugins/$PLUGIN" ] || { echo "no such plugin: $PLUGIN"; exit 1; }

git fetch -q origin
[ -z "$(git status --porcelain)" ] || { echo "dirty tree: commit or stash first (a release from a dirty tree ships whatever happens to be on disk)"; git status --short | head; exit 1; }
[ "$(git rev-list --count HEAD..origin/main)" = "0" ] || { echo "HEAD is behind origin/main: pull first"; exit 1; }
grep -qE "^## What's new in .*\b$VERSION\b" CHANGELOG.md || { echo "CHANGELOG.md has no '## What's new in ... $VERSION' entry: write it first, the README header is generated from it"; exit 1; }

python3 - "$PLUGIN" "$VERSION" <<'PY'
import json, sys, re
plugin, version = sys.argv[1:3]
p = f"plugins/{plugin}/.claude-plugin/plugin.json"; d = json.load(open(p)); d["version"] = version
json.dump(d, open(p, "w"), indent=2); open(p, "a").write("\n")
m = json.load(open(".claude-plugin/marketplace.json")); m.get("metadata", {}).pop("version", None)
if plugin == "outlier-radar":   # the marketplace version tracks the flagship plugin only
    m["version"] = version
    r = open("README.md").read()
    open("README.md", "w").write(re.sub(r"## What's new in [0-9.]+[^\n]*", f"## What's new in {version}", r, count=1))
json.dump(m, open(".claude-plugin/marketplace.json", "w"), indent=2); open(".claude-plugin/marketplace.json", "a").write("\n")
print(f"{plugin} -> {version}" + ("; marketplace and README header follow it" if plugin == "outlier-radar" else "; marketplace version unchanged (tracks outlier-radar)"))
PY

if [ "$SKIP_HISTORY" = "--skip-history" ]; then
  echo "WARNING: history scan skipped on request. Private strings remain reachable in public git history until the rewrite in yapcut-alex/archive/history-rewrite-2026-09-09/RUNBOOK.md runs. Do not make a habit of this flag."
else
  bash .githooks/pre-commit --history || { echo "history scan failed: private material is reachable in git history. Run the rewrite runbook, or pass --skip-history knowingly."; exit 1; }
fi
if [ -x tests/run.sh ]; then tests/run.sh --fast || { echo "fast tests failed"; exit 1; }; fi

git add -A
if git diff --cached --quiet; then echo "version already at $VERSION in the tree; tagging HEAD"; else git commit -m "$PLUGIN $VERSION: $NOTE"; fi
git tag -f -a "$PLUGIN-v$VERSION" -m "$NOTE"
git push origin main --tags

if command -v claude >/dev/null 2>&1; then
  claude plugin marketplace update yapcut || echo "run by hand: claude plugin marketplace update yapcut"
  claude plugin update "$PLUGIN@yapcut" || echo "run by hand: claude plugin update $PLUGIN@yapcut"
fi
WS="$HOME/Desktop/Claude/yapcut-alex"
[ -x "$WS/relink-engine.sh" ] && "$WS/relink-engine.sh" || true
# prune cache dirs older than the installed version
python3 - "$PLUGIN" <<'PY'
import json, os, shutil, sys
plugin = sys.argv[1]
reg = json.load(open(os.path.expanduser("~/.claude/plugins/installed_plugins.json")))["plugins"].get(f"{plugin}@yapcut", [])
if reg:
    keep = reg[0]["version"]; base = os.path.expanduser(f"~/.claude/plugins/cache/yapcut/{plugin}")
    for d in os.listdir(base) if os.path.isdir(base) else []:
        if d != keep and os.path.isdir(os.path.join(base, d)):
            shutil.rmtree(os.path.join(base, d)); print("pruned cache", d)
PY
echo "released $PLUGIN $VERSION"

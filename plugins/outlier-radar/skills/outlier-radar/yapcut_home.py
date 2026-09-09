#!/usr/bin/env python3
"""yapcut_home.py: the ONE workspace resolver for every YapCut script.

Both plugins import this (the editor ships a byte-identical copy under
scripts/yaplib/home.py). Resolution order, and there is no other:

  1. --dir <path> or --dir=<path> on the command line (consumed from argv)
  2. $YAPCUT_HOME, then the legacy $OUTLIER_RADAR_HOME / $LEAD_MAGNET_HOME
  3. the current directory, if it holds radar-config.json, brand-config.json or brand.json
  4. ~/outlier-radar, under the same test

Nothing else. In particular there is NO fallback to the skill folder: that fallback is
how six scripts run from ~/Desktop/Claude quietly graded the bundled example week inside
the plugin cache and exited 0 (audit, 2026-09-09). When no workspace is found the caller
gets a clear exit 2 naming every place that was looked in, or None when required=False.

Never Path.resolve() here. Every script is reachable through a symlink from a workspace,
and resolve() follows it out of the workspace into the plugin cache. abspath/expanduser
do not resolve symlinks.
"""
import os
import pathlib
import sys

MARKERS = ("radar-config.json", "brand-config.json", "brand.json")
ENV_KEYS = ("YAPCUT_HOME", "OUTLIER_RADAR_HOME", "LEAD_MAGNET_HOME")
DEFAULT = "~/outlier-radar"


def _p(s):
    return pathlib.Path(os.path.abspath(os.path.expanduser(str(s))))


def is_home(p):
    p = _p(p)
    return any((p / m).exists() for m in MARKERS)


def radar_home(argv=None, required=True):
    """Return the workspace path. Consumes --dir from argv (sys.argv by default)."""
    argv = sys.argv if argv is None else argv
    looked = []
    for i, a in enumerate(list(argv)):
        if a == "--dir" and i + 1 < len(argv):
            home = _p(argv[i + 1]); del argv[i:i + 2]; return home
        if a.startswith("--dir="):
            home = _p(a.split("=", 1)[1]); del argv[i]; return home
    for k in ENV_KEYS:
        v = os.environ.get(k)
        if v:
            return _p(v)
    cwd = _p(os.getcwd())
    if is_home(cwd):
        return cwd
    looked.append(str(cwd))
    default = _p(DEFAULT)
    if is_home(default):
        return default
    looked.append(str(default))
    if not required:
        return None
    sys.stderr.write(
        "no YapCut workspace found. Looked for radar-config.json / brand-config.json in:\n"
        + "".join(f"  {p}\n" for p in looked)
        + "Pass --dir <workspace>, or export YAPCUT_HOME=<workspace>.\n"
        "A fresh install has no workspace until discovery creates one (say: run outlier radar).\n")
    sys.exit(2)


def voice_dir(argv=None):
    return radar_home(argv) / "voice-corpus"


if __name__ == "__main__":
    print(radar_home())

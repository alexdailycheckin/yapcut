#!/usr/bin/env python3
"""voice_home.py: workspace resolution for the voice stack. Imported, not run.

Two rules here, both learned by breaking them.

1. **NEVER `Path.resolve()`.** Every script in this skill is reachable through a symlink
   (the reference deployment symlinks each one into a working directory). `resolve()`
   follows the symlink out of the workspace and into the skill folder, so anything that
   located workspace data that way silently looked in the wrong place. That is exactly what
   disabled `spoken_lint.py --corpus` for a week: it printed one "no corpus" line and
   exited on every run it ever had, while the constant it was supposed to replace sat
   underneath a comment telling the reader to derive it from the corpus. Use
   `os.path.abspath`, which does not resolve symlinks.

2. **Follow the documented resolution order**, the same one the playbook and the other
   scripts use, so the voice stack cannot disagree with the rest of the skill about where
   the workspace is: `--dir`, then `$OUTLIER_RADAR_HOME`, then a directory containing
   `radar-config.json`, then `~/outlier-radar`.
"""
import os
import pathlib
import sys


def radar_home(argv=None):
    argv = sys.argv if argv is None else argv
    if "--dir" in argv:
        i = argv.index("--dir")
        home = pathlib.Path(argv[i + 1]).expanduser()
        del argv[i:i + 2]
        return home
    env = os.environ.get("OUTLIER_RADAR_HOME")
    if env:
        return pathlib.Path(env).expanduser()
    cwd = pathlib.Path.cwd()
    if (cwd / "radar-config.json").exists() or (cwd / "voice-corpus").is_dir():
        return cwd
    # no resolve(): see rule 1
    here = pathlib.Path(os.path.abspath(__file__)).parent
    for cand in (here, here.parent):
        if (cand / "radar-config.json").exists() or (cand / "voice-corpus").is_dir():
            return cand
    default = pathlib.Path("~/outlier-radar").expanduser()
    if (default / "radar-config.json").exists() or (default / "voice-corpus").is_dir():
        return default
    return cwd


def voice_dir(argv=None):
    return radar_home(argv) / "voice-corpus"

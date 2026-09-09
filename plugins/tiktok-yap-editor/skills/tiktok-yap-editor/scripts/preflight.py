#!/usr/bin/env python3
"""Preflight check for the tiktok-yap-editor pipeline.

Verifies the exact tools the pipeline depends on and prints install hints for
anything missing. Run this first so you fail fast with a clear fix instead of
discovering a missing dependency three steps into a render.

Checks, in order: ffmpeg + ffprobe, the libass `ass` filter (the ONE caption
burn path; the Pillow PNG-overlay fallback was removed 2026-09-09 along with
caption_frames.py and compose.sh), whisper-cli + a ggml model, every Python
package listed in requirements.txt (repo root), the fonts the default presets
name, and that the shipped brand-config.default.json agrees with yaplib.brand.

Exit 0 when everything passes, 1 otherwise.
"""
import glob
import importlib
import os
import re
import shutil
import subprocess
import sys

SCRIPTS = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, SCRIPTS)
from yaplib import brand, fonts  # noqa: E402

# pip name -> import name, for the packages a requirements line may carry
IMPORT_NAMES = {"pillow": "PIL", "fonttools": "fontTools", "pyyaml": "yaml"}

ok = True


def check(label, passed, hint=""):
    global ok
    mark = "OK " if passed else "MISSING"
    print(f"  [{mark}] {label}")
    if not passed:
        ok = False
        if hint:
            print(f"          fix: {hint}")


def find_requirements():
    """requirements.txt at the repo root: walk up from scripts/ until found."""
    d = SCRIPTS
    for _ in range(7):
        cand = os.path.join(d, "requirements.txt")
        if os.path.isfile(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    return None


def fc_has(family):
    try:
        out = subprocess.run(["fc-list"], capture_output=True, text=True, check=True).stdout
        return family.lower() in out.lower()
    except (OSError, subprocess.CalledProcessError):
        return False


print("=== tiktok-yap-editor preflight ===")

# ffmpeg + ffprobe
has_ffmpeg = shutil.which("ffmpeg") is not None
check("ffmpeg", has_ffmpeg, "brew install ffmpeg-full && brew link --overwrite --force ffmpeg-full")
check("ffprobe", shutil.which("ffprobe") is not None, "comes with ffmpeg")

# the ass filter: build_ass.py + compose_ass.sh is the only caption path
if has_ffmpeg:
    try:
        filters = subprocess.run(["ffmpeg", "-hide_banner", "-filters"],
                                 capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        filters = ""
        print(f"          (ffmpeg -filters failed: {e})")
    has_ass = " ass " in filters or " subtitles " in filters
    check("libass / ass filter (the caption burn path)", has_ass,
          "the default `ffmpeg` bottle lacks libass. Install the full build:\n"
          "          brew install ffmpeg-full && brew link --overwrite --force ffmpeg-full\n"
          "          (if a later `brew upgrade` relinks the minimal ffmpeg, re-run the link command)")

# whisper.cpp + model
check("whisper-cli (whisper.cpp)", shutil.which("whisper-cli") is not None, "brew install whisper-cpp")
models = glob.glob(os.path.expanduser("~/.whisper-models/ggml-*.bin"))
env_model = os.environ.get("WHISPER_MODEL", "")
check("whisper ggml model (~/.whisper-models/ or $WHISPER_MODEL)",
      bool(models) or os.path.isfile(os.path.expanduser(env_model)),
      "mkdir -p ~/.whisper-models && curl -L -o ~/.whisper-models/ggml-small.en.bin "
      "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin")
if models:
    print(f"          found: {', '.join(os.path.basename(m) for m in models)}")

# python packages: whatever requirements.txt lists must import
req = find_requirements()
if req:
    print(f"  requirements: {req}")
    for line in open(req, encoding="utf-8"):
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        name = re.split(r"[<>=!~\[;\s]", line, 1)[0]
        mod = IMPORT_NAMES.get(name.lower(), name)
        try:
            importlib.import_module(mod)
            check(f"python package {name}", True)
        except Exception:
            check(f"python package {name}", False, f"pip3 install {name}")
else:
    check("requirements.txt (repo root)", False,
          "the file is missing from this checkout; checking Pillow directly")
    try:
        importlib.import_module("PIL")
        check("python package Pillow", True)
    except Exception:
        check("python package Pillow", False, "pip3 install Pillow")

# fonts the default presets name. Resolved by family through yaplib.fonts (the
# same lookup every script uses), with fontconfig as a second opinion.
for fam in ["Montserrat Black", "Anton"]:
    check(f"{fam} font (default presets)", fonts.is_installed(fam) or fc_has(fam),
          "run: bash scripts/setup_fonts.sh  (installs the fonts + a static "
          "Montserrat Black; the cask alone ships a variable font that renders Thin)")

# the shipped default brand config must agree with the code defaults
bad = brand.self_check()
check("brand-config.default.json agrees with yaplib.brand DEFAULTS", not bad, "; ".join(bad))

print("=== " + ("ALL GOOD" if ok else "FIX THE MISSING ITEMS ABOVE") + " ===")
sys.exit(0 if ok else 1)

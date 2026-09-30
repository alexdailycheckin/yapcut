"""Glue between a finished yapcut cut and the HyperFrames kit.

from_yap() finds the caption-free cut, the corrected words and the finished voice for one video
in a yapcut workdir, and returns an Episode themed from that creator's brand-config.json.
run() builds it, carves the music bed around the voice once, runs `hyperframes check`,
snapshots every card at the moment before it leaves (the containment check the linter cannot
do), and with "render" writes the MP4.

    ep = from_yap("episode-01", "/path/to/footage/folder", show=True)
    ...cards...
    run(ep, sys.argv[1:], out="/path/to/output/episode-01.mp4")
"""
import os, subprocess, sys, json

HERE = os.path.dirname(os.path.realpath(__file__))
SCRIPTS = os.path.dirname(HERE)
sys.path.insert(0, SCRIPTS)
from hfkit.kit import Episode  # noqa: E402
from hfkit.themes.cards import from_brand  # noqa: E402

HFV = "hyperframes@0.8.96"


def _library(explicit=None):
    if explicit:
        return explicit
    from hfkit.sfx_library import default_dir
    return os.path.join(default_dir(), "library.json")


def from_yap(name, workdir, show=False, final=None, root=None, library=None, theme=None):
    """name: the video's stem in <workdir>/.yap_build (full_<name>.mp4, w_<name>.json).
    final: the finished yapcut MP4 whose loudness-normalized audio becomes the voice; without it
    the cut's own audio is normalized to -14 LUFS."""
    from yaplib import words as yw, brand
    b = os.path.join(workdir, ".yap_build")
    cut = next((p for p in (os.path.join(b, f"full_{name}.nopunch.mp4"), os.path.join(b, f"full_{name}.mp4")) if os.path.exists(p)), None)
    if not cut:
        raise SystemExit(f"no cut for {name} in {b}: run yapcut first")
    root = root or os.path.join(workdir, ".hyperframes", name)
    os.makedirs(root, exist_ok=True)
    ws = [list(w) for w in yw.load_words(os.path.join(b, f"w_{name}.json"))]
    corr = os.path.join(b, f"{name}_corrections.json")
    if os.path.exists(corr):
        ws = yw.apply_corrections(ws, corr)
    words = os.path.join(root, "words.json")
    json.dump([{"t0": round(w[0], 3), "t1": round(w[1], 3), "w": w[2]} for w in ws], open(words, "w"))
    voice = os.path.join(root, "voice.m4a")
    src = final if final and os.path.exists(final) else cut
    af = [] if src == final else ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"]
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", src, "-vn", *af, "-c:a", "aac", "-b:a", "192k", voice], check=True)
    if theme is None:
        theme = from_brand(brand.load(workdir=b))
    return Episode(name, words=words, footage=cut, voice=voice, theme=theme, show=show, project_root=root, library=_library(library))


def sh(cmd, cwd):
    print("$", " ".join(cmd))
    return subprocess.run(cmd, cwd=cwd)


def run(ep, args=(), out=None):
    root = ep.build()
    if not os.path.exists(os.path.join(root, ".bed.carved.html")):
        print("carve:", "ok" if ep.carve() else "skipped, bed stays flat at the theme volume")
    r = sh(["npx", "-y", HFV, "check"], root)
    snaps = sorted({s for s in ep.snaps if 0 < s < ep.dur})
    if snaps:
        sh(["npx", "-y", HFV, "snapshot", "--no-end", "--at", ",".join(f"{s:.2f}" for s in snaps), "-o", "snapshots", "--describe", "false"], root)
        print(f"look at every frame in {root}/snapshots before rendering: a card whose content leaves its box fails there, not in check")
    if "render" in args:
        out = out or os.path.join(root, f"{ep.name}.mp4")
        sh(["npx", "-y", HFV, "render", "-o", out], root)
    return r.returncode

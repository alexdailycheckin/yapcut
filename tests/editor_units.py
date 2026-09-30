#!/usr/bin/env python3
"""editor_units.py: the editor contracts that need no footage, no whisper and no fonts.

Each one pins a defect from the 2026-09-30 batch:
  - a per-video brand-config.json in <footage>/.yap_build made that folder the workspace,
    so finalize delivered into it and logged the filmed event there (yaplib/home.py)
  - an index-keyed caption drop deleted a real word after a re-cut (yaplib/words.py)
  - the hook fitter wrapped an over-wide first line into an orphan word, and the minimal
    style drew the claim on line two at 55% (build_ass.py)
  - receipts defaulted to under the caption for the whole video (burn_pips.py)
Exit 0 clean, 2 with every failure listed.
"""
import contextlib, filecmp, io, json, os, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
SCRIPTS = os.path.join(ROOT, "plugins/tiktok-yap-editor/skills/tiktok-yap-editor/scripts")
RADAR = os.path.join(ROOT, "plugins/outlier-radar/skills/outlier-radar")
sys.path.insert(0, SCRIPTS)
fails = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        fails.append(msg)


# --- workspace resolver -------------------------------------------------------
check(filecmp.cmp(os.path.join(SCRIPTS, "yaplib/home.py"), os.path.join(RADAR, "yapcut_home.py"), shallow=False),
      "yaplib/home.py and yapcut_home.py are byte-identical")
from yaplib import home  # noqa: E402
with tempfile.TemporaryDirectory() as t:
    ws, build = os.path.join(t, "ws"), os.path.join(t, "ws", "input", "sep 1", ".yap_build")
    os.makedirs(build)
    for d in (ws, build):
        json.dump({}, open(os.path.join(d, "brand-config.json"), "w"))
    check(home.is_home(ws), "a folder with brand-config.json is a workspace")
    check(not home.is_home(build), "a .yap_build with only brand-config.json is not a workspace")
    check(not home.is_home(os.path.join(build, "evidence")), "nothing under a .yap_build is a workspace")
    json.dump({}, open(os.path.join(build, "radar-config.json"), "w"))
    check(home.is_home(build), "radar-config.json marks a workspace even inside .yap_build")

# --- caption corrections that name their word ---------------------------------
from yaplib import words as ywords  # noqa: E402
W = [(0, 1, "Acme"), (1, 2, "sold"), (2, 3, "software"), (3, 4, "to"), (4, 5, "chat,"), (5, 6, "-")]
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "c.json")

    def run(c):
        json.dump(c, open(p, "w"))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            out = [w[2] for w in ywords.apply_corrections(W, p)]
        return out, err.getvalue()

    out, err = run({"drop": {"2": {"from": "-"}}, "fix": {"4": {"from": "chat", "to": "ChatGPT"}}})
    check("software" in out and "ChatGPT" in out, f"a stale named drop is skipped, a live named fix applies: {out}")
    check("is at #5 now" in err, "the stale entry is reported with where its word sits now")
    out, _ = run({"drop": [1], "fix": {"0": "Acme Labs"}})
    check(out[:2] == ["Acme Labs", "software"], f"legacy list drop and string fix still apply blind: {out}")
    out, _ = run({"drop": [{"index": 5, "from": "-"}]})
    check(out[-1] == "chat,", f"a list drop entry with 'from' applies while it matches: {out}")

# --- hook fitter and style ----------------------------------------------------
sys.argv = ["build_ass.py"]
import build_ass  # noqa: E402
NOFONT = "No Such Font For Tests"          # forces the char-width estimate: same on every machine
lines, size, _ = build_ass.fit_hook(["Reasons to follow", "or unfollow me"], NOFONT, False, 0, 120, 972, 3, 54)
check(lines == ["Reasons to follow", "or unfollow me"] and 54 <= size < 120,
      f"an over-wide line 1 shrinks before it wraps (no orphan word): {lines} at {size}px")
lines, size, _ = build_ass.fit_hook(["Your pricing page is lying to every buyer you have"], NOFONT, False, 0, 120, 972, 3, 54)
check(len(lines) > 1, f"a line that cannot fit at the floor still wraps: {lines} at {size}px")
check(build_ass.minimal_demoted(["ChatGPT ads:", "$1 billion in", "under 200 days"]) == 1,
      "minimal becomes outline when line two is longer than line one")
check(build_ass.minimal_demoted(["Nobody reads your deck", "(and why)"]) == 0,
      "minimal stays when line two is small print")

# --- receipt placement --------------------------------------------------------
import burn_pips  # noqa: E402
meta = {"hook": {"top": 200, "bottom": 659, "secs": 5.0}, "caption_band": {"top": 1220, "bottom": 1420}}
def place(p, iw, ih):
    with contextlib.redirect_stdout(io.StringIO()):
        return burn_pips.fit_pip(p, iw, ih, meta)


w, y = place({"file": "a.png", "start": 8.0, "end": 10.0}, 1440, 810)
check(y == 180 and y + int(w * 810 / 1440) <= 440, f"a pip without y after the hook sits in the band above the head: y {y}, w {w}")
w, y = place({"file": "b.png", "start": 0.0, "end": 4.0}, 1240, 300)
check(y == 1424 and w <= 620 and y + int(w * 300 / 1240) <= 1580,
      f"a pip without y during the hook sits under the caption, above the bottom chrome: y {y}, w {w}")
w, y = place({"file": "c.png", "start": 5.0, "end": 6.5, "w": 640, "y": 170}, 1280, 400)
check((w, y) == (640, 170), f"an explicit y is honoured: y {y}, w {w}")

# --- finalize warns when it would deliver into a build folder -----------------
with tempfile.TemporaryDirectory() as t:
    foot = os.path.join(t, "input", "sep 1"); build = os.path.join(foot, ".yap_build")
    os.makedirs(build)
    final = os.path.join(build, "clip.mp4"); open(final, "wb").write(b"\0" * 64)
    env = dict(os.environ, YAPCUT_HOME=os.path.join(t, "ws"), HOME=t)
    env.pop("YAP_LIBRARY", None)
    r = subprocess.run(["bash", os.path.join(SCRIPTS, "finalize.sh"), final, foot, "clip", "--standalone",
                        "--out-dir", os.path.join(build, "output", "sep 1")],
                       capture_output=True, text=True, env=env, cwd=build)
    check(r.returncode == 0 and "WARNING the output dir resolved inside a build directory" in r.stdout,
          f"finalize warns on an output dir inside .yap_build (rc {r.returncode})")

if fails:
    print(f"{len(fails)} failure(s)")
    sys.exit(2)

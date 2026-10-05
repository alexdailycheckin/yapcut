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

# --- HyperFrames kit: anchors, counters, containment, sounds, no brand ----------
from hfkit import kit as hk  # noqa: E402
from hfkit.themes.cards import from_brand, build as theme_build  # noqa: E402
with tempfile.TemporaryDirectory() as t:
    words = [{"t0": 0.1 + 0.4 * i, "t1": 0.45 + 0.4 * i, "w": w} for i, w in enumerate(
        "Acme bought a spreadsheet startup. It is running at $7 billion a year. That's a bet.".split())]
    json.dump(words, open(os.path.join(t, "w.json"), "w"))
    clip = os.path.join(t, "cut.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=gray:s=1080x1920:d=8", "-f", "lavfi", "-i",
                    "anullsrc=r=48000:cl=stereo", "-t", "8", "-shortest", "-c:v", "libx264", "-c:a", "aac", clip], check=True)
    lib = os.path.join(t, "lib"); os.makedirs(os.path.join(lib, "files"))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono", "-t", "1", os.path.join(lib, "files", "x.mp3")], check=True)
    json.dump({tag: {"file": "files/x.mp3", "seconds": 1.0} for tag in ("card_in", "card_in_heavy", "headline", "counter", "money", "pop",
               "slam", "bed_corporate")}, open(os.path.join(lib, "library.json"), "w"))
    ep = hk.Episode("unit", words=os.path.join(t, "w.json"), footage=clip, voice=clip, project_root=os.path.join(t, "p"),
                    library=os.path.join(lib, "library.json"))
    check(ep.t("running at $7 billion") == 2.9 and ep.e("a spreadsheet startup") == 2.05, "phrase anchors read the cut's own seconds")
    try:
        ep.t("never said this"); check(False, "an unknown phrase stops the build")
    except SystemExit:
        check(True, "an unknown phrase stops the build")
    f = hk._fmt({"pre": "$", "suf": " billion", "dec": 1}, 7, final="$7 billion")
    check(len(hk._widest(f)) == len("$7.0 billion") and hk._num(hk._fmt("rank", 1), 100) == "#100", "counters measure their widest text first")
    ep.hook(["Acme just", "bought a spreadsheet"], spark="spreadsheet")
    ep.counter(7, {"pre": "$", "suf": " billion", "dec": 1}, 3.0, ep.t("$7 billion"), 2.7, 6.0, "Run rate", "example.com", "1 Jan 2026")
    ep.title("That's a bet.", 6.0, ep.dur, slam_at=ep.t("thats a bet"))
    ep.push(0.5, 2.0); ep.push(2.2, 3.0)
    try:
        ep.build(); check(False, "overlapping push-ins are refused")
    except SystemExit:
        check(True, "overlapping push-ins are refused")
    ep.pushes = [(0.5, 2.0, 1.05)]; ep._built = False
    html = open(os.path.join(ep.build(), "index.html")).read()
    check("{{" not in html and "document.fonts.ready" in html and ".flowrow" in html, "the page fits rows to their card after fonts load")
    check('src="assets/lib/x.mp3"' in html and os.path.exists(os.path.join(t, "p", "assets", "lib", "x.mp3")), "sounds come from the library by tag")
    check(ep.snaps and all(0 < s < ep.dur for s in ep.snaps), "every card has a snapshot time before it leaves")
    neutral = from_brand({})
    check(neutral["contact"] is None and neutral["star"] is None, "the default theme carries no creator's brand")
    th = from_brand({"accent_hex": "#1570EF", "ink_hex": "#101010", "handle": "YOU.COM", "contact_lines": ["you@you.com"]})
    check("#1570EF" in th["css"] and th["contact"] == ["YOU.COM", "you@you.com"], "the theme reads accent, ink and contact from brand-config")
    check(theme_build("#E8232F")["css"] == theme_build("#E8232F")["css"], "the theme build is deterministic")
    # the two-sided chart (3.7.0): rows build as they are said, the newest right cell is lit, cells stay one line
    ep2 = hk.Episode("pairs", words=os.path.join(t, "w.json"), footage=clip, voice=clip, project_root=os.path.join(t, "p2"),
                     library=os.path.join(lib, "library.json"))
    ep2.pairs(("If you want", "You need"), [dict(left="Replies", right="One line about them", at=0.2, right_at=0.4),
                                            dict(left="Referrals", right="Ask the same day", at=3.0, right_at=3.6)], 1.0, 7.0)
    h2 = open(os.path.join(ep2.build(), "index.html")).read()
    check('class="pairs"' in h2 and "If you want" in h2 and h2.count('class="prow"') == 2, "pairs draws a head and one row per item")
    check('q("#pr1r1")' in h2 and 'q("#pr1r0")' not in h2, "a row said before the card lands is drawn with it; a later row builds on its line")
    check("height: 0, marginTop: 0, opacity: 0" in h2, "a row not said yet takes no room, so the card grows a row at a time")
    ep3 = hk.Episode("hook0", words=os.path.join(t, "w.json"), footage=clip, voice=clip, project_root=os.path.join(t, "p3"),
                     library=os.path.join(lib, "library.json"))
    ep3.hook(["$22.6 billion", "to sell more"], count=dict(line=0, token="$22.6", value=22.6, fmt={"pre": "$", "dec": 1}))
    h3 = open(os.path.join(ep3.build(), "index.html")).read()
    check("$22.6" in h3 and "$0.0" not in h3, "a number on the hook's first line is drawn at its final value at frame zero")
    check('tl.set("#pr1h0", {opacity: 0}, 3.6)' in h2 and 'tl.set("#pr1h1", {opacity: 1}, 3.6)' in h2, "the newest right cell lights as the one before it settles")
    check('document.querySelectorAll(".pairs")' in h2, "the chart scales its type together so every cell stays on one line")


# --- what's new: shown once per version, the minor line on a first run, never crashes ---
sys.path.insert(0, os.path.join(ROOT, "plugins/tiktok-yap-editor/hooks"))
import whats_new as wn  # noqa: E402
es = wn.entries()
check(es and all(e[2] and e[3] for e in es), "every WHATS-NEW.md entry has a title and a body")
cur = wn.current()
check(any(e[1] == cur for e in es), f"WHATS-NEW.md has an entry for the current version {cur}")
fake = [((3, 5, 1), "3.5.1", "b", "x"), ((3, 5, 0), "3.5.0", "a", "x"), ((3, 4, 0), "3.4.0", "old", "x")]
check([e[1] for e in wn.pending("3.5.1", None, fake)] == ["3.5.1", "3.5.0"], "a machine with no record sees the current minor line")
check([e[1] for e in wn.pending("3.5.1", "3.5.0", fake)] == ["3.5.1"] and wn.pending("3.5.1", "3.5.1", fake) == [],
      "a machine sees only what it has not seen")
with tempfile.TemporaryDirectory() as t:
    wn.SEEN = os.path.join(t, "seen.json")
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        sys.stdin = io.StringIO('{"source": "startup"}'); wn.hook()
    first = out.getvalue()
    out2 = io.StringIO()
    with contextlib.redirect_stdout(out2):
        sys.stdin = io.StringIO('{"source": "startup"}'); wn.hook()
    d = json.loads(first) if first.strip() else {}
    check(d.get("hookSpecificOutput", {}).get("hookEventName") == "SessionStart" and d.get("systemMessage"), "the hook prints a banner and a notice")
    check(out2.getvalue() == "", "the notice shows once")
    wn.SEEN = os.path.join(t, "fresh", "seen.json")
    out3 = io.StringIO()
    with contextlib.redirect_stdout(out3):
        sys.stdin = io.StringIO("not json"); wn.hook()
    check(True, "a broken hook input never fails the session")
    sys.stdin = sys.__stdin__
check(filecmp.cmp(os.path.join(ROOT, "plugins/tiktok-yap-editor/hooks/whats_new.py"),
                  os.path.join(ROOT, "plugins/outlier-radar/hooks/whats_new.py"), shallow=False),
      "both plugins ship the same whats_new.py")
radar_meta = json.load(open(os.path.join(ROOT, "plugins/outlier-radar/.claude-plugin/plugin.json")))
check(max(e[0] for e in wn.entries(os.path.join(ROOT, "plugins/outlier-radar/WHATS-NEW.md"))) >= wn.vt(radar_meta["version"]),
      f"outlier-radar WHATS-NEW.md is not behind the plugin ({radar_meta['version']})")
with tempfile.TemporaryDirectory() as t:
    man = os.path.join(t, "voice-corpus", "manual"); os.makedirs(man)
    json.dump({}, open(os.path.join(t, "radar-config.json"), "w"))
    open(os.path.join(man, "vlog.md"), "w").write("register: personal\nform: monologue\n\n" + "word " * 3000)
    open(os.path.join(man, "rant.md"), "w").write("register: work\nform: monologue\n\n" + "word " * 900)
    check(wn._work_monologue_words(os.path.join(t, "voice-corpus")) < wn.WORK_MONOLOGUE_WORDS,
          "an off-subject monologue does not count toward the voice supply")
    open(os.path.join(man, "rant2.md"), "w").write("register: work\nform: monologue\n\n" + "word " * 2000)
    check(wn._work_monologue_words(os.path.join(t, "voice-corpus")) >= wn.WORK_MONOLOGUE_WORDS,
          "twenty minutes of on-subject monologue clears the voice check")

# --- logo picker (3.7.2): Wikipedia's category-class coin shipped as three brands' logos -------
import logo_fetch  # noqa: E402
PAGES = {
    "Yahoo": {"wikitext": "{{Infobox company\n| name = Yahoo\n| logo = Yahoo! (2019).svg\n| type = Subsidiary\n}}",
              "images": ["File:Symbol category class.svg", "File:Yahoo! (2019).svg", "File:Commons-logo.svg"]},
    "ChatGPT": {"wikitext": "{{Infobox software\n| logo = [[File:OpenAI logo 2025 (symbol).svg|class=skin-invert|120px]]\n}}",
                "images": ["File:Countries where ChatGPT is available.svg", "File:Symbol category class.svg"]},
    "Acme": {"wikitext": "{{Infobox company\n| name = Acme\n}}",
             "images": ["File:Symbol category class.svg", "File:Acme headquarters.jpg", "File:Acme logo 2020.svg"]},
}


def fake_api(params):
    page = PAGES[params.get("page") or params.get("titles")]
    if params["action"] == "parse":
        return {"parse": {"wikitext": {"*": page["wikitext"]}}}
    return {"query": {"pages": {"1": {"images": [{"title": t} for t in page["images"]]}}}}


logo_fetch.api = fake_api
check(logo_fetch.pick_logo_file("Yahoo") == "File:Yahoo! (2019).svg", "the infobox logo wins over the category-class coin")
check(logo_fetch.pick_logo_file("ChatGPT") == "File:OpenAI logo 2025 (symbol).svg",
      "an infobox logo inside [[File:...|120px]] is read, not a chart that names the brand")
check(logo_fetch.pick_logo_file("Acme") == "File:Acme logo 2020.svg",
      "with no infobox logo the guess skips Wikipedia's icons and prefers a logo file")


if fails:
    print(f"{len(fails)} failure(s)")
    sys.exit(2)

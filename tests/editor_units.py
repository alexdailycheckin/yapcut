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
    _, caps = ep._captions()
    check(all(b["t0"] >= a["t1"] for a, b in zip(caps, caps[1:])), "a caption group leaves before the next one shows")
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
    # the bed carve (3.7.8): media-treatment --apply stamps data-hf-id ahead of id="bed" before carve runs
    open(os.path.join(ep.root, "index.html"), "w").write(
        html.replace('<audio id="bed"', '<audio data-hf-id="hf-unit" id="bed" data-fx-carve="{}"', 1))
    os.makedirs(os.path.join(t, "home", ".claude", "skills", "hyperframes-audio", "scripts"))
    open(os.path.join(t, "home", ".claude", "skills", "hyperframes-audio", "scripts", "carve.mjs"), "w").close()
    run0, home0, ep.core = subprocess.run, os.environ["HOME"], t
    subprocess.run, os.environ["HOME"] = (lambda *a, **k: subprocess.CompletedProcess(a, 0, "", "")), os.path.join(t, "home")
    try:
        carved = ep.carve()
    finally:
        subprocess.run, os.environ["HOME"] = run0, home0
    saved = open(os.path.join(ep.root, ".bed.carved.html")).read() if carved else ""
    check(saved.startswith('<audio id="bed"') and "data-fx-carve" in saved and "data-hf-id" not in saved,
          "carve finds the bed behind a data-hf-id stamp and saves it unstamped for the next build")
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

# --- cutter (3.7.3): a soft word at the edge of a pause is a word, not silence ----------------
# 2026-10-05: inside protect_tail rows the pause trim cut "If" off "If this was helpful", "from"
# off "shout out from?" and the "m" off "who to buy from". Each soft word sat between the -42dB
# gate and -55dB. A synthetic take: a loud word trailing into a soft one, a 1.5s pause on a
# gated mic's -75dB floor, then a soft word leading into a loud one.
import math, random, wave  # noqa: E402
import yapcut  # noqa: E402


def take(path, parts, seed=7):
    """parts: (seconds, dB RMS, "voice" | "room"). A voice is a 140Hz harmonic stack, a room is noise."""
    rng, out, n = random.Random(seed), [], 0
    for dur, db, kind in parts:
        amp = 32768 * 10 ** (db / 20)
        for _ in range(int(dur * 16000)):
            t = n / 16000; n += 1
            if kind == "voice":
                out.append(amp / 0.8803 * sum(math.sin(2 * math.pi * 140 * k * t) / k for k in range(1, 11)))
            else:
                out.append(rng.gauss(0, amp))
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"".join(int(max(-32768, min(32767, round(x)))).to_bytes(2, "little", signed=True) for x in out))


def cut(path, end, protect=True):
    a = yapcut.parse_args(["--clauses", "-", "--out", "unit.mp4"])
    with contextlib.redirect_stdout(io.StringIO()):
        return [(A, B) for _, A, B, _ in yapcut.plan([{"src": path, "start": 0.0, "end": end, "protect_tail": protect}],
                                                     {path: yapcut.envelope(path)}, a)]


with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "soft.wav")
    take(p, [(0.3, -75, "room"), (0.6, -26, "voice"), (0.3, -48, "voice"), (1.5, -75, "room"),
             (0.2, -50, "voice"), (0.6, -26, "voice"), (0.3, -75, "room")])
    k = cut(p, 3.8)
    check(len(k) == 2 and k[0][1] >= 1.2, f"a soft word after a loud one, before a pause, is kept to its end: {k}")
    check(len(k) == 2 and k[1][0] <= 2.7, f"a soft word after a pause, before a loud one, is kept from its start: {k}")
    check(len(k) == 2 and k[1][0] - k[0][1] >= 1.2, f"the pause between them is still cut: {k}")
    p = os.path.join(t, "noisy.wav")
    take(p, [(0.3, -47, "room"), (0.6, -26, "voice"), (1.5, -47, "room"), (0.6, -26, "voice"), (0.3, -47, "room")])
    k = cut(p, 3.3)
    check(len(k) == 2 and k[1][0] - k[0][1] >= 1.0,
          f"room tone above -55dB is not a word: a noisy take's pause is still cut: {k}")
    p = os.path.join(t, "mumble.wav")
    take(p, [(0.3, -75, "room"), (0.6, -26, "voice"), (1.2, -50, "voice"), (0.6, -26, "voice"), (0.3, -75, "room")])
    k = cut(p, 3.0)
    check(len(k) == 1 and k[0][0] <= 0.3 and k[0][1] >= 2.7,
          f"a soft voice filling a whole pause is kept once, never as two keeps that overlap: {k}")

# --- cutter (3.7.5): a sentence ends under the gate and still stays in the cut ----------------
# 2026-10-11: with no protect_tail, "stopped tomorrow" lost both words to a 0.10s dip between
# them, "say that" ended on "tha-" because its fade sat at -55..-61dB, and "do it." sat 0.37s
# after "how you". With protect_tail, a clause ending past the take's last measured frame kept
# a 20ms sliver instead of the last word. The room tone of every take was -74..-79dB.
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "tail.wav")
    take(p, [(0.3, -75, "room"), (0.6, -26, "voice"), (0.2, -50, "voice"), (0.14, -66, "room"),
             (0.25, -50, "voice"), (0.15, -58, "voice"), (1.5, -75, "room"), (0.6, -26, "voice"), (0.3, -75, "room")])
    k = cut(p, 4.04, protect=False)
    check(len(k) == 2 and k[0][1] >= 1.6,
          f"soft words after a dip under the edge level, and their fade, end the first keep: {k}")
    check(len(k) == 2 and k[1][0] - k[0][1] >= 1.2, f"the pause after the sentence is still cut: {k}")
    p = os.path.join(t, "late.wav")
    take(p, [(0.3, -75, "room"), (0.6, -26, "voice"), (0.37, -75, "room"), (0.4, -48, "voice"),
             (1.5, -75, "room"), (0.6, -26, "voice"), (0.3, -75, "room")])
    k = cut(p, 4.07, protect=False)
    check(len(k) == 2 and k[0][1] >= 1.67,
          f"a soft last word a short pause after its line is kept to its end: {k}")
    check(len(k) == 2 and k[1][0] - k[0][1] >= 1.0, f"and the long pause after it is still cut: {k}")
    p = os.path.join(t, "breath.wav")
    take(p, [(0.3, -75, "room"), (0.6, -26, "voice"), (0.4, -75, "room"), (0.4, -63, "room"),
             (0.7, -75, "room"), (0.6, -26, "voice"), (0.3, -75, "room")])
    k = cut(p, 3.3, protect=False)
    check(len(k) == 2 and k[0][1] <= 1.1 and k[1][0] >= 2.2,
          f"a breath in the pause is not a word: the cut does not reach it: {k}")
    p = os.path.join(t, "end.wav")
    take(p, [(0.3, -75, "room"), (0.6, -26, "voice"), (0.6, -75, "room"), (0.3, -50, "voice"), (0.2, -75, "room")])
    k = cut(p, 2.02)
    check(len(k) == 1 and abs(k[0][1] - 2.02) < 1e-6,
          f"protect_tail on a clause that ends past the take keeps the real last word to the clause end: {k}")

# --- caption timing (3.7.7): DTW times, checked against the voice ------------------------------
import align_words as aw  # noqa: E402


def full_json(words):
    """A whisper -ojf transcript: (text, segment start s, segment end s, dtw s)."""
    return {"transcription": [{"text": " " + w, "offsets": {"from": round(a * 1000), "to": round(b * 1000)},
                               "tokens": [{"text": " " + w, "t_dtw": round(d * 100)}]} for w, a, b, d in words]}


# segment offsets stack "taken a new" inside 80 ms; DTW spreads them
w = aw.align(full_json([("taken", 9.06, 9.09, 9.20), ("a", 9.09, 9.14, 9.42), ("new", 9.14, 9.44, 9.60)]))
st = [x["offsets"]["from"] / 1000 for x in w]
check(st == [9.14, 9.36, 9.54] and all(x["offsets"]["to"] > x["offsets"]["from"] for x in w),
      f"words take DTW's times, less its 60 ms lag, not the stacked segment offsets: {st}")
# a word DTW stamps in the pause after the voice stopped moves back onto the voice
sp = [False] * 100 + [True] * 50 + [False] * 60 + [True] * 50   # voice 1.0-1.5 s, quiet, voice 2.1-2.6 s
w = aw.align(full_json([("the", 1.0, 1.2, 1.06), ("numbers.", 1.2, 1.5, 1.72), ("Next", 2.1, 2.4, 2.16)]), sp)
st = [x["offsets"]["from"] / 1000 for x in w]
check(1.18 <= st[1] <= 1.3, f"a trailing word stamped in the pause moves back onto the voice: {st}")
check(st == sorted(st), "a moved word never passes its neighbours")

# --- HDR sources (3.7.10): an HLG take is tone-mapped to SDR BT.709, an SDR take is untouched ------
# 2026-10-17: iPhone takes arrived 10-bit HLG, the cut passed the tags through, and the HyperFrames
# render took its HDR path and wrote 31 GB of raw frames. Tiny tagged clips stand in for the takes.
from yaplib import media  # noqa: E402


def tagged(path, trc, prim, space, pix):
    media.ffmpeg(["-f", "lavfi", "-i", "testsrc2=s=192x108:d=0.2:r=30", "-vf",
                  f"setparams=color_primaries={prim}:color_trc={trc}:colorspace={space}:range=tv,format={pix}",
                  "-c:v", "libx264", path], what="fixture")


def tags(path):
    s = media.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                   "stream=pix_fmt,color_transfer,color_primaries,color_space", "-of", "json", path]).stdout
    s = json.loads(s)["streams"][0]
    return s.get("pix_fmt"), s.get("color_transfer"), s.get("color_primaries"), s.get("color_space")


if media.has_tonemap_filters():
    with tempfile.TemporaryDirectory() as t:
        hlg, pq, sdr, out = (os.path.join(t, n) for n in ("hlg.mp4", "pq.mp4", "sdr.mp4", "out.mp4"))
        tagged(hlg, "arib-std-b67", "bt2020", "bt2020nc", "yuv420p10le")
        tagged(pq, "smpte2084", "bt2020", "bt2020nc", "yuv420p10le")
        tagged(sdr, "bt709", "bt709", "bt709", "yuv420p")
        check((media.hdr_kind(hlg), media.hdr_kind(pq), media.hdr_kind(sdr)) == ("HLG", "PQ", ""),
              "HLG and PQ sources read as HDR, a bt709 source as SDR")
        check(media.sdr_tonemap(sdr) == "", "an SDR source gets no tone map, so its cut is the same command")
        check("tin=smpte2084" in media.sdr_tonemap(pq), "a PQ source is linearised from PQ, not HLG")
        media.ffmpeg(["-i", hlg, "-vf", media.sdr_tonemap(hlg) + "scale=96:54", "-pix_fmt", "yuv420p",
                      *media.SDR_TAGS, out], what="tone map")
        check(tags(out) == ("yuv420p", "bt709", "bt709", "bt709"),
              f"an HLG source comes out 8-bit and tagged bt709: {tags(out)}")

        # 3.7.11: 3.7.10's mobius at npl=100 clipped faces (Apple's SDR rendering: face luma 111,
        # mobius: 184). Flat HLG greys pin the curve: mid-grey must land mid-grey, light grey must
        # roll off under white. Mobius gave Y 175 and 219 here; the tuned curve gives 93 and 146.
        def grey_y(rgb):
            g = os.path.join(t, f"g{rgb}.mp4")
            media.ffmpeg(["-f", "lavfi", "-i", f"color=c=0x{rgb}:s=64x64:d=0.1:r=30", "-vf",
                          "setparams=color_primaries=bt2020:color_trc=arib-std-b67:colorspace=bt2020nc:range=tv,"
                          "format=yuv420p10le", "-c:v", "libx264", g], what="grey fixture")
            r = media.run(["ffmpeg", "-nostdin", "-v", "error", "-i", g, "-vf", media.sdr_tonemap(g) +
                           "signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
                           "-frames:v", "1", "-f", "null", "-"]).stdout
            return float(r.split("YAVG=")[1].split()[0])
        mid, light = grey_y("808080"), grey_y("C0C0C0")
        check(80 <= mid <= 110, f"an HLG mid-grey lands mid-grey in SDR (Y {mid:.0f}; 3.7.10's mobius gave 175)")
        check(light <= 170, f"an HLG light grey rolls off under white, not clipped (Y {light:.0f}; mobius gave 219)")
else:
    print("  skip HDR tone map: this ffmpeg has no zscale/tonemap (preflight.py flags it)")


# --- the script settles its own repeats (3.8.0): 2026-10-23, five scripted cuts, every one failed a gate ---
from yaplib import script as yscript  # noqa: E402
import stutter_check as sc  # noqa: E402
SCRIPT = ("They poke at it, they make a joke about it, they poke at it again. Right now people talk to a "
          "chatbot when they're lonely. A chatbot is always there. They noticed. That's what they do. They notice.")
stoks = yscript.tokens(SCRIPT)
check(yscript.alike("notice", "noticed") and yscript.alike("belt", "built") and not yscript.alike("they", "then"),
      "alike: an inflection and a consonant skeleton match, a different word does not")
check(yscript.count(stoks, ["they", "poke", "at", "it"]) == 2, "the script says 'they poke at it' twice")
check(yscript.says_twice_near(stoks, ["a", "chatbot"], 8), "the script's own 'a chatbot ... A chatbot' is near")


def words_of(text, t=0.0):
    out = []
    for w in text.split():
        out.append((t, t + 0.3, w, sc.norm(w))); t += 0.35
    return out


take = words_of("They poke at it, they make a joke about it, they poke at it again.")
fl = [f for f in sc.find_flags(take) if "poke" in f[4]]
check(fl and sc.scripted(fl[0], take, stoks), f"a re-read the script says as often is settled: {fl}")
take3 = words_of("They poke at it, they poke at it, they make a joke about it, they poke at it again.")
fl3 = [f for f in sc.find_flags(take3) if "poke" in f[4]]
check(fl3 and not any(sc.scripted(f, take3, stoks) for f in fl3),
      "said three times where the script says it twice: still a restart")
take_r = words_of("Right now people talk to a chatbot when they're alone a chatbot is always there.")
fr = [f for f in sc.find_flags(take_r) if "chatbot" in f[4]]
check(fr and sc.scripted(fr[0], take_r, stoks), f"a written restart shape with an ad-libbed word between is settled: {fr}")
check(not (fr and sc.scripted(fr[0], take_r, stoks, free=0.0)), "nothing after the opinion slot starts is settled")
with tempfile.TemporaryDirectory() as t:
    p = os.path.join(t, "ok.json")
    json.dump(["a lot", {"key": "put googly eyes on the printer", "why": "his callback, listened"},
               {"key": "no reason given", "why": ""}], open(p, "w"))
    check(sc.load_accepted(p) == {"a lot", "put googly eyes on the printer", "no reason given"},
          "the accept-file reads bare keys and keyed entries")
    check(sc.load_accepted_high(p) == {"put googly eyes on the printer"}, "only an entry with a reason clears a HIGH")

# --- caption words from the script (3.8.0): lowercase transcript, "fineman" for Feynman --------------
import script_fix  # noqa: E402
cut = [(i * 0.4, i * 0.4 + 0.3, w) for i, w in enumerate(
    "richard fineman is my favorite example he cracked the combination logs i think they noticed it".split())]
scr = "Richard Feynman is my favorite example. He cracked the combination locks. I think they notice it.".split()
fixes, drops, swapped = script_fix.plan(cut, scr, locked=set())
got = [fixes.get(i, w[2]) for i, w in enumerate(cut)]
check(got[:2] == ["Richard", "Feynman"] and "locks." in got and got[got.index("locks.") + 1] == "I",
      f"script case, punctuation and near-miss words restored: {got}")
check(got[-2] == "noticed", f"an inflection is how it was said, never swapped for the script's: {got[-2]}")
fixes2, _, _ = script_fix.plan(cut, scr, locked={1})
check(1 not in fixes2, "a hand fix is never overridden")
fixes3, _, _ = script_fix.plan(cut, scr, locked=set(), free=cut[5][0])
check(1 in fixes3 and 8 not in fixes3, "words after the opinion slot keep their own form")

# --- the restart scan decodes a take once (3.8.0): keeps map windows to the cut, joins come from the cut ---
import xwin_scan as xs  # noqa: E402
check(xs.grid_times(1.0, 3.0, 1.1, 0.45) == [1.35, 1.8], "grid windows lie wholly inside the span, on the take's grid")
check(xs.grid_times(1.2, 3.2, 1.1, 0.45) == [1.35, 1.8], "the grid does not move when the keep's edges move")
rows = {"1.1": [[0.0, "it's the same bet we made", 1.0], [1.0, "it's the same bet we made at the company", 1.0]]}
check(any(h[0] == "x-window" for h in xs.find_hits(rows)), "two windows that do not overlap in the cut are two passes")
rows["1.1"][1][0] = 0.9
check(not any(h[0] == "x-window" for h in xs.find_hits(rows)), "windows that overlap in cut time share audio")
with tempfile.TemporaryDirectory() as t:
    a = xs.Store(os.path.join(t, "s.json")); a.put("k1", "hello"); a.save()
    b = xs.Store(os.path.join(t, "s.json")); b.put("k2", ""); c = xs.Store(os.path.join(t, "s.json")); c.put("k3", "x")
    b.save(); c.save()
    d = xs.Store(os.path.join(t, "s.json"))
    check(d.get("k1") == "hello" and d.get("k2") == "" and d.get("k3") == "x", "two stores saving one file lose nothing")
pcm = bytes(range(256)) * 400
check(xs.window_key(xs.window_bytes(pcm, 0.5, 1.1)) == xs.window_key(xs.window_bytes(pcm[:], 0.5, 1.1)) !=
      xs.window_key(xs.window_bytes(pcm, 0.95, 1.1)), "a window's key is its audio")
ev = {"kind": "x-window", "lo": 0.0, "hi": 4.0, "grams": {("they", "notice")}, "words": {"they", "notice"},
      "wins": {1.1}, "pairs": {(1.1, 0.0, 2.0)}}
toks = [(0.5, "they"), (0.8, "notice")]
check(xs.score(ev, toks)[0] >= 0.6 and xs.score(ev, toks, stoks)[0] < 0.6,
      "the merged shape is MEDIUM, unless the script says it twice right there")

# --- yapbatch (3.8.0): the failing gate and its fix are read from yapfull's log, the ETA from timed steps ---
import yapbatch  # noqa: E402
with tempfile.TemporaryDirectory() as t:
    log = os.path.join(t, "log.txt")
    open(log, "w").write("gate hook_words: ok\nGATE dead_air FAILED (rc 2). The cut is not tight: raise --silence-db.\n")
    check(yapbatch.failing_gate(log) == ("dead_air", "The cut is not tight: raise --silence-db."),
          "the failing gate and its fix come from yapfull's log")
    st = yapbatch.Status(t, ["a", "b", "c"])
    st.set("a", state="done", gates_s=300.0, after_s=200.0, has_after=True)
    st.set("b", state="gate-failed", gates_s=100.0, gate="caption", has_after=True)
    st.set("c", state="queued", has_after=True)
    left, unknown = st.eta()
    check(abs(left - 400.0) < 1 and not unknown,
          f"ETA: one queued video at the mean gate time (300, 100) plus the mean render (200): {left}")
    check("stopped at caption" in open(os.path.join(t, "batch_status.txt")).read(), "the status names the stopped gate")
    v = {"name": "x", "clauses": os.path.join(t, "clauses_x.json")}
    check(yapbatch.prescan_plan(v, t, from_cut=True) == v["clauses"], "no cut yet: prescan the clause plan")
    open(os.path.join(t, "keeps_full_x.json"), "w").write("[]")
    check(yapbatch.prescan_plan(v, t, from_cut=True).endswith("keeps_full_x.json"), "a rerun on a 1x cut: prescan its keeps")
    check(yapbatch.prescan_plan(v, t, from_cut=False) == v["clauses"], "a fresh cut: the old keeps say nothing")
    open(os.path.join(t, "full_x.mp4.speed"), "w").write("1.1")
    open(os.path.join(t, "keeps_full_x.1x.json"), "w").write("[]")
    check(yapbatch.prescan_plan(v, t, from_cut=True).endswith("keeps_full_x.1x.json"),
          "a rerun on a sped-up cut: prescan the 1x keeps, never the rescaled ones")


# --- pauses the envelope cannot see (3.8.1): 2026-10-23, wind as loud as the voice --------------------
import yapcut as ycut  # noqa: E402
from yaplib import gaps as ygaps  # noqa: E402
W = [(70.0, 71.18, "physicist."), (74.36, 74.6, "For"), (74.6, 79.29, "cabinets."), (83.18, 83.54, "Because,"),
     (83.54, 83.6, ".")]
check([c[:2] for c in ygaps.word_gap_candidates(W)] == [(71.18, 74.36), (79.29, 83.18)],
      "word gaps of 0.6s or more between spoken words, punctuation ignored")
A = ycut.parse_args(["--clauses", "x", "--out", "y"])
SRC = "take.mov"
keeps = [(SRC, 62.2, 103.4, 0.0)]
cands = {SRC: [(71.18, 74.36, "physicist", "for"), (79.29, 83.18, "cabinets", "because")]}
out, made = ycut.split_at_word_gaps(keeps, [], cands, lambda s, e1, s2: (e1, s2), A)
check([(round(x, 2), round(y, 2)) for _s, x, y, _g in out] == [(62.2, 71.3), (74.28, 79.41), (83.1, 103.4)],
      f"a keep holding two confirmed gaps is split 0.12s after each last word, 0.08s before each next: {out}")
out, _ = ycut.split_at_word_gaps(keeps, [], cands, lambda s, e1, s2: None, A)
check(out == keeps, "an unconfirmed gap is never cut")
out, _ = ycut.split_at_word_gaps(keeps, [{"src": SRC, "start": 62.3, "end": 103.4, "keep_whole": True}], cands,
                                 lambda s, e1, s2: (e1, s2), A)
check(out == keeps, "a keep_whole clause is never split")
edge = [(SRC, 62.2, 71.3, 0.0), (SRC, 73.64, 79.0, 0.0), (SRC, 72.0, 73.0, 0.0)]
out, _ = ycut.split_at_word_gaps(edge, [], {SRC: cands[SRC][:1]}, lambda s, e1, s2: (e1, s2), A)
check([(round(x, 2), round(y, 2)) for _s, x, y, _g in out] == [(62.2, 71.3), (74.28, 79.0)],
      f"a keep that starts inside the gap is trimmed to the word, one wholly inside it is dropped: {out}")
class _Inner:
    def __call__(self, s, e1, s2):
        return None
    def inner(self, s, e1, s2):
        return [(133.61, 134.79, "congratulations", "I")]
out, made = ycut.split_at_word_gaps([(SRC, 128.0, 137.1, 0.0)], [], {SRC: [(123.29, 135.18, "and", "I")]}, _Inner(), A)
check([(round(x, 2), round(y, 2)) for _s, x, y, _g in out] == [(128.0, 133.73), (134.71, 137.1)] and len(made) == 1,
      f"a long gap the full transcript made of dropped lines is replaced by the proven pause inside it: {out}")
check(ygaps.GapConfirm.real([(70.0, 71.18, "physicist"), (74.4, 74.6, "for")], 71.18, 74.36),
      "a window that hears the next word where the take does and nothing between confirms the gap")
check(not ygaps.GapConfirm.real([(70.0, 71.18, "x"), (72.5, 72.9, "spoken"), (74.4, 74.6, "for")], 71.18, 74.36),
      "a word starting inside the gap means the take's transcript dropped speech: rejected")
check(ygaps.GapConfirm.real([(70.0, 72.9, "physicist"), (74.4, 74.6, "for")], 71.18, 74.36),
      "a last word dragged into the pause only shrinks the gap: still confirmed")
check(not ygaps.GapConfirm.real([(70.0, 71.18, "x")], 71.18, 74.36), "a window that never hears the next word does not confirm")


class _Counted(ygaps.GapConfirm):
    """GapConfirm with whisper replaced by a log of the windows it would transcribe."""
    def __init__(self):
        super().__init__({SRC: "unused.wav"}, "")
        self.calls = []

    def window_words(self, src, t0, t1):
        self.calls.append((t0, t1))
        return []


g = _Counted()
near = [(41.2, 42.0), (44.5, 45.3), (47.1, 47.9), (50.0, 50.8)]
wins = {gap: [] for gap in near}
for e1, s2 in near:
    n = len(g.calls)
    g._windows(SRC, e1, s2)
    wins[(e1, s2)] = g.calls[n:]
spans = sorted({w for w in g.calls})
check(len(g.calls) < 2 * len(near),
      f"four pauses inside 10s share grid windows instead of two windows each: {len(g.calls)} transcriptions")
ctx = ygaps.WG["confirm_pad_s"] * 0.75
grid = [(a, b) for a, b in spans if b - a == ygaps.WG.get("confirm_window_s", 28.0)]
check(all(sum(1 for a, b in grid if a <= e1 - ctx and b >= s2 + ctx) >= 2 for e1, s2 in near),
      f"every pause sits inside two grid windows with confirm context on both sides: {grid}")
g2 = _Counted()
g2._windows(SRC, 60.0, 75.0)
check(len(g2.calls) == 2 and all(b - a < 28.0 for a, b in g2.calls[-1:]),
      f"a 15s gap no two grid windows can hold falls back to the per-gap windows: {g2.calls}")
g3 = _Counted()
g3._windows(SRC, 1.0, 1.8)
check(len(g3.calls) == 2 and g3.calls[0][0] == 0.0,
      f"a gap in the first seconds of the take, before any grid window has context, uses the per-gap windows: {g3.calls}")


# =====================================================================================================
# 3.9.0: the audio says where the repeats are, the dictionary passes the ad-libs, decisions come at
# once, the whisper lock is fair, and the clause plan is proposed from the script
# =====================================================================================================
import math as _math  # noqa: E402
import random as _random  # noqa: E402
import wave as _wave  # noqa: E402
import numpy as _np  # noqa: E402
from yaplib import envelope as yenv  # noqa: E402
from yaplib import repeats as yrep  # noqa: E402
from yaplib import lexicon as ylex  # noqa: E402
from yaplib import take as ytake  # noqa: E402
from yaplib import whisper as ywhisper  # noqa: E402

# --- the envelope in numpy is the loop it replaced ---------------------------------------------------
check(yenv._self_check() == 0.0, "yaplib/envelope.py matches yapcut's per-sample loop to the last bit")
_series = [-75.0] * 50 + [-25.0] * 100 + [-75.0] * 120 + [-26.0] * 100 + [-74.0] * 30
check(abs(yenv.longest_quiet(_series, 1.4, 2.8, -60.0) - 1.2) < 0.02, "longest_quiet measures the pause under the level")
check(yenv.quiet(_series, 1.5, 2.6, -60.0) and not yenv.quiet(_series, 0.4, 1.6, -60.0), "quiet() is most of the frames under the level")
check(yenv.peak(_series, 0.5, 1.0) == -25.0 and yenv.quietest(_series) < -70, "peak and quietest read the series")


# --- a synthetic voice: a phrase said twice is found at its lag, noise and silence are not --------------
def _syllable(dur, f0, seed):
    r = _random.Random(seed)
    amps = [r.uniform(0.05, 1.0) / (k ** 0.7) for k in range(1, 25)]
    n = int(dur * 16000)
    t = _np.arange(n) / 16000
    phase = 2 * _math.pi * _np.cumsum(f0 * (1 + 0.08 * _np.sin(2 * _math.pi * t / dur))) / 16000
    x = sum(a * _np.sin(k * phase) for k, a in enumerate(amps, 1))
    return x * _np.hanning(n) / (_np.max(_np.abs(x)) + 1e-9)


def _phrase(seeds, rate=1.0):
    out = []
    for i, sd in enumerate(seeds):
        out.append(_syllable(0.16 / rate, 130.0 * (1 + 0.1 * ((i % 3) - 1)), sd))
        out.append(_np.zeros(int(0.04 / rate * 16000)))
    return _np.concatenate(out)


def _room(dur, db=-62.0, seed=1):
    return _np.random.RandomState(seed).normal(0, 10 ** (db / 20), int(dur * 16000))


def voice_pcm():
    A, B, C2 = [11, 12, 13, 14, 15, 16], [21, 22, 23, 24, 25], [31, 32, 33, 34, 35, 36, 37]
    parts = [_room(0.5), _phrase(A), _room(0.35), _phrase(A, rate=1.1), _room(1.0), _phrase(B), _room(0.3), _phrase(C2), _room(0.5)]
    sig = _np.concatenate(parts) * 0.3
    sig = sig + _room(len(sig) / 16000, -60, 2)
    lenA = len(_phrase(A)) / 16000
    return _np.clip(sig * 32768, -32768, 32767).astype(_np.int16), 0.5, lenA, 0.5 + lenA + 0.35


_pcm, _tA1, _lenA, _tA2 = voice_pcm()
_evs = yrep.find(_pcm, max_lag=3.5)
check(len(_evs) == 1 and abs(_evs[0].t0 - _tA1) < 0.15 and abs(_evs[0].lag - (_tA2 - _tA1)) < 0.12,
      f"a phrase said twice (the second pass 10% faster) is one repeat at its lag: {_evs}")
check(yrep.find((_np.random.RandomState(5).normal(0, 0.05, 16000 * 4) * 32768).astype(_np.int16)) == [],
      "white noise, as similar to itself at every lag, is no repeat")
check(yrep.find(_np.zeros(16000 * 3, _np.int16)) == [], "silence is no repeat")
check(yrep.spans_of(_evs, 0.6)[0][0] < _tA1 and yrep.spans_of(_evs, 0.6)[0][1] > _tA2 + _lenA,
      "spans_of covers both passes with its pad")
with tempfile.TemporaryDirectory() as t:
    _w = os.path.join(t, "v.wav")
    _o = _wave.open(_w, "wb"); _o.setnchannels(1); _o.setsampwidth(2); _o.setframerate(16000); _o.writeframes(_pcm.tobytes()); _o.close()
    check(len(yrep.find_file(_w, max_lag=3.5)) == 1, "find_file reads a 16 kHz wav")
    import xwin_scan as xs2  # noqa: E402
    _dur = len(_pcm) / 16000
    with contextlib.redirect_stdout(io.StringIO()):
        _sp, _kept = xs2.heard_twice(_pcm.tobytes(), [(0.0, _dur)], 3.5)
        _sp2, _kept2 = xs2.heard_twice(_pcm.tobytes(), [(_tA2 - 0.1, _dur)], 3.5)
    check(len(_kept) == 1 and len(_sp) == 1, "heard_twice keeps a repeat whose passes sit in the spans")
    check(_kept2 == [], "a repeat whose first pass the cut left out costs no window")
    check(xs2.clip_spans([(0.0, 5.0), (8.0, 9.0)], 4.0, 8.5) == [(4.0, 5.0), (8.0, 8.5)], "clip_spans cuts spans to a keep")

# --- the lexicon ---------------------------------------------------------------------------------------
check(ylex.is_word("heard") and ylex.is_word("handling") and ylex.is_word("features") and ylex.is_word("you've"),
      "an irregular past, an -ing with a dropped e, a plural and a contraction are ordinary words")
check(not ylex.is_word("Warhounds") and not ylex.is_word("Andriel") and not ylex.is_word("chatgbt"),
      "a name, a mis-heard name and a garble are not")
check("company" in ylex.bases("companies") and "run" in ylex.bases("running"), "bases puts the -ies and the doubled consonant back")
check(ylex.contraction_base("can't") == "can" and ylex.contraction_base("it's") == "it", "contractions fold to their base")
for _a, _b in (("Claude", "cloud"), ("Claude", "clod"), ("Anduril", "Andriel"), ("Lamm", "Lam"), ("Feynman", "fineman"), ("ChatGPT", "chatgbt")):
    check(ylex.phonetic(_a) == ylex.phonetic(_b), f"{_a} and {_b} share a sound key ({ylex.phonetic(_a)})")
check(ylex.phonetic("Quartz") != ylex.phonetic("courts"), "Quartz and courts do not")
with tempfile.TemporaryDirectory() as t:
    check(ylex.learn(["Stealth", "opinion", "60"], home=t) == 2 and ylex.learned(home=t) == {"stealth", "opinion"},
          "learn() keeps lowercase words, never a number, and learned() reads them back")
    check(ylex.learn(["opinion"], home=t) == 0, "a word learned once is not new")
    os.makedirs(os.path.join(t, "input", "b", ".yap_build"))
    open(os.path.join(t, "input", "b", ".yap_build", "x_script.txt"), "w").write("Richard Feynman cracked the locks.")
    json.dump(["sus", "vibe"], open(os.path.join(t, "input", "b", ".yap_build", "x_capqa_ok.json"), "w"))
    _n, _tot = ylex.seed([os.path.join(t, "input")], home=t)
    check({"feynman", "locks", "sus", "vibe"} <= ylex.learned(home=t), f"seed() learns every script word and accepted word ({_n} new)")
    check(ylex.known("Feynman", learned_words=ylex.learned(home=t)), "a learned name is known afterwards")

# --- the caption gate: ad-libs pass, names, numbers and garbles ask -----------------------------------
import caption_qa as cq  # noqa: E402
_vocab = set(cq.canon("Warhound raised money. Ben Lamm runs the company. It made $200 million.")) | cq.GLUE
_g, _ad = cq.judge(["Warhounds", "heard", "stealth", "Andriel", "60", "Besides", "Government", "chatgbt", "you’ve"],
                   _vocab, {"besides"}, set())
check(set(_ad) == {"heard", "stealth", "Besides", "you’ve"}, f"ordinary words and a capital that starts a sentence are ad-libs: {_ad}")
check([w for w, _f in _g] == ["Andriel", "60", "Government", "chatgbt"],
      f"a name, a number, a capital mid-sentence and a garble need a ruling: {[w for w, _f in _g]}")
check(not any(w == "Warhounds" for w, _f in _g) and "Warhounds" not in _ad, "an inflection of a script word is the script")
_g2, _ = cq.judge(["clod—ish"], _vocab, None, set())
check(_g2 and _g2[0][1][0].startswith("<em/en dash"), "a dash on screen is always flagged")
with tempfile.TemporaryDirectory() as t:
    _wj = os.path.join(t, "w.json")
    json.dump({"transcription": [{"offsets": {"from": 0, "to": 300}, "text": " now."}, {"offsets": {"from": 300, "to": 600}, "text": " Besides"},
                                 {"offsets": {"from": 600, "to": 900}, "text": " the"}]}, open(_wj, "w"))
    check(cq.sentence_starts(_wj) == {"now", "besides"}, "sentence_starts reads the first word and every word after a sentence end")

# --- script_fix: inflections stay, names take the script's spelling everywhere -------------------------
import script_fix as sfx  # noqa: E402
check(sfx.inflection("notice", "noticed") and sfx.inflection("run", "running") and sfx.inflection("survey", "surveyed"),
      "notice/noticed, run/running and survey/surveyed are inflections")
check(not sfx.inflection("lam", "lamm") and not sfx.inflection("andriel", "anduril"), "lam/lamm is a garble, not an inflection")
_cut = [(i * 0.4, i * 0.4 + 0.3, w) for i, w in enumerate(
    "Ben Lamb runs Colossal and Palmer Lucky, a founder of Andriel, says Andriel wants dogs. Lamb agrees now. Besides the dogs".split())]
_scr = "Ben Lamm runs Colossal and Palmer Luckey, a founder of Anduril, says Anduril wants dogs. Lamm agrees now, when the dogs".split()
_fx, _dr, _sw = sfx.plan(_cut, _scr, locked=set())
_got = [_fx.get(i, w[2]) for i, w in enumerate(_cut)]
check(_got.count("Lamm") == 2 and "Lamb" not in _got, f"a name is fixed at every occurrence, not only the aligned one: {_got}")
check(_got.count("Anduril") == 1 and _got.count("Anduril,") == 1 and "Luckey," in _got, f"names inside a replace block and a trailing comma survive: {_got}")
check(_got[_got.index("now,") + 1] == "besides", f"a capital whisper gave an ad-lib after a sentence end the script removed is lowered: {_got}")
# 3.9.1: a form of the script's word is how it was said. On Ep48 (2026-10-25) "don't" became "doesn't"
# twice, off script, because the two are 0.8 alike by letters and the swap then spread everywhere.
check(sfx.same_family("don't", "doesn't") and sfx.same_family("compute.", "computing,") and not sfx.same_family("Lamb", "Lamm"),
      "don't and doesn't, compute and computing are one word; Lamb and Lamm are not")
check(not sfx.similar("don't", "doesn't") and not sfx.similar("compute", "computing") and sfx.similar("fineman", "Feynman"),
      "a form of the script's word is never a garble; a mis-spelled name still is")
check(not sfx.similar("making", "keeping") and not sfx.similar("has", "had") and sfx.similar("clod", "Claude") and sfx.similar("logs", "locks"),
      "two ordinary words only somewhat alike are a paraphrase; a name or a close garble is still fixed")
_cut3 = [(i * 0.4, i * 0.4 + 0.3, w) for i, w in enumerate("it doesn't matter, they don't really try, I don't know.".split())]
_fx3, _, _sw3 = sfx.plan(_cut3, "It don't matter, they doesn't really try.".split(), locked=set())
_got3 = [_fx3.get(i, w[2]) for i, w in enumerate(_cut3)]
check("doesn't" in _got3[1] and _got3[4] == "don't" and _got3[8] == "don't",
      f"an aligned don't/doesn't pair is left as said, and nothing spreads to the other occurrences: {_got3}")
_cut2 = [(0, 0.3, "the"), (0.4, 0.7, "courts"), (0.8, 1.1, "said")]
_fx2, _, _ = sfx.plan(_cut2, "The Quartz piece said".split(), locked=set())
check(1 not in _fx2 or _fx2[1] == "courts", "an ordinary lowercase word that merely sounds like a script name stays")

# --- the dead-air gate measures a pause by the microphone, no whisper ---------------------------------
def _voice_wav(path, parts, seed=7):
    """parts: (seconds, dB RMS, "voice" | "room"), the cutter tests' synthetic take (the name `take` is
    a word list further up)."""
    rng, out, n = _random.Random(seed), [], 0
    for dur, db, kind in parts:
        amp = 32768 * 10 ** (db / 20)
        for _ in range(int(dur * 16000)):
            t = n / 16000; n += 1
            if kind == "voice":
                out.append(amp / 0.8803 * sum(_math.sin(2 * _math.pi * 140 * k * t) / k for k in range(1, 11)))
            else:
                out.append(rng.gauss(0, amp))
    with _wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes(b"".join(int(max(-32768, min(32767, round(x)))).to_bytes(2, "little", signed=True) for x in out))


with tempfile.TemporaryDirectory() as t:
    _wav = os.path.join(t, "w_x.wav")
    _voice_wav(_wav, [(0.3, -75, "room"), (0.8, -26, "voice"), (1.2, -75, "room"), (0.8, -26, "voice"), (0.3, -75, "room")])
    _al = os.path.join(t, "w_x.json")
    json.dump({"transcription": [{"offsets": {"from": 300, "to": 1100}, "text": " first"},
                                 {"offsets": {"from": 2300, "to": 3100}, "text": " second"}]}, open(_al, "w"))
    _r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "gap_check.py"), "--video", _wav, "--aligned", _al],
                        capture_output=True, text=True)
    check(_r.returncode == 2 and "measured by the microphone" in _r.stdout and "DEAD AIR: 1." in _r.stdout,
          f"a 1.2s pause between two words fails, measured by the microphone (rc {_r.returncode}): {_r.stdout.strip().splitlines()[-3:]}")
    _r2 = subprocess.run([sys.executable, os.path.join(SCRIPTS, "gap_check.py"), "--video", _wav, "--aligned", _al, "--allow", "1.1"],
                         capture_output=True, text=True)
    check(_r2.returncode == 0 and "allowed beat" in _r2.stdout, "the same pause allowed as a beat passes")
    json.dump({"transcription": [{"offsets": {"from": 300, "to": 1100}, "text": " first"},
                                 {"offsets": {"from": 1500, "to": 3100}, "text": " second"}]}, open(_al, "w"))
    _voice_wav(_wav, [(0.3, -75, "room"), (0.8, -26, "voice"), (0.4, -75, "room"), (1.6, -26, "voice"), (0.3, -75, "room")])
    _r3 = subprocess.run([sys.executable, os.path.join(SCRIPTS, "gap_check.py"), "--video", _wav, "--aligned", _al],
                         capture_output=True, text=True)
    check(_r3.returncode == 0 and "clean" in _r3.stdout, f"a 0.4s pause is cadence (rc {_r3.returncode})")

# --- gates.sh: deferred decision gates stop together; the compose signature follows its inputs ----------
with tempfile.TemporaryDirectory() as t:
    _sh = f"""set -u; SCRIPTS="{SCRIPTS}"; source "$SCRIPTS/gates.sh"; gates_init "{t}/g.json" tiktok out.mp4
gates_defer; gate_finish a 2 "fix A"; gate_finish b 0; gate_finish c 2 "fix C"; echo "still here"; gates_settle; echo "never"
"""
    _r = subprocess.run(["bash", "-c", _sh], capture_output=True, text=True)
    _g = json.load(open(os.path.join(t, "g.json")))["gates"]
    check(_r.returncode == 2 and "GATE a FAILED" in _r.stdout and "GATE c FAILED" in _r.stdout and "still here" in _r.stdout
          and "never" not in _r.stdout and "DECISIONS NEEDED (a, c)" in _r.stdout and _g == {"a": 2, "b": 0, "c": 2},
          f"two deferred red gates are both printed, then the build stops (rc {_r.returncode})")
    _sh2 = f"""set -u; SCRIPTS="{SCRIPTS}"; source "$SCRIPTS/gates.sh"; gates_init "{t}/g2.json" tiktok out.mp4
gate_finish a 2 "fix A"; echo "never"
"""
    _r2 = subprocess.run(["bash", "-c", _sh2], capture_output=True, text=True)
    check(_r2.returncode == 2 and "never" not in _r2.stdout, "outside defer a red gate still stops the build at once")
    open(os.path.join(t, "cap.ass"), "w").write("Dialogue: x\n")
    _sh3 = f"""SCRIPTS="{SCRIPTS}"; source "$SCRIPTS/gates.sh"; compose_sig abc "{t}/cap.ass" ""; compose_sig abc "{t}/cap.ass" ""; compose_sig abd "{t}/cap.ass" \"\""""
    _out = subprocess.run(["bash", "-c", _sh3], capture_output=True, text=True).stdout.split()
    check(len(_out) == 3 and _out[0] == _out[1] and _out[0] != _out[2], "compose_sig is stable and follows the cut's hash")
    import yapbatch as yb  # noqa: E402
    _log = os.path.join(t, "log.txt")
    open(_log, "w").write("GATE stutter_restart FAILED (rc 2). cut it.\nx\nGATE caption FAILED (rc 2). fix it.\nDECISIONS NEEDED\n")
    check(yb.failing_gate(_log) == ("stutter_restart+caption", "stutter_restart: cut it. | caption: fix it."),
          f"yapbatch names every deferred gate that failed: {yb.failing_gate(_log)}")

# --- media: the hardware paths can be switched off ------------------------------------------------------
_env0 = os.environ.get("YAP_NO_HWACCEL")
os.environ["YAP_NO_HWACCEL"] = "1"
check(media.hwaccel_args() == [] and media.intermediate_encoder()[1] == "libx264", "YAP_NO_HWACCEL=1 keeps software decode and libx264")
if _env0 is None:
    del os.environ["YAP_NO_HWACCEL"]
else:
    os.environ["YAP_NO_HWACCEL"] = _env0

# --- the whisper lock is first come first served ---------------------------------------------------------
with tempfile.TemporaryDirectory() as t:
    _worker = os.path.join(t, "w.py")
    open(_worker, "w").write(f"""import os, sys, time
sys.path.insert(0, {SCRIPTS!r})
from yaplib import whisper as yw
k, delay = sys.argv[1], float(sys.argv[2])
time.sleep(delay)
with yw.lock({os.path.join(t, "lock")!r}, {os.path.join(t, "q")!r}):
    open({os.path.join(t, "order.txt")!r}, "a").write(k + "\\n"); time.sleep(0.7)
""")
    _ps = [subprocess.Popen([sys.executable, _worker, k, d]) for k, d in (("1", "0"), ("2", "0.25"), ("3", "0.5"))]
    for _p in _ps:
        _p.wait(timeout=30)
    _order = open(os.path.join(t, "order.txt")).read().split()
    check(_order == ["1", "2", "3"], f"three waiters take the lock in the order they arrived: {_order}")
    check(not os.path.exists(os.path.join(t, "lock")) and not os.listdir(os.path.join(t, "q")), "the lock and the queue are left clean")

# --- the take: runs of speech, and the clause plan from a script ----------------------------------------
check(ytake.runs_of([-75.0] * 20 + [-25.0] * 50 + [-75.0] * 40 + [-25.0] * 30, -42.0, 0.1) == [(0.2, 0.7), (1.1, 1.4)],
      "runs_of finds the speech between the silences")
import clauses_from_script as cfs  # noqa: E402
from yaplib import script as yscript2  # noqa: E402
_script = "We shipped it last week. The buyers loved the new flow. That is the whole bet."
_sents = cfs.sentences(_script)
check(len(_sents) == 3 and _sents[0][0] == yscript2.tokens("We shipped it last week."), "sentences split the script and keep their tokens")
_take_text = ("we shipped it we shipped it last week honestly the buyers loved the the buyers loved the new flow "
              "loved the new flow that is the whole bet thank you")
_wd, _t = [], 0.0
for _i, _w in enumerate(_take_text.split()):
    if _w in ("honestly", "that", "thank") or _i in (8 + 1,):          # a pause before and after the aside, and before the lines
        _t += 0.5
    _wd.append((_t, _t + 0.35, _w)); _t += 0.45
_toks = [yscript2.norm(w[2]) for w in _wd]
_plan = cfs.choose(_toks, _sents, 0.6)
check(all(p for p, _o in _plan), f"every sentence is found in the take: {_plan}")
check(_plan[0][0][0] == 3 and _plan[0][1] == [(0, 3)], f"the second pass at the first line is chosen and the aborted first pass is an earlier attempt: {_plan[0]}")
_takeinfo = {"repeats": [], "voice": -26.0}
_role, _why, _listen = cfs.roles_of(_wd, _toks, _sents, _plan, _takeinfo, yscript2.tokens(_script))
check(_role[:3] == ["attempt"] * 3 and _role[3:8] == ["kept"] * 5, f"the aborted first pass is cut, the full one kept: {_role[:8]}")
check(_role[8] == "adlib", "an ad-lib between lines stays")
check(_role[-2:] == ["noise", "noise"], f"a 'thank you' whisper hears in a breath is noise: {_role[-2:]}")
check(_role[15:19] == ["attempt"] * 4 and _role[19:23] == ["adlib"] * 4,
      f"the end of a line said again right after is replaced by the later pass: {_role[9:23]}")
check(any("said twice inside" in m for _t, m in _listen) or "attempt" in _role[9:12],
      "a doubled 'the buyers' is a listen item or a cut")

# 3.9.2: whisper.cpp now and then aborts in its DTW median filter (exit 134); the cut survives it
class _Run:
    def __init__(self, codes): self.codes, self.n = list(codes), 0
    def __call__(self, *a, **k):
        self.n += 1
        return type("R", (), {"returncode": self.codes.pop(0)})()
_real_run, _real_load = ygaps.subprocess.run, ygaps.ywords.load_words
ygaps.ywords.load_words = lambda path: [(0.0, 0.4, "hello")]
ygaps.subprocess.run = _r = _Run([134, 0])
check(ygaps.aligned_words("x.wav", "/nonexistent/x") == [(0.0, 0.4, "hello")] and _r.n == 2,
      "a transcription that aborts once is retried and its words come back")
ygaps.subprocess.run = _r = _Run([134, 134, 134])
try:
    ygaps.aligned_words("x.wav", "/nonexistent/x"); _raised = False
except ygaps.TranscribeFailed:
    _raised = True
check(_raised and _r.n == 3, "three aborts in a row raise TranscribeFailed")
ygaps.subprocess.run, ygaps.ywords.load_words = _real_run, _real_load


class _Aborts(ygaps.GapConfirm):
    def __init__(self):
        super().__init__({SRC: "unused.wav"}, "")
    def window_words(self, src, t0, t1):
        return None


_g = _Aborts()
check(_g(SRC, 71.18, 74.36) is None and not any(k.startswith(os.path.basename(SRC) + "@") for k in _g.d)
      and not any(k.startswith("win:") for k in _g.d),
      "a gap whose windows whisper could not transcribe is kept, and nothing about it is cached")


# --- transcribe.sh --words: a beam-search abort falls back to greedy; a failure leaves no stale words ----
with tempfile.TemporaryDirectory() as t:
    import wave as _wave
    _bin = os.path.join(t, "bin"); os.makedirs(_bin)
    open(os.path.join(_bin, "whisper-cli"), "w").write("""#!/usr/bin/env bash
echo "$*" >> "$FAKE_WHISPER_LOG"
if [ "${FAKE_WHISPER_FAIL:-}" = always ] || [[ " $* " != *" -bs 1 "* ]]; then
  echo "WHISPER_ASSERT: whisper.cpp:8807: filter_width < a->ne[2]" >&2; exit 134
fi
while [ $# -gt 0 ]; do [ "$1" = -of ] && of="$2"; shift; done
echo '{"transcription": []}' > "$of.json"
""")
    os.chmod(os.path.join(_bin, "whisper-cli"), 0o755)
    _clip = os.path.join(t, "clip.wav")
    with _wave.open(_clip, "w") as _w:
        _w.setnchannels(1); _w.setsampwidth(2); _w.setframerate(16000); _w.writeframes(b"\0\0" * 16000)
    _out = os.path.join(t, "w_clip")
    _env = dict(os.environ, PATH=_bin + os.pathsep + os.environ["PATH"], WHISPER_MODEL=os.path.join(t, "ggml-small.en.bin"),
                FAKE_WHISPER_LOG=os.path.join(t, "calls.txt"))
    _r = subprocess.run(["bash", os.path.join(SCRIPTS, "transcribe.sh"), _clip, _out, "--words"], env=_env,
                        capture_output=True, text=True)
    _calls = open(os.path.join(t, "calls.txt")).read().splitlines()
    check(_r.returncode == 0 and len(_calls) == 2 and "-bs 1 -bo 1" in _calls[1] and "fell back to greedy" in _r.stdout
          and "filter_width" in _r.stdout and os.path.exists(_out + ".json"),
          f"a beam-search abort is retried greedy and says so (rc {_r.returncode}, {len(_calls)} calls)")
    for _f in (_out + ".full.json", _out + ".json"):
        open(_f, "w").write('{"transcription": [{"text": "the last cut", "offsets": {"from": 0, "to": 500}}]}')
    _r = subprocess.run(["bash", os.path.join(SCRIPTS, "transcribe.sh"), _clip, _out, "--words"],
                        env=dict(_env, FAKE_WHISPER_FAIL="always"), capture_output=True, text=True)
    check(_r.returncode == 134 and not os.path.exists(_out + ".full.json") and not os.path.exists(_out + ".json"),
          f"whisper failing both ways exits non-zero and leaves no earlier run's words (rc {_r.returncode})")
    import yapbatch as _yb  # noqa: E402
    _log = os.path.join(t, "yapfull.log")
    open(_log, "w").write("--- dur: 50 ---\nSTEP transcribe FAILED (rc 134): the cut's word transcript (transcribe.sh --words). x\nexit 134\n")
    check((_yb.failing_step(_log) or "").startswith("STEP transcribe FAILED (rc 134)"), "yapbatch names the yapfull step that broke")

# --- take_lessons reads only what was said: no seg/ runs, no # headers, no [m:ss.s] stamps -------------
with tempfile.TemporaryDirectory() as t:
    sys.path.insert(0, RADAR)
    import take_lessons as _tl  # noqa: E402
    _b = os.path.join(t, "takes"); os.makedirs(os.path.join(_b, ".yap_build", "tx")); os.makedirs(os.path.join(_b, ".yap_build", "seg"))
    open(os.path.join(_b, "AB12-CD.mp4"), "w").close()
    _said = " ".join(["word%d" % i for i in range(25)])
    open(os.path.join(_b, ".yap_build", "tx", "AB12-CD.txt"), "w").write(
        "# AB12-CD.mp4: 60.0s, 25 words\n# said twice (1): the restarts\n#     9.08  'word1'  again at 10.2\n\n"
        f"[0:00.9]  {' '.join(_said.split()[:10])} \n[1:05.1]  {' '.join(_said.split()[10:])} \n")
    open(os.path.join(_b, ".yap_build", "seg", "AB12-CD.txt"), "w").write("0\t0.93-3.01\t" + _said + "\n")
    import pathlib as _pl
    _found = _tl.takes(_pl.Path(_b))
    check(len(_found) == 1 and _found[0][0] == "AB12-CD", f"one transcript per take, seg/ left out: {[k for k, _ in _found]}")
    _txt = _found[0][1] if _found else ""
    check("#" not in _txt and "[" not in _txt and "said twice" not in _txt and _txt.split() == _said.split(),
          f"the take reads as speech only: {_txt[:60]!r}")

if fails:
    print(f"{len(fails)} failure(s)")
    sys.exit(2)

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


if fails:
    print(f"{len(fails)} failure(s)")
    sys.exit(2)

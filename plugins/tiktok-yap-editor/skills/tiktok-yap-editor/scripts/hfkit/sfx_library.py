#!/usr/bin/env python3
"""The tagged sound library the HyperFrames kit plays from.

Each tag names what an on-screen event MEANS (a card lands, a number lands, a line strikes
through), and the kit picks the sound by tag, never by decoration. The picks below are
catalog IDs in HeyGen's sound and music library, chosen by ear from ranked searches. This
file ships the IDs, not the audio: every creator downloads the files with their own HeyGen
account, so the audio is fetched under that account's terms and never redistributed here.

    python3 sfx_library.py fetch            download every pick (needs the HeyGen CLI, a free account is enough)
    python3 sfx_library.py offline          no account: map every tag to the CC0 pack gen_sfx.py synthesizes
    python3 sfx_library.py search "cash register" [--music]    rank catalog candidates for a new tag

HeyGen CLI:  curl -fsSL https://static.heygen.ai/cli/install.sh | bash   then   heygen auth login
The library lands in <workspace>/assets/sfx-library/ (plugin updates never touch it), else in
<skill>/assets/sfx-library/. Pass --dir to put it elsewhere.
"""
import argparse, json, os, shutil, subprocess, sys, urllib.request

HERE = os.path.dirname(os.path.realpath(__file__))
SCRIPTS = os.path.dirname(HERE)
SKILL = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)

PICKS = [  # (tag, query that surfaced it, catalog id prefix, kind, what it sounds like)
    ("card_in", "soft paper card slide whoosh", "72d0b14394", "sound_effects", "short airy swish, 0.3s"),
    ("card_in_heavy", "soft paper card slide whoosh", "d1546edf41", "sound_effects", "whoosh into a muted thud"),
    ("headline", "marker pen scribble on paper", "9b77ef762e", "sound_effects", "single paper page turn"),
    ("pop", "clean ui pop bubble appear", "4558aa1365", "sound_effects", "bright UI pop"),
    ("pop_small", "clean ui pop bubble appear", "13175e257d", "sound_effects", "tiny hollow pop"),
    ("tap", "applause small audience short", "1511fc9768", "sound_effects", "single brief tap"),
    ("message", "smartphone notification ding message received", "fd8d689329", "sound_effects", "UI notification chime"),
    ("notify_double", "smartphone notification ding message received", "79690ddf00", "sound_effects", "double alert chime"),
    ("win", "achievement unlocked level up chime", "64bc0cce56", "sound_effects", "ascending chime into a bell"),
    ("chime_short", "achievement unlocked level up chime", "9eddaec30f", "sound_effects", "two quick rising tones"),
    ("money", "cash register cha-ching", "2d6aa30f6b", "sound_effects", "cash register bell and clatter"),
    ("coins", "counting numbers ticking rolling counter slot machine", "d81327f4a9", "sound_effects", "clinking small pieces"),
    ("counter", "counting numbers ticking rolling counter slot machine", "7925f861f3", "sound_effects", "fast mechanical ticking, trimmed to the count"),
    ("fail", "wrong answer error buzz short", "fa2bd3a7b2", "sound_effects", "buzzer, keep it low"),
    ("slam", "deep cinematic boom impact trailer", "7e1cbac754", "sound_effects", "deep boom"),
    ("riser", "short tension riser build 2 seconds", "762c29b841", "sound_effects", "2s riser, cuts off hard"),
    ("tick", "ui check tick confirm", "4f71acbdde", "sound_effects", "double tick"),
    ("strike", "strike through scratch record scratch", "30c6a8c8cc", "sound_effects", "vinyl record scratch"),
    ("shutter", "camera shutter photo", "e6d7dae993", "sound_effects", "shutter double click"),
    ("thud", "stamp approved thud", "12b333917d", "sound_effects", "heavy stamp thud"),
    ("sweep", "graph bars rising upward whoosh", "f21dfc942d", "sound_effects", "short synthetic sweep"),
    ("applause", "applause small audience short", "0a051ee00d", "sound_effects", "crowd clapping"),
    ("typing", "phone keyboard tap", "420ffbbe7d", "sound_effects", "crisp keyboard burst"),
    ("sting", "logo reveal sting whoosh", "68ce3485ed", "sound_effects", "fast sweeping whoosh"),
    ("whip", "logo reveal sting whoosh", "04ba947247", "sound_effects", "whoosh into a whip crack"),
    ("drop", "coin drop single", "9c635c3436", "sound_effects", "sub-bass drop"),
    ("glitch", "wrong answer error buzz short", "6e2f785647", "sound_effects", "short glitch burst"),
    ("bed_corporate", "upbeat light corporate business podcast bed", "4e0d0a501e", "music", "upbeat optimistic corporate, 84s"),
    ("bed_documentary", "tense curious documentary underscore pulse", "071503c18d", "music", "measured documentary ambient, 69s"),
    ("bed_tech", "minimal modern tech background bed calm confident instrumental", "5ccbb5ecf1", "music", "calm modern tech bed, 40s"),
]

# no account: every tag falls back to the nearest sound in the CC0 pack gen_sfx.py synthesizes
OFFLINE = {"card_in": "swish", "card_in_heavy": "whoosh", "headline": "swish", "pop": "click", "pop_small": "click", "tap": "click",
           "message": "ding", "notify_double": "ding", "win": "ding", "chime_short": "ding", "money": "ding", "coins": "ding",
           "counter": "click", "fail": "impact", "slam": "impact", "riser": "riser", "tick": "click", "strike": "swish",
           "shutter": "click", "thud": "impact", "sweep": "whoosh", "applause": "whoosh", "typing": "click", "sting": "whoosh",
           "whip": "whoosh", "drop": "impact", "glitch": "click", "bed_corporate": "bed_drive", "bed_documentary": "bed_calm",
           "bed_tech": "bed_calm"}


def default_dir():
    try:
        from yaplib.home import radar_home
        home = radar_home(required=False)
    except Exception:
        home = None
    return os.path.join(str(home), "assets", "sfx-library") if home else os.path.join(SKILL, "assets", "sfx-library")


def _heygen():
    exe = shutil.which("heygen") or os.path.expanduser("~/.local/bin/heygen")
    if not os.path.exists(exe):
        raise SystemExit("HeyGen CLI not found. Install it (curl -fsSL https://static.heygen.ai/cli/install.sh | bash), run "
                         "`heygen auth login`, or use `sfx_library.py offline` for the no-account pack.")
    return exe


def search(q, kind="sound_effects", n=6, min_score=0.35):
    r = subprocess.run([_heygen(), "audio", "sounds", "list", "--query", q, "--type", kind, "--limit", str(n), "--min-score", str(min_score)],
                       capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f"heygen audio sounds list failed: {(r.stderr or r.stdout)[-400:]}\n(signed in? run `heygen auth login`)")
    d = json.loads(r.stdout or "{}")
    items = d.get("data", d)
    if isinstance(items, dict):
        items = items.get("sounds") or items.get("items") or items.get("data") or []
    return items or []


def _duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path], capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except ValueError:
        return 0.0


def fetch(out):
    os.makedirs(os.path.join(out, "files"), exist_ok=True)
    lib, missing = {}, []
    for tag, q, pid, kind, note in PICKS:
        hit = next((it for it in search(q, kind, 12, 0.3) if str(it.get("id", "")).startswith(pid)), None)
        url = hit and (hit.get("audio_url") or hit.get("url") or hit.get("download_url"))
        if not url:
            missing.append(tag)
            continue
        rel = f"files/{tag}.mp3"
        urllib.request.urlretrieve(url, os.path.join(out, rel))
        lib[tag] = {"file": rel, "id": hit.get("id"), "kind": kind, "seconds": float(hit.get("duration") or 0) or _duration(os.path.join(out, rel)),
                    "description": hit.get("description"), "note": note, "query": q, "source": "heygen"}
        print(f"{tag:15s} {lib[tag]['seconds']:5.1f}s  {note}")
    json.dump(lib, open(os.path.join(out, "library.json"), "w"), indent=1)
    print(f"{len(lib)} sounds -> {out}/library.json" + (f"; not found in the catalog, pick replacements with search: {missing}" if missing else ""))


def offline(out):
    subprocess.run([sys.executable, os.path.join(SCRIPTS, "gen_sfx.py")], check=True)
    from gen_sfx import _pack_dir
    pack = _pack_dir()
    lib = {}
    for tag, *_ in PICKS:
        name = OFFLINE[tag]
        f = next((os.path.join(pack, name + ext) for ext in (".wav", ".m4a") if os.path.exists(os.path.join(pack, name + ext))), None)
        if f:
            lib[tag] = {"file": f, "seconds": _duration(f), "source": "gen_sfx (CC0)", "note": f"offline stand-in: {name}"}
    os.makedirs(out, exist_ok=True)
    json.dump(lib, open(os.path.join(out, "library.json"), "w"), indent=1)
    print(f"{len(lib)} tags mapped to the CC0 pack in {pack} -> {out}/library.json")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["fetch", "offline", "search"])
    ap.add_argument("query", nargs="*")
    ap.add_argument("--music", action="store_true")
    ap.add_argument("--dir", default=None)
    a = ap.parse_args()
    out = a.dir or default_dir()
    if a.cmd == "fetch":
        fetch(out)
    elif a.cmd == "offline":
        offline(out)
    else:
        for q in a.query:
            print(f"## {q}")
            for i, it in enumerate(search(q, "music" if a.music else "sound_effects")):
                print(f"  {i} {it.get('score', 0):.2f} {float(it.get('duration') or 0):5.1f}s {str(it.get('id', ''))[:10]} | "
                      f"{(it.get('description') or it.get('name') or '')[:120]}")


if __name__ == "__main__":
    main()

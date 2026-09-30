#!/usr/bin/env python3
"""What's new in a YapCut plugin, shown once per version per machine.

As the plugin's SessionStart hook (--hook), the first session after an update shows a one-line
banner and hands Claude the unseen WHATS-NEW.md entries plus what this machine still needs, so
the creator hears it once, in plain words, at the start of the session. By hand:

    python3 whats_new.py          the entries you have not seen, then the setup check
    python3 whats_new.py --all    every entry
    python3 whats_new.py --check  only the setup check

The same file ships in both plugins (tests check they stay byte-identical); it reads which one
it is from plugin.json. The last version seen per plugin lives in ~/.config/yapcut/seen.json. A
machine with no record sees every entry of the current minor line (3.5.x), so someone coming
from 3.4 gets 3.5.0 and 3.5.1. The hook never fails a session: any error prints nothing.
"""
import json, os, re, shutil, subprocess, sys

PLUGIN = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
try:
    NAME = json.load(open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")))["name"]
except Exception:
    NAME = os.path.basename(PLUGIN)
SKILL = os.path.join(PLUGIN, "skills", NAME)
TITLE = {"tiktok-yap-editor": "YapCut editor", "outlier-radar": "Outlier Radar"}.get(NAME, NAME)
SEEN = os.path.expanduser("~/.config/yapcut/seen.json")
HOOK_ONLY_ON = ("startup", "")  # not on resume, clear or compact: the notice is for a fresh session


def vt(s):
    return tuple(int(x) for x in re.findall(r"\d+", s)[:3])


def current():
    return json.load(open(os.path.join(PLUGIN, ".claude-plugin", "plugin.json")))["version"]


def entries(path=None):
    """[(version tuple, 'x.y.z', title, body)] from WHATS-NEW.md, in file order (newest first)."""
    text = open(path or os.path.join(PLUGIN, "WHATS-NEW.md"), encoding="utf-8").read()
    out = []
    for m in re.finditer(r"^## (\d+\.\d+\.\d+): ([^\n]*)\n(.*?)(?=^## \d+\.\d+\.\d+:|\Z)", text, re.S | re.M):
        out.append((vt(m.group(1)), m.group(1), m.group(2).strip(), m.group(3).strip()))
    return out


def pending(cur, seen, es):
    c = vt(cur)
    if seen:
        s = vt(seen)
        return [e for e in es if s < e[0] <= c]
    return [e for e in es if e[0][:2] == c[:2] and e[0] <= c]


def read_seen():
    try:
        return json.load(open(SEEN)).get(NAME)
    except Exception:
        return None


def write_seen(v):
    try:
        d = json.load(open(SEEN)) if os.path.exists(SEEN) else {}
    except Exception:
        d = {}
    d[NAME] = v
    os.makedirs(os.path.dirname(SEEN), exist_ok=True)
    json.dump(d, open(SEEN, "w"), indent=1)


def _node_major():
    node = shutil.which("node")
    if not node:
        return 0
    try:
        return int(re.findall(r"\d+", subprocess.run([node, "--version"], capture_output=True, text=True, timeout=3).stdout)[0])
    except Exception:
        return 0


def ready_editor():
    """HyperFrames packaging on this machine. Fast: no network, no npx."""
    rows = [(_node_major() >= 22, "Node 22 or newer", "install it (on a Mac: brew install node)"),
            (bool(shutil.which("ffmpeg")), "ffmpeg", "install it (on a Mac: brew install ffmpeg)")]
    lib = False
    try:
        sys.path.insert(0, os.path.join(SKILL, "scripts"))
        from hfkit.sfx_library import default_dir
        lib = os.path.exists(os.path.join(default_dir(), "library.json"))
    except Exception:
        pass
    if not lib:
        heygen = bool(shutil.which("heygen") or os.path.exists(os.path.expanduser("~/.local/bin/heygen")))
        rows.append((heygen, "HeyGen CLI (for the sound library)",
                     "curl -fsSL https://static.heygen.ai/cli/install.sh | bash, then heygen auth login (a free account)"))
    rows.append((lib, "the YapCut sound library", "python3 scripts/hfkit/sfx_library.py fetch (needs the HeyGen CLI) or offline (no account)"))
    rows.append((os.path.exists(os.path.expanduser("~/.claude/skills/hyperframes-audio/scripts/carve.mjs")),
                 "HeyGen's HyperFrames skills (optional: ducks the music under your voice)", "npx skills add heygen-com/hyperframes"))
    return "HyperFrames packaging", rows


WORK_MONOLOGUE_WORDS = 2500  # about twenty minutes at 150 words a minute (3.10.1: the voice fix is supply)


def _work_monologue_words(vc):
    """Words in hand-filed sources marked register: work and form: monologue: the creator alone with a
    camera, on their own subject. A monologue off subject (a personal vlog) does not count."""
    import glob
    total = 0
    for f in glob.glob(os.path.join(vc, "manual", "**", "*.md"), recursive=True) + glob.glob(os.path.join(vc, "manual", "**", "*.txt"), recursive=True):
        try:
            t = open(f, encoding="utf-8", errors="ignore").read()
        except Exception:
            continue
        r = re.search(r"^register:\s*([A-Za-z]+)\s*$", t, re.M | re.I)
        fm = re.search(r"^form:\s*([A-Za-z]+)", t, re.M | re.I)
        if r and fm and r.group(1).lower() == "work" and fm.group(1).lower() == "monologue":
            total += len(t.split())
    return total


def ready_radar():
    """What the weekly scripts learn from, in this machine's workspace."""
    ws = None
    try:
        sys.path.insert(0, SKILL)
        from yapcut_home import radar_home
        ws = radar_home(argv=[], required=False)
    except Exception:
        pass
    rows = [(ws is not None, "a YapCut workspace", "say \"run outlier radar\": the first run interviews you and creates it")]
    if ws is not None:
        words = _work_monologue_words(os.path.join(str(ws), "voice-corpus"))
        rows.append((words >= WORK_MONOLOGUE_WORDS,
                     f"twenty minutes of you alone to camera about your subject in the voice corpus (about {words // 150} minutes so far)",
                     "record it, then ask Claude to add it to the voice corpus as register: work, form: monologue"))
        filmed = False
        try:
            for line in open(os.path.join(str(ws), "performance", "tracking.jsonl"), encoding="utf-8"):
                if '"filmed"' in line or '"posted"' in line:
                    filmed = True
                    break
        except Exception:
            pass
        rows.append((filmed, "the scripts you filmed, marked", "after you film one, tell Claude \"I filmed <the script>\""))
        rows.append((os.path.isdir(os.path.join(str(ws), "mobile")), "the Anima phone app linked (optional)",
                     "if you use Anima on your iPhone, say \"connect anima\""))
    return "the weekly scripts", rows


def readiness():
    try:
        return {"tiktok-yap-editor": ready_editor, "outlier-radar": ready_radar}.get(NAME, lambda: ("", []))()
    except Exception:
        return "", []


def render(es, check):
    label, rows = check
    parts = [f"## {v}: {t}\n\n{b}" for _, v, t, b in es]
    if rows:
        missing = [r for r in rows if not r[0]]
        parts.append(f"Setup check for {label}: everything is in place." if not missing else
                     f"Setup check for {label}, still needed on this machine:\n" + "\n".join(f"- {w}: {fix}" for _, w, fix in missing))
    return "\n\n".join(parts)


def hook():
    try:
        try:
            src = (json.load(sys.stdin) or {}).get("source", "")
        except Exception:
            src = ""
        if src not in HOOK_ONLY_ON:
            return
        cur = current()
        es = pending(cur, read_seen(), entries())
        if not es:
            return
        write_seen(cur)
        body = render(es, readiness())
        ctx = (f"The {TITLE} plugin ({NAME}) was just updated to {cur}. At the start of your first reply, tell the user "
               "once, in two or three plain sentences, what is new and what they would need to do to use it, from the notice "
               "and the setup check below; then do what they asked. Offer to run the setup steps that need no account; "
               "installs are theirs to approve and sign-ins are theirs to do. Do not bring it up again this session.\n\n" + body)
        titles = "; ".join(t for _, _, t, _ in reversed(es))
        print(json.dumps({"systemMessage": f"{TITLE} {cur}: {titles}. Claude will say what changed and what to do.",
                          "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}))
    except Exception:
        return


def main():
    a = sys.argv[1:]
    if "--hook" in a:
        hook()
        return
    check = readiness()
    if "--check" in a:
        print(render([], check))
        return
    cur = current()
    es = entries() if "--all" in a else pending(cur, read_seen(), entries())
    print(render(es, check) if es else f"Nothing new since {read_seen()}.\n\n" + render([], check))
    if "--all" not in a:
        write_seen(cur)


if __name__ == "__main__":
    main()

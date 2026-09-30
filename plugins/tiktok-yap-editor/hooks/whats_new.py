#!/usr/bin/env python3
"""What's new in the YapCut editor, shown once per version per machine.

As the plugin's SessionStart hook (--hook), the first session after an update shows a one-line
banner and hands Claude the unseen WHATS-NEW.md entries plus what this machine still needs, so
the creator hears it once, in plain words, at the start of the session. By hand:

    python3 whats_new.py          the entries you have not seen, then the setup check
    python3 whats_new.py --all    every entry
    python3 whats_new.py --check  only the setup check for the newest features

The last version seen lives in ~/.config/yapcut/seen.json. A machine with no record sees every
entry of the current minor line (3.5.x), so someone coming from 3.4 gets 3.5.0 and 3.5.1.
The hook never fails a session: any error prints nothing and exits 0.
"""
import json, os, re, shutil, subprocess, sys

PLUGIN = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
NAME = "tiktok-yap-editor"
SCRIPTS = os.path.join(PLUGIN, "skills", NAME, "scripts")
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


def readiness():
    """[(ready, what, how to fix)] for HyperFrames packaging on this machine. Fast: no network, no npx."""
    rows = []
    node = shutil.which("node")
    major = 0
    if node:
        try:
            major = int(re.findall(r"\d+", subprocess.run([node, "--version"], capture_output=True, text=True, timeout=3).stdout)[0])
        except Exception:
            major = 0
    rows.append((major >= 22, "Node 22 or newer", "install it (on a Mac: brew install node)"))
    rows.append((bool(shutil.which("ffmpeg")), "ffmpeg", "install it (on a Mac: brew install ffmpeg)"))
    lib = False
    try:
        sys.path.insert(0, SCRIPTS)
        from hfkit.sfx_library import default_dir
        lib = os.path.exists(os.path.join(default_dir(), "library.json"))
    except Exception:
        pass
    heygen = bool(shutil.which("heygen") or os.path.exists(os.path.expanduser("~/.local/bin/heygen")))
    if not lib:
        rows.append((heygen, "HeyGen CLI (for the sound library)",
                     "curl -fsSL https://static.heygen.ai/cli/install.sh | bash, then heygen auth login (a free account)"))
    rows.append((lib, "the YapCut sound library", "python3 scripts/hfkit/sfx_library.py fetch (needs the HeyGen CLI) or offline (no account)"))
    rows.append((os.path.exists(os.path.expanduser("~/.claude/skills/hyperframes-audio/scripts/carve.mjs")),
                 "HeyGen's HyperFrames skills (optional: ducks the music under your voice)", "npx skills add heygen-com/hyperframes"))
    return rows


def render(es, rows):
    parts = [f"## {v}: {t}\n\n{b}" for _, v, t, b in es]
    missing = [r for r in rows if not r[0]]
    check = "Setup check for HyperFrames packaging: everything is in place." if not missing else \
        "Setup check for HyperFrames packaging, still needed on this machine:\n" + "\n".join(f"- {w}: {fix}" for _, w, fix in missing)
    return "\n\n".join(parts + [check])


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
        ctx = (f"The YapCut editor plugin ({NAME}) was just updated to {cur}. At the start of your first reply, tell the user "
               "once, in two or three plain sentences, what is new and what they would need to do to use it, from the notice "
               "and the setup check below; then do what they asked. Offer to run the setup steps that need no account; "
               "installs are theirs to approve and sign-ins are theirs to do. Do not bring it up again this session.\n\n" + body)
        titles = "; ".join(t for _, _, t, _ in reversed(es))
        print(json.dumps({"systemMessage": f"YapCut editor {cur}: {titles}. Claude will say what changed and what to install.",
                          "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ctx}}))
    except Exception:
        return


def main():
    a = sys.argv[1:]
    if "--hook" in a:
        hook()
        return
    rows = readiness()
    if "--check" in a:
        print(render([], rows))
        return
    cur = current()
    es = entries() if "--all" in a else pending(cur, read_seen(), entries())
    print(render(es, rows) if es else f"Nothing new since {read_seen()}.\n\n" + render([], rows))
    if "--all" not in a:
        write_seen(cur)


if __name__ == "__main__":
    main()

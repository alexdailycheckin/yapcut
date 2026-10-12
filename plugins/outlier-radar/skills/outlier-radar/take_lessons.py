#!/usr/bin/env python3
"""
Learn from the takes. When the creator films a script and does not like how it sounds, they
say it their own way on camera. Those departures are the best voice lesson the engine gets:
the script said one thing, the person said another, and the person is right.

This matches every take transcript in a batch to the script it came from, then keeps only
what the creator said differently: a line they replaced, a line they added, a line they cut.
The parts they read as written are left out on purpose, because a straight read of the
engine's own script teaches the engine its own voice back.

Usage:
  python3 take_lessons.py <batch folder>          match, record, print what changed
  python3 take_lessons.py <batch folder> --dry    print only, record nothing

The batch folder is the one the editor transcribes into (`input/<batch>`); transcripts are read
from its `.yap_build/` (`*.txt`, or the cut's `w_<name>.json`). Scripts come from every week
file and every campaign. Each lesson lands once in `voice-corpus/takes.jsonl`, keyed on the
take, so running it twice changes nothing. `voice_brief.py` prints the newest of them under
"HOW THEY ACTUALLY SAID IT", right after the approved scripts.

Added 3.21.0 (2026-10-12). The creator's words: "as I record these, if I don't like how they
sound, I'm going to read them in my voice... you can learn how I speak that way and improve
them every time."
"""
import datetime
import difflib
import json
import os
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yapcut_home import radar_home  # noqa: E402
import rules  # noqa: E402

MIN_WORDS = 4        # a change shorter than this is a stutter or a slip, not a rewrite
MIN_MATCH = 0.35     # below this share of matching words, the take is not a read of that script
RETOLD = 0.6         # below this share read as written, the creator retold it in their own words


def words(text):
    return re.findall(r"[a-z0-9$%']+", (text or "").lower().replace("’", "'"))


def raw_words(text):
    return re.findall(r"\S+", (text or "").replace("\n", " "))


def scripts(home):
    """Every item with a script, from every week file and every campaign."""
    out = []
    for sub in ("weeks", "campaigns"):
        d = home / sub
        for f in sorted(d.glob("*.json")) if d.exists() else []:
            if f.name.endswith(".gate.json"):
                continue
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
            for lane in tuple(rules.video_lanes()) + ("days",):
                for it in data.get(lane) or []:
                    if isinstance(it, dict) and it.get("script"):
                        text = ((it.get("spoken_hook") or "") + " " + it["script"]).strip()
                        out.append({"id": it.get("id"), "title": it.get("title") or "", "text": text,
                                    "source": f"{sub}/{f.name}"})
    return out


def takes(batch):
    """One transcript per filmed clip: `<clip>.txt` or `t_<clip>.txt` under `.yap_build/`, where
    <clip> is the start of a video file's name in the batch. The editor writes many derived files
    beside them (segments, logs, concatenations); those are ignored. A batch whose clips are gone
    falls back to the cuts' `w_<name>.json`."""
    build = batch / ".yap_build"
    clips = {p.stem.split("-")[0].split(" ")[0].upper() for p in batch.iterdir()
             if p.suffix.lower() in (".mp4", ".mov", ".m4v")} if batch.exists() else set()
    found = []
    for f in sorted(build.rglob("*.txt")) if build.exists() else []:
        stem = f.stem[2:] if f.stem.startswith("t_") else f.stem
        if stem.split("-")[0].upper() in clips:
            found.append((stem, f.read_text(encoding="utf-8", errors="ignore")))
    if not found and build.exists():
        for f in sorted(build.rglob("w_*.json")):
            try:
                w = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
            ws = w.get("words") if isinstance(w, dict) else w
            if isinstance(ws, list):
                found.append((f.stem, " ".join(str(x.get("word") or x.get("w") or x.get("text") or "").strip()
                                               for x in ws if isinstance(x, dict))))
    return [(k, t) for k, t in found if len(words(t)) >= 20]


def best_script(take_text, pool):
    tw = words(take_text)
    best, best_r = None, 0.0
    for s in pool:
        sm = difflib.SequenceMatcher(None, words(s["text"]), tw, autojunk=False)
        matched = sum(b.size for b in sm.get_matching_blocks())
        r = matched / max(1, len(words(s["text"])))
        if r > best_r:
            best, best_r = s, r
    return best, best_r


def _sentence(tokens, i1, i2):
    """Widen [i1, i2) to whole sentences: a lesson read out of context teaches nothing."""
    ends = lambda t: t.endswith((".", "!", "?", ".\"", "?\"", "!\""))
    lo = i1
    while lo > 0 and not ends(tokens[lo - 1]):
        lo -= 1
    hi = max(i2, lo)
    while hi < len(tokens) and (hi == lo or not ends(tokens[hi - 1])):
        hi += 1
    return lo, hi


def changes(script_text, take_text):
    """What the creator said differently, as whole sentences: replaced, added, cut. A change
    shorter than MIN_WORDS is a stutter, not a rewrite. When most of the script was said their
    own way, the whole retelling is the lesson."""
    a_raw, b_raw = raw_words(script_text), raw_words(take_text)
    a = [re.sub(r"[^a-z0-9$%']", "", w.lower()) for w in a_raw]
    b = [re.sub(r"[^a-z0-9$%']", "", w.lower()) for w in b_raw]
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    kept = sum(m.size for m in sm.get_matching_blocks()) / max(1, len(a))
    if kept < RETOLD:
        return [{"kind": "retold", "script": " ".join(a_raw), "said": " ".join(b_raw)}], kept
    blocks = sm.get_matching_blocks()

    def script_side(j_lo, j_hi, i_lo, i_hi):
        """The script sentence(s) behind a stretch of the take: the words they kept from it."""
        for i, j, size in blocks:
            if size and j < j_hi and j + size > j_lo:
                i_lo = min(i_lo, i + max(0, j_lo - j))
                i_hi = max(i_hi, i + min(size, j_hi - j))
        return _sentence(a_raw, i_lo, i_hi) if i_hi > i_lo else (i_lo, i_lo)

    spans = []
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "equal" or max(i2 - i1, j2 - j1) < MIN_WORDS:
            continue
        bj = _sentence(b_raw, j1, j2) if op != "delete" else (j1, j1)
        ai = script_side(bj[0], bj[1], i1, i2 if op != "insert" else i1)
        if op != "insert" and ai[1] == ai[0]:
            ai = _sentence(a_raw, i1, i2)
        if spans and (ai[0] < spans[-1][1][1] or bj[0] < spans[-1][2][1]):
            prev = spans.pop()
            ai = (min(prev[1][0], ai[0]), max(prev[1][1], ai[1]))
            bj = (min(prev[2][0], bj[0]), max(prev[2][1], bj[1]))
        spans.append((op, ai, bj))
    out = []
    for op, (i1, i2), (j1, j2) in spans:
        script_span, said_span = " ".join(a_raw[i1:i2]), " ".join(b_raw[j1:j2])
        kind = "added" if not script_span else "cut" if not said_span else "replaced"
        out.append({"kind": kind, "script": script_span, "said": said_span})
    return out, kept


def main():
    home = radar_home()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry" in sys.argv
    if not args:
        print("usage: take_lessons.py <batch folder> [--dry]")
        return 2
    batch = pathlib.Path(args[0]).expanduser()
    if not batch.is_absolute():
        batch = (home / batch) if (home / batch).exists() else batch.resolve()
    pool = scripts(home)
    ledger = home / "voice-corpus" / "takes.jsonl"
    seen = set()
    if ledger.exists():
        for line in ledger.read_text(encoding="utf-8").splitlines():
            try:
                seen.add(json.loads(line).get("take"))
            except ValueError:
                pass
    today = datetime.date.today().isoformat()
    new = []
    found = takes(batch)
    if not found:
        print(f"no transcripts in {batch}/.yap_build: transcribe the takes first")
        return 1
    for key, text in found:
        take_id = f"{batch.name}/{key}"
        s, r = best_script(text, pool)
        if not s or r < MIN_MATCH:
            print(f"- {key}: no script matched (best {r:.0%}); free talk, left out")
            continue
        diffs, kept = changes(s["text"], text)
        print(f"\n=== {key} -> {s['id']}  {s['title']}  (read {kept:.0%} as written, "
              f"{len(diffs)} change{'s' if len(diffs) != 1 else ''})")
        for d in diffs:
            if d["kind"] == "retold":
                print(f"  retold in their own words:\n    {d['said']}")
            elif d["kind"] == "added":
                print(f"  + said: {d['said']}")
            elif d["kind"] == "cut":
                print(f"  - cut:  {d['script']}")
            else:
                print(f"  ~ script: {d['script']}\n    said:   {d['said']}")
        if take_id in seen or dry:
            continue
        for d in diffs:
            new.append(dict(d, take=take_id, id=s["id"], title=s["title"], at=today,
                            read_as_written=round(kept, 2)))
        seen.add(take_id)
    if new and not dry:
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with ledger.open("a", encoding="utf-8") as fh:
            for row in new:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"\nrecorded {len(new)} change(s) in {ledger}")
    elif not dry:
        print("\nnothing new to record")
    return 0


if __name__ == "__main__":
    sys.exit(main())

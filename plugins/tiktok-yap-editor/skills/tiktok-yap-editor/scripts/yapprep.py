#!/usr/bin/env python3
"""yapprep: every take of a filming day, read once, before anyone writes a clause plan (3.9.0).

On 2026-10-25 the agent wrote prep.sh, prepq.sh, match.py, wtx.sh and a watcher to do this by
hand for twenty takes, one decode at a time, while the cuts ran. This is that prep as one
command. For each take it leaves, in <footage>/.yap_build/:

  audio/<stem>.wav           16 kHz mono (yapcut reads it; made once)
  audio/<stem>.take.json     the whole take's aligned words (the lines whisper dropped filled
                             back in), its runs of speech, what it says twice (yaplib/take.py)
  tx/<stem>.txt              the take as text: a time mark and a new line at every pause, and
                             at the top every stretch the take says twice, with its words
  seg/<stem>.txt             every run of speech between pauses, numbered, with its words: the
                             silence-accurate boundaries a clause plan is written from

The repeats at the top of tx/<stem>.txt are the restarts, in the order they happen: "35.1
'OpenAI's vice president' again at 37.5". That is the list the clause plan cuts, and
clauses_from_script.py writes the plan from it when the script is known.

With --scripts (a folder of *.txt / *_script.txt, or the Radar's week JSON files) each take is
matched to the script it reads, by shared word trigrams, and the match is printed; the plan
is then one command per video:

    python3 clauses_from_script.py --src <take> --script <name>_script.txt --workdir .yap_build --name <name>

Usage: yapprep.py <footage folder | take files...> [--workdir DIR] [--scripts PATH...]
                  [--silence-db -42] [--d 0.1] [--refresh]
One whisper decode at a time (yaplib/whisper.py); a take already read is not read again.
"""
import argparse
import glob
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import rules  # noqa: E402
from yaplib import take as ytake  # noqa: E402

C = rules.get("cut")
EXT = (".mp4", ".mov", ".m4v", ".mts", ".MP4", ".MOV", ".M4V", ".MTS")


def takes_of(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            out += sorted(f for f in glob.glob(os.path.join(p, "*")) if f.endswith(EXT) and os.path.isfile(f))
        elif os.path.isfile(p):
            out.append(p)
    return out


def toks(s):
    return re.sub(r"[^a-z0-9' ]", " ", (s or "").lower().replace("’", "'")).split()


def tri(ws):
    return {tuple(ws[i:i + 3]) for i in range(len(ws) - 2)}


def load_scripts(paths):
    """{id: (title, text)} from text files and from Radar week JSON (items with a script)."""
    out = {}
    for p in paths:
        files = sorted(glob.glob(os.path.join(p, "*"))) if os.path.isdir(p) else [p]
        for f in files:
            if f.endswith(".json"):
                try:
                    d = json.load(open(f, encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                items = []
                if isinstance(d, dict):
                    for v in d.values():
                        if isinstance(v, list):
                            items += [x for x in v if isinstance(x, dict) and x.get("script")]
                elif isinstance(d, list):
                    items = [x for x in d if isinstance(x, dict) and x.get("script")]
                for it in items:
                    out[it.get("id") or f"{os.path.basename(f)}:{len(out)}"] = (
                        it.get("title", ""), " ".join(str(it.get(k, "")) for k in ("spoken_hook", "script")))
            elif f.endswith(".txt"):
                out[os.path.basename(f)] = ("", open(f, encoding="utf-8").read())
    return out


def match_script(take, scripts):
    """(score, id, title) of the script the take reads, by shared trigrams over the script's."""
    t = tri(toks(" ".join(w[2] for w in take["words"])))
    best = (0.0, "", "")
    for sid, (title, text) in scripts.items():
        s = tri(toks(text))
        if not s:
            continue
        score = len(t & s) / len(s)
        if score > best[0]:
            best = (score, sid, title)
    return best


def write_reports(take, workdir):
    stem = ytake.stem_of(take["src"])
    os.makedirs(os.path.join(workdir, "tx"), exist_ok=True)
    os.makedirs(os.path.join(workdir, "seg"), exist_ok=True)
    head = [f"# {os.path.basename(take['src'])}: {take['dur']:.1f}s, {len(take['words'])} words, "
            f"{len(take['runs'])} runs of speech, floor {take['floor']} dB, voice {take['voice']} dB"]
    if take["filled"]:
        head.append(f"# {take['filled']} run(s) the whole-take decode dropped were decoded alone and put back")
    if take["repeats"]:
        head.append(f"# said twice ({len(take['repeats'])}): the restarts a clause plan cuts, first pass then second")
        for r in take["repeats"]:
            weak = "  (weak: far apart and a low score)" if r["lag"] > 4.0 and r["score"] < 10 else ""
            head.append(f"#   {r['t0']:7.2f}  {ytake.said(take['words'], r['t0'], r['t1'])!r}  again at {r['again']:.2f}{weak}")
    else:
        head.append("# nothing said twice")
    open(os.path.join(workdir, "tx", stem + ".txt"), "w", encoding="utf-8").write(
        "\n".join(head) + "\n\n" + ytake.transcript_text(take))
    lines = []
    for i, (a, b) in enumerate(take["runs"]):
        if b - a < 0.3:
            continue
        lines.append(f"{i}\t{a:.2f}-{b:.2f}\t{ytake.starting(take['words'], a, b)}")
    open(os.path.join(workdir, "seg", stem + ".txt"), "w", encoding="utf-8").write("\n".join(lines) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="+", help="a footage folder, or take files")
    ap.add_argument("--workdir", default="", help="default: <footage>/.yap_build")
    ap.add_argument("--scripts", nargs="*", default=[], help="script text files, folders, or Radar week JSON")
    ap.add_argument("--silence-db", type=float, default=C["silence_db"])
    ap.add_argument("--d", type=float, default=C["min_silence_s"], help="the shortest silence that ends a run")
    ap.add_argument("--refresh", action="store_true", help="read every take again")
    a = ap.parse_args()
    takes = takes_of(a.paths)
    if not takes:
        sys.exit("yapprep: no takes found")
    workdir = a.workdir or os.path.join(os.path.dirname(os.path.abspath(takes[0])) if os.path.isfile(a.paths[0])
                                       else os.path.abspath(a.paths[0]), ".yap_build")
    os.makedirs(workdir, exist_ok=True)
    scripts = load_scripts(a.scripts) if a.scripts else {}
    print(f"yapprep: {len(takes)} take(s) -> {workdir}" + (f", {len(scripts)} script(s)" if scripts else ""), flush=True)
    for src in takes:
        t0 = time.time()
        take = ytake.read(src, workdir, a.silence_db, a.d, refresh=a.refresh)
        write_reports(take, workdir)
        line = (f"  {os.path.basename(src)}: {take['dur']:.0f}s, {len(take['words'])} words, "
                f"{len(take['repeats'])} said twice, {len(take['runs'])} runs ({time.time() - t0:.0f}s)")
        if scripts:
            score, sid, title = match_script(take, scripts)
            line += f"  reads {sid} {title!r} ({score:.2f})" if score >= 0.15 else "  reads no known script"
        print(line, flush=True)
    print(f"read: tx/<take>.txt (the words, the repeats at the top), seg/<take>.txt (the runs)")


if __name__ == "__main__":
    main()

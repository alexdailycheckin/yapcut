#!/usr/bin/env python3
"""turing_check.py: the blind test. Can a judge tell the week's scripts from the creator?

WHY. voice_brief.py has ended on "if these were shuffled together, could a stranger pick out
which one was generated?" since 2026-08-30 and cited a turing_check.py that did not exist
(audit 2026-09-09, Q1 item 8). Meanwhile the cadence gates were a proxy the writer learned:
the 08-31 batch cleared every floor with nine sentences longer than anything in the corpus
while its speech markers stayed at the rejected level. A distribution can be satisfied a
hundred ways; a blind reader cannot be. So this is the ruling machine test, and the cadence
gates are the warnings that explain a failure.

HOW. n passages from the week's spoken scripts and n from the creator's own on-subject speech
(voice-corpus/corpus-work-spoken.txt), each 2 to 4 sentences, shuffled by a seed derived from
the week string so two sessions build the same sheet. The judge labels every passage real or
generated. If the judge is right about 75 percent or more of them the batch is
distinguishable and FAILS; 65 to 75 WARNS; under 65 is chance and PASSES. With n=8 a side
(16 passages) 12 right is p of about 0.04 under a coin flip.

A LinkedIn-only week (no distribution[] or office[] scripts) is tested the same way against
corpus-work-typed.txt, the creator's own writing, as --lane linkedin (chosen on its own when
the week has no spoken scripts). The typed corpus is thin in most workspaces; the sheet says
so and the verdict still stands on whatever it could sample.

FILES, all under voice-corpus/:
  turing-<week>.json          the blind sheet: {week, lane, seed, n, items: [{k, text}]}
  turing-<week>.key.json      the truth, kept apart so a judge never sees it
  turing-<week>.answers.json  the answers: a template to fill by hand, or the judge's output

Usage:
  python3 turing_check.py --week weeks/2026-09-07.json [--n 8] [--dir <workspace>]
      writes the sheet, the key and an answers template; rc 1 (not judged yet)
  python3 turing_check.py --week 2026-09-07 --judge claude
      asks the claude CLI to label the sheet, scores it, writes the answers; rc 0/1/2
  python3 turing_check.py --week 2026-09-07 --answers voice-corpus/turing-2026-09-07.answers.json
      scores a filled answers file against the key; rc 0/1/2

Exit codes (Contract 1): 0 pass, 1 warn or not judged, 2 fail (the batch is distinguishable).
"""
import argparse
import json
import os
import pathlib
import random
import re
import shutil
import subprocess
import sys

# realpath locates the sibling module through the workspace symlink; the workspace itself is
# resolved by yapcut_home and never by following a symlink (see yapcut_home.py).
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yapcut_home import radar_home  # noqa: E402

HOME = radar_home()          # consumes --dir; exits 2 with the places looked when none found
CORPUS = {"spoken": "corpus-work-spoken.txt", "linkedin": "corpus-work-typed.txt"}
MIN_WORDS = 12               # a passage shorter than this is a fragment, not a sample
FAIL_AT, WARN_AT = 0.75, 0.65
LABELS = {"real": "real", "creator": "real", "human": "real", "r": "real",
          "generated": "generated", "ai": "generated", "model": "generated",
          "script": "generated", "g": "generated", "fake": "generated"}


def scrub(text):
    """Same scrub as voice_brief.py: headers, provenance lines, bracketed notes are not speech."""
    text = re.sub(r"^#+.*$", "", text, flags=re.M)
    text = re.sub(r"^_.*_$", "", text, flags=re.M)
    text = re.sub(r"^(mode|register):.*$", "", text, flags=re.M | re.I)
    text = re.sub(r"^\s*-\s*", "", text, flags=re.M)
    text = re.sub(r"\[[^\]]*\]", " ", text, flags=re.S)
    text = re.sub(r"\(context[^)]*\)", " ", text, flags=re.I | re.S)
    return re.sub(r"[ \t]{2,}", " ", text)


def sentences(text):
    text = text.replace("\n", " ")
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def windows(text, rng):
    """2 to 4 consecutive sentences per passage, sizes rotating so no passage length gives
    the side away. Drops fragments under MIN_WORDS."""
    sents = sentences(text)
    out, i = [], 0
    while i < len(sents):
        size = 2 + rng.randrange(3)
        w = " ".join(sents[i:i + size])
        if len(w.split()) >= MIN_WORDS:
            out.append(w)
        i += size
    return out


def week_file(arg):
    p = pathlib.Path(arg)
    if p.exists():
        return p
    alt = HOME / arg
    if alt.exists():
        return alt
    if re.match(r"^\d{4}-\d{2}-\d{2}$", arg):
        alt = HOME / "weeks" / f"{arg}.json"
        if alt.exists():
            return alt
    return None


def week_passages(d, lane, rng):
    """(source id, text) windows from the week. spoken: spoken_hook + script of every
    distribution[] and office[] item. linkedin: every linkedin[] body and embedded twin."""
    out = []
    if lane == "spoken":
        for ln in ("distribution", "office"):
            for it in d.get(ln) or []:
                text = " ".join(x for x in (it.get("spoken_hook"), it.get("script")) if x)
                for w in windows(text, rng):
                    out.append((it.get("id") or ln, w))
    else:
        posts = list(d.get("linkedin") or [])
        for it in d.get("distribution") or []:
            tw = it.get("linkedin")
            if isinstance(tw, dict) and tw.get("body"):
                posts.append(tw)
        for p in posts:
            body = re.sub(r"^\s*(\d+[.)]|[→↳•\-\*])\s+", "", p.get("body") or "", flags=re.M)
            for w in windows(body, rng):
                out.append((p.get("id") or "linkedin", w))
    return out


def spread(pairs, n, rng):
    """Take n passages spread across sources: one per source round-robin, then fill."""
    by = {}
    for sid, text in pairs:
        by.setdefault(sid, []).append(text)
    for v in by.values():
        rng.shuffle(v)
    picked, order = [], list(by)
    rng.shuffle(order)
    while len(picked) < n and any(by.values()):
        for sid in order:
            if by[sid] and len(picked) < n:
                picked.append((sid, by[sid].pop()))
    return picked


def build(wpath, n, lane):
    d = json.load(open(wpath))
    week = str(d.get("week") or wpath.stem)
    seed = sum((i + 1) * ord(c) for i, c in enumerate(week))
    rng = random.Random(seed)
    has_spoken = any((it.get("script") or it.get("spoken_hook"))
                     for ln in ("distribution", "office") for it in d.get(ln) or [])
    if lane == "auto":
        lane = "spoken" if has_spoken else "linkedin"
    cpath = HOME / "voice-corpus" / CORPUS[lane]
    if not cpath.exists():
        print(f"no corpus at {cpath}. Run segment_corpus.py first; nothing can be compared "
              "without the creator's own words.")
        return None, 1
    gen = spread(week_passages(d, lane, rng), n, rng)
    if not gen:
        print(f"nothing to test: {wpath.name} has no {lane} text.")
        return None, 1
    real_pool = windows(scrub(cpath.read_text(encoding="utf-8")), rng)
    if len(real_pool) < 2:
        print(f"{cpath.name} is too thin to sample from ({len(real_pool)} passage(s)).")
        return None, 1
    real = rng.sample(real_pool, min(len(gen), len(real_pool)))
    gen = gen[:len(real)]
    items = [{"truth": "generated", "source": sid, "text": t} for sid, t in gen]
    items += [{"truth": "real", "source": cpath.name, "text": t} for t in real]
    rng.shuffle(items)
    for i, it in enumerate(items, 1):
        it["k"] = f"p{i:02d}"
    thin = f" ({cpath.name} holds only {len(real_pool)} passages; thin)" if len(real_pool) < 12 else ""
    sheet = {"week": week, "week_file": str(wpath), "lane": lane, "seed": seed,
             "n": len(real), "corpus": cpath.name,
             "instructions": ("Each passage is either the creator speaking unscripted (real) or a "
                              "script written for them (generated). Exactly half are real. Label "
                              "every k as real or generated."),
             "items": [{"k": it["k"], "text": it["text"]} for it in items]}
    key = {"week": week, "lane": lane, "seed": seed,
           "truth": {it["k"]: {"truth": it["truth"], "source": it["source"]} for it in items}}
    vc = HOME / "voice-corpus"
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", week)
    sp, kp, ap = vc / f"turing-{slug}.json", vc / f"turing-{slug}.key.json", vc / f"turing-{slug}.answers.json"
    sp.write_text(json.dumps(sheet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    kp.write_text(json.dumps(key, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if not ap.exists():
        tmpl = {"week": week, "instructions": sheet["instructions"] + " Fill every null with "
                "\"real\" or \"generated\", then run turing_check.py --week " + week +
                " --answers " + str(ap.relative_to(HOME)),
                "answers": {it["k"]: None for it in items}}
        ap.write_text(json.dumps(tmpl, indent=2) + "\n", encoding="utf-8")
    print(f"sheet: {len(items)} passages ({len(real)} real, {len(gen)} generated), lane {lane}, "
          f"seed {seed}{thin}")
    print(f"  {sp.relative_to(HOME)}   the blind sheet, give this to the judge")
    print(f"  {kp.relative_to(HOME)}   the truth, never shown to the judge")
    print(f"  {ap.relative_to(HOME)}   answers template")
    return {"sheet": sheet, "key": key, "paths": (sp, kp, ap)}, 0


def load_answers(path):
    data = json.load(open(path))
    raw = data.get("answers") if isinstance(data, dict) and isinstance(data.get("answers"), dict) else data
    out = {}
    for k, v in (raw or {}).items():
        if isinstance(v, dict):
            v = v.get("label") or v.get("answer") or v.get("truth")
        if v is None:
            continue
        lab = LABELS.get(str(v).strip().lower())
        if lab:
            out[k] = lab
    return out


def score(built, answers, judge_name):
    sheet, key = built["sheet"], built["key"]
    truth = key["truth"]
    text = {it["k"]: it["text"] for it in sheet["items"]}
    answered = [k for k in truth if k in answers]
    if not answered:
        print("no answers to score (every k is null).")
        return 1
    correct = [k for k in answered if answers[k] == truth[k]["truth"]]
    acc = len(correct) / len(answered)
    caught = [k for k in answered if truth[k]["truth"] == "generated" and answers[k] == "generated"]
    misread = [k for k in answered if truth[k]["truth"] == "real" and answers[k] == "generated"]
    print(f"\njudge {judge_name}: {len(correct)}/{len(answered)} right "
          f"({100 * acc:.0f}%), {len(truth) - len(answered)} unanswered")
    print(f"{'k':<5}{'truth':<11}{'answer':<11}{'ok':<4}{'source':<26}passage")
    for k in sorted(truth):
        a = answers.get(k, "-")
        ok = "" if a == "-" else ("yes" if a == truth[k]["truth"] else "NO")
        print(f"{k:<5}{truth[k]['truth']:<11}{a:<11}{ok:<4}{truth[k]['source'][:24]:<26}{text[k][:60]}")
    if caught:
        print(f"\nGENERATED PASSAGES THE JUDGE CAUGHT ({len(caught)}), the tells to fix:")
        for k in caught:
            print(f"  {k} [{truth[k]['source']}] {text[k][:160]}")
    if misread:
        print(f"\nreal passages the judge called generated ({len(misread)}): where the creator reads as written")
        for k in misread:
            print(f"  {k} {text[k][:120]}")
    if acc >= FAIL_AT:
        verdict, rc = "FAIL: the batch is distinguishable from the creator", 2
    elif acc >= WARN_AT:
        verdict, rc = "warn: the judge is above chance; read the caught passages", 1
    else:
        verdict, rc = "PASS: the judge cannot tell the batch from the creator", 0
    print(f"\n{verdict}  (fail at {int(FAIL_AT * 100)}%, warn at {int(WARN_AT * 100)}%)")
    sp = built["paths"][0]
    sheet["verdict"] = {"judge": judge_name, "right": len(correct), "answered": len(answered),
                        "accuracy": round(acc, 3), "caught": caught, "misread": misread, "rc": rc}
    sp.write_text(json.dumps(sheet, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"turing_check: rc {rc}")
    return rc


def judge_claude(built):
    """Ask the claude CLI, no tools, one JSON object back. Nothing here knows the truth."""
    exe = shutil.which("claude")
    if not exe:
        print("warn: no `claude` CLI on PATH; fill the answers template by hand or install it.")
        return None
    sheet = built["sheet"]
    prompt = (sheet["instructions"] + " Reply with ONE JSON object and nothing else: "
              "{\"answers\": {\"p01\": \"real\" | \"generated\", ...}} covering every k.\n\n"
              + "\n\n".join(f"{it['k']}: {it['text']}" for it in sheet["items"]))
    try:
        p = subprocess.run([exe, "-p", prompt], capture_output=True, text=True, timeout=240)
    except subprocess.TimeoutExpired:
        print("warn: claude -p timed out after 240s")
        return None
    out = p.stdout or ""
    m = re.search(r"\{.*\}", out, re.S)
    if not m:
        print(f"warn: claude returned no JSON (rc {p.returncode}): {out[:200]!r} {p.stderr[:200]!r}")
        return None
    try:
        answers = load_answers_obj(json.loads(m.group(0)))
    except ValueError:
        print(f"warn: claude's JSON did not parse: {m.group(0)[:200]!r}")
        return None
    ap = built["paths"][2]
    ap.write_text(json.dumps({"week": sheet["week"], "judge": "claude", "answers": answers},
                             indent=2) + "\n", encoding="utf-8")
    print(f"  {ap.relative_to(HOME)}   claude's answers")
    return answers


def load_answers_obj(obj):
    raw = obj.get("answers") if isinstance(obj.get("answers"), dict) else obj
    out = {}
    for k, v in raw.items():
        lab = LABELS.get(str(v).strip().lower())
        if lab:
            out[k] = lab
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--week", required=True, help="week file, workspace-relative path, or YYYY-MM-DD")
    ap.add_argument("--n", type=int, default=8, help="passages per side (default 8)")
    ap.add_argument("--lane", choices=("auto", "spoken", "linkedin"), default="auto")
    ap.add_argument("--judge", choices=("none", "claude"), default="none")
    ap.add_argument("--answers", help="a filled answers file to score against the key")
    ap.add_argument("--dir", help="workspace (consumed by yapcut_home when given)")
    a = ap.parse_args()

    wpath = week_file(a.week)
    if not wpath:
        print(f"no week file for {a.week!r} (looked in the cwd, {HOME} and {HOME / 'weeks'})")
        return 2
    built, rc = build(wpath, max(2, a.n), a.lane)
    if built is None:
        return rc
    if a.answers:
        p = pathlib.Path(a.answers)
        if not p.exists() and (HOME / a.answers).exists():
            p = HOME / a.answers
        if not p.exists():
            print(f"no answers file at {p}")
            return 2
        return score(built, load_answers(p), f"answers file {p.name}")
    if a.judge == "claude":
        answers = judge_claude(built)
        if answers is None:
            print("turing_check: not judged -> rc 1")
            return 1
        return score(built, answers, "claude")
    print("\nnot judged yet: give the sheet to a reader who has not seen the week, collect their "
          "labels in the answers file, then re-run with --answers. Or --judge claude.")
    print("turing_check: not judged -> rc 1")
    return 1


if __name__ == "__main__":
    sys.exit(main())

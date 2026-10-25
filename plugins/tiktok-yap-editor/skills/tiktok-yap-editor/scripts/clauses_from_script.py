#!/usr/bin/env python3
"""A clause plan from the script and the take: the last complete attempt at every line (3.9.0).

Writing the clause plan was the slowest step of every batch and the one that clipped words:
read a 900-word transcript, find the restarts, re-transcribe a window around each boundary,
type thirty rows. The rule the agent applied by hand is simple to state: for every sentence
of the script, keep the last attempt the creator made at it; cut the earlier attempts; keep
everything they said that is not in the script (an aside, an opinion, a reaction), because
that is their voice; cut what whisper heard in a breath ("Thank you.").

This writes that plan. Each script sentence is matched against every stretch of the take
that resembles it (token similarity, inflections and mis-hearings allowed), in script order,
and the last attempt wins when attempts are equally good. Take words that match no sentence
are ad-libs and stay, unless they are an earlier attempt at the sentence that follows (the
words say so, or the audio does: yaplib/repeats.py heard the same thing twice there). Every
boundary between something kept and something cut is placed on the quietest frame of the pause
between them (the envelope, not a transcript time), and a boundary with no pause to sit in is
listed to be listened to.

Output: clauses_<name>.json (or --out), ready for yapcut, and clauses_<name>.proposed.md: what
was kept and cut and why, sentence by sentence, for the person approving the plan. The plan is
a proposal: read the report, listen where it says to, then run it.

Usage: clauses_from_script.py --src <take> --script <name>_script.txt --workdir .yap_build --name <name>
                              [--out clauses_<name>.json] [--silence-db -42] [--d 0.1] [--min-sim 0.6]
The plan also cuts a restart inside a chosen line (the words say it twice where the script says
it once), the earlier of two passes the transcript merged (the audio heard both), a fragment said
again after a pause, and the word or two left beside a cut.
Exit 0 with a plan, 2 when the take does not read the script (fewer than half its sentences found).
"""
import argparse
import difflib
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import envelope as yenv  # noqa: E402
from yaplib import rules  # noqa: E402
from yaplib import script as yscript  # noqa: E402
from yaplib import take as ytake  # noqa: E402

C = rules.get("cut")
NOISE = {"you", "thank you", "thanks", "bye", "okay", "ok", "so", "um", "uh", "yeah", "thank you bye", "hmm"}


def sentences(text):
    """The script's sentences as token lists (yaplib.script.norm), with their text."""
    out = []
    for s in re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text.strip())):
        t = yscript.tokens(s)
        if t:
            out.append((t, s.strip()))
    return out


def sim(a, b):
    """Token similarity in [0, 1]: a ratio over tokens, with inflections and mis-hearings alike."""
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    m = sum(bl.size for bl in sm.get_matching_blocks())
    near = 0
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op == "replace" and i2 - i1 == j2 - j1:
            near += sum(1 for x, y in zip(a[i1:i2], b[j1:j2]) if yscript.alike(x, y))
    return 2.0 * (m + near) / max(1, len(a) + len(b))


def attempts(toks, sent, start, min_sim, stop=None):
    """Every stretch of the take in [start, stop), that resembles the sentence: [(sim, i, j)]
    over token indices [i, j), overlapping ones collapsed to their best, in take order."""
    L = len(sent)
    stop = len(toks) if stop is None else stop
    found = []
    lo, hi = max(2, int(L * 0.6)), int(L * 1.5) + 2
    for i in range(start, stop):
        best = None
        for n in range(lo, hi + 1):
            j = i + n
            if j > stop:
                break
            s = sim(toks[i:j], sent)
            if best is None or s > best[0]:
                best = (s, i, j)
        if best and best[0] >= min_sim:
            found.append(best)
    return _collapse(found)


def _collapse(found):
    found = sorted(found, key=lambda x: (-x[0], x[1]))
    out = []
    for s, i, j in found:
        if any(i < oj and j > oi for _s, oi, oj in out):
            continue
        out.append((s, i, j))
    return sorted(out, key=lambda x: x[1])


def earlier_attempts(toks, sent, start, stop, near):
    """Stretches in [start, stop) that begin the sentence and abandon it: a window of 3 tokens
    or more compared with the sentence's own start (a restart re-attempts from the top), at
    `near` or better. [(sim, i, j)], collapsed."""
    found = []
    for i in range(start, stop):
        best = None
        for n in range(3, min(len(sent) + 3, stop - i) + 1):
            j = i + n
            s = sim(toks[i:j], sent[:min(len(sent), n + 2)])
            if best is None or s > best[0]:
                best = (s, i, j)
        if best and best[0] >= near:
            found.append(best)
    return _collapse(found)


def choose(toks, sents, min_sim, slack=0.08, near=0.6):
    """For each sentence, in order: (chosen (i, j) or None, [earlier attempts (i, j)]). The last of
    the attempts within `slack` of the best wins (the creator's later pass is the cleaner one),
    searched from the end of the previous sentence's chosen attempt. Earlier, abandoned attempts
    at the sentence are looked for one sentence further back (a restart of this line can sit
    between two attempts at the line before) and only before the chosen one; anything after it
    belongs to a later sentence or is a callback and is left alone."""
    plan, start, prev_start = [], 0, 0
    for sent, _text in sents:
        found = attempts(toks, sent, start, min_sim)
        back = False
        if not found:
            # a line said out of its script order (the Warhound take said its last two lines
            # mid-take): take it where it is, and the search for the next line stays put
            found = attempts(toks, sent, 0, min_sim, stop=start)
            back = True
        if not found:
            plan.append((None, []))
            continue
        best = max(s for s, _i, _j in found)
        s, i, j = [(s, i, j) for s, i, j in found if s >= best - slack][-1]
        others = [] if back else [(oi, oj) for _os, oi, oj in earlier_attempts(toks, sent, prev_start, i, near)]
        plan.append(((i, j), others))
        if not back:
            prev_start, start = start, j
    return plan


def is_noise(words, i, j):
    text = " ".join(yscript.norm(w[2]) for w in words[i:j]).strip()
    return j - i <= 2 and text in NOISE


def boundary(env, t_cut_end, t_keep_start, level):
    """Where to cut between a dropped word ending at t_cut_end and a kept word starting at
    t_keep_start: the quietest frame between them. (time, tight) where tight means there was
    no pause to sit in and a person should listen."""
    a, b = min(t_cut_end, t_keep_start), max(t_cut_end, t_keep_start)
    i0, i1 = int(round(a / yenv.HOP)), int(round(b / yenv.HOP))
    if i1 - i0 < 3:
        return (a + b) / 2.0, True
    seg = env[i0:i1]
    k = min(range(len(seg)), key=lambda x: seg[x])
    t = (i0 + k) * yenv.HOP
    return t, seg[k] > level          # no dip at all between the two words


def words_in(words, a, b):
    """The words that sit mostly (40% or more of their length) inside [a, b]."""
    out = []
    for x, (s, e, _t) in enumerate(words):
        ov = min(e, b) - max(s, a)
        if ov > 0 and ov >= 0.4 * max(0.05, e - s):
            out.append(x)
    return out


def phrase_end(words, x, pause=0.4):
    """The index after the last word of the phrase word x is in: the run of words with no pause of
    `pause` or more between them."""
    j = x + 1
    while j < len(words) and words[j][0] - words[j - 1][1] < pause:
        j += 1
    return j


def roles_of(words, toks, sents, plan, take, script_toks):
    """What each take word is: kept (a chosen attempt), adlib, attempt (cut), noise (cut), with why;
    and [(time, note)] of places to listen to."""
    import stutter_check as sc
    role = ["adlib"] * len(words)
    why = [""] * len(words)
    listen = []
    for k, (p, others) in enumerate(plan):
        for i, j in others:
            for x in range(i, j):
                if role[x] == "adlib":
                    role[x], why[x] = "attempt", f"an earlier attempt at sentence {k + 1}"
        if p:
            for x in range(p[0], p[1]):
                role[x], why[x] = "kept", f"sentence {k + 1}"
    # a re-read of a chosen line's tail right after it ("...like the mammoth and the dodo. bring back
    # animals like the mammoth and a dodo"): the later pass wins, the line's tail is cut
    for k, (p, _o) in enumerate(plan):
        if not p:
            continue
        j = p[1]
        if j >= len(words) or role[j] != "adlib" or words[j][0] - words[j - 1][1] > 3.0:
            continue
        e = j
        while e < len(words) and role[e] == "adlib":
            e += 1
        best = None
        for n in range(3, min(p[1] - p[0], e - j + 2) + 1):
            s_ = sim(toks[j:min(e, j + n + 2)], toks[p[1] - n:p[1]])
            if s_ >= 0.6 and (best is None or s_ >= best[0]):
                best = (s_, n)
        if best:
            for x in range(p[1] - best[1], p[1]):
                role[x], why[x] = "attempt", f"the end of sentence {k + 1}, said again right after"
    # a restart inside a chosen attempt ("is an accounting chair is an accounting is an accounting
    # charge"): the words say it twice where the script says it once. A HIGH (three words or more,
    # or a doubled function word) is cut; a MEDIUM is a person's call (the 2026-08-27 ruling), listed
    for k, (p, _o) in enumerate(plan):
        if not p:
            continue
        w = [(words[x][0], words[x][1], words[x][2], sc.norm(words[x][2])) for x in range(p[0], p[1])]
        for st, en, kind, conf, text, _t0, _t1 in sc.find_flags(w):
            if not (kind.startswith("restart") or kind.startswith("repeat")):
                continue
            if sc.scripted((st, en, kind, conf, text, _t0, _t1), w, script_toks):
                continue
            if conf != "HIGH":
                listen.append((w[st][0], f"said twice inside a line, a decision (deliberate or a restart): {text!r}"))
                continue
            for x in range(p[0] + st, p[0] + en):
                role[x], why[x] = "attempt", f"said twice inside sentence {k + 1}: {text!r}"
    # the audio's own word (yaplib/repeats.py): something said twice within a few seconds
    for r in take["repeats"]:
        if r["lag"] > 4.0:
            continue
        p1 = words_in(words, r["t0"], r["t1"])
        p2 = words_in(words, r["again"], r["again"] + (r["t1"] - r["t0"]))
        if not p1 and not p2:
            continue
        # the transcript merged two passes: one pass has words, the other is a hole in a kept line
        # that goes on after the hole (a hole at the end of a line is the pause after it)
        kept1 = p1 and all(role[x] == "kept" for x in p1)
        kept2 = p2 and all(role[x] == "kept" for x in p2)
        hole = (r["again"], r["again"] + (r["t1"] - r["t0"])) if kept1 and not p2 else ((r["t0"], r["t1"]) if kept2 and not p1 else None)
        if hole:
            after = [x for x in range(len(words)) if hole[1] <= words[x][0] <= hole[1] + 1.0 and role[x] == "kept"]
            if after:
                for x in words_in(words, r["t0"], r["again"] - 0.05):
                    if role[x] == "kept":
                        role[x], why[x] = "attempt", f"the transcript merged two passes; said again at {r['again']:.2f}s"
            continue
        # a fragment, then a pause, then the line ("Best in class. ... Best in class models"): the
        # fragment and the rest of its phrase go
        if p1 and p2 and all(role[x] == "adlib" for x in p1) and len(p1) < len(p2) \
                and not yscript.says_twice_near(script_toks, [toks[x] for x in p1], 40):
            e1 = phrase_end(words, p1[-1])
            if e1 <= p2[0] and words[p2[0]][0] - words[e1 - 1][1] >= 0.4:
                for x in range(p1[0], e1):
                    if role[x] == "adlib":
                        role[x], why[x] = "attempt", f"a fragment said again at {r['again']:.2f}s"
    # whisper's breath words
    i = 0
    while i < len(words):
        if role[i] == "adlib":
            j = i
            while j < len(words) and role[j] == "adlib":
                j += 1
            if is_noise(words, i, j):
                for x in range(i, j):
                    role[x], why[x] = "noise", "a word whisper hears in a breath"
            i = j
        else:
            i += 1
    # an ad-lib of a word or two glued to something cut is part of it ("It's | the first half of
    # this year | alone." where the middle was an earlier attempt): orphan fragments go with it
    changed = True
    while changed:
        changed = False
        i = 0
        while i < len(words):
            if role[i] != "adlib":
                i += 1
                continue
            j = i
            while j < len(words) and role[j] == "adlib":
                j += 1
            short = (j - i) <= 2 and words[j - 1][1] - words[i][0] <= 0.6
            glued_before = i > 0 and role[i - 1] == "attempt" and words[i][0] - words[i - 1][1] < 0.35
            glued_after = j < len(words) and role[j] == "attempt" and words[j][0] - words[j - 1][1] < 0.35
            if short and (glued_before or glued_after):
                for x in range(i, j):
                    role[x], why[x] = "attempt", "a fragment left beside a cut"
                changed = True
            elif glued_before or glued_after:
                # the first or last word or two of a longer ad-lib, parted from the rest by a pause
                e = phrase_end(words, i)
                if glued_before and e - i <= 2 and e < j:
                    for x in range(i, e):
                        role[x], why[x] = "attempt", "a fragment left beside a cut"
                    changed = True
                b = j - 1
                while b > i and words[b][0] - words[b - 1][1] < 0.4:
                    b -= 1
                if glued_after and j - b <= 2 and b > i and not changed:
                    for x in range(b, j):
                        role[x], why[x] = "attempt", "a fragment left beside a cut"
                    changed = True
            i = j
    return role, why, listen


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src", required=True, help="the take (video or 16 kHz wav)")
    ap.add_argument("--script", required=True, help="<name>_script.txt, the words read on camera")
    ap.add_argument("--workdir", default="", help="<footage>/.yap_build (default: beside the take)")
    ap.add_argument("--name", default="", help="the video's name (clauses_<name>.json)")
    ap.add_argument("--out", default="")
    ap.add_argument("--silence-db", type=float, default=C["silence_db"])
    ap.add_argument("--d", type=float, default=C["min_silence_s"])
    ap.add_argument("--min-sim", type=float, default=0.6, help="how alike a stretch must be to count as an attempt")
    ap.add_argument("--pad", type=float, default=0.1, help="seconds kept before the first and after the last word of a clause")
    a = ap.parse_args()
    workdir = a.workdir or os.path.join(os.path.dirname(os.path.abspath(a.src)), ".yap_build")
    name = a.name or os.path.splitext(os.path.basename(a.script))[0].replace("_script", "")
    out = a.out or os.path.join(workdir, f"clauses_{name}.json")
    take = ytake.read(a.src, workdir, a.silence_db, a.d)
    words = take["words"]
    toks = [yscript.norm(w[2]) for w in words]
    sents = sentences(open(a.script, encoding="utf-8").read())
    env = yenv.of_file(take["wav"])
    level = take["voice"] - 12.0      # a boundary wants a dip this far under the voice
    plan = choose(toks, sents, a.min_sim)
    found = sum(1 for p, _o in plan if p)
    role, why, listen = roles_of(words, toks, sents, plan, take, yscript.tokens(open(a.script, encoding="utf-8").read()))
    # clauses: maximal runs of kept words (matched or ad-lib), split where something is cut
    clauses, tight, i = [], [], 0
    keep = [r in ("kept", "adlib") for r in role]
    while i < len(words):
        if not keep[i]:
            i += 1
            continue
        j = i
        while j < len(words) and keep[j]:
            j += 1
        start = words[i][0] - a.pad
        if i > 0 and not keep[i - 1]:
            start, t_ = boundary(env, words[i - 1][1], words[i][0], level)
            if t_:
                tight.append((start, f"...{words[i - 1][2]} | {words[i][2]}..."))
        end = words[j - 1][1] + a.pad
        if j < len(words) and not keep[j]:
            end, t_ = boundary(env, words[j - 1][1], words[j][0], level)
            if t_:
                tight.append((end, f"...{words[j - 1][2]} | {words[j][2]}..."))
        label = re.sub(r"[^a-z0-9]+", "-", " ".join(w[2] for w in words[i:i + 3]).lower()).strip("-")[:28] or f"c{len(clauses) + 1}"
        clauses.append({"src": os.path.abspath(a.src), "start": round(max(0.0, start), 3), "end": round(min(take["dur"], end), 3),
                        "label": label})
        i = j
    # the report
    rep = [f"# clause plan for {name}: {len(clauses)} clause(s) from {os.path.basename(a.src)}, "
           f"{found}/{len(sents)} script sentences found", ""]
    for k, ((p, others), (sent, text)) in enumerate(zip(plan, sents)):
        rep.append(f"## {k + 1}. {text}")
        if p:
            rep.append(f"  kept  {words[p[0]][0]:7.2f}-{words[p[1] - 1][1]:6.2f}  {ytake.said(words, words[p[0]][0], words[p[1] - 1][1])}")
        else:
            rep.append("  NOT FOUND in the take (never said, or said too differently)")
        for i, j in others:
            rep.append(f"  cut   {words[i][0]:7.2f}-{words[j - 1][1]:6.2f}  {' '.join(w[2] for w in words[i:j])}")
    adlibs = []
    i = 0
    while i < len(words):
        if role[i] != "kept":
            j = i
            while j < len(words) and role[j] == role[i] and why[j] == why[i]:
                j += 1
            adlibs.append((role[i], words[i][0], words[j - 1][1], " ".join(w[2] for w in words[i:j]), why[i]))
            i = j
        else:
            i += 1
    rep.append("")
    rep.append("## not in the script: kept (the creator's own words) or cut (why)")
    for r, s, e, text, w in adlibs:
        rep.append(f"  {'kept' if r == 'adlib' else 'cut '} {s:7.2f}-{e:6.2f}  {text}" + (f"   [{w}]" if r != "adlib" else ""))
    if tight:
        rep.append("")
        rep.append("## LISTEN: boundaries with no pause to sit in (the cut lands between two words)")
        for t, ctx in tight:
            rep.append(f"  {t:7.2f}  {ctx}")
    if listen:
        rep.append("")
        rep.append("## LISTEN: kept, but said twice (deliberate, or a restart to cut by hand)")
        for t, note in sorted(listen):
            rep.append(f"  {t:7.2f}  {note}")
    rep.append("")
    rep.append("## the plan")
    for c in clauses:
        rep.append(f"  {c['start']:7.2f}  {c['end']:7.2f}  {c['label']}")
    md = out[:-5] + ".proposed.md" if out.endswith(".json") else out + ".proposed.md"
    open(md, "w", encoding="utf-8").write("\n".join(rep) + "\n")
    if found < len(sents) / 2:
        print(f"clauses_from_script: only {found} of {len(sents)} script sentences found in the take; "
              f"is this the right script? Nothing written except the report: {md}")
        return 2
    json.dump(clauses, open(out, "w"), indent=1)
    speech = sum(c["end"] - c["start"] for c in clauses)
    print(f"clauses_from_script: {len(clauses)} clauses -> {out} ({speech:.1f}s of {take['dur']:.1f}s kept; "
          f"{found}/{len(sents)} sentences, {sum(len(o) for _p, o in plan)} earlier attempt(s) cut, "
          f"{sum(1 for r, *_ in adlibs if r == 'adlib')} ad-lib(s) kept, "
          f"{sum(1 for r, *_ in adlibs if r != 'adlib')} other cut(s), {len(tight)} boundary(ies) to listen to)")
    print(f"  report: {md}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

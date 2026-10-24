#!/usr/bin/env python3
"""Catch stutters and restarts in a yap take so they never ship.

the creator kept hitting the same defect: a take where they say a word twice ("the
the"), restarts a clause ("you're not bad at this ... you're not bad at this"),
or the source has a triple restart ("now use AI, now use AI, now use AI in
their buying process"). These were caught BY HAND, clip by clip. This makes it
automatic: run it on the word-level transcript and it reports every stutter
with timestamps, plus a ready-to-use caption drop-list and video cut-ranges.

Input is the SAME whisper JSON build_ass.py eats: whisper-cli -oj -ml 1 -sow
-dtw  ->  {"transcription":[{"offsets":{"from":ms,"to":ms},"text":"..."}]}.
Word indices match build_ass.py exactly (non-empty words only), so the emitted
drops feed straight into build_ass.py --corrections. Each names the word it drops,
so a re-cut that moves the index skips it instead of deleting another word.

Usage:
  python3 stutter_check.py --words words.json
      [--emit-corrections fix.json]   # merge {"drop":{"<idx>":{"from":word}}} for captions
      [--accept-file <out>_stutter_ok.json]
      [--script <out>_script.txt] [--free-from <opinion start s>]
      [--max-phrase 6] [--gap 3] [--strict]
Exit code: 0 = clean, 2 = something needs a decision (so a QA gate can fail).

The script settles a repeat it says itself (3.8.0, yaplib/script.py): printed "script", never
dropped, never gating. The accept-file takes bare keys (clear a MEDIUM) and
{"key": ..., "why": ...} entries (clear a HIGH too, because a reason was written down).

It KEEPS the later (usually cleaner) delivery and drops the earlier repeat.
Function-word dups and >=3x runs are HIGH confidence; a one-off content-word
repeat (could be deliberate emphasis: "very very") is flagged MEDIUM so a human
can veto. --strict drops MEDIUM too.

MEDIUM MUST BE ADJUDICATED, IT IS NOT ADVISORY (2026-08-27). This gate used to
print MEDIUM and let the build pass, and on 2026-08-24 that shipped a real
restart: "Toronto's local... Toronto's local news ran it" was flagged MEDIUM in
BOTH runs of the CBRE episode, sitting in a cluster with the deliberate "CNBC
ran it / Gizmodo ran it" anaphora, so it was waved through with them and went
out in the delivered file. The detector was right; nothing forced a decision.
The caption gate has never shipped a garble because it refuses to pass until
every flagged word is either fixed or written into an accept-file, so the
repetition gate now works the same way: each MEDIUM must be cut from the clause
plan or listed in --accept-file before the build proceeds. Keys are the
normalised repeated text, so they survive a re-cut (timestamps do not).
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import words as ywords  # noqa: E402
from yaplib import script as yscript  # noqa: E402

FUNCTION = {"the", "a", "an", "i", "you", "we", "they", "it", "to", "and",
            "of", "that", "this", "is", "in", "on", "so", "but", "for", "my",
            "your", "no", "not", "do", "dont", "im", "its", "be", "he", "she"}


def norm(t):
    return re.sub(r"[^a-z0-9']", "", t.lower())


def skel(t):
    # consonant skeleton: 'belt' and 'built' both -> 'blt'. Whisper often hears
    # a fumbled first take differently ("belt in" vs "built in"); exact-token
    # matching misses the restart, the skeleton does not. Only meaningful for
    # skeletons >= 3 chars ('in'/'an' would otherwise collide on 'n').
    return re.sub(r"[aeiou]", "", norm(t))


def same(a, b):
    if a == b:
        return True
    sa, sb = skel(a), skel(b)
    return len(sa) >= 3 and sa == sb


def accept_key(text):
    """Stable identity for a flagged repeat: the normalised words, space joined.
    Deliberately NOT time-based, so an accepted call survives a re-cut."""
    return " ".join(k for k in (norm(t) for t in text.split()) if k)


def _accept_entries(path):
    if not path:
        return []
    try:
        d = json.load(open(path))
    except Exception:
        return []
    return d if isinstance(d, list) else []


def load_accepted(path):
    """Every key in the accept-file. An entry is a bare string (clears a MEDIUM) or
    {"key": "...", "why": "..."} (3.8.0: also clears a HIGH, see load_accepted_high)."""
    out = set()
    for x in _accept_entries(path):
        k = x.get("key", "") if isinstance(x, dict) else str(x)
        if k:
            out.add(accept_key(k))
    return out


def load_accepted_high(path):
    """Keys that clear a HIGH: only entries that carry a written reason. A HIGH used to be
    clearable only by YAP_ALLOW_STUTTER=1, which silenced all three detectors for the whole
    video (three of five 2026-10-23 cuts shipped that way, for one deliberate callback each).
    A reason per repeat keeps every other repeat gated."""
    return {accept_key(x["key"]) for x in _accept_entries(path)
            if isinstance(x, dict) and x.get("key") and str(x.get("why", "")).strip()}


def scripted(flag, w, script, free=None):
    """Why the script settles this flag, or "". w is the word list the flag indexes into
    ((t0, t1, text, norm) tuples); script is yaplib.script.load() output. A repeat counts as
    scripted only when the script says it as many times, as close together, as the take does;
    nothing after the opinion slot's start (free) is settled by the script."""
    if not script:
        return ""
    st, en, kind, conf, text, t0, t1 = flag
    if free is not None and t0 >= free:
        return ""
    tok = [yscript.norm(x[2]) for x in w]
    m = re.match(r"repeat x(\d+)", kind)
    if m:
        n = int(m.group(1))
        return f"the script says it {n} times in a row" if yscript.says_run(script, tok[st], n) else ""
    m = re.match(r"restart (\d+)w(?: \+(\d+) filler)?", kind)
    if m:
        L, g = int(m.group(1)), int(m.group(2) or 0)
        unit = tok[st:st + L]
        return ("the script says it twice here" if yscript.says_twice_near(script, unit, L + g + 2) else "")
    m = re.match(r"re-read (\d+)w", kind)
    if m:
        L = int(m.group(1))
        unit = tok[st:st + L]
        heard_in = tok if free is None else [t for t, x in zip(tok, w) if x[0] < free]
        said, heard = yscript.count(script, unit), yscript.count(heard_in, unit)
        if said >= 2 and heard <= said:
            return f"the script says it {said} times, the take {heard}"
    return ""


def load_words(path):
    """[(t0, t1, text, norm)]: yaplib.words.load_words plus the normalised
    token, so the index here is the canonical word index build_ass.py and
    the corrections json use."""
    return [(s, e, t, norm(t)) for s, e, t in ywords.load_words(path)]


def find_flags(w, max_phrase=6, gap=3):
    """Detection core. w = [(t0,t1,text,norm), ...]. Returns flag tuples
    (start_i, end_i_exclusive_to_drop, kind, conf, text, t0, t1)."""
    class A: pass
    a = A(); a.max_phrase = max_phrase; a.gap = gap
    n = len(w)
    tok = [x[3] for x in w]
    flags = []           # (start_i, end_i_exclusive_to_drop, kind, conf, text, t0, t1)
    covered = [False] * n

    # --- Pass A: immediate single-word duplicate runs (the the / no no no) ---
    i = 0
    while i < n:
        j = i + 1
        while j < n and tok[j] and same(tok[j], tok[i]):
            j += 1
        run = j - i
        if run >= 2 and tok[i] and w[j - 1][1] - w[i][0] >= 0.15:
            conf = "HIGH" if (run >= 3 or tok[i] in FUNCTION) else "MEDIUM"
            # "used it, it had": a function-word dup across a clause boundary
            # (trailing punctuation on the first) is normal English -> review.
            if run == 2 and w[i][2].rstrip()[-1:] in ",.?!":
                conf = "MEDIUM"
            # keep the LAST occurrence, drop i..j-2
            for k in range(i, j - 1):
                covered[k] = True
            flags.append((i, j - 1, f"repeat x{run}", conf,
                          " ".join(w[k][2] for k in range(i, j)),
                          w[i][0], w[j - 2][1]))
            i = j
        else:
            i += 1

    # --- Pass B/C: phrase restart, adjacent or with a small filler gap ---
    # longest n first so "you're not bad at this" wins over "not bad".
    for L in range(a.max_phrase, 1, -1):
        i = 0
        while i + 2 * L <= n + a.gap:
            if i + L > n or any(covered[i:i + L]) or not all(tok[i:i + L]):
                i += 1; continue
            first = tok[i:i + L]
            matched = False
            for g in range(0, a.gap + 1):
                s = i + L + g
                if s + L > n:
                    break
                if any(covered[s:s + L]):
                    continue
                if all(same(x, y) for x, y in zip(tok[s:s + L], first)):
                    # Evidence from the Jun 29/Jul 5 batch: every true restart
                    # was a >=3-word echo; every 2-word echo was rhetoric
                    # ("it's not, it's not X", "match your grammar / match
                    # your scar tissue"). 2-word echoes -> MEDIUM (the line
                    # audit adjudicates); >=3 words -> HIGH (gates the build).
                    conf = "MEDIUM" if L == 2 else "HIGH"
                    # g==0 means the two halves are back to back with nothing
                    # between them, which is the ABORTED-RESTART shape ("Toronto's
                    # local... Toronto's local news"). g>=1 put a real word in
                    # between, which is how anaphora reads ("CNBC ran it, Gizmodo
                    # ran it"). Both stay MEDIUM at L==2 because "again, and
                    # again, and again" is also adjacent and deliberate, but the
                    # label says which shape it is so the review is not a coin flip.
                    kind = f"restart {L}w" + (f" +{g} filler" if g else " adjacent")
                    for k in range(i, s):
                        covered[k] = True
                    flags.append((i, s, kind,
                                  conf, " ".join(w[k][2] for k in range(i, s + L)),
                                  w[i][0], w[s - 1][1]))
                    matched = True
                    i = s + L
                    break
            if not matched:
                i += 1

    # --- Pass D: distant line repetition (missed a line, re-read it) ---
    # A >=4-word phrase spoken twice is almost never style: within
    # 20s it is a re-read of a missed line (HIGH, gates the build); farther
    # apart it may be a deliberate callback of the hook/button (MEDIUM).
    # Both copies are reported; corrections default to dropping the FIRST,
    # the line audit picks the cleaner take. Needs >=2 content words so
    # naturally recurring filler ("and then you can") never flags.
    for L in range(a.max_phrase, 3, -1):
        seen = {}
        for i in range(0, n - L + 1):
            if any(covered[i:i + L]) or not all(tok[i:i + L]):
                continue
            key = tuple(skel(t) or t for t in tok[i:i + L])
            if sum(1 for t in tok[i:i + L] if t not in FUNCTION) < 2:
                continue
            if key in seen:
                p0 = seen[key]
                if i - p0 > L + a.gap:            # beyond Pass B's reach
                    dt = w[i][0] - w[p0][0]
                    # topic noun phrases recur naturally ("a cease and desist
                    # letter" twice in a video ABOUT one); a true missed-line
                    # re-read echoes the whole line. 6+ word echoes within 20s
                    # gate the build; shorter or older echoes go to review.
                    conf = "HIGH" if (dt <= 20.0 and L >= 6) else "MEDIUM"
                    for k in list(range(p0, p0 + L)) + list(range(i, i + L)):
                        covered[k] = True
                    flags.append((p0, p0 + L,
                                  f"re-read {L}w (again @{w[i][0]:.1f}s)", conf,
                                  " ".join(w[k][2] for k in range(p0, p0 + L)),
                                  w[p0][0], w[p0 + L - 1][1]))
                    continue
            seen[key] = i

    flags.sort(key=lambda f: f[0])
    return flags


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", required=True)
    ap.add_argument("--emit-corrections", default="")
    ap.add_argument("--max-phrase", type=int, default=6)
    ap.add_argument("--gap", type=int, default=3,
                    help="allow up to N filler words between a restart's two halves")
    ap.add_argument("--strict", action="store_true",
                    help="also drop MEDIUM-confidence (one-off content-word) repeats")
    ap.add_argument("--accept-file", default="",
                    help="JSON list of repeats already listened to and judged "
                         "deliberate. An unlisted MEDIUM fails the gate: MEDIUM "
                         "is a decision to make, not a note to skim.")
    ap.add_argument("--script", default="",
                    help="<out>_script.txt: a repeat the script says as often, as close together, "
                         "is the script and needs no decision (3.8.0)")
    ap.add_argument("--free-from", type=float, default=None,
                    help="seconds where the unscripted opinion slot starts: the script settles nothing after it")
    a = ap.parse_args()

    w = load_words(a.words)
    flags = find_flags(w, a.max_phrase, a.gap)
    script = yscript.load(a.script)
    why = {f: scripted(f, w, script, a.free_from) for f in flags}
    accepted = load_accepted(a.accept_file)
    accepted_high = load_accepted_high(a.accept_file)
    settled = {f for f in flags if why[f] or (f[3] == "HIGH" and accept_key(f[4]) in accepted_high)}
    keep = [f for f in flags if (a.strict or f[3] == "HIGH") and f not in settled]
    unjudged = [f for f in flags
                if f[3] != "HIGH" and not a.strict and f not in settled
                and accept_key(f[4]) not in accepted]

    if not flags:
        print("clean: no stutters or restarts detected")
        return

    print(f"found {len(flags)} stutter/restart span(s) "
          f"({sum(1 for f in flags if f[3]=='HIGH')} HIGH):\n")
    for f in flags:
        st, en, kind, conf, text, t0, t1 = f
        if why[f]:
            act = "script"
        elif f in settled:
            act = "ok'd"
        elif conf == "HIGH" or a.strict:
            act = "DROP"
        elif accept_key(text) in accepted:
            act = "ok'd"
        else:
            act = "JUDGE"
        print(f"  [{conf:6}] {t0:6.2f}-{t1:6.2f}s  {kind:20} {act:6} "
              f"words {st}-{en-1}  | \"{text}\"" + (f"  ({why[f]})" if why[f] else ""))

    drop = sorted({k for f in keep for k in range(f[0], f[1])})
    print(f"\ncaption drop indices ({len(drop)} words): {drop}")
    print("video cut-ranges to remove (seconds):")
    for st, en, kind, conf, text, t0, t1 in keep:
        print(f"  {t0:.2f} -> {t1:.2f}")

    if a.emit_corrections:
        try:
            existing = json.load(open(a.emit_corrections))
        except Exception:
            existing = {}
        # the drop form that names its word, so a re-cut cannot turn it on another one;
        # legacy list entries stay blind ({}), exactly as they were applied before
        cur = existing.get("drop", [])
        if isinstance(cur, list):
            cur = {str(v["index"] if isinstance(v, dict) else v):
                   ({"from": v["from"]} if isinstance(v, dict) and v.get("from") else {})
                   for v in cur}
        cur.update(ywords.drop_entries(w, drop))
        existing["drop"] = dict(sorted(cur.items(), key=lambda kv: int(kv[0])))
        json.dump(existing, open(a.emit_corrections, "w"), indent=2)
        print(f"\nwrote/merged {len(drop)} drops into {a.emit_corrections}")

    if unjudged:
        print(f"\n{len(unjudged)} repeat(s) need a decision. LISTEN to each span, then "
              "either cut it out via the clause plan, or, if it is deliberate, add "
              "its key to the accept-file"
              + (f" ({a.accept_file})" if a.accept_file else " (--accept-file)") + ":")
        print(json.dumps(sorted({accept_key(f[4]) for f in unjudged}), indent=2))

    if keep and any(f[3] == "HIGH" for f in keep):
        print("\nA HIGH is a real restart until shown otherwise: cut it via the clause plan. If you "
              "listened and it is deliberate, add {\"key\": \"<its words>\", \"why\": \"<what you heard>\"} "
              "to the accept-file; a bare key clears a MEDIUM only.")
    sys.exit(2 if (any(f[3] == "HIGH" for f in keep) or unjudged) else 0)


if __name__ == "__main__":
    main()

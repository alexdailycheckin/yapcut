#!/usr/bin/env python3
"""hook_lint.py: mechanical checks on the two positions a batch gets judged by,
the first line and the last one. v4 (2026-08-10, closings added).

The RULING gate is human and not in this file: the VACUUM TEST. A cold scroller with
zero context, sound off, one fixation, must instantly get what the video is about.
Plain concrete claim; duplicating the spoken hook's claim is fine and often right
(dual-track for sound-off viewers); clever riddles are dead. Law:
references/the-show.md, "The text-hook layer".

This lint only checks what a machine can judge:
  FAIL too-long   more than 9 words
  FAIL banned     banned words / em or en dashes
  FAIL epigram    the two-sentence antithesis, anywhere in shipping copy
  WARN no-alts    fewer than 2 text_hook_alts (burn-and-test wants variants)
  WARN batch-rhyme  two hooks in the batch open with the same word

Why closings are in a file called hook_lint: openings were gated from the start and
closings never were, so the same closing mold landed on two adjacent episodes in the
08-02 batch and nothing caught it. First line and last line are the same class of
problem, so they get checked in the same pass.

Usage: python3 hook_lint.py --week weeks/<date>.json [--dir <workspace>]

Exit codes (Contract 1, 2026-09-09): 0 pass, 1 warnings only, 2 any FAIL. --dir is
accepted so every gate takes the same argv; a relative --week that is not found from
the cwd is looked up under the workspace.
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yapcut_home import radar_home  # noqa: E402

HOME = radar_home(required=False)   # consumes --dir; the lint needs no workspace itself

BANNED = {"leverage", "utilize", "delve", "seamless", "unlock", "empower",
          "game-changer", "revolutionize", "guys"}

# The two-sentence antithesis epigram: "That's not a social team. That's a
# permission structure." Both halves short and symmetrical, the second asserting
# what the first denied. It reads as a conclusion while carrying no fact, which is
# why it kept winning the closing slot on merit it did not have. Mirrors the
# ~/.claude/hooks/prose-gate.py deny, which covers prose files but not week JSON.
EPIGRAM = re.compile(
    r"\b(?:it|that|this)(?:'s\s+not|\s+is\s+not|\s+was\s+not|\s+isn'?t|\s+wasn'?t)\s+"
    r"(?:\w+[ ,]){0,5}\w+\s*[.!?,]\s+"
    r"(?:it|that|this)(?:'s|\s+is|\s+was)\s+(?:\w+[ ,]){0,5}\w+\s*[.!?]",
    re.I,
)

# Everything a viewer or reader actually receives. Internal fields (directions,
# value, psych, note) are working notes and are deliberately not linted.
SHIPPING_FIELDS = ("text_hook", "spoken_hook", "script")


def epigram_hits(item):
    """(field, matched text, sits_on_the_closing_line) per epigram in shipping copy."""
    out = []
    fields = [(f, item.get(f) or "") for f in SHIPPING_FIELDS]
    fields.append(("linkedin.body", (item.get("linkedin") or {}).get("body") or ""))
    for field, text in fields:
        close = closing_line(text)
        for m in EPIGRAM.finditer(text):
            snippet = m.group(0).strip()
            out.append((field, snippet, snippet in close))
    return out


def closing_line(text):
    lines = [l.strip() for l in (text or "").split("\n") if l.strip()]
    return lines[-1] if lines else ""


def lint_item(item, batch_first_words):
    hook = item.get("text_hook", "") or ""
    fails, warns = [], []

    nwords = len(hook.split())
    if nwords > 9:
        fails.append(f"too-long: {nwords} words (max 9)")
    if "—" in hook or "–" in hook:
        fails.append("banned: em/en dash")
    hits = BANNED & set(re.findall(r"[a-z-]+", hook.lower()))
    if hits:
        fails.append(f"banned: {', '.join(sorted(hits))}")

    alts = item.get("text_hook_alts") or []
    if len(alts) < 2:
        warns.append(f"no-alts: {len(alts)} alternates (want 2+ for hook testing)")

    first = (hook.split() or [""])[0].lower().strip(".,!?")
    if first and batch_first_words.count(first) > 1:
        warns.append(f"batch-rhyme: another hook in this batch also opens with '{first}'")

    for field, snippet, at_close in epigram_hits(item):
        where = f"{field}, CLOSING LINE" if at_close else field
        fails.append(f"epigram [{where}]: \"{snippet}\"")

    return fails, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True)
    ap.add_argument("--dir", help="workspace (consumed by yapcut_home when given first)")
    args = ap.parse_args()
    path = args.week
    if not os.path.exists(path) and HOME is not None and not os.path.isabs(path):
        alt = os.path.join(str(HOME), path)
        if os.path.exists(alt):
            path = alt
    if not os.path.exists(path):
        print(f"no week file at {path}")
        sys.exit(2)
    week = json.load(open(path))
    items = week.get("distribution", []) + week.get("office", [])
    firsts = [(it.get("text_hook", "").split() or [""])[0].lower().strip(".,!?")
              for it in items]

    n_fail = n_warn = 0
    for it in items:
        fails, warns = lint_item(it, firsts)
        status = "FAIL" if fails else ("warn" if warns else "pass")
        n_fail += len(fails)
        n_warn += len(warns)
        print(f"[{status}] {it['id']}: \"{it.get('text_hook','')}\"")
        for f in fails:
            print(f"        FAIL {f}")
        for w in warns:
            print(f"        warn {w}")

    # The batch check, gate 6. Openings were always eyeballed in a column; closings
    # never were, which is how one mold took two slots in the same slate unseen.
    print("\nCLOSING LINES (read them in a column: two on the same mold = rewrite one)")
    for it in items:
        close = closing_line(it.get("script", "")) or "(no script)"
        print(f"  {it['id']:16} {close[-88:]}")

    print("\nREMINDER: the ruling gate is the human VACUUM TEST (the-show.md).")
    rc = 2 if n_fail else (1 if n_warn else 0)
    print(f"hook_lint: {n_fail} fail, {n_warn} warn -> rc {rc}")
    sys.exit(rc)


if __name__ == "__main__":
    main()

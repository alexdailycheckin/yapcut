#!/usr/bin/env python3
"""hook_lint.py: mechanical checks for burned text hooks. v3 (2026-08-02).

The RULING gate is human and not in this file: the VACUUM TEST. A cold scroller with
zero context, sound off, one fixation, must instantly get what the video is about.
Plain concrete claim; duplicating the spoken hook's claim is fine and often right
(dual-track for sound-off viewers); clever riddles are dead. Law:
references/the-show.md, "The text-hook layer".

This lint only checks what a machine can judge:
  FAIL too-long   more than 9 words
  FAIL banned     banned words / em or en dashes
  WARN no-alts    fewer than 2 text_hook_alts (burn-and-test wants variants)
  WARN batch-rhyme  two hooks in the batch open with the same word

Usage: python3 scripts/hook_lint.py --week weeks/<date>.json  (exit 1 on any FAIL)
"""
import argparse, json, re, sys

BANNED = {"leverage", "utilize", "delve", "seamless", "unlock", "empower",
          "game-changer", "revolutionize", "guys"}


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

    return fails, warns


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week", required=True)
    args = ap.parse_args()
    week = json.load(open(args.week))
    items = week.get("distribution", []) + week.get("office", [])
    firsts = [(it.get("text_hook", "").split() or [""])[0].lower().strip(".,!?")
              for it in items]

    any_fail = False
    for it in items:
        fails, warns = lint_item(it, firsts)
        status = "FAIL" if fails else ("warn" if warns else "pass")
        any_fail |= bool(fails)
        print(f"[{status}] {it['id']}: \"{it.get('text_hook','')}\"")
        for f in fails:
            print(f"        FAIL {f}")
        for w in warns:
            print(f"        warn {w}")
    print("\nREMINDER: the ruling gate is the human VACUUM TEST (the-show.md).")
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()

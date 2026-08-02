#!/usr/bin/env python3
"""hook_lint.py: machine gate for on-screen text hooks (the two-channels law).

The text hook is a SECOND channel, not a caption of the first. At second zero the
viewer already gets the news from the headline receipt and the story from the voice;
the burned text must carry what neither does: the stake or the twist. This lint
catches the failure modes that keep shipping:

  FAIL duplicate-channel   text_hook shares >=2 content words (or is a substring)
                           of the first ~10 spoken words
  FAIL too-long            more than 7 words (one-fixation ceiling)
  FAIL banned              banned words / em or en dashes
  WARN topic-label         no digit, no tension lexicon hit, no question mark:
                           likely a label, not a gap
  WARN no-alts             text_hook_alts missing or < 2 (burn-and-test workflow
                           wants variants ready)
  WARN batch-rhyme         two hooks in the batch open with the same word

Usage: python3 scripts/hook_lint.py --week weeks/<date>.json  (exit 1 on any FAIL)
"""
import argparse, json, re, sys

STOP = set("""a an the this that these those is are was were be been being it its of in on at
to for with by from as and or but so if then than not no do does did done have has had you
your we our they their he she his her i my me who what when where how why will would can
could just about into over under out up down off more most very really new week this
sort of""".split())

BANNED = {"leverage", "utilize", "delve", "seamless", "unlock", "empower",
          "game-changer", "revolutionize", "guys"}

TENSION = {"free", "trap", "secret", "banned", "mistake", "wrong", "lie", "lied",
           "nobody", "everyone", "never", "always", "hidden", "quietly", "pay",
           "paying", "paid", "broke", "dead", "dying", "stole", "steal", "owns",
           "own", "beat", "lost", "won", "back", "sale", "worth", "cost", "polite",
           "checkbox", "imaginary", "waiting", "first", "last"}


def content_words(text):
    words = re.findall(r"[a-z0-9']+", text.lower())
    return [w for w in words if w not in STOP and len(w) > 2]


def lint_item(item, batch_first_words):
    hook = item.get("text_hook", "") or ""
    spoken = item.get("spoken_hook", "") or ""
    fails, warns = [], []

    nwords = len(hook.split())
    if nwords > 7:
        fails.append(f"too-long: {nwords} words (max 7)")
    if "—" in hook or "–" in hook:
        fails.append("banned: em/en dash")
    hits = BANNED & set(re.findall(r"[a-z-]+", hook.lower()))
    if hits:
        fails.append(f"banned: {', '.join(sorted(hits))}")

    spoken_head = " ".join(spoken.split()[:10]).lower()
    hcw = set(content_words(hook))
    scw = set(content_words(spoken_head))
    shared = hcw & scw
    norm_hook = " ".join(re.findall(r"[a-z0-9']+", hook.lower()))
    if norm_hook and norm_hook in " ".join(re.findall(r"[a-z0-9']+", spoken.lower())):
        fails.append("duplicate-channel: text hook is contained in the spoken hook")
    elif len(shared) >= 2:
        fails.append(f"duplicate-channel: shares {sorted(shared)} with the spoken opener")

    NUMWORDS = {"zero", "one", "two", "three", "four", "five", "six", "seven",
                "eight", "nine", "ten", "hundred", "thousand", "million", "billion",
                "trillion", "half", "double", "triple"}
    has_number = bool(re.search(r"\d", hook)) or bool(
        set(re.findall(r"[a-z]+", hook.lower())) & NUMWORDS)
    if not has_number and not (hcw & TENSION) and "?" not in hook:
        warns.append("topic-label: no digit, no tension word, no question; likely a label not a gap")

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
    items = week.get("distribution", [])
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
    sys.exit(1 if any_fail else 0)


if __name__ == "__main__":
    main()

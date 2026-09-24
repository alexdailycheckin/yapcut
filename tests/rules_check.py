#!/usr/bin/env python3
"""rules_check.py: the two rulebooks are the only place their numbers live.

Each plugin carries a rules.json that its scripts read on the Mac and the Anima app reads
on the phone. This check fails the build when that stops being true:

  - a rulebook does not parse, or lost its version
  - a number the two plugins share disagrees between them (the text hook limit)
  - a duplicated literal came back into a script that should read the rulebook
    (the drift 3.3.0 removed: six cutter flags in yapfull.sh, the live caption scale
    and hook height as shell overrides, the loudness target written four times)
  - the gate wording in rules.json and the playbook the engine reads stopped matching

Exit 0 clean, 2 with every failure listed.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
ED = os.path.join(ROOT, "plugins/tiktok-yap-editor/skills/tiktok-yap-editor")
RA = os.path.join(ROOT, "plugins/outlier-radar/skills/outlier-radar")
fails = []


def load(p):
    try:
        with open(p) as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        fails.append(f"{os.path.relpath(p, ROOT)} does not parse: {e}")
        return {}


def text(p):
    with open(p) as f:
        return f.read()


ed = load(os.path.join(ED, "rules.json"))
ra = load(os.path.join(RA, "rules.json"))
for name, r in (("editor", ed), ("radar", ra)):
    if not isinstance(r.get("rules_version"), int):
        fails.append(f"{name} rules.json has no integer rules_version")

# One number, two plugins: the Radar writes the text hook the editor burns.
if ed and ra and ed["hook"]["max_words"] != ra["text_hook"]["max_words"]:
    fails.append(f"hook word limit disagrees: editor hook.max_words {ed['hook']['max_words']} "
                 f"vs radar text_hook.max_words {ra['text_hook']['max_words']}")

# Literals that must not come back.
banned_literals = {
    "scripts/yapfull.sh": [r"--min-gap\b", r"--silence-db\b", r"--padr\b", r"--active-scale\b", r"--hook-y\b", r"HOOK_SECS:-5"],
    "scripts/storyfull.sh": [r"--active-scale\b", r"--hook-y\b", r"HOOK_SECS:-5"],
    "scripts/compose_ass.sh": [r"I=-14\b", r"limit=0\.841"],
    "scripts/gates.sh": [r"-gt 9\b", r"-gt 7\b", r'"6\.0" if'],
    "scripts/yapcut.py": [r"ALT=\[1\.00", r"default=0\.55", r"afade=t=in:st=0:d=0\.004"],
    "scripts/build_ass.py": [r'"minimal": dict\(', r"size -= 4\b"],
}
for rel, pats in banned_literals.items():
    body = text(os.path.join(ED, rel))
    code = "\n".join(l for l in body.splitlines() if not l.lstrip().startswith("#"))
    for p in pats:
        if re.search(p, code):
            fails.append(f"{rel}: '{p}' is back; that value lives in rules.json")
for rel, pats in {"hook_lint.py": [r'BANNED = \{"leverage"'], "check_fidelity.py": [r"DEFAULT_CEILING, DEFAULT_WPS = 189"],
                  "build_pack.py": [r"DEFAULT_CEILING, DEFAULT_WPS = 189"]}.items():
    for p in pats:
        if re.search(p, text(os.path.join(RA, rel))):
            fails.append(f"{rel}: '{p}' is back; that value lives in rules.json")

# Gate wording: rules.json is what the phone's judge reads, SKILL.md is what the engine reads.
squash = lambda s: re.sub(r"\s+", " ", s)
if ra:
    if ra["gates"]["two_question"] not in text(os.path.join(RA, "SKILL.md")):
        fails.append("radar rules.json gates.two_question no longer appears verbatim in SKILL.md")
    if squash(ra["gates"]["vacuum_test"]) not in squash(text(os.path.join(RA, "hook_lint.py"))):
        fails.append("radar rules.json gates.vacuum_test no longer matches hook_lint.py's docstring")

# The phone's interview and writer text must still be what the playbook says.
if ra:
    skill = text(os.path.join(RA, "SKILL.md"))
    for q in (ra.get("onboarding") or {}).get("questions", []):
        if q.get("skill_ref") and q["skill_ref"] not in skill:
            fails.append(f"radar onboarding question '{q.get('key')}' points at SKILL.md text that is gone: {q['skill_ref']!r}")
    w = ra.get("writer") or {}
    for label in ("language", "quantity"):
        if w.get(label) and w[label] not in skill:
            fails.append(f"radar writer.{label} no longer appears verbatim in SKILL.md")
    for m in w.get("five_moves", []):
        if f"| {m['move']} | {m['does']} |" not in skill:
            fails.append(f"radar writer.five_moves '{m['move']}' no longer matches the SKILL.md table")

# Every pattern compiles.
for name, spec in (ra.get("patterns") or {}).items():
    if name.startswith("_"):
        continue
    try:
        re.compile(spec["pattern"])
    except re.error as e:
        fails.append(f"radar patterns.{name} does not compile: {e}")

if fails:
    print("\n".join("  FAIL " + f for f in fails))
    sys.exit(2)
print("  rulebooks consistent")

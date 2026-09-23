#!/usr/bin/env python3
"""rules.py: the editor's rulebook, loaded once.

`rules.json` sits at the skill root and holds every number the Mac editor and the phone
editor share (the Anima app reads the same file). Scripts read it here instead of carrying
their own literal, so a value changes in one place and both editors follow on the next
release. Before 3.3.0 six cutter numbers lived in yapcut.py AND yapfull.sh, and the live
caption scale and hook height were shell overrides of a preset that said something else.

    from yaplib import rules
    rules.get("cut.min_gap_s")          # 0.55
    rules.R["captions"]["presets"]      # the whole table

Shell scripts use the CLI, which prints one value (JSON for lists and objects):

    python3 yaplib/rules.py get hook.seconds

A missing key is an error, never a silent default: a rulebook that lost a value must
fail loudly, or the two editors drift without anyone seeing it.
"""
import json
import os
import sys

PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "rules.json")


def _load():
    with open(PATH) as f:
        return json.load(f)


R = _load()


def get(path, rules=None):
    node = R if rules is None else rules
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            raise KeyError(f"rules.json has no '{path}' (missing '{key}'); {os.path.abspath(PATH)}")
        node = node[key]
    return node


def _main(argv):
    if len(argv) == 3 and argv[1] == "get":
        v = get(argv[2])
        print(json.dumps(v) if isinstance(v, (list, dict)) else ("true" if v is True else "false" if v is False else v))
        return 0
    if len(argv) == 2 and argv[1] == "path":
        print(os.path.abspath(PATH))
        return 0
    print("usage: rules.py get <dotted.key> | rules.py path", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(_main(sys.argv))

#!/usr/bin/env python3
"""rules.py: the Radar's rulebook, loaded once.

`rules.json` sits beside this file and holds the script rules the Mac engine and the phone
share: the week schema's lanes, qa values and id shape, the word ceiling, the text-hook
limits, the epigram and candour patterns, and the two-question gate as text. The Anima app
reads the same file, so a rule changes in one place and both surfaces follow on the next
release.

    import rules
    rules.get("text_hook.max_words")    # 9
    rules.regex("epigram")              # compiled with the file's flags

A missing key is an error, never a silent default: a rulebook that lost a value must fail
loudly, or the two surfaces drift without anyone seeing it.
"""
import json
import os
import re
import sys

PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "rules.json")

with open(PATH) as _f:
    R = json.load(_f)

_FLAGS = {"i": re.I, "m": re.M, "s": re.S}


def get(path):
    node = R
    for key in path.split("."):
        if not isinstance(node, dict) or key not in node:
            raise KeyError(f"rules.json has no '{path}' (missing '{key}'); {PATH}")
        node = node[key]
    return node


def compile_pattern(spec):
    flags = 0
    for c in spec.get("flags", ""):
        flags |= _FLAGS[c]
    return re.compile(spec["pattern"], flags)


def regex(name):
    """A pattern from `patterns.<name>`, or any {pattern, flags} object by dotted path."""
    spec = get(name if "." in name else f"patterns.{name}")
    return compile_pattern(spec)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "get":
        v = get(sys.argv[2])
        print(json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v)
        sys.exit(0)
    print("usage: rules.py get <dotted.key>", file=sys.stderr)
    sys.exit(2)

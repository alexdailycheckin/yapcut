#!/usr/bin/env python3
"""Append the brand CTA block (handle + contact lines) to a caption .ass file.

One implementation for both orchestrators: yapfull.sh and storyfull.sh used to
carry this as two copies of an inline Python heredoc, each with its own hex to
ASS colour converter (the audit's third copy). The block sits bottom-centre for
the last --lead seconds, in the label font, with the accent spark glyph.

Usage:
  cta_block.py --ass cap_<out>.ass --dur <seconds> --handle "YOURNAME.COM" \
      [--contact "line1\\nline2"] --font "Space Mono" --accent "#FF5A2A" \
      --base "#FFFFFB" --ink "#232323" [--lead 9.7]
An empty --handle is a no-op (exit 0), so callers need no branch.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import ass as yass  # noqa: E402
from yaplib import media  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ass", required=True)
    ap.add_argument("--dur", type=float, required=True, help="video duration (block ends here)")
    ap.add_argument("--handle", default="")
    ap.add_argument("--contact", default="", help="extra lines, newline separated")
    ap.add_argument("--font", default="Montserrat Black")
    ap.add_argument("--accent", default="none")
    ap.add_argument("--base", default="#FFFFFF")
    ap.add_argument("--ink", default="#000000")
    ap.add_argument("--lead", type=float, default=9.7, help="seconds before the end the block appears")
    a = ap.parse_args()

    if not a.handle.strip():
        return 0
    A = None if yass.is_none(a.accent) else yass.hex_to_ass(a.accent)
    B = yass.hex_to_ass(a.base)
    I = yass.hex_to_ass(a.ink)
    hs = max(0.0, a.dur - a.lead)
    lines = [l for l in a.contact.replace("\\n", "\n").split("\n") if l.strip()]
    spark = (f"{{\\1c{A}&}}+ " if A else "+ ")
    body = spark + f"{{\\1c{B}&}}{a.handle}"
    for l in lines:
        body += rf"\N{{\fs30\1c{B}&}}{l}"
    ev = (rf"Dialogue: 2,{yass.cs(hs)},{yass.cs(a.dur)},Cap,,0,0,0,,"
          rf"{{\an2\pos({media.W // 2},{media.H - 128})\fn {a.font}\3c{I}\bord5\shad0\fsp2\fad(150,0)}}"
          rf"{{\fs38}}{body}")
    with open(a.ass, encoding="utf-8") as f:
        s = f.read()
    with open(a.ass, "w", encoding="utf-8") as f:
        f.write(s.rstrip() + "\n" + ev + "\n")
    print(f"cta block: {a.handle} from {hs:.2f}s to {a.dur:.2f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

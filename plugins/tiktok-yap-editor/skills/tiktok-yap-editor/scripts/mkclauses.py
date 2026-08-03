#!/usr/bin/env python3
"""Build a clauses.json for yapcut from compact rows, so a long plan stays readable.

Writing clause plans by hand means repeating the absolute source path on every
entry, which makes a 30-clause episode unreviewable and easy to typo. Feed the
segmenter's run boundaries in as `start end label [flags]` instead.

Usage:
  python3 mkclauses.py /abs/path/CLIP.MOV out.json <<'ROWS'
  # start  end    label               flags
  1.20     9.76   hook                protect_tail
  12.24    14.78  the-turn            protect_tail
  59.84    70.35  the-stat            gain=6
  ROWS

Flags:
  protect_tail  keep the final word's decay (stops the tail trim eating it)
  keep_whole    no internal silence processing at all
  gain=<db>     boost a quietly-spoken span

Take the numbers from segmenter.py, whose boundaries are silence-accurate, and
NOT from a full-file word transcript, whose times drift by up to ~2s mid-file.
Blank lines and #-comments are ignored.
"""
import json
import sys

if len(sys.argv) < 3:
    sys.exit(__doc__)

src, out = sys.argv[1], sys.argv[2]
clauses = []
for lineno, line in enumerate(sys.stdin, 1):
    line = line.strip()
    if not line or line.startswith("#"):
        continue
    parts = line.split()
    if len(parts) < 3:
        sys.exit(f"line {lineno}: need at least 'start end label', got {line!r}")
    try:
        start, end = float(parts[0]), float(parts[1])
    except ValueError:
        sys.exit(f"line {lineno}: start and end must be numbers, got {line!r}")
    if end <= start:
        sys.exit(f"line {lineno}: end must be after start ({start} -> {end})")
    c = {"src": src, "start": start, "end": end, "label": parts[2]}
    for f in parts[3:]:
        if f == "protect_tail":
            c["protect_tail"] = True
        elif f == "keep_whole":
            c["keep_whole"] = True
        elif f.startswith("gain="):
            c["gain_db"] = float(f.split("=", 1)[1])
        else:
            sys.exit(f"line {lineno}: unknown flag {f!r}")
    clauses.append(c)

if not clauses:
    sys.exit("no clauses read from stdin")

# overlapping clauses replay the same audio twice, which reads as a stutter
for a, b in zip(clauses, clauses[1:]):
    if b["start"] < a["end"]:
        sys.exit(f"{a['label']} ends {a['end']} but {b['label']} starts "
                 f"{b['start']}: overlapping clauses replay audio")

json.dump(clauses, open(out, "w"), indent=1)
speech = sum(c["end"] - c["start"] for c in clauses)
print(f"{len(clauses)} clauses -> {out}  ({speech:.1f}s of source selected)")

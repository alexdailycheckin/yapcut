#!/usr/bin/env python3
"""clip_clock.py: when each clip was filmed, in the phone's local time, for the time stamps on a
day-in-the-life or Pomodoro-break edit (3.6.0).

    python3 clip_clock.py <clip or folder> [...]          one line per clip, in filming order
    python3 clip_clock.py <clips> --json                   [{file, clock, at}] for a spec

An iPhone writes `com.apple.quicktime.creationdate` with the local offset ("2026-10-06T07:42:10+0100");
that is the clock on the wall when the clip started, which is what the stamp shows. Without it the
container's UTC `creation_time` is converted to this Mac's local time, and a clip with neither is
listed last with no clock: stamp it from the capture list, never by guessing.

Exit 0, 2 when no clip was found.
"""
import datetime
import glob
import json
import os
import subprocess
import sys

EXT = (".mov", ".mp4", ".m4v")


def clips(args):
    out = []
    for a in args:
        if os.path.isdir(a):
            out += sorted(p for p in glob.glob(os.path.join(a, "*")) if p.lower().endswith(EXT))
        elif os.path.exists(a):
            out.append(a)
    return out


def captured_at(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format_tags", "-of", "json", path],
                       capture_output=True, text=True)
    try:
        tags = json.loads(r.stdout or "{}").get("format", {}).get("tags", {})
    except ValueError:
        tags = {}
    tags = {k.lower(): v for k, v in tags.items()}
    local = tags.get("com.apple.quicktime.creationdate")
    if local:
        try:
            return datetime.datetime.strptime(local.strip(), "%Y-%m-%dT%H:%M:%S%z")
        except ValueError:
            pass
    utc = tags.get("creation_time")
    if utc:
        try:
            return datetime.datetime.fromisoformat(utc.strip().replace("Z", "+00:00")).astimezone()
        except ValueError:
            pass
    return None


def main(argv):
    as_json = "--json" in argv
    files = clips([a for a in argv if a != "--json"])
    if not files:
        print(__doc__)
        return 2
    rows = [(f, captured_at(f)) for f in files]
    far = datetime.datetime.max.replace(tzinfo=datetime.timezone.utc)
    rows.sort(key=lambda r: r[1] or far)
    if as_json:
        print(json.dumps([{"file": f, "clock": t.strftime("%H:%M") if t else None,
                           "at": t.isoformat() if t else None} for f, t in rows], indent=1))
    else:
        for f, t in rows:
            print(f"{t.strftime('%H:%M') if t else '--:--'}  {os.path.basename(f)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

#!/usr/bin/env python3
"""strip_meta: take the tool fingerprints out of a finished video (3.9.7).

An export from 1 November 2026 carried container tags naming its renderer (hyperframes_renderer,
hyperframes_version), FFmpeg's own encoder strings (Lavf in the container, Lavc and libx264 on the
video stream) and x264's settings string inside the H.264 bitstream. No platform is known to act on
them, but they name the tool for no benefit. This rewrites the file without them, in place, with no
re-encode:

  - `-map_metadata -1 -map_chapters -1` drops every global and stream tag and the chapters
  - `-fflags +bitexact` and the per-stream bitexact flags stop FFmpeg writing its own encoder tags
  - on H.264 and HEVC, `filter_units=remove_types=6` / `39|40` drops the SEI units, where x264 and
    x265 write their settings string (a plain stream copy keeps it)
  - `-movflags +faststart` as every export has

Then it checks the result the way the spec asks: no tag containing hyperframes, heygen, lavf, lavc,
c2pa or the word ai, no "hyperframes", "heygen" or "x264 - core" anywhere in the file's bytes, and
the same duration (within one frame), resolution and stream count as before. A check that fails
leaves the original untouched and exits 2.

    strip_meta.py <video> [<video> ...]      strip in place, then check
    strip_meta.py --check <video> [...]      check only (exit 2 on a finding)
"""
import json, os, re, shutil, subprocess, sys

BAD_TAG = re.compile(r"hyperframes|heygen|lavf|lavc|c2pa|\bai\b", re.I)
BAD_BYTES = (b"hyperframes", b"heygen", b"x264 - core", b"x265 (build")
SEI = {"h264": "6", "hevc": "39|40"}


def probe(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                          "format=duration:format_tags:stream=codec_type,codec_name,width,height:stream_tags",
                          "-of", "json", path], capture_output=True, text=True)
    if out.returncode:
        raise SystemExit(f"strip_meta: cannot read {path}: {out.stderr.strip()}")
    return json.loads(out.stdout)


def findings(path):
    d = probe(path)
    bad = []
    for scope, tags in [("format", d.get("format", {}).get("tags", {}))] + \
                       [(f"stream {i}", s.get("tags", {})) for i, s in enumerate(d.get("streams", []))]:
        for k, v in tags.items():
            if BAD_TAG.search(f"{k}={v}"):
                bad.append(f"{scope} tag {k}={v}")
    data = open(path, "rb").read().lower()
    bad += [f"bytes contain {b.decode()!r}" for b in BAD_BYTES if b in data]
    return bad


def shape(d):
    v = [s for s in d["streams"] if s.get("codec_type") == "video"]
    return (len(d["streams"]), (v[0].get("width"), v[0].get("height")) if v else None,
            float(d["format"].get("duration", 0)))


def strip(path):
    before = probe(path)
    vcodec = next((s.get("codec_name") for s in before["streams"] if s.get("codec_type") == "video"), None)
    tmp = path + ".strip.mp4"
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", path, "-map", "0", "-map_metadata", "-1", "-map_chapters", "-1",
           "-c", "copy", "-fflags", "+bitexact", "-flags:v", "+bitexact", "-flags:a", "+bitexact"]
    if vcodec in SEI:
        cmd += ["-bsf:v", f"filter_units=remove_types={SEI[vcodec]}"]
    cmd += ["-movflags", "+faststart", tmp]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise SystemExit(f"strip_meta: ffmpeg failed on {path}: {r.stderr.strip()[-400:]}")
    n0, wh0, d0 = shape(before)
    n1, wh1, d1 = shape(probe(tmp))
    bad = findings(tmp)
    if (n0, wh0) != (n1, wh1) or abs(d0 - d1) > 1 / 30:
        bad.append(f"shape changed: {n0} streams {wh0} {d0:.3f}s -> {n1} streams {wh1} {d1:.3f}s")
    if bad:
        os.remove(tmp)
        print(f"strip_meta: {path} NOT stripped, the result failed its check:\n  " + "\n  ".join(bad))
        return False
    shutil.move(tmp, path)
    print(f"strip_meta: {path} clean ({wh1[0]}x{wh1[1]}, {d1:.2f}s)")
    return True


def main(argv):
    check = "--check" in argv
    paths = [a for a in argv if a != "--check"]
    if not paths:
        print(__doc__)
        return 1
    ok = True
    for p in paths:
        if check:
            bad = findings(p)
            print(f"strip_meta: {p} " + ("clean" if not bad else "FOUND:\n  " + "\n  ".join(bad)))
            ok &= not bad
        else:
            ok &= strip(p)
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

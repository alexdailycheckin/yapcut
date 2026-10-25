#!/usr/bin/env python3
"""ffmpeg/ffprobe helpers and the one canvas definition (W x H = 1080 x 1920).

run(cmd, what) is the only way a yaplib caller shells out: a non-zero exit
raises with the tool's stderr in the message, so a failed ffprobe can never
turn into float('') three lines later (yapcut.py:388 before this module).

CLI (for the shell orchestrators):
  python3 yaplib/media.py duration <file>            -> prints seconds
  python3 yaplib/media.py drift <file> [--limit S]   -> prints drift, exit 2 over limit
  python3 yaplib/media.py streams <file>             -> codec_type=duration lines
  python3 yaplib/media.py has-audio <file>           -> exit 0 yes, 1 no
  python3 yaplib/media.py hdr <file>                 -> prints HLG or PQ, exit 0 HDR, 1 SDR
"""
import json
import subprocess
import sys

W, H = 1080, 1920          # the vertical canvas every script targets
FPS = 30

# Drift limit on the SHIPPED file: 2 frames + ~45ms AAC priming/padding. The
# aac encode inflates the audio STREAM duration with silence; content sync is
# gated strictly (0.067) inside yapcut on the cut itself.
DRIFT_LIMIT_FINAL = 0.112
DRIFT_LIMIT_CUT = 0.067


class MediaError(RuntimeError):
    pass


def run(cmd, what="command", capture=True, text=True, **kw):
    """subprocess.run with check semantics and a readable failure message.
    Returns the CompletedProcess. stderr is captured so the caller's terminal
    stays clean on success and the message carries the tool's own words on
    failure."""
    try:
        return subprocess.run(list(cmd), check=True, capture_output=capture,
                              text=text, **kw)
    except FileNotFoundError as e:
        raise MediaError(f"{what}: {cmd[0]} is not installed ({e})") from None
    except subprocess.CalledProcessError as e:
        err = (e.stderr or "").strip() if isinstance(e.stderr, str) else ""
        tail = "\n".join(err.splitlines()[-12:])
        raise MediaError(f"{what} failed (rc {e.returncode}): {' '.join(map(str, cmd))}\n{tail}") from None


def probe_duration(path):
    """Container duration in seconds. Raises MediaError on any failure."""
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "csv=p=0", str(path)], what="ffprobe duration").stdout.strip()
    try:
        return float(out)
    except ValueError:
        raise MediaError(f"ffprobe duration: no duration for {path!r} (got {out!r})") from None


def audio_start(path):
    """How far after movie time zero the first audio stream starts, in seconds (0.0 if none).

    An iPhone MOV's audio track routinely starts ~29 ms after its video. Anything that
    decodes the audio to a WAV (the cutter's envelope, whisper's words) measures from the
    first audio sample, while `ffmpeg -ss` seeks the movie timeline, so a time measured on
    the WAV lands this much early when used as a seek point. Measured 2026-09-24 by
    cross-correlating seeks against the full decode: -29.0 ms at every point in the take.
    """
    def probe(entries, select=None):
        cmd = ["ffprobe", "-v", "error"] + (["-select_streams", select] if select else []) + [
            "-show_entries", entries, "-of", "csv=p=0", str(path)]
        out = run(cmd, what="ffprobe start").stdout.strip().splitlines()
        try:
            return float(out[0]) if out else 0.0
        except ValueError:
            return 0.0
    # -ss counts from the file's own start, which is not always zero, so the offset is the audio
    # stream's start relative to the container's.
    v = probe("stream=start_time", "a:0") - probe("format=start_time")
    return v if v == v and 0.0 < v < 1.0 else 0.0


# HDR SOURCES (3.7.10). iPhone video shot in HDR is 10-bit BT.2020 with an HLG transfer (PQ from
# other phones and cameras). The cut used to pass those tags through to its 8-bit H.264, and on
# 2026-10-17 the HyperFrames render took its HDR layered-composite path on such a cut and wrote
# 31 GB of raw frames before the disk filled. A cut now tone-maps an HDR source to SDR BT.709
# inside the segment pass (no extra generation) and tags the result bt709. libplacebo would need
# Vulkan, which a Mac does not have, so the chain is zscale + tonemap.
#
# THE CURVE (3.7.11). 3.7.10 shipped mobius at npl=100 and the creator called it tragic: faces
# clipped flat and salmon, face luma 184 where Apple's own SDR rendering of the frame gives 111.
# With no peak given, tonemap reads a linear frame as peaking at 1.0, so mobius compressed
# nothing and clipped. The target is Apple's rendering (AVAssetImageGenerator, forceSDR), with one
# trap: that frame comes back in BT.2020 primaries (QuickTime nclc 9-1-9), so it is compared after
# conversion to 709. Against it, npl=1000 (HLG's reference display) into reinhard peak 1.5,
# param 0.5 scores mean-abs 2.45 at 40.0s of the take it was tuned on (face luma 110), and 3.09 on
# frames from four other takes it never saw. Apple's own HEVC export scored 8.05 (9 levels bright).
# PQ goes through the same curve untested: no PQ clip with an Apple reference was at hand.
HDR_TRANSFERS = {"arib-std-b67": "HLG", "smpte2084": "PQ"}
SDR_TAGS = ["-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709"]
# Since ffmpeg 7.1 the encoder takes primaries and transfer from the frames and ignores the two
# flags above (only -colorspace and range are negotiated), so the tags that stick ride on the
# frames: zscale sets them in the tone map, and this stamps them where frames may arrive untagged.
SDR_STAMP = "setparams=color_primaries=bt709:color_trc=bt709:colorspace=bt709"


def color_transfer(path):
    """The first video stream's color_transfer tag ('' when untagged or there is no video).
    JSON, not csv: an iPhone HDR stream carries side data (Dolby Vision, the display matrix),
    and csv prints it as extra fields, so the tag came back as 'arib-std-b67,'."""
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=color_transfer", "-of", "json", str(path)], what="ffprobe color").stdout
    streams = json.loads(out or "{}").get("streams") or [{}]
    return streams[0].get("color_transfer", "")


def hdr_kind(path):
    """'HLG' or 'PQ' for an HDR source, '' for SDR."""
    return HDR_TRANSFERS.get(color_transfer(path), "")


def sdr_tonemap(path):
    """The filter chain that brings an HDR source to 8-bit SDR BT.709, ending in a comma so it
    prefixes an existing -vf. '' for an SDR source, so an SDR cut's filter graph stays the same."""
    t = color_transfer(path)
    if t not in HDR_TRANSFERS:
        return ""
    return (f"zscale=tin={t}:min=bt2020nc:pin=bt2020:rin=tv:t=linear:npl=1000,format=gbrpf32le,"
            "zscale=p=bt709,tonemap=tonemap=reinhard:param=0.5:peak=1.5:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,format=yuv420p,")


def has_tonemap_filters():
    """True when this ffmpeg has the zscale and tonemap filters an HDR source needs."""
    try:
        out = run(["ffmpeg", "-hide_banner", "-filters"], what="ffmpeg filters").stdout
    except MediaError:
        return False
    return " zscale " in out and " tonemap " in out


_CAPS = {}


def _ffmpeg_lists(flag, name):
    """True when `ffmpeg -<flag>` lists `name` (cached per process)."""
    key = (flag, name)
    if key not in _CAPS:
        try:
            out = run(["ffmpeg", "-hide_banner", flag], what=f"ffmpeg {flag}").stdout
        except MediaError:
            out = ""
        _CAPS[key] = any(line.split()[1:2] == [name] for line in out.splitlines() if line.strip())
    return _CAPS[key]


def hwaccel_args():
    """['-hwaccel', 'videotoolbox'] on a Mac that has it, else []: hardware decode of the source,
    frames handed to the filters in system memory (the tone map and the scale read them as before).
    YAP_NO_HWACCEL=1 turns it off for one run."""
    import os
    if os.environ.get("YAP_NO_HWACCEL") == "1":
        return []
    if "hwaccels" not in _CAPS:
        try:
            out = run(["ffmpeg", "-hide_banner", "-hwaccels"], what="ffmpeg hwaccels").stdout
        except MediaError:
            out = ""
        _CAPS["hwaccels"] = out.split()
    return ["-hwaccel", "videotoolbox"] if "videotoolbox" in _CAPS["hwaccels"] else []


def intermediate_encoder():
    """(ffmpeg args, name) for a throwaway intermediate at transparent quality: VideoToolbox H.264
    at constant quality 80 where it exists (3.9.0), else libx264 veryfast crf 12. YAP_NO_HWACCEL=1
    keeps libx264."""
    import os
    if os.environ.get("YAP_NO_HWACCEL") != "1" and _ffmpeg_lists("-encoders", "h264_videotoolbox"):
        return (["-c:v", "h264_videotoolbox", "-q:v", "80", "-allow_sw", "1"], "h264_videotoolbox")
    return (["-c:v", "libx264", "-preset", "veryfast", "-crf", "12"], "libx264")


def probe_streams(path):
    """{codec_type: {duration, width, height, sample_rate, r_frame_rate}} for
    the first stream of each type."""
    out = run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
              what="ffprobe streams").stdout
    res = {}
    for s in json.loads(out or "{}").get("streams", []):
        t = s.get("codec_type")
        if t in res:
            continue
        d = s.get("duration")
        res[t] = {
            "duration": float(d) if d not in (None, "N/A") else None,
            "width": s.get("width"), "height": s.get("height"),
            "sample_rate": int(s["sample_rate"]) if s.get("sample_rate") else None,
            "r_frame_rate": s.get("r_frame_rate"),
        }
    return res


def stream_durations(path):
    """{'video': s, 'audio': s} (missing keys when the stream is absent)."""
    return {t: v["duration"] for t, v in probe_streams(path).items()
            if v.get("duration") is not None}


def drift(path):
    """video duration minus audio duration, in seconds (0 when a stream is missing)."""
    sd = stream_durations(path)
    return sd.get("video", 0.0) - sd.get("audio", 0.0)


def has_audio(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
               "stream=index", "-of", "csv=p=0", str(path)], what="ffprobe audio").stdout
    return bool(out.strip())


def image_size(path):
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
               "stream=width,height", "-of", "csv=p=0", str(path)],
              what="ffprobe image size").stdout.strip()
    w, h = out.split(",")[:2]
    return int(w), int(h)


def ffmpeg(args, what="ffmpeg"):
    """ffmpeg with the house flags (-nostdin -y ... -hide_banner -loglevel error)."""
    return run(["ffmpeg", "-nostdin", "-y", *map(str, args), "-hide_banner",
                "-loglevel", "error"], what=what)


def _cli(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    cmd, path = argv[0], argv[1]
    try:
        if cmd == "duration":
            print(f"{probe_duration(path):.3f}")
        elif cmd == "streams":
            for t, d in stream_durations(path).items():
                print(f"{t}={d:.3f}")
        elif cmd == "has-audio":
            sys.exit(0 if has_audio(path) else 1)
        elif cmd == "hdr":
            k = hdr_kind(path)
            if k:
                print(k)
            sys.exit(0 if k else 1)
        elif cmd == "drift":
            limit = DRIFT_LIMIT_FINAL
            if "--limit" in argv:
                limit = float(argv[argv.index("--limit") + 1])
            d = drift(path)
            print(f"--- QA: video-audio drift {d:+.3f}s (limit {limit:.3f}s) ---")
            if abs(d) > limit:
                print(f"DRIFT GATE FAILED: picture is {d:+.3f}s vs voice (limit {limit:.3f}s). DO NOT SHIP.")
                sys.exit(2)
        else:
            sys.exit(f"unknown command {cmd!r}\n{__doc__}")
    except MediaError as e:
        sys.exit(f"media: {e}")


if __name__ == "__main__":
    _cli(sys.argv[1:])

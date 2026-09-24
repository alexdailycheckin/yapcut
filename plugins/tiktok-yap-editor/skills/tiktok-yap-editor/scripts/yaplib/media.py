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

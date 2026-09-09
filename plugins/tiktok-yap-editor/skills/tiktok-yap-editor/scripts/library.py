#!/usr/bin/env python3
"""Footage library: persistent tagged index of every clip the yap editor touches.

Records live in <library>/library.jsonl, one JSON object per line, keyed by a
CONTENT hash (file size + the first megabyte), so a clip keeps its record when
its folder is renamed or moved: reconcile finds it again by hash.

Where <library> is, first hit wins:
  1. $YAP_LIBRARY
  2. <workspace>/footage-library, workspace = yaplib.home.radar_home(required=False)
     (--dir <workspace>, $YAPCUT_HOME, a cwd holding a marker, ~/outlier-radar)
  3. nothing: a clear error naming the places looked, exit 2.
There is no skill-folder fallback and the library never lives next to this
script (the private copy that did is what tied it to one Mac).

Commands:
  prep <clip-or-folder> [--workdir DIR]   extract metadata + frame montage + transcript
                                          per clip, so Claude can tag it in one read
  upsert <records.json>                   merge tagged records into library.jsonl
  find <keyword> [keyword ...]            search all text fields (AND across keywords);
                                          a record whose file is gone prints [MISSING]
  mark-used <keyword> --edit NAME         stamp used_in on every record matching keyword
  reconcile --roots <dir> [<dir> ...]     hash every clip under the roots: a record whose
                                          file moved is re-pathed (same hash), one whose
                                          file cannot be found gets missing_since (and
                                          loses it when the file turns up again).
                                          Nothing is ever deleted.
  stats                                   library overview, alive vs missing

A record looks like:
  {"id","path","source_folder","shot_at","duration_s","resolution","kind",
   "transcript","tags":{"topics","actions","setting","background","people",
   "objects","wardrobe","time_of_day","mood","shot_type"},
   "moments":[{"in","out","desc"}], "hooks":[], "used_in":[], "posted":false,
   "missing_since":"YYYY-MM-DD"   (only while the file cannot be found)}

Exit codes: 0 ok, 2 no library reachable / bad input.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from yaplib import media  # noqa: E402
from yaplib.home import radar_home  # noqa: E402

SCRIPTS = Path(os.path.dirname(os.path.realpath(__file__)))
TRANSCRIBE = SCRIPTS / "transcribe.sh"       # the sibling script, wherever the plugin lives
VIDEO_EXTS = {".mov", ".mp4", ".m4v", ".mts"}
LIB_DIR = None                               # set by configure()
LIB_FILE = None


def configure(home):
    """Resolve the library directory (module doc) and set LIB_DIR / LIB_FILE."""
    global LIB_DIR, LIB_FILE
    env = os.environ.get("YAP_LIBRARY")
    if env:
        LIB_DIR = Path(os.path.abspath(os.path.expanduser(env)))
    elif home is not None:
        LIB_DIR = Path(home) / "footage-library"
    else:
        sys.stderr.write(
            "library: no footage library reachable. Looked at:\n"
            "  $YAP_LIBRARY (unset)\n"
            "  <workspace>/footage-library (no workspace: --dir, $YAPCUT_HOME, a cwd\n"
            "  holding radar-config.json / brand-config.json, ~/outlier-radar all empty)\n"
            "Set YAP_LIBRARY=<dir>, or pass --dir <workspace> / export YAPCUT_HOME.\n")
        sys.exit(2)
    LIB_FILE = LIB_DIR / "library.jsonl"
    return LIB_DIR


def today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def clip_hash(path: Path) -> str:
    h = hashlib.md5()
    h.update(str(path.stat().st_size).encode())
    with open(path, "rb") as f:
        h.update(f.read(1 << 20))
    return h.hexdigest()[:12]


def ffprobe(path: Path) -> dict:
    out = media.run(["ffprobe", "-v", "quiet", "-print_format", "json",
                     "-show_format", "-show_streams", str(path)], what="ffprobe").stdout
    data = json.loads(out or "{}")
    v = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), {})
    fmt = data.get("format", {})
    return {
        "duration_s": round(float(fmt.get("duration", 0) or 0), 2),
        "resolution": f'{v.get("width", "?")}x{v.get("height", "?")}',
        "shot_at": (fmt.get("tags", {}).get("creation_time")
                    or v.get("tags", {}).get("creation_time") or ""),
    }


def make_montage(path: Path, duration: float, out_jpg: Path) -> list:
    """4 evenly spaced frames tiled 2x2 with timestamp labels. One Read = whole clip."""
    from PIL import Image, ImageDraw
    times = [max(0.1, duration * p) for p in (0.08, 0.35, 0.62, 0.9)]
    frames = []
    for i, t in enumerate(times):
        fp = out_jpg.with_suffix(f".f{i}.jpg")
        media.ffmpeg(["-ss", f"{t:.2f}", "-i", str(path), "-frames:v", "1",
                      "-vf", "scale=480:-2", str(fp)], what="ffmpeg montage frame")
        frames.append((t, fp))
    imgs = [Image.open(fp) for _, fp in frames]
    w, h = imgs[0].size
    grid = Image.new("RGB", (w * 2, h * 2), "black")
    draw = ImageDraw.Draw(grid)
    for i, img in enumerate(imgs):
        x, y = (i % 2) * w, (i // 2) * h
        grid.paste(img, (x, y))
        t = frames[i][0]
        label = f"{int(t // 60)}:{t % 60:04.1f}"
        draw.rectangle([x + 4, y + 4, x + 74, y + 26], fill="black")
        draw.text((x + 10, y + 8), label, fill="white")
    grid.save(out_jpg, quality=80)
    for _, fp in frames:
        fp.unlink()
    return [round(t, 1) for t, _ in frames]


def load() -> list:
    if LIB_FILE is None or not LIB_FILE.exists():
        return []
    return [json.loads(l) for l in LIB_FILE.read_text(encoding="utf-8").splitlines() if l.strip()]


def save(records: list):
    LIB_FILE.parent.mkdir(parents=True, exist_ok=True)
    LIB_FILE.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records),
                        encoding="utf-8")


def is_missing(r: dict) -> bool:
    return bool(r.get("missing_since")) or not Path(r.get("path", "")).exists()


def iter_clips(roots):
    """Every video file under the roots (or the root itself when it is a file).
    Hidden directories (.yap_build, .prep) are skipped."""
    for root in roots:
        root = Path(os.path.abspath(os.path.expanduser(str(root))))
        if root.is_file():
            if root.suffix.lower() in VIDEO_EXTS:
                yield root
            continue
        if not root.is_dir():
            print(f"reconcile: root is not a directory, skipped: {root}")
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
            for fn in sorted(filenames):
                if not fn.startswith(".") and Path(fn).suffix.lower() in VIDEO_EXTS:
                    yield Path(dirpath) / fn


def cmd_prep(target: Path, workdir: Path):
    clips = ([target] if target.is_file()
             else sorted(p for p in target.iterdir() if p.suffix.lower() in VIDEO_EXTS))
    if not clips:
        sys.exit(f"no video clips found in {target}")
    workdir.mkdir(parents=True, exist_ok=True)
    existing = {r["id"] for r in load()}
    stubs = []
    for clip in clips:
        cid = clip_hash(clip)
        base = workdir / clip.stem
        meta = ffprobe(clip)
        if cid in existing:
            print(f"SKIP {clip.name} (already in library)")
            continue
        frame_times = make_montage(clip, meta["duration_s"], base.with_suffix(".montage.jpg"))
        try:
            media.run(["bash", str(TRANSCRIBE), str(clip), str(base)], what="transcribe.sh")
        except media.MediaError as e:
            print(f"  transcript skipped for {clip.name}: {str(e).splitlines()[0]}")
        txt = base.with_suffix(".txt")
        transcript = txt.read_text(encoding="utf-8").strip() if txt.exists() else ""
        clip_abs = Path(os.path.abspath(clip))
        stub = {"id": cid, "path": str(clip_abs), "source_folder": clip_abs.parent.name,
                **meta, "frame_times": frame_times, "transcript": transcript}
        stubs.append(stub)
        print(f"PREP {clip.name}  {meta['duration_s']}s  "
              f"montage={base.name}.montage.jpg  words={len(transcript.split())}")
    (workdir / "stubs.json").write_text(json.dumps(stubs, indent=1), encoding="utf-8")
    print(f"\n{len(stubs)} stubs -> {workdir}/stubs.json")


def cmd_upsert(records_file: Path):
    new = json.loads(records_file.read_text(encoding="utf-8"))
    if isinstance(new, dict):
        new = [new]
    lib = {r["id"]: r for r in load()}
    added = updated = 0
    for r in new:
        r.setdefault("used_in", [])
        r.setdefault("posted", False)
        r["tagged_at"] = today()
        r.pop("frame_times", None)
        if r["id"] in lib:
            lib[r["id"]].update(r)
            updated += 1
        else:
            lib[r["id"]] = r
            added += 1
    save(list(lib.values()))
    print(f"library: +{added} added, {updated} updated, {len(lib)} total")


def flatten(r: dict) -> str:
    parts = [r.get("path", ""), r.get("kind", ""), r.get("transcript", ""),
             r.get("notes", ""), r.get("source_folder", "")]
    for v in (r.get("tags") or {}).values():
        parts.append(" ".join(v) if isinstance(v, list) else str(v))
    parts += [m.get("desc", "") for m in r.get("moments", [])]
    parts += r.get("hooks", [])
    parts += r.get("reads_as", [])
    parts += r.get("used_in", [])
    return " ".join(parts).lower()


def cmd_find(keywords: list):
    hits = [r for r in load() if all(k.lower() in flatten(r) for k in keywords)]
    n_missing = 0
    for r in hits:
        tags = r.get("tags", {})
        missing = is_missing(r)
        n_missing += missing
        pre = "[MISSING] " if missing else ""
        print(f'{pre}== {Path(r["path"]).name}  [{r.get("kind", "?")}] '
              f'{r.get("duration_s", "?")}s  {r.get("shot_at", "")[:16]}  '
              f'{r.get("source_folder", "?")}  used_in={r.get("used_in") or "-"}')
        if missing:
            print(f'   file not found: {r["path"]}'
                  + (f'  (missing since {r["missing_since"]})' if r.get("missing_since") else
                     "  (run: library.py reconcile --roots <footage dirs>)"))
        print(f'   topics: {", ".join(tags.get("topics", []))} | '
              f'setting: {tags.get("setting", "?")} | mood: {tags.get("mood", "?")}')
        for m in r.get("moments", []):
            print(f'   {m["in"]}-{m["out"]}s  {m["desc"]}')
    print(f"\n{len(hits)} match(es)" + (f", {n_missing} missing on disk" if n_missing else ""))


def cmd_mark_used(keywords: list, edit: str):
    """Match on the clip filename only: free-text matching would stamp records
    whose notes merely mention the target clip."""
    lib = load()
    n = 0
    for r in lib:
        name = Path(r["path"]).name.lower()
        if all(k.lower() in name for k in keywords) and edit not in r["used_in"]:
            r["used_in"].append(edit)
            n += 1
    save(lib)
    print(f"stamped used_in={edit} on {n} record(s)")


def cmd_reconcile(roots: list):
    lib = load()
    if not lib:
        print("library: empty, nothing to reconcile")
        return
    by_hash, n_files = {}, 0
    for p in iter_clips(roots):
        n_files += 1
        by_hash.setdefault(clip_hash(p), p)
    stamp = today()
    repathed = returned = alive = missing = 0
    for r in lib:
        new = by_hash.get(r["id"])
        if new is not None and str(new) != r.get("path"):
            print(f"REPATH {Path(r.get('path', '?')).name}: {r.get('path')} -> {new}")
            r["path"] = str(new)
            r["source_folder"] = new.parent.name
            repathed += 1
        if new is not None or Path(r.get("path", "")).exists():
            if r.pop("missing_since", None) is not None:
                returned += 1
            alive += 1
        else:
            if not r.get("missing_since"):
                r["missing_since"] = stamp
                print(f"MISSING {Path(r.get('path', '?')).name}: {r.get('path')} (since {stamp})")
            missing += 1
    save(lib)
    print(f"reconcile: {n_files} file(s) under {len(roots)} root(s); {repathed} re-pathed, "
          f"{returned} found again, {alive} alive, {missing} missing (kept, never deleted)")


def cmd_stats():
    lib = load()
    folders, kinds = {}, {}
    alive = missing = 0
    for r in lib:
        folders[r.get("source_folder", "?")] = folders.get(r.get("source_folder", "?"), 0) + 1
        kinds[r.get("kind", "?")] = kinds.get(r.get("kind", "?"), 0) + 1
        if is_missing(r):
            missing += 1
        else:
            alive += 1
    total_s = sum(r.get("duration_s", 0) or 0 for r in lib)
    print(f"library: {LIB_FILE}")
    print(f"{len(lib)} clips, {total_s / 60:.1f} min total, {alive} alive, {missing} missing on disk"
          + ("  (library.py reconcile --roots <footage dirs> re-paths moved files)" if missing else ""))
    print("by kind:  ", ", ".join(f"{k}={v}" for k, v in sorted(kinds.items())))
    print("by folder:", ", ".join(f"{k}={v}" for k, v in sorted(folders.items())))


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    # radar_home consumes --dir from argv before argparse sees it; it never exits
    # with required=False, so --help still works with no workspace at all
    home = radar_home(argv=argv, required=False)
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", help="workspace holding footage-library/ (else $YAPCUT_HOME, "
                    "a cwd marker, ~/outlier-radar); $YAP_LIBRARY overrides all of these")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("prep"); p.add_argument("target")
    p.add_argument("--workdir", default=None, help="scratch for montages + transcripts (default <library>/.prep)")
    p = sub.add_parser("upsert"); p.add_argument("records")
    p = sub.add_parser("find"); p.add_argument("keywords", nargs="+")
    p = sub.add_parser("mark-used"); p.add_argument("keywords", nargs="+"); p.add_argument("--edit", required=True)
    p = sub.add_parser("reconcile"); p.add_argument("--roots", nargs="+", required=True,
                                                   help="footage directories (or files) to hash")
    sub.add_parser("stats")
    a = ap.parse_args(argv)
    if a.dir:
        home = radar_home(argv=["--dir", a.dir], required=False)
    configure(home)
    if a.cmd == "prep":
        cmd_prep(Path(a.target).expanduser(), Path(a.workdir) if a.workdir else LIB_DIR / ".prep")
    elif a.cmd == "upsert":
        cmd_upsert(Path(a.records))
    elif a.cmd == "find":
        cmd_find(a.keywords)
    elif a.cmd == "mark-used":
        cmd_mark_used(a.keywords, edit=a.edit)
    elif a.cmd == "reconcile":
        cmd_reconcile(a.roots)
    else:
        cmd_stats()
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except media.MediaError as e:
        sys.exit(f"library: {e}")

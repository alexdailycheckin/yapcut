#!/usr/bin/env python3
"""Link this workspace to the Anima app on the creator's iPhone. The phrase is "connect anima".

Anima and the Mac share Anima's own folder in iCloud Drive (the app's iCloud container, which
shows as "Anima" in Finder). This script finds that folder, gives the workspace a folder of its
own inside it, writes `pairing.json` there, which the phone is watching for, points
`mobile.sync_dir` at it so every dashboard build refreshes the week, and copies the newest week
across now. Run it again at any time: it keeps the same folder and rewrites the pairing.

The shared folder, per workspace:

    YapCut/<workspace-id>/
      pairing.json        this script: who the Mac is, which workspace, whether discovery is done
      status.json         build_dashboard.py: when the week was last written
      weeks/<week>.json   build_dashboard.py, through mobile.sync_dir
      brand-config.json   build_dashboard.py
      inbox/              the phone: one file per event (a pick, a kill with its reason, ...)
      output/<week>/      the phone: its cuts and edit records, for log_perf.py --edits

The Mac never writes inside inbox/ or output/, and the phone never writes anywhere else, so
iCloud never has two devices editing one file.

Exit 0 linked; 2 no workspace (from yapcut_home); 3 Anima's folder is not on this Mac, with the
reason in plain words.
"""
import argparse
import datetime
import glob
import json
import os
import pathlib
import re
import shutil
import socket
import subprocess
import sys
import uuid

from yapcut_home import radar_home

MOBILE_DOCUMENTS = pathlib.Path.home() / "Library" / "Mobile Documents"
# macOS names another developer's iCloud container with that developer's team id in front
# (`6FJR96W34Q~iCloud~com~animaai~app`), so match the suffix rather than one exact name.
CONTAINER_SUFFIX = "iCloud~com~animaai~app"
WEEK_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")


def find_container():
    """Anima's iCloud folder on this Mac, or None while iCloud has not brought it over."""
    try:
        names = sorted(n for n in os.listdir(MOBILE_DOCUMENTS) if n.endswith(CONTAINER_SUFFIX))
    except OSError:
        return None
    for name in names:
        docs = MOBILE_DOCUMENTS / name / "Documents"
        if docs.is_dir():
            return docs
    return None


def mac_name():
    try:
        name = subprocess.run(["scutil", "--get", "ComputerName"], capture_output=True, text=True,
                              timeout=5).stdout.strip()
        return name or socket.gethostname()
    except (OSError, subprocess.SubprocessError):
        return socket.gethostname()


def plugin_version():
    manifest = pathlib.Path(__file__).resolve().parents[2] / ".claude-plugin" / "plugin.json"
    try:
        return json.loads(manifest.read_text())["version"]
    except (OSError, ValueError, KeyError):
        return "unknown"


def why_missing():
    """The folder appears on the Mac only once the phone has written to it and iCloud has
    carried it over, so the three reasons are checked from the most to the least likely."""
    if not (MOBILE_DOCUMENTS / "com~apple~CloudDocs").exists():
        return ("iCloud Drive is off on this Mac. Turn it on in System Settings, under your "
                "name, then iCloud, then iCloud Drive, and run this again.")
    return ("Anima's folder is not on this Mac yet. Open Anima on your iPhone once, which "
            "creates the folder, and check the iPhone and this Mac are signed in to the same "
            "Apple ID. iCloud can take a minute to bring it over; then run this again.")


def newest_week(ws):
    weeks = sorted(p for p in glob.glob(os.path.join(ws, "weeks", "*.json"))
                   if WEEK_RE.match(os.path.basename(p)))
    return weeks[-1] if weeks else None


def write_json(path, data):
    """Write through a temporary file, so iCloud never uploads half a file."""
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ws = radar_home(argv)  # consumes --dir; exits 2 naming the places it looked
    ap = argparse.ArgumentParser(prog="anima_link.py",
                                 description="Link this workspace to the Anima app on your iPhone.")
    ap.add_argument("--container", help="Anima's iCloud folder (default: the real one; for tests)")
    args = ap.parse_args(argv)

    container = pathlib.Path(args.container).expanduser() if args.container else find_container()
    if container is None or not container.is_dir():
        print(why_missing())
        return 3

    cfg_path = pathlib.Path(ws) / "radar-config.json"
    cfg = json.loads(cfg_path.read_text())
    mobile = cfg.get("mobile") if isinstance(cfg.get("mobile"), dict) else {}
    wid = mobile.get("workspace_id") or str(uuid.uuid4())
    folder = container / "YapCut" / wid
    for sub in ("inbox", "weeks", "output"):
        (folder / sub).mkdir(parents=True, exist_ok=True)

    name = ((cfg.get("brand") or {}).get("name") or "").strip() or "Your YapCut"
    discovery_done = (pathlib.Path(ws) / "positioning.md").exists()
    pairing = {
        "v": 1,
        "workspace_id": wid,
        "workspace_name": name,
        "mac_name": mac_name(),
        "yapcut_version": plugin_version(),
        "discovery_done": discovery_done,
        "linked_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
    }
    write_json(folder / "pairing.json", pairing)

    mobile["workspace_id"] = wid
    mobile["sync_dir"] = str(folder)
    cfg["mobile"] = mobile
    write_json(cfg_path, cfg)

    week = newest_week(ws)
    if week:
        shutil.copy2(week, folder / "weeks" / os.path.basename(week))
    brand = pathlib.Path(ws) / "brand-config.json"
    if brand.exists():
        shutil.copy2(brand, folder / "brand-config.json")

    print(f"Linked {name}'s workspace to Anima, in {folder}.")
    print(f"On your iPhone, Anima now asks to connect to YapCut on {pairing['mac_name']}.")
    if week:
        print(f"The newest week, {os.path.basename(week)}, is in the shared folder; every dashboard "
              "build refreshes it.")
    else:
        print("There is no week yet; the first dashboard build puts it in the shared folder.")
    if not discovery_done:
        print("Discovery is not done on this Mac. Answer the interview in Anima and the first run "
              "reads the answers from the inbox.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

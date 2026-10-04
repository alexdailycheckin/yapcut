#!/usr/bin/env python3
"""Link this workspace to the Anima app on the creator's iPhone, over the local Wi-Fi.
The phrase is "connect anima".

While this runs, the Mac announces itself on the network as "YapCut on <Mac name>" (Bonjour,
`_anima._tcp`), prints a 6-digit code, and serves the phone. The phone finds the Mac, the
creator types the code once, and from then on the phone syncs whenever this is running and
both are on the same Wi-Fi. Nothing is installed and nothing runs when this is closed: the
link is open only while the creator works.

It replaced a shared iCloud Drive folder on 2026-09-29. A phone with full iCloud storage cannot
upload even a 1 KB file (NSFileProviderErrorDomain -1003), and the free tier is 5 GB, so
iCloud would have failed for every creator whose storage is full.

What the phone can do, each call but /pair carrying `Authorization: Bearer <token>`:

    POST /pair                 {"code", "device"} -> {"token", "workspace_id", "workspace_name", "mac_name", "sync_code"}
    GET  /status               who the Mac is, the newest week and when it was written
    GET  /week                 the newest weeks/<date>.json
    GET  /brand                brand-config.json
    POST /inbox                one event (a pick, a kill with its reason, a posted link...)
    PUT  /output/<week>/<name> a cut or its edit record

`/pair` and `/status` also hand the phone the workspace's sync code (anima_sync.py), so a phone
paired here syncs from anywhere afterwards without typing it. The link pushes the week to the
sync relay when it opens.

The Mac keeps what arrives under `<workspace>/mobile/`: `devices.json` (paired phones, token
hashes only), `inbox/` and `output/<week>/`. The phone never writes anywhere else.

Run it in the background from Claude Code; Ctrl-C or the time limit closes it.
Exit 0 closed normally; 2 no workspace (from yapcut_home); 3 the port is taken.
"""
import argparse
import datetime
import glob
import hashlib
import http.server
import json
import os
import pathlib
import re
import secrets
import signal
import socket
import subprocess
import sys
import threading
import uuid

from yapcut_home import radar_home
import rules

SERVICE = "_anima._tcp"
WEEK_RE = re.compile(r"^\d{4}-\d{2}-\d{2}\.json$")
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._ -]{0,120}$")
MAX_UPLOAD = 2 * 1024 ** 3
MAX_CODE_TRIES = 5


def mac_name():
    try:
        name = subprocess.run(["scutil", "--get", "ComputerName"], capture_output=True, text=True,
                              timeout=5).stdout.strip()
        return name or socket.gethostname()
    except (OSError, subprocess.SubprocessError):
        return socket.gethostname()


def local_host():
    try:
        name = subprocess.run(["scutil", "--get", "LocalHostName"], capture_output=True, text=True,
                              timeout=5).stdout.strip()
        return f"{name}.local" if name else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def lan_ip():
    """The address of the interface the Mac would use for the network; nothing is sent."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except OSError:
        return ""


def newest_week(ws):
    weeks = sorted(p for p in glob.glob(os.path.join(ws, "weeks", "*.json")) if WEEK_RE.match(os.path.basename(p)))
    return weeks[-1] if weeks else None


# The phone's view of the week (3.17.0). Anima parses a week with its own bundled copy of the
# rulebook, which knows two video lanes and reads the prompter from `script`. Until the app
# ships the new lanes, the week travels folded: explainers ride in the primary lane and moments
# in the secondary, titled so they read as what they are, and the opinion slot lands at the end
# of the script as the prompter's last lines. The week file on the Mac is never changed.
PHONE_LANES = ("distribution", "office")
MOMENT_TITLES = {"day-in-the-life": "Day in the life", "pomodoro-break": "Pomodoro break"}


def phone_week(path, ws=None):
    """The newest week as bytes for the phone. Anything that does not parse goes as it is."""
    raw = pathlib.Path(path).read_bytes()
    try:
        d = json.loads(raw)
    except ValueError:
        return raw
    if not isinstance(d, dict):
        return raw
    try:
        cfg = json.loads((pathlib.Path(ws or os.path.dirname(os.path.dirname(path))) / "radar-config.json").read_text())
    except (OSError, ValueError):
        cfg = {}
    label = rules.opinion_label(cfg)
    folded = False
    for lane in rules.video_lanes():
        for it in d.get(lane) or []:
            ideas = rules.opinion_ideas(it)
            if isinstance(it, dict) and ideas and it.get("script"):
                it["script"] = (it["script"].rstrip() + "\n\n" + label + "\n\n"
                                + "\n\n".join(f"Idea: {i}" for i in ideas))
                folded = True
    for it in d.get("explainers") or []:
        if isinstance(it, dict):
            d.setdefault("distribution", []).append(dict(it, title=f"Explainer: {it.get('title') or it.get('id')}"))
            folded = True
    for it in d.get("moments") or []:
        if not isinstance(it, dict):
            continue
        cap = [c for c in it.get("clips") or [] if c]
        lines = [f"{c.get('t') or ''} {c.get('moment') or ''}".strip() + "." if isinstance(c, dict) else f"{c}." for c in cap]
        kind = MOMENT_TITLES.get(it.get("format"), "Moments")
        d.setdefault("office", []).append(dict(it, title=f"{kind}: {it.get('title') or it.get('id')}",
                                               spoken_hook=it.get("spoken_hook") or "Film these moments.",
                                               script="\n\n".join(lines) or it.get("script") or ""))
        folded = True
    if not folded:
        return raw
    for lane in rules.video_lanes():
        if lane not in PHONE_LANES:
            d.pop(lane, None)
    return json.dumps(d, ensure_ascii=False, indent=1).encode()


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def workspace_identity(ws):
    """The workspace's id and display name. The first call writes `mobile.workspace_id` into
    radar-config.json, the only change the link makes to the workspace's own files."""
    cfg_path = pathlib.Path(ws) / "radar-config.json"
    cfg = json.loads(cfg_path.read_text())
    mobile = cfg.get("mobile") if isinstance(cfg.get("mobile"), dict) else {}
    if not mobile.get("workspace_id"):
        mobile["workspace_id"] = str(uuid.uuid4())
        cfg["mobile"] = mobile
        tmp = cfg_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")
        os.replace(tmp, cfg_path)
    name = ((cfg.get("brand") or {}).get("name") or "").strip() or "Your YapCut"
    return mobile["workspace_id"], name


class Link:
    """The workspace side of the link: identity, the pairing code, paired phones."""

    def __init__(self, ws, code=None):
        self.ws = pathlib.Path(ws)
        self.workspace_id, self.workspace_name = workspace_identity(ws)
        # The sync code goes only to a phone that proved it is paired (/pair, /status).
        self.sync_code = None
        self.mac = mac_name()
        self.home = self.ws / "mobile"
        for sub in ("inbox", "output"):
            (self.home / sub).mkdir(parents=True, exist_ok=True)
        self.devices_path = self.home / "devices.json"
        self.code = code or f"{secrets.randbelow(10 ** 6):06d}"
        self.tries = 0
        self.lock = threading.Lock()

    def devices(self):
        try:
            return json.loads(self.devices_path.read_text())
        except (OSError, ValueError):
            return []

    def save_devices(self, devices):
        tmp = self.devices_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(devices, indent=2) + "\n")
        os.replace(tmp, self.devices_path)

    @staticmethod
    def digest(token):
        return hashlib.sha256(token.encode()).hexdigest()

    def pair(self, code, device):
        with self.lock:
            if self.tries >= MAX_CODE_TRIES:
                return None, "too many wrong codes; restart connect anima for a new one"
            if not secrets.compare_digest(str(code), self.code):
                self.tries += 1
                return None, "that code does not match"
            token = secrets.token_urlsafe(32)
            devices = [d for d in self.devices() if d.get("device") != device]
            devices.append({"device": device, "token_sha256": self.digest(token), "paired_at": now_iso()})
            self.save_devices(devices)
            return token, None

    def device_for(self, token):
        if not token:
            return None
        h = self.digest(token)
        for d in self.devices():
            if secrets.compare_digest(d.get("token_sha256", ""), h):
                return d
        return None

    def status(self, paired=False):
        week = newest_week(self.ws)
        extra = {"sync_code": self.sync_code} if paired and self.sync_code else {}
        return {
            **extra,
            "v": 1,
            "workspace_id": self.workspace_id,
            "workspace_name": self.workspace_name,
            "mac_name": self.mac,
            "week": os.path.basename(week) if week else None,
            "written_at": (datetime.datetime.fromtimestamp(os.path.getmtime(week)).astimezone()
                           .isoformat(timespec="seconds") if week else None),
        }


def make_handler(link, quiet=False):
    class Handler(http.server.BaseHTTPRequestHandler):
        server_version = "YapCut-Anima/1"

        def log_message(self, fmt, *args):
            if not quiet:
                sys.stdout.write(f"  {self.command} {self.path.split('?')[0]} {args[1] if len(args) > 1 else ''}\n")
                sys.stdout.flush()

        def send_json(self, code, body):
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def send_file(self, path):
            self.send_bytes(pathlib.Path(path).read_bytes())

        def send_bytes(self, data):
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def authed(self):
            auth = self.headers.get("Authorization", "")
            token = auth[7:] if auth.startswith("Bearer ") else ""
            device = link.device_for(token)
            if not device:
                self.send_json(401, {"error": "not paired; pair with the code connect anima shows"})
            return device

        def read_body(self, limit=1024 * 1024):
            n = int(self.headers.get("Content-Length") or 0)
            if n > limit:
                raise ValueError("too large")
            return self.rfile.read(n) if n else b""

        def do_GET(self):
            path = self.path.split("?")[0]
            if not self.authed():
                return
            if path == "/status":
                return self.send_json(200, link.status(paired=True))
            if path == "/week":
                week = newest_week(link.ws)
                return self.send_bytes(phone_week(week, link.ws)) if week else self.send_json(404, {"error": "no week yet"})
            if path == "/brand":
                brand = link.ws / "brand-config.json"
                return self.send_file(brand) if brand.exists() else self.send_json(404, {"error": "no brand config"})
            self.send_json(404, {"error": "unknown path"})

        def do_POST(self):
            path = self.path.split("?")[0]
            if path == "/pair":
                try:
                    body = json.loads(self.read_body() or b"{}")
                except ValueError:
                    return self.send_json(400, {"error": "bad request"})
                device = str(body.get("device") or "iPhone")[:80]
                token, err = link.pair(body.get("code", ""), device)
                if not token:
                    return self.send_json(403, {"error": err})
                print(f"Paired with {device}.")
                sys.stdout.flush()
                return self.send_json(200, {"token": token, **link.status(paired=True)})
            if path == "/inbox":
                device = self.authed()
                if not device:
                    return
                try:
                    event = json.loads(self.read_body())
                except ValueError:
                    return self.send_json(400, {"error": "an event is one JSON object"})
                if not isinstance(event, dict):
                    return self.send_json(400, {"error": "an event is one JSON object"})
                kind = re.sub(r"[^a-z0-9-]", "", str(event.get("type", "event")).lower())[:24] or "event"
                stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                dest = link.home / "inbox" / f"{stamp}-{kind}.json"
                event.setdefault("device", device.get("device"))
                event.setdefault("received_at", now_iso())
                dest.write_text(json.dumps(event, indent=2, ensure_ascii=False) + "\n")
                return self.send_json(200, {"saved": dest.name})
            self.send_json(404, {"error": "unknown path"})

        def do_PUT(self):
            parts = self.path.split("?")[0].strip("/").split("/")
            if len(parts) != 3 or parts[0] != "output":
                return self.send_json(404, {"error": "PUT /output/<week>/<name>"})
            if not self.authed():
                return
            week, name = parts[1], parts[2]
            if not SAFE_NAME.match(week) or not SAFE_NAME.match(name) or ".." in week or ".." in name:
                return self.send_json(400, {"error": "bad file name"})
            n = int(self.headers.get("Content-Length") or 0)
            if n <= 0 or n > MAX_UPLOAD:
                return self.send_json(400, {"error": "missing or too large"})
            folder = link.home / "output" / week
            folder.mkdir(parents=True, exist_ok=True)
            tmp = folder / f".{name}.part"
            left = n
            with open(tmp, "wb") as f:
                while left:
                    chunk = self.rfile.read(min(1024 * 1024, left))
                    if not chunk:
                        break
                    f.write(chunk)
                    left -= len(chunk)
            if left:
                tmp.unlink(missing_ok=True)
                return self.send_json(400, {"error": "upload cut short"})
            os.replace(tmp, folder / name)
            self.send_json(200, {"saved": f"mobile/output/{week}/{name}"})

    return Handler


def advertise(link, port):
    """Announce the link on the network with the macOS dns-sd tool. The phone reads the host,
    the address and the port from the TXT record."""
    txt = ["v=1", f"ws={link.workspace_id}", f"name={link.mac}", f"host={local_host()}", f"ip={lan_ip()}",
           f"port={port}"]
    try:
        return subprocess.Popen(["dns-sd", "-R", f"YapCut on {link.mac}", SERVICE, "local", str(port), *txt],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        print("dns-sd is missing, so the phone cannot find this Mac by itself.")
        return None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ws = radar_home(argv)  # consumes --dir; exits 2 naming the places it looked
    ap = argparse.ArgumentParser(prog="anima_link.py",
                                 description="Link this workspace to the Anima app on your iPhone, over the Wi-Fi.")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--minutes", type=float, default=120, help="close the link after this long (default 120)")
    ap.add_argument("--code", help="a fixed pairing code, for tests")
    ap.add_argument("--no-bonjour", action="store_true", help="do not announce on the network (tests)")
    ap.add_argument("--no-sync", action="store_true", help="do not push to the sync relay (tests)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args(argv)

    link = Link(ws, code=args.code)
    try:
        server = http.server.ThreadingHTTPServer(("0.0.0.0", args.port), make_handler(link, args.quiet))
    except OSError as e:
        print(f"Port {args.port} is taken ({e.strerror}). Close the other connect anima, or pass --port.")
        return 3
    announcer = None if args.no_bonjour else advertise(link, args.port)

    def close(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, close)

    if not args.no_sync:
        # Sync from anywhere: make the code on the first run, push the week, hand paired phones
        # the code. A relay problem never stops the Wi-Fi link.
        try:
            import anima_sync
            relay = anima_sync.load_relay(ws)
            link.sync_code = relay["code"]
            _sent, err = anima_sync.push(ws, relay)
            if err:
                print(f"Sync from anywhere could not push this time: {err}")
        except Exception as e:
            print(f"Sync from anywhere is off this time: {e}")

    paired = len(link.devices())
    print(f"Anima link open for {link.workspace_name}, as YapCut on {link.mac}.")
    print(f"On your iPhone, open Anima, tap YapCut on {link.mac} and enter the code: {link.code}")
    if paired:
        print(f"{paired} phone(s) already paired sync without the code.")
    if link.sync_code:
        print(f"Away from this Wi-Fi, tap Use a sync code in Anima instead and type: {link.sync_code}")
    print(f"The link closes in {args.minutes:g} minutes, or when this stops.")
    sys.stdout.flush()
    timer = threading.Timer(args.minutes * 60, lambda: os.kill(os.getpid(), signal.SIGTERM))
    timer.daemon = True
    timer.start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        if announcer:
            announcer.terminate()
        print("Anima link closed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

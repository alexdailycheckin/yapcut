#!/usr/bin/env python3
"""Keep the Anima app's copy of the week current from anywhere, with a sync code.
The phrase is "anima sync code". It also runs by itself after every dashboard build, once the
creator has a code.

The Mac seals the newest week with a key derived from the creator's sync code and uploads it to
Anima's relay. The phone downloads it and opens it with the same code, on any network, with the
Mac asleep. The relay stores bytes it cannot read, because the code never leaves the Mac and the
phone. It exists so the scripts reach the phone to film later wherever it is, not only on the
Mac's Wi-Fi. "connect anima" (anima_link.py) pushes too, and hands a phone paired over the Wi-Fi
the code, so that phone never types it.

    python3 anima_sync.py              print the sync code (made on the first run) and push the week
    python3 anima_sync.py --push       push only if the week changed, quietly: the build's hook
    python3 anima_sync.py --new-code   a new code and box; the old code stops getting new weeks

The code, the box's write secret and what was last pushed live in `<workspace>/mobile/relay.json`.
Anyone with the code can read the week, so it is the creator's to keep, like a password.

Sealing, version AS1. Anima's `SyncCode.swift` mirrors it, and one test vector pins both:

    dk      = PBKDF2-HMAC-SHA256(the normalized code, salt "anima-sync-v1", 100000 rounds, 96 bytes)
    enc key = dk[0:32]    mac key = dk[32:64]    box id = hex(dk[64:96])
    stream  = HMAC-SHA256(enc key, nonce || counter as 4 bytes big-endian), counter 0, 1, 2...
    blob    = "AS1" || nonce (16 random bytes) || plain XOR stream || HMAC-SHA256(mac key, all before it)

It uses the standard library only: the Python on a Mac has no AES, and nothing is installed.

Exit 0 pushed or nothing to push; 2 no workspace (from yapcut_home); 4 the relay refused or
could not be reached.
"""
import argparse
import datetime
import hashlib
import hmac
import json
import os
import pathlib
import secrets
import sys
import urllib.error
import urllib.request

from anima_link import mac_name, newest_week, now_iso, phone_week, workspace_identity
from yapcut_home import radar_home

RELAY = "https://anima-sync.netlify.app"
ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # Crockford base32: no I, L, O or U to misread
CODE_LEN = 12
MAGIC = b"AS1"
SALT = b"anima-sync-v1"
ROUNDS = 100_000


# The code and the seal

def new_code():
    raw = "".join(secrets.choice(ALPHABET) for _ in range(CODE_LEN))
    return "-".join(raw[i:i + 4] for i in range(0, CODE_LEN, 4))


def normalize(code):
    """What the creator types, as the key sees it: case, dashes and spaces do not matter, and the
    letters people confuse with digits read as the digits."""
    s = code.upper().replace("O", "0").replace("I", "1").replace("L", "1")
    return "".join(ch for ch in s if ch in ALPHABET)


def keys(code):
    dk = hashlib.pbkdf2_hmac("sha256", normalize(code).encode(), SALT, ROUNDS, dklen=96)
    return dk[:32], dk[32:64], dk[64:].hex()


def _stream(enc_key, nonce, n):
    out = bytearray()
    counter = 0
    while len(out) < n:
        out += hmac.new(enc_key, nonce + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        counter += 1
    return bytes(out[:n])


def _xor(a, b):
    return (int.from_bytes(a, "big") ^ int.from_bytes(b, "big")).to_bytes(len(a), "big") if a else b""


def seal(plain, enc_key, mac_key, nonce=None):
    nonce = nonce or secrets.token_bytes(16)
    body = MAGIC + nonce + _xor(plain, _stream(enc_key, nonce, len(plain)))
    return body + hmac.new(mac_key, body, hashlib.sha256).digest()


def open_sealed(blob, enc_key, mac_key):
    """The plain bytes, or ValueError when the blob is not AS1 or the code is wrong."""
    if len(blob) < len(MAGIC) + 16 + 32 or not blob.startswith(MAGIC):
        raise ValueError("not an Anima sync blob")
    body, tag = blob[:-32], blob[-32:]
    if not hmac.compare_digest(tag, hmac.new(mac_key, body, hashlib.sha256).digest()):
        raise ValueError("the code does not open this blob")
    nonce, cipher = body[3:19], body[19:]
    return _xor(cipher, _stream(enc_key, nonce, len(cipher)))


# The workspace side

def relay_path(ws):
    return pathlib.Path(ws) / "mobile" / "relay.json"


def load_relay(ws, create=True, fresh=False):
    p = relay_path(ws)
    if p.exists() and not fresh:
        return json.loads(p.read_text())
    if not create:
        return None
    r = {"relay": RELAY, "code": new_code(), "write_secret": secrets.token_urlsafe(32), "pushed": {},
         "made_at": now_iso()}
    save_relay(ws, r)
    return r


def save_relay(ws, r):
    p = relay_path(ws)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(r, indent=2) + "\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def _put(r, box, name, blob):
    req = urllib.request.Request(f"{r['relay'].rstrip('/')}/box/{box}/{name}", data=blob, method="PUT")
    req.add_header("Authorization", "Bearer " + r["write_secret"])
    req.add_header("Content-Type", "application/octet-stream")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as e:
        # A relay that refuses early can drop the connection before its reason arrives.
        try:
            why = e.read().decode(errors="replace")[:200]
        except OSError:
            why = ""
        return e.code, why
    except (urllib.error.URLError, OSError) as e:
        return 0, str(getattr(e, "reason", e))


def status_doc(ws, week):
    wid, wname = workspace_identity(ws)
    return {
        "v": 1,
        "workspace_id": wid,
        "workspace_name": wname,
        "mac_name": mac_name(),
        "week": os.path.basename(week) if week else None,
        "written_at": (datetime.datetime.fromtimestamp(os.path.getmtime(week)).astimezone()
                       .isoformat(timespec="seconds") if week else None),
        "pushed_at": now_iso(),
    }


def push(ws, r, force=False):
    """Uploads the brand config, then the week, then the status that names the week, each only
    when it changed since the last push. The status goes last, so a phone never sees a week
    named that has not arrived. Returns (what was pushed, an error or None)."""
    enc_key, mac_key, box = keys(r["code"])
    week = newest_week(ws)
    brand = pathlib.Path(ws) / "brand-config.json"
    pushed = r.setdefault("pushed", {})
    sent = []
    parts = [("brand", brand if brand.exists() else None), ("week", pathlib.Path(week) if week else None)]
    for name, path in parts:
        if not path:
            continue
        data = phone_week(path, ws) if name == "week" else path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if not force and pushed.get(name) == {"file": path.name, "sha256": digest}:
            continue
        code, why = _put(r, box, name, seal(data, enc_key, mac_key))
        if code != 200:
            return sent, f"the relay answered {code or 'nothing'} for {name}: {why}"
        pushed[name] = {"file": path.name, "sha256": digest}
        sent.append(name)
    if sent or force or "status" not in pushed:
        doc = status_doc(ws, week)
        code, why = _put(r, box, "status", seal(json.dumps(doc).encode(), enc_key, mac_key))
        if code != 200:
            return sent, f"the relay answered {code or 'nothing'} for status: {why}"
        pushed["status"] = {"week": doc["week"], "pushed_at": doc["pushed_at"]}
        sent.append("status")
    save_relay(ws, r)
    return sent, None


def push_quietly(ws):
    """The build's hook: push when the creator has a sync code, never fail the build."""
    try:
        r = load_relay(ws, create=False)
        if not r:
            return None
        sent, err = push(ws, r)
        if err:
            print(f"anima sync: {err}")
        elif "week" in sent:
            print("anima sync: the phone gets this week the next time it checks")
        return err
    except Exception as e:  # a sync problem must never stop a dashboard build
        print(f"anima sync skipped: {e}")
        return str(e)


def spoken_week(file):
    try:
        d = datetime.date.fromisoformat(os.path.basename(file)[:10])
    except (TypeError, ValueError):
        return file
    n = d.day
    suffix = "th" if 11 <= n % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{d.strftime('%B')} {n}{suffix}"


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ws = radar_home(argv)  # consumes --dir; exits 2 naming the places it looked
    ap = argparse.ArgumentParser(prog="anima_sync.py",
                                 description="Sync the week to the Anima app from anywhere, with a code.")
    ap.add_argument("--push", action="store_true", help="push if the week changed, print only problems")
    ap.add_argument("--new-code", action="store_true", help="a new code and box; the old code stops getting weeks")
    ap.add_argument("--force", action="store_true", help="push everything even if nothing changed")
    args = ap.parse_args(argv)

    if args.push:
        return 4 if push_quietly(ws) else 0

    r = load_relay(ws, fresh=args.new_code)
    sent, err = push(ws, r, force=args.force or args.new_code)
    week = newest_week(ws)
    if err:
        print(f"Could not sync: {err}")
    elif week:
        print(f"The week of {spoken_week(week)} is on Anima's sync, sealed with your code."
              if "week" in sent else f"The week of {spoken_week(week)} was already synced.")
    else:
        print("No week yet. It syncs after the first weekly run.")
    print(f"Sync code: {r['code']}")
    print("On your iPhone, open Anima, tap Use a sync code and type it once. Keep it like a password.")
    return 4 if err else 0


if __name__ == "__main__":
    sys.exit(main())

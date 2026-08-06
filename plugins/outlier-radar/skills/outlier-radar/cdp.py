#!/usr/bin/env python3
"""cdp.py: minimal Chrome DevTools Protocol client, stdlib only.

Exists because the box has no playwright/selenium/websocket-client and the
receipt pipeline needs three things plain `chrome --screenshot` cannot do:

  1. run JS in the page (to remove consent/promo overlays before shooting),
  2. read the DOM (to get the real headline text, and to verify what shipped),
  3. screenshot an exact rect (so the crop is the headline block by geometry,
     not by an ink-density guess that lands on a nav list or a photo).

~80 lines of RFC 6455 client framing + a request/response loop is cheaper than
a dependency. Text frames only; handles 16/64-bit lengths and continuation
frames, which matters because a full-page screenshot arrives base64 in one
multi-megabyte message.

Usage:
    with Browser(width=1440, height=2200) as b:
        page = b.page()
        page.goto("https://example.com")
        r = page.eval("document.title")
        png = page.screenshot(clip={"x":0,"y":0,"width":800,"height":400,"scale":2})
"""
import base64
import json
import os
import socket
import struct
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request

CHROME = os.environ.get(
    "CHROME_BIN", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")

# Consent-management platforms, resolved to a dead IP so the banner script never
# arrives. Belt and braces with the JS remover: some CMPs inject into a shadow
# root or an iframe that is awkward to walk, but they all have to load first.
CMP_HOSTS = [
    "cdn.cookielaw.org", "geolocation.onetrust.com", "cdn-ukwest.onetrust.com",
    "consent.cookiebot.com", "consentcdn.cookiebot.com",
    "sdk.privacy-center.org", "api.privacy-center.org",
    "cdn.privacy-mgmt.com", "sourcepoint.mgr.consensu.org",
    "quantcast.mgr.consensu.org", "cmp.quantcast.com", "cmp.osano.com",
    "delivery.consentmanager.net", "cdn.consentmanager.net",
    "fundingchoicesmessages.google.com", "funding-choices.appspot.com",
    "cmp.inmobi.com", "cdn.trustarc.com", "consent.trustarc.com",
    "static.cookiebot.com", "app.usercentrics.eu", "api.usercentrics.eu",
    "privacy-proxy.usercentrics.eu", "cdn.cookiefirst.com",
    "consent.google.com", "cdn.iubenda.com", "cs.iubenda.com",
    "cmp.pubtech.ai", "cdn.didomi.io",
]


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


class WS:
    """Client-side WebSocket, text frames only."""

    def __init__(self, url: str, timeout: float = 60.0):
        u = urllib.parse.urlparse(url)
        self.sock = socket.create_connection((u.hostname, u.port), timeout=timeout)
        self.sock.settimeout(timeout)
        path = u.path + (f"?{u.query}" if u.query else "")
        key = base64.b64encode(os.urandom(16)).decode()
        self.sock.sendall(
            f"GET {path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\n"
            f"Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n"
            .encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise EOFError("handshake closed")
            buf += chunk
        head, _, self.buf = buf.partition(b"\r\n\r\n")
        if b"101" not in head.split(b"\r\n")[0]:
            raise RuntimeError(f"upgrade refused: {head[:120]!r}")

    def send(self, obj) -> None:
        payload = json.dumps(obj).encode()
        n = len(payload)
        hdr = b"\x81"
        if n < 126:
            hdr += bytes([0x80 | n])
        elif n < 65536:
            hdr += bytes([0x80 | 126]) + struct.pack(">H", n)
        else:
            hdr += bytes([0x80 | 127]) + struct.pack(">Q", n)
        mask = os.urandom(4)
        self.sock.sendall(hdr + mask
                          + bytes(b ^ mask[i % 4] for i, b in enumerate(payload)))

    def _read(self, n: int) -> bytes:
        while len(self.buf) < n:
            chunk = self.sock.recv(1 << 20)
            if not chunk:
                raise EOFError("socket closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def recv(self):
        data = b""
        while True:
            b0, b1 = self._read(2)
            fin, op, ln = b0 & 0x80, b0 & 0x0F, b1 & 0x7F
            if ln == 126:
                ln = struct.unpack(">H", self._read(2))[0]
            elif ln == 127:
                ln = struct.unpack(">Q", self._read(8))[0]
            payload = self._read(ln) if ln else b""
            if op == 0x8:
                raise EOFError("peer closed")
            if op in (0x9, 0xA):          # ping/pong: not our data
                continue
            data += payload
            if fin:
                return json.loads(data.decode("utf-8", "replace"))

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass


class Page:
    def __init__(self, ws: WS):
        self.ws = ws
        self._id = 0
        self.call("Page.enable")
        self.call("Runtime.enable")

    def call(self, method: str, params=None, timeout: float = 45.0):
        self._id += 1
        mid = self._id
        self.ws.send({"id": mid, "method": method, "params": params or {}})
        deadline = time.time() + timeout
        while time.time() < deadline:
            msg = self.ws.recv()
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"{method}: {msg['error']}")
                return msg.get("result", {})
        raise TimeoutError(method)

    def _drain_until(self, event: str, timeout: float) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                self.ws.sock.settimeout(max(0.5, deadline - time.time()))
                msg = self.ws.recv()
            except (socket.timeout, TimeoutError):
                return False
            if msg.get("method") == event:
                return True
        return False

    def goto(self, url: str, settle: float = 1.6, timeout: float = 30.0) -> bool:
        """Navigate and wait for load. Returns False on load timeout: the page
        may still be usable (lazy news pages fire load late), so the caller
        decides, rather than this throwing away a good capture."""
        self.call("Page.navigate", {"url": url}, timeout=timeout)
        ok = self._drain_until("Page.loadEventFired", timeout)
        self.ws.sock.settimeout(60.0)
        time.sleep(settle)
        return ok

    def eval(self, expr: str, timeout: float = 45.0):
        r = self.call("Runtime.evaluate", {
            "expression": expr, "returnByValue": True, "awaitPromise": True,
        }, timeout=timeout)
        if r.get("exceptionDetails"):
            raise RuntimeError(r["exceptionDetails"].get("text", "js error"))
        return r.get("result", {}).get("value")

    def screenshot(self, clip=None, timeout: float = 60.0) -> bytes:
        params = {"format": "png", "captureBeyondViewport": True}
        if clip:
            params["clip"] = clip
        r = self.call("Page.captureScreenshot", params, timeout=timeout)
        return base64.b64decode(r["data"])


class Browser:
    def __init__(self, width=1440, height=2200, block_cmp=True, scale=1):
        self.port = _free_port()
        self._tmp = tempfile.TemporaryDirectory()
        args = [
            CHROME, "--headless=new", f"--remote-debugging-port={self.port}",
            f"--user-data-dir={self._tmp.name}", "--no-first-run",
            "--no-default-browser-check", "--disable-gpu", "--hide-scrollbars",
            "--mute-audio", "--disable-extensions",
            f"--window-size={width},{height}",
            f"--force-device-scale-factor={scale}",
            # a real UA: several outlets serve a stub to obvious headless agents
            "--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        ]
        if block_cmp:
            rules = ", ".join(f"MAP {h} 0.0.0.0" for h in CMP_HOSTS)
            args.append(f"--host-resolver-rules={rules}")
        self.proc = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL)
        self.ws_url = self._wait_devtools()

    def _wait_devtools(self, timeout=25.0) -> str:
        deadline = time.time() + timeout
        url = f"http://127.0.0.1:{self.port}/json/list"
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(url, timeout=2) as r:
                    for t in json.load(r):
                        if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                            return t["webSocketDebuggerUrl"]
            except Exception:
                time.sleep(0.3)
        raise RuntimeError("Chrome DevTools never came up")

    def page(self) -> Page:
        return Page(WS(self.ws_url))

    def close(self) -> None:
        try:
            self.proc.terminate()
            self.proc.wait(timeout=10)
        except Exception:
            self.proc.kill()
        self._tmp.cleanup()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

#!/usr/bin/env python3
"""One whisper decode at a time on this machine, first come first served (3.9.0).

whisper.cpp runs on the GPU, and two decodes side by side are slower together than one after
the other. Until 3.8.3 only the cross-window scan took a lock, and only inside its own build
folder: on 2026-10-25 a take's word transcript, the word-gap confirmations, the restart scan
and a prescan from a second batch all shared the GPU with it, and one scan's 124 windows took
439 seconds, 3.5 seconds a window against 1.2 alone. That lock was also unfair: a prescan
decoding in chunks took it back the instant it let go, and a gate's decode waited behind it for
over an hour until the prescan was killed by hand.

Every whisper call the editor makes now goes through run(), which takes a per-user lock
(~/.cache/yapcut/whisper.lock) in the order the callers arrived: each waiter leaves a ticket in
whisper.q/ and the oldest live ticket gets the lock next. A ticket or a lock whose process is
gone is cleared by whoever finds it. The shell scripts call it as

    python3 yaplib/whisper.py run -- whisper-cli -m model -f in.wav ...

The wait is silent for the first few seconds and then says so once, so a batch that queues
behind another batch's decode is visible in its log.
"""
import os
import subprocess
import sys
import time

BASE = os.path.join(os.path.expanduser("~"), ".cache", "yapcut")
LOCK = os.path.join(BASE, "whisper.lock")
QUEUE = os.path.join(BASE, "whisper.q")
SAY_AFTER_S = 5


def _alive(pid):
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def _owner(path):
    try:
        with open(os.path.join(path, "pid")) as f:
            return int(f.read() or 0)
    except (OSError, ValueError):
        return 0


class lock:
    """`with whisper.lock():` holds the machine-wide decode lock, in arrival order."""

    def __init__(self, path=None, queue=None):
        self.dir = path or LOCK
        self.q = queue or QUEUE
        self.ticket = None

    def _tickets(self):
        """Live tickets, oldest first: (name, pid). Dead ones are removed on the way."""
        out = []
        try:
            names = sorted(os.listdir(self.q))
        except OSError:
            return out
        for n in names:
            try:
                pid = int(n.rsplit("-", 1)[1])
            except (IndexError, ValueError):
                pid = 0
            if _alive(pid):
                out.append((n, pid))
            else:
                try:
                    os.remove(os.path.join(self.q, n))
                except OSError:
                    pass
        return out

    def __enter__(self):
        os.makedirs(self.q, exist_ok=True)
        self.ticket = f"{time.time_ns():020d}-{os.getpid()}"
        with open(os.path.join(self.q, self.ticket), "w") as f:
            f.write(str(os.getpid()))
        waited, said, mine = 0.0, False, os.getpid()
        while True:
            live = self._tickets()
            first = live[0][1] if live else mine
            if first == mine:
                try:
                    os.mkdir(self.dir)
                    with open(os.path.join(self.dir, "pid"), "w") as f:
                        f.write(str(mine))
                    return self
                except FileExistsError:
                    owner = _owner(self.dir)
                    if not _alive(owner) and waited >= 2:        # gone or never wrote a pid: take it over
                        subprocess.run(["rm", "-rf", self.dir])
                        continue
            if waited >= SAY_AFTER_S and not said:
                print(f"  waiting for another whisper decode to finish ({len(live)} in the queue)", flush=True)
                said = True
            time.sleep(0.5)
            waited += 0.5

    def __exit__(self, *exc):
        subprocess.run(["rm", "-rf", self.dir])
        if self.ticket:
            try:
                os.remove(os.path.join(self.q, self.ticket))
            except OSError:
                pass
            self.ticket = None


def run(cmd, **kw):
    """subprocess.run(cmd) under the lock. Keyword arguments pass through."""
    with lock():
        return subprocess.run(list(cmd), **kw)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if len(argv) >= 2 and argv[0] == "run":
        argv = argv[1:]
        if argv and argv[0] == "--":
            argv = argv[1:]
        sys.exit(run(argv).returncode)
    sys.exit("usage: whisper.py run -- <whisper-cli command...>")

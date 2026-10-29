#!/usr/bin/env python3
"""yapbatch: a batch of Mode A videos through cut, gates and an optional render, as one queue.

On 2026-10-23 a five-video batch took two working sessions. No single step was slow enough to
explain that: the agent wrote about twenty one-off drivers (runcut.sh, cutq.sh, matteq.sh,
recut.sh, run_all.sh, run2.sh, run3.sh, finish.sh, a copy of gates.sh), stopped between steps,
and the creator asked "done?" or "eta?" eight times. This is the driver those scripts kept
reinventing, with the pipeline's rules built in:

  - one video at a time through yapfull.sh, and the `after` step (the HyperFrames render)
    only once that video's gates pass, one render at a time
  - a gate that fails (rc 2) stops THAT video, records the gate and its fix, and the queue
    moves on to the next video; nothing ever sets a YAP_ALLOW_* override for you
  - the restart scan's take windows are decoded ahead (xwin_scan.py --prescan) in one
    background lane, so a video's cut and the previous video's render overlap the scan; the
    gate waits for its own video's prescan, and a fair lock keeps whisper to one decode at a
    time (since 3.9.0 the scan decodes only around what the audio says twice, so the prescan
    is a minute or two a take)
  - <workdir>/batch_status.json and batch_status.txt say where every video is, why a failed
    one failed, and an ETA from the steps already timed. `yapbatch.py <batch> --status` prints it.

The batch file (JSON):
  {
    "workdir": "<footage>/.yap_build",            default: the batch file's folder
    "out": "{workdir}/house/{name}.mp4",          yapfull's output, per video
    "env": {"YAP_SPEED": "1.1", "YAP_CUT_ARGS": "--min-gap 0.3 --silence-db -38"},
    "after": "cd ~/ws/hyperframes && python3 specs/{name}.py render",   optional
    "videos": [
      {"name": "fut-unfakeable", "hook": "The|Unfakeable", "spark": "Unfakeable",
       "clauses": "clauses_fut-unfakeable.json",   default clauses_<name>.json in workdir
       "env": {}, "after": null, "from_cut": false}
    ]
  }
{name}, {workdir} and {out} are filled in `out` and `after`. A video's env and after win over
the batch's. Paths are relative to the workdir.

Usage:
  yapbatch.py <batch.json>                 run every video
  yapbatch.py <batch.json> --only a,b      run these (others keep their status)
  yapbatch.py <batch.json> --resume        skip videos already done
  yapbatch.py <batch.json> --from-cut      YAP_FROM_CUT=1 for every video (caption or hook fixes)
  yapbatch.py <batch.json> --serial        no background prescan: each step after the last
  yapbatch.py <batch.json> --status        print the status and exit
Exit 0 when every video it ran is done, 2 when any stopped at a gate or failed.
"""
import argparse, datetime, json, os, re, subprocess, sys, threading, time

SCRIPTS = os.path.dirname(os.path.realpath(__file__))
LOCK = threading.Lock()
AT = [0]   # index of the video at its gates, read by the prescan lane


def now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def secs(a, b):
    return (datetime.datetime.fromisoformat(b) - datetime.datetime.fromisoformat(a)).total_seconds()


def fmt_dur(s):
    s = int(max(0, s))
    return f"{s // 3600}h{s % 3600 // 60:02d}m" if s >= 3600 else f"{s // 60}m{s % 60:02d}s"


class Status:
    """batch_status.json: {"videos": {name: {...}}, "started": ...}, rewritten on every change."""

    def __init__(self, wd, names):
        self.path = os.path.join(wd, "batch_status.json")
        self.txt = os.path.join(wd, "batch_status.txt")
        try:
            self.d = json.load(open(self.path))
        except (OSError, ValueError):
            self.d = {}
        self.d.setdefault("videos", {})
        for n in names:
            self.d["videos"].setdefault(n, {"state": "queued"})
        self.order = names

    def set(self, name, **kw):
        with LOCK:
            v = self.d["videos"].setdefault(name, {})
            v.update(kw)
            self.d["updated"] = now()
            json.dump(self.d, open(self.path, "w"), indent=1)
            open(self.txt, "w").write(self.render())

    def eta(self):
        """Seconds left: each remaining step at the mean of the same step already timed."""
        took = {"gates": [], "after": [], "prescan": []}
        for v in self.d["videos"].values():
            for step in took:
                t = v.get(f"{step}_s")
                if t:
                    took[step].append(t)
        mean = {k: (sum(x) / len(x) if x else None) for k, x in took.items()}
        left, unknown = 0.0, False
        for n in self.order:
            v = self.d["videos"].get(n, {})
            st = v.get("state", "queued")
            if st in ("done", "gate-failed", "failed", "after-failed"):
                continue
            for step, states in (("gates", ("queued", "gates")), ("after", ("queued", "gates", "after"))):
                if step == "after" and not v.get("has_after"):
                    continue
                if st in states:
                    m = mean[step]
                    if m is None:
                        unknown = True
                        continue
                    running = v.get(f"{step}_started") if st == step else None
                    left += max(0.0, m - secs(running, now())) if running else m
        return left, unknown

    def render(self):
        rows = [f"yapbatch status, {now()}"]
        for n in self.order:
            v = self.d["videos"].get(n, {})
            st = v.get("state", "queued")
            bits = [f"{n:28} {st:13}"]
            if v.get("prescan"):
                bits.append(f"prescan {v['prescan']}")
            if v.get("gates_s"):
                bits.append(f"gates {fmt_dur(v['gates_s'])}")
            if v.get("after_s"):
                bits.append(f"after {fmt_dur(v['after_s'])}")
            if v.get("gate"):
                bits.append(f"stopped at {v['gate']}: {v.get('fix', '')}")
            if v.get("error"):
                bits.append(v["error"])
            rows.append("  ".join(bits))
        left, unknown = self.eta()
        rows.append(f"ETA: {fmt_dur(left)}" + (" plus steps not yet timed" if unknown else ""))
        return "\n".join(rows) + "\n"


def fill(tpl, **kw):
    return tpl.format(**kw) if tpl else tpl


def failing_gate(log):
    """('dead_air', 'the fix message') from yapfull's 'GATE x FAILED (rc 2). msg' lines. Since 3.9.0 the
    decision gates are deferred and several can fail in one run: every one is named, with every fix."""
    found = []
    for line in open(log, errors="ignore"):
        mm = re.match(r"GATE (\S+) FAILED \(rc 2\)\.\s*(.*)", line.strip())
        if mm and mm.group(1) not in [g for g, _ in found]:
            found.append((mm.group(1), mm.group(2)))
    if not found:
        return (None, None)
    return ("+".join(g for g, _ in found), " | ".join(f"{g}: {fix}" for g, fix in found) if len(found) > 1 else found[0][1])


def failing_step(log):
    """yapfull's 'STEP x FAILED (rc n): what' line for a step that broke rather than a gate that ruled."""
    for line in open(log, errors="ignore"):
        if line.startswith("STEP ") and " FAILED " in line:
            return line.strip()
    return None


def run_logged(cmd, log, env, cwd=None, shell=False):
    with open(log, "w") as f:
        f.write(f"$ {cmd if shell else ' '.join(cmd)}\n"); f.flush()
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT, env=env, cwd=cwd, shell=shell)
        f.write(f"exit {r.returncode}\n")
    return r.returncode


def prescan_plan(v, wd, from_cut):
    """What to prescan: on a rerun from an existing cut, exactly its 1x keeps (the windows the
    gate reads); otherwise the clause plan, the best guess before the cut exists."""
    k = os.path.join(wd, f"keeps_full_{v['name']}")
    sped = os.path.exists(os.path.join(wd, f"full_{v['name']}.mp4.speed"))
    if from_cut and sped and os.path.isfile(k + ".1x.json"):
        return k + ".1x.json"            # a sped-up cut's keeps are rescaled; the 1x copy is the take's
    if from_cut and not sped and os.path.isfile(k + ".json"):
        return k + ".json"
    return v["clauses"]


def prescan_one(v, wd, st, env, from_cut=False):
    mark = os.path.join(wd, "xwin_src", f".prescan_{v['name']}")
    os.makedirs(os.path.dirname(mark), exist_ok=True)
    t0 = now()
    st.set(v["name"], prescan="running")
    rc = run_logged([sys.executable, os.path.join(SCRIPTS, "xwin_scan.py"), "--prescan", prescan_plan(v, wd, from_cut),
                     "--store-dir", os.path.join(wd, "xwin_src"), "--workdir", wd],
                    os.path.join(wd, f"prescan_{v['name']}.log"), env)
    st.set(v["name"], prescan="done" if rc == 0 else f"failed rc {rc} (the gate decodes it)",
           prescan_s=secs(t0, now()))
    open(mark, "w").write(str(rc))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("batch")
    ap.add_argument("--only", default="")
    ap.add_argument("--resume", action="store_true")
    ap.add_argument("--from-cut", action="store_true")
    ap.add_argument("--serial", action="store_true")
    ap.add_argument("--no-prescan", action="store_true")
    ap.add_argument("--status", action="store_true")
    a = ap.parse_args()

    b = json.load(open(a.batch))
    wd = os.path.abspath(os.path.expanduser(b.get("workdir") or os.path.dirname(os.path.abspath(a.batch))))
    vids = []
    for v in b["videos"]:
        v = dict(v)
        v["clauses"] = os.path.join(wd, os.path.expanduser(v.get("clauses") or f"clauses_{v['name']}.json"))
        v["out"] = os.path.join(wd, os.path.expanduser(fill(v.get("out") or b.get("out") or "{workdir}/house/{name}.mp4",
                                                            name=v["name"], workdir=wd, out="")))
        v["after"] = fill(v.get("after", b.get("after")) or "", name=v["name"], workdir=wd, out=v["out"])
        vids.append(v)
    st = Status(wd, [v["name"] for v in vids])
    if a.status:
        print(st.render(), end="")
        return 0

    only = {x.strip() for x in a.only.split(",") if x.strip()}
    todo = [v for v in vids if (not only or v["name"] in only)
            and not (a.resume and st.d["videos"].get(v["name"], {}).get("state") == "done")]
    if not todo:
        print("yapbatch: nothing to run"); print(st.render(), end="")
        return 0
    for v in todo:
        missing = [p for p in (v["clauses"],) if not os.path.isfile(p)]
        if missing or not v.get("hook"):
            sys.exit(f"yapbatch: {v['name']} needs a clauses file and a hook ({missing or 'no hook'})")
        st.set(v["name"], state="queued", has_after=bool(v["after"]), gate=None, fix=None, error=None,
               prescan=None if not a.no_prescan else "off")

    base_env = dict(os.environ)
    base_env.update({k: str(x) for k, x in (b.get("env") or {}).items()})
    prescan = not a.no_prescan
    lane = None
    if prescan:
        for v in todo:
            m = os.path.join(wd, "xwin_src", f".prescan_{v['name']}")
            if os.path.exists(m):
                os.remove(m)
        if not a.serial:
            def ahead():
                # one video ahead of the gates, never more (3.8.3): the lane used to prescan every queued video while
                # the first was still at its gates, and on 2026-10-25 the video being gated waited on the whisper
                # lock behind the prescans of the two videos after it
                for i, v in enumerate(todo):
                    while i > 0 and AT[0] < i - 1:
                        time.sleep(5)
                    prescan_one(v, wd, st, base_env, a.from_cut or v.get("from_cut"))
            lane = threading.Thread(target=ahead, daemon=True)
            lane.start()

    print(f"yapbatch: {len(todo)} video(s) in {wd}; status in batch_status.txt", flush=True)
    bad = 0
    for i, v in enumerate(todo):
        AT[0] = i
        env = dict(base_env)
        env.update({k: str(x) for k, x in (v.get("env") or {}).items()})
        if a.from_cut or v.get("from_cut"):
            env["YAP_FROM_CUT"] = "1"
        if prescan:
            if a.serial:
                prescan_one(v, wd, st, env, a.from_cut or v.get("from_cut"))
            env["YAP_XWIN_WAIT"] = os.path.join(wd, "xwin_src", f".prescan_{v['name']}")
        os.makedirs(os.path.dirname(v["out"]), exist_ok=True)
        log = os.path.join(wd, f"log_{v['name']}.txt")
        t0 = now()
        st.set(v["name"], state="gates", gates_started=t0, log=log)
        print(f"[{t0[11:16]}] {v['name']}: cut and gates", flush=True)
        rc = run_logged(["bash", os.path.join(SCRIPTS, "yapfull.sh"), wd, v["clauses"], v["out"],
                         v["hook"], v.get("spark", "")], log, env)
        st.set(v["name"], gates_s=secs(t0, now()))
        if rc != 0:
            gate, fix = failing_gate(log)
            bad += 1
            if gate:
                st.set(v["name"], state="gate-failed", gate=gate, fix=fix)
                print(f"  {v['name']}: stopped at the {gate} gate. {fix} (log: {log})", flush=True)
            else:
                step = failing_step(log)
                st.set(v["name"], state="failed", error=f"{step or f'yapfull exit {rc}'}, see {os.path.basename(log)}")
                print(f"  {v['name']}: {step or f'yapfull exit {rc}'} (log: {log})", flush=True)
            continue
        if v["after"]:
            t1 = now()
            st.set(v["name"], state="after", after_started=t1)
            print(f"[{t1[11:16]}] {v['name']}: after: {v['after']}", flush=True)
            alog = os.path.join(wd, f"after_{v['name']}.log")
            rc = run_logged(v["after"], alog, env, cwd=wd, shell=True)
            st.set(v["name"], after_s=secs(t1, now()))
            if rc != 0:
                bad += 1
                st.set(v["name"], state="after-failed", error=f"after exit {rc}, see {os.path.basename(alog)}")
                print(f"  {v['name']}: after step exit {rc} (log: {alog})", flush=True)
                continue
        st.set(v["name"], state="done", finished=now())
        print(f"[{now()[11:16]}] {v['name']}: done -> {v['out']}", flush=True)
    if lane:
        lane.join()
    print(st.render(), end="")
    return 2 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

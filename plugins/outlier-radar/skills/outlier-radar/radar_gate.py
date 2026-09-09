#!/usr/bin/env python3
"""radar_gate.py: run every machine gate on a week file. One table, one exit code, one stamp.

WHY THIS EXISTS. Until 2026-09-09 there were five gate scripts and no gate: each chose its
own exit code, check_fidelity.py had none at all, nothing sequenced them, and the dashboard
rendered whatever the week file held. The shipped example week failed 3 of 3 on the
fingerprint gate and 1 of 2 on the LinkedIn gate and every installer's first dashboard was
built from it. The human was the only gate.

WHAT IT RUNS, in order:
  check_fidelity   schema pass, fidelity, cadence (warn by default), LinkedIn laws
  hook_lint        first line and last line, the epigram, banned words
  spoken_lint      verbless runs, rejected phrases, absence claims, cadence floors
  source_check     opens every source URL in Chrome and proves the claim strings are on the
                   page. Network. --skip source when offline.
  visual_lint      the feed floor on any render path the week file names (`render` keys and
                   `visual.path`). Skipped when the file names none.
  weeks            cross-file: two week files carrying the same `week` string FAIL, ids
                   shared across week files WARN (a superseded pair is exempt).

EXIT CODE = the highest rc any gate returned (Contract 1: 0 pass, 1 warnings, 2 any FAIL). A
gate that crashes counts as 2. build_dashboard.py reads the stamp this writes.

THE STAMP (Contract 4): weeks/<date>.gate.json in the WORKSPACE, never beside a week file
that lives inside the plugin, so grading the bundled example never writes into the repo.
  {week_file, passed_at (ISO), engine (plugin version), results {gate: rc}, skipped [], ok}

Usage:
  python3 radar_gate.py --week weeks/2026-09-07.json [--dir <workspace>]
  python3 radar_gate.py --week weeks/2026-09-07.json --skip source,visual
  python3 radar_gate.py --week ... --allow-unvalidated     # no targets.json yet: grade anyway
  python3 radar_gate.py --week ... --strict-cadence        # cadence rules FAIL again
  python3 radar_gate.py --all                              # stamp every week in weeks/
"""
import argparse
import datetime
import glob
import json
import os
import subprocess
import sys

# realpath locates SIBLING scripts through the workspace symlink. The workspace itself is
# resolved by yapcut_home, never by following a symlink (see yapcut_home.py).
HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
from yapcut_home import radar_home  # noqa: E402

HOME = radar_home()          # consumes --dir; exits 2 with the places looked when none found
PY = sys.executable or "python3"
GATES = ("check_fidelity", "hook_lint", "spoken_lint", "source_check", "visual_lint", "weeks")
SKIP_ALIASES = {"source": "source_check", "visual": "visual_lint", "fidelity": "check_fidelity",
                "hook": "hook_lint", "spoken": "spoken_lint", "weeks": "weeks"}
TIMEOUT = {"source_check": 900}


def engine_version():
    p = os.path.join(HERE, "..", "..", ".claude-plugin", "plugin.json")
    try:
        return json.load(open(p)).get("version", "unknown")
    except Exception:
        return "unknown"


def run(cmd, timeout=300):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired:
        return 2, "", f"timed out after {timeout}s"
    except Exception as e:  # missing interpreter, unreadable script
        return 2, "", repr(e)


def summarise(rc, out, err):
    """One line per gate: the script's own closing line when it printed one, else the
    last stderr line so a traceback is visible in the table rather than swallowed."""
    lines = [l.strip() for l in (out or "").splitlines() if l.strip()]
    errs = [l.strip() for l in (err or "").splitlines() if l.strip()]
    if rc not in (0, 1, 2):
        return "crashed: " + (errs[-1][:96] if errs else f"rc {rc}")
    if lines:
        return lines[-1][:110]
    if errs:
        return errs[-1][:110]
    return f"rc {rc}"


def norm_rc(rc):
    return rc if rc in (0, 1, 2) else 2


def week_path(p):
    if os.path.exists(p) or os.path.isabs(p):
        return os.path.abspath(p)
    alt = os.path.join(str(HOME), p)
    if os.path.exists(alt):
        return alt
    alt = os.path.join(str(HOME), "weeks", os.path.basename(p))
    return alt if os.path.exists(alt) else os.path.abspath(p)


def is_week_file(f):
    b = os.path.basename(f)
    return b.endswith(".json") and not b.endswith(".gate.json") and ".bak" not in b


def find_renders(d):
    """Every render path the week file names: `render` / `renders` keys holding a path or
    a list of paths, and `visual.path`. Relative paths resolve against the workspace."""
    found, missing = [], []

    def add(v):
        if isinstance(v, str) and v.strip():
            p = v.strip()
            full = p if os.path.isabs(p) else os.path.join(str(HOME), p)
            (found if os.path.exists(full) else missing).append(full)
        elif isinstance(v, list):
            for x in v:
                add(x)

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if k in ("render", "renders"):
                    add(v)
                elif k == "visual" and isinstance(v, dict):
                    add(v.get("path"))
                    add(v.get("render"))
                walk(v)
        elif isinstance(o, list):
            for x in o:
                walk(x)

    walk(d)
    return found, missing


def collect_ids(d):
    ids = set()
    for lane in ("distribution", "office", "linkedin", "gtm_linkedin"):
        for it in d.get(lane) or []:
            if isinstance(it, dict):
                if it.get("id"):
                    ids.add(it["id"])
                tw = it.get("linkedin")
                if isinstance(tw, dict) and tw.get("id"):
                    ids.add(tw["id"])
    return ids


def cross_week(path, d):
    """Cross-file checks. Returns (rc, lines)."""
    lines, rc = [], 0
    mine = os.path.abspath(path)
    week = d.get("week")
    my_ids = collect_ids(d)
    supersedes = d.get("supersedes")
    others = []
    for f in sorted(glob.glob(os.path.join(str(HOME), "weeks", "*.json"))):
        if not is_week_file(f) or os.path.abspath(f) == mine:
            continue
        if os.path.basename(f) == os.path.basename(mine):
            # The gated file lives outside the workspace (the bundled example, or a file
            # passed by absolute path) and the workspace holds a same-named copy. Two paths
            # to one week file are not two week files; only one can render.
            lines.append(f"note: {os.path.basename(f)} also exists in the workspace weeks/; "
                         f"treated as the same week file, not a duplicate")
            continue
        try:
            od = json.load(open(f))
        except Exception as e:
            lines.append(f"warn: {os.path.basename(f)} is not valid JSON ({type(e).__name__})")
            rc = max(rc, 1)
            continue
        if isinstance(od, dict):
            others.append((f, od))
    for f, od in others:
        if week and od.get("week") == week:
            lines.append(f"FAIL: {os.path.basename(f)} carries the same week string {week!r}. "
                         f"Two files for one week render twice on the dashboard and split "
                         f"performance rows. Archive one, or set `supersedes` and change `week`.")
            rc = 2
    for f, od in others:
        exempt = (supersedes and od.get("week") == supersedes) or \
                 (od.get("supersedes") and od.get("supersedes") == week)
        shared = sorted(my_ids & collect_ids(od))
        if shared and not exempt:
            shown = ", ".join(shared[:6]) + (" ..." if len(shared) > 6 else "")
            lines.append(f"warn: {len(shared)} id(s) also in {os.path.basename(f)}: {shown}. "
                         f"Tracking and performance key on id; one file overwrites the other.")
            rc = max(rc, 1)
    if not any(l.startswith(("FAIL", "warn")) for l in lines):
        lines.insert(0, f"weeks: {len(others) + 1} week file(s), no duplicate week string, no shared ids")
    return rc, lines


def gate_week(wpath, skip, allow_unvalidated, strict_cadence, verbose):
    d = json.load(open(wpath))
    rows, results, skipped = [], {}, []
    home = str(HOME)

    def record(name, rc, text):
        rc = norm_rc(rc)
        results[name] = rc
        rows.append((name, rc, text))

    def gate(name, cmd, timeout=300):
        if name in skip:
            skipped.append(name)
            rows.append((name, "-", "skipped"))
            return
        rc, out, err = run(cmd, timeout)
        if verbose:
            print(f"\n----- {name} -----")
            print(out.rstrip())
            if err.strip():
                print(err.rstrip())
        record(name, rc, summarise(rc, out, err))

    fid = [PY, os.path.join(HERE, "check_fidelity.py"), "--dir", home, "--week", wpath]
    if allow_unvalidated:
        fid.append("--allow-unvalidated")
    if strict_cadence:
        fid.append("--strict-cadence")
    gate("check_fidelity", fid)
    gate("hook_lint", [PY, os.path.join(HERE, "hook_lint.py"), "--dir", home, "--week", wpath])
    sp = [PY, os.path.join(HERE, "spoken_lint.py"), "--dir", home, "--week", wpath]
    if strict_cadence:
        sp.append("--strict-cadence")
    gate("spoken_lint", sp)
    gate("source_check", [PY, os.path.join(HERE, "source_check.py"), "--dir", home, "--week", wpath],
         TIMEOUT["source_check"])

    if "visual_lint" in skip:
        skipped.append("visual_lint")
        rows.append(("visual_lint", "-", "skipped"))
    else:
        renders, missing = find_renders(d)
        if renders:
            rc, out, err = run([PY, os.path.join(HERE, "visual_lint.py")] + renders)
            if verbose:
                print(f"\n----- visual_lint -----\n{out.rstrip()}\n{err.rstrip()}")
            text = summarise(rc, out, err)
            if missing:
                text += f"  ({len(missing)} named render(s) not on disk)"
                rc = max(norm_rc(rc), 1)
            record("visual_lint", rc, text)
        elif missing:
            record("visual_lint", 1, f"{len(missing)} render path(s) named, none on disk: "
                                     + os.path.basename(missing[0]))
        else:
            skipped.append("visual_lint")
            rows.append(("visual_lint", "-", "no render paths in the week file, skipped"))

    if "weeks" in skip:
        skipped.append("weeks")
        rows.append(("weeks", "-", "skipped"))
    else:
        rc, lines = cross_week(wpath, d)
        n_f = sum(1 for l in lines if l.startswith("FAIL"))
        n_w = sum(1 for l in lines if l.startswith("warn"))
        record("weeks", rc, lines[0][:110] if not (n_f or n_w) else
               f"{n_f} fail, {n_w} warn: " + lines[0][:80])
        if verbose or n_f or n_w:
            for l in lines:
                print(f"  weeks: {l}")

    worst = max([rc for rc in results.values()] or [0])
    stamp = {
        "week_file": os.path.relpath(wpath, home) if wpath.startswith(home) else wpath,
        "week": d.get("week"),
        "passed_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "engine": engine_version(),
        "results": results,
        "skipped": skipped,
        "ok": worst < 2,
        "rc": worst,
    }
    stamp_dir = os.path.join(home, "weeks")
    os.makedirs(stamp_dir, exist_ok=True)
    stamp_path = os.path.join(stamp_dir, os.path.basename(wpath)[:-5] + ".gate.json")
    with open(stamp_path, "w") as fh:
        json.dump(stamp, fh, indent=2)
        fh.write("\n")
    return rows, worst, stamp_path


def print_table(wpath, rows, worst, stamp_path):
    print(f"\n{os.path.basename(wpath)}   engine {engine_version()}   workspace {HOME}")
    print(f"{'gate':<16}{'rc':>3}  summary")
    print("-" * 78)
    for name, rc, text in rows:
        print(f"{name:<16}{str(rc):>3}  {text}")
    print("-" * 78)
    verdict = {0: "PASS", 1: "PASS with warnings", 2: "FAIL"}[worst]
    print(f"{'exit':<16}{worst:>3}  {verdict}   stamp: {os.path.relpath(stamp_path, str(HOME))}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--week", help="week file (absolute, cwd-relative, or workspace-relative)")
    ap.add_argument("--all", action="store_true", help="gate and stamp every week in weeks/")
    ap.add_argument("--dir", help="workspace (consumed by yapcut_home when given)")
    ap.add_argument("--skip", default="", help="comma list: source,visual,hook,spoken,fidelity,weeks")
    ap.add_argument("--allow-unvalidated", action="store_true",
                    help="grade cadence against the defaults when targets.json is missing")
    ap.add_argument("--strict-cadence", action="store_true",
                    help="cadence distribution rules FAIL instead of WARN")
    ap.add_argument("-v", "--verbose", action="store_true", help="print every gate's full output")
    a = ap.parse_args()

    skip = set()
    for s in a.skip.split(","):
        s = s.strip()
        if not s:
            continue
        name = SKIP_ALIASES.get(s, s)
        if name not in GATES:
            print(f"unknown gate in --skip: {s!r}. Known: {', '.join(GATES)}")
            return 2
        skip.add(name)

    if a.all:
        files = [f for f in sorted(glob.glob(os.path.join(str(HOME), "weeks", "*.json")))
                 if is_week_file(f)]
    elif a.week:
        files = [week_path(a.week)]
    else:
        print("need --week <file> or --all")
        return 2
    if not files:
        print(f"no week files under {os.path.join(str(HOME), 'weeks')}")
        return 2

    worst_all = 0
    for f in files:
        if not os.path.exists(f):
            print(f"no week file at {f}")
            return 2
        rows, worst, stamp = gate_week(f, skip, a.allow_unvalidated, a.strict_cadence, a.verbose)
        print_table(f, rows, worst, stamp)
        worst_all = max(worst_all, worst)
    if len(files) > 1:
        print(f"\n{len(files)} week(s) stamped, worst rc {worst_all}")
    return worst_all


if __name__ == "__main__":
    sys.exit(main())

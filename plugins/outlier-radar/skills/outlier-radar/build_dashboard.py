#!/usr/bin/env python3
"""Build dashboard.html from the workspace's weeks/*.json.

The page lives in three real files next to this script, dashboard/template.html,
dashboard/style.css and dashboard/app.js, so HTML, CSS and JS tooling can see them
(the 3.4.1 blank-card TypeError hid inside a Python string for a week). They are
read at build time and inlined, so the OUTPUT is still one self-contained
dashboard.html. Week data, campaigns, the tracking seed and the UI labels travel
as <script type="application/json"> blocks that app.js parses.

Token pass: the assembled document is substituted once, so a __TOKEN__ may live in
whichever of the three files it belongs to (brand colours in style.css, labels and
logos in template.html). The data blocks are inserted last, so week text can never
be token-substituted.

Tracking: performance/tracking.jsonl (Contract 5) seeds the browser's `track`
object at build time; what you change in the browser overlays it in localStorage,
and Export > Performance writes the merged view for `log_perf.py --import`.

Gate stamps: a week whose weeks/<stem>.gate.json is missing, older than the week
file, or records a FAIL is listed as a WARN. --strict turns that into exit 2.

Workspace resolution is yapcut_home.radar_home (Contract 2): --dir, $YAPCUT_HOME,
$OUTLIER_RADAR_HOME, cwd with a marker, ~/outlier-radar with a marker. A workspace
with no weeks/ yet shows the bundled example week.

Run: python3 build_dashboard.py [--dir <workspace>] [--open] [--strict] [--all]
Exit: 0 built (warnings are printed, not fatal), 2 refused (--strict with stamp
problems, no workspace, or a missing template part).
"""
import argparse
import base64
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime

# realpath is right HERE: it locates the sibling module and the dashboard/ parts
# through the workspace's symlink. It is never used to locate the workspace.
HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)
from yapcut_home import radar_home  # noqa: E402

TPL_DIR = os.path.join(HERE, "dashboard")

# Contract 3, top level. Anything else is a legacy key: WARN, never FAIL, because
# 17 real weeks carry them and the page still renders the ones it knows
# (method, coined_term, signals, food).
WEEK_KEYS = {
    "schema_version", "week", "positioning", "supersedes",
    "distribution", "office", "linkedin", "gtm_linkedin", "inspiration",
    "experiment", "ammo", "promised",
}

# Contract 5: the tracking event -> the dashboard status it seeds.
EVENT_STATUS = {"filmed": "filmed", "posted": "posted", "ignored": "ignored"}

_MIME = {".png": "image/png", ".webp": "image/webp", ".jpg": "image/jpeg",
         ".jpeg": "image/jpeg", ".gif": "image/gif"}

# With no logo file anywhere the original rings mark renders, so a bare install
# still has a masthead. __C_ACCENT__ is filled by the token pass.
RINGS_MARK = """<svg class="mark" viewBox="0 0 34 34" fill="none" aria-hidden="true">
      <circle cx="17" cy="17" r="15.5" stroke="currentColor" stroke-opacity=".25" stroke-width="1.5"/>
      <circle cx="17" cy="17" r="9.5" stroke="currentColor" stroke-opacity=".35" stroke-width="1.5"/>
      <path d="M17 17 L28.5 8.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <circle cx="23.5" cy="21.5" r="3.2" fill="__C_ACCENT__"/>
      <circle cx="17" cy="17" r="1.8" fill="currentColor"/>
    </svg>"""

# The partner pill: mark, name, link, and the one-line tagline beneath it.
# LOCKED, not a config surface (the creator's call, 2026-08-13): the pill is the price
# of the free tool. Outlier Radar is built by alexmuresan.com in partnership
# with Reach, and every install renders that credit. The source is open, so a
# fork can strip it; the config deliberately cannot, and no key is read here.
REACH_MARK = ('<svg class="pmark" width="16" height="16" viewBox="0 0 32 32" fill="none" xmlns="http://www.w3.org/2000/svg">'
              '<rect width="32" height="32" rx="8" fill="#0F0F0F"></rect>'
              '<rect x="1" y="1" width="30" height="30" rx="7" stroke="white" stroke-opacity="0.12" stroke-width="2"></rect>'
              '<path d="M8.718 23.161V11.185l4.938 2.716V26l-4.938-2.839Z" fill="#B5F7FF"></path>'
              '<path d="M23.9 16.928l-8.025 4.691v-5.081l7.901-4.425.124 4.815Z" fill="white"></path>'
              '<path d="M25.997 21.679l-5.087-3.003-5.036 2.942 5.185 2.9 4.938-2.839Z" fill="url(#ycReachA)"></path>'
              '<path d="M13.651 6 8.713 8.84l10.179 6.016 4.884-2.743L13.651 6Z" fill="url(#ycReachB)"></path>'
              '<defs><linearGradient id="ycReachA" x1="23.199" y1="22.063" x2="16.276" y2="16.48" gradientUnits="userSpaceOnUse"><stop stop-color="white"></stop><stop offset="1" stop-color="#00BED8"></stop></linearGradient>'
              '<linearGradient id="ycReachB" x1="25.875" y1="15.683" x2="11.93" y2="7.003" gradientUnits="userSpaceOnUse"><stop stop-color="#00BED8"></stop><stop offset="0.58" stop-color="white"></stop></linearGradient></defs></svg>')
PARTNER = "Reach"
PARTNER_URL = "https://usereach.ai"
PARTNER_TAGLINE = ("Get recommended on AI when your customer "
                   "is looking for options")
PARTNER_HTML = (f'<div class="partnerwrap">'
                f'<a class="partner" href="{PARTNER_URL}" target="_blank" '
                f'rel="noopener">with {REACH_MARK}<b>{PARTNER}</b></a>'
                f'<div class="ptag">{PARTNER_TAGLINE}</div></div>')


def warn(msg):
    print("WARN " + msg)


def _base(path):
    return os.path.basename(path)


# ---------------------------------------------------------------- config + brand

def load_config(ws):
    """Optional radar-config.json lets any installer name their two lanes and
    carry their brand. Defaults work with no config at all."""
    p = os.path.join(ws, "radar-config.json")
    if not os.path.exists(p):
        return {}
    try:
        with open(p, encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception as e:
        print("bad radar-config.json, using defaults:", e)
        return {}


def lane_label(cfg, key, default):
    v = cfg.get(key)
    if isinstance(v, dict):
        return v.get("label") or default
    return v or default


def _hex_rgb(h):
    h = (h or "").lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        return (15, 118, 110)


def _mix(rgb, target, amount):
    return tuple(round(c + (t - c) * amount) for c, t in zip(rgb, target))


def _hex(rgb):
    return "#%02X%02X%02X" % rgb


def _luma(rgb):
    return (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255.0


def brand_tokens(cfg):
    """Colours and fonts from radar-config.json, with NEUTRAL fallbacks: a fresh
    install belongs to whoever installed it. The accent derivatives (headline
    emphasis, soft wash) are computed from the accent so a non-warm accent never
    drags the author's palette along."""
    brand = cfg.get("brand") or {}
    bc = brand.get("colors") or {}
    bf = brand.get("fonts") or {}
    c_bg = bc.get("bg") or "#FFFFFF"
    c_ink = bc.get("ink") or "#17191C"
    c_accent = bc.get("accent") or "#0F766E"
    # The card surfaces belong to the dashboard's own light/dark theme, not to the
    # brand block, so a dark brand bg paints a dark page under light cards and
    # near-white ink vanishes on them. Accept a light bg, refuse a dark one and say why.
    if _luma(_hex_rgb(c_bg)) < 0.5:
        print("radar-config brand.colors.bg is dark: ignoring bg/ink and using the "
              "dashboard's own theme (use the header toggle for dark mode). "
              "brand.colors.accent and brand.fonts still apply.")
        c_bg, c_ink = "#FFFFFF", "#17191C"
    ar = _hex_rgb(c_accent)
    return {
        "__C_BG__": c_bg,
        "__C_INK__": c_ink,
        "__C_ACCENT__": c_accent,
        "__ACCENT_RGB__": ",".join(str(c) for c in ar),
        # light mode: toward black so it reads as text, not a button fill
        "__ACCENT_TEXT__": bc.get("accent_text") or _hex(_mix(ar, (0, 0, 0), 0.18)),
        # dark mode: toward white so it clears a dark surface
        "__ACCENT_TEXT_DARK__": bc.get("accent_text_dark") or _hex(_mix(ar, (255, 255, 255), 0.35)),
        "__F_DISPLAY__": bf.get("display") or "Inter",
        "__F_BODY__": bf.get("body") or "Inter",
        "__F_MONO__": bf.get("mono") or "Space Mono",
        "__FONT_IMPORT__": bf.get("google_import") or (
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800"
            "&family=Space+Mono:wght@400;700&display=swap"),
    }


# ---------------------------------------------------------------- logos

def _logo_candidates(ws, stem):
    for d in (ws, HERE):
        for ext in (".svg", ".png", ".webp", ".jpg", ".jpeg", ".gif"):
            yield os.path.join(d, stem + ext)


def load_logo(ws, stem, css_class, fallback=None, attrs=""):
    """Inline stem.(svg|png|...) as markup, workspace first, then the kit. The
    dashboard is one file, so raster art travels as a data URI. `attrs` lets the
    caller pin an id on the img so other places reference it instead of carrying
    a second copy of the bytes."""
    for p in _logo_candidates(ws, stem):
        if not os.path.exists(p):
            continue
        ext = os.path.splitext(p)[1].lower()
        try:
            if ext == ".svg":
                with open(p, encoding="utf-8") as fh:
                    s = fh.read().strip()
                if "<svg" in s:
                    return s
            else:
                with open(p, "rb") as fh:
                    b64 = base64.b64encode(fh.read()).decode("ascii")
                return (f'<img class="{css_class}"{attrs} alt="" aria-hidden="true" '
                        f'src="data:{_MIME[ext]};base64,{b64}">')
        except Exception as e:
            print(f"unreadable {_base(p)}, skipping it:", e)
    return fallback


# ---------------------------------------------------------------- weeks

def _week_files(d):
    """weeks/*.json minus the gate stamps that live beside them."""
    return sorted((f for f in glob.glob(os.path.join(d, "weeks", "*.json"))
                   if not f.endswith(".gate.json")), reverse=True)


def load_weeks(ws, show_all=False):
    """Return ([(path, week_dict)], bundled). Newest file first. Dedupes on the
    `week` string (newest mtime wins, WARN names both), hides weeks another week
    `supersedes` unless show_all, warns on legacy top-level keys, and drops the
    bundled sample once real weeks exist."""
    files = _week_files(ws)
    bundled = False
    if not files:
        files = _week_files(HERE)
        if files:
            print("no weeks in the workspace yet: showing the bundled example week")
            bundled = True
    entries = []
    for f in files:
        try:
            with open(f, encoding="utf-8") as fh:
                w = json.load(fh)
        except Exception as e:
            warn(f"skip {_base(f)}: {e}")
            continue
        if not isinstance(w, dict) or not w.get("week"):
            warn(f"skip {_base(f)}: not a week object with a `week` string")
            continue
        entries.append((f, w))

    for f, w in entries:
        unknown = sorted(k for k in w if k not in WEEK_KEYS)
        if unknown:
            warn(f"{_base(f)}: unknown top-level keys (legacy; the page renders the ones it knows): "
                 + ", ".join(unknown))

    kept, order = {}, []
    for f, w in entries:
        k = str(w["week"])
        if k not in kept:
            kept[k] = (f, w)
            order.append(k)
            continue
        of, ow = kept[k]
        newer, older = (((f, w), (of, ow)) if os.path.getmtime(f) >= os.path.getmtime(of)
                        else ((of, ow), (f, w)))
        warn(f'two files carry week "{k}": {_base(older[0])} and {_base(newer[0])}; '
             f'keeping the newer file, {_base(newer[0])}')
        kept[k] = newer
    entries = [kept[k] for k in order]

    superseded = {str(w["supersedes"]): _base(f) for f, w in entries if w.get("supersedes")}
    if superseded and not show_all:
        shown = []
        for f, w in entries:
            k = str(w["week"])
            if k in superseded:
                print(f'hiding week "{k}" ({_base(f)}): superseded by {superseded[k]} (--all shows it)')
                continue
            shown.append((f, w))
        entries = shown

    if len(entries) > 1:
        entries = [(f, w) for f, w in entries if str(w.get("week", "")).lower() != "example"]
    return entries, bundled


def _parse_iso(s):
    if not s or not isinstance(s, str):
        return None
    try:
        return datetime.fromisoformat(s.strip().replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def stamp_problems(entries):
    """Contract 4. [(week_basename, reason)] for every shown week whose
    weeks/<stem>.gate.json is missing, unreadable, records a FAIL, or predates the
    week file's last edit."""
    out = []
    for f, _w in entries:
        stem = os.path.splitext(f)[0]
        sp = stem + ".gate.json"
        if not os.path.exists(sp):
            out.append((_base(f), "no gate stamp"))
            continue
        try:
            with open(sp, encoding="utf-8") as fh:
                st = json.load(fh)
        except Exception as e:
            out.append((_base(f), f"unreadable gate stamp: {e}"))
            continue
        if not isinstance(st, dict):
            out.append((_base(f), "gate stamp is not an object"))
            continue
        if st.get("ok") is False:
            out.append((_base(f), "gate stamp records a FAIL"))
            continue
        passed = _parse_iso(st.get("passed_at"))
        if passed is None:
            passed = os.path.getmtime(sp)
        if passed < os.path.getmtime(f):
            out.append((_base(f), "week file edited after its stamp"))
    return out


# ---------------------------------------------------------------- tracking + campaigns

def load_tracking(ws):
    """Contract 5. Fold performance/tracking.jsonl into {id: {status, link?, notes?}}.
    Events are applied in `at` order (file order breaks ties), so the latest event
    per id sets the status; a link or notes carried by any event is kept."""
    p = os.path.join(ws, "performance", "tracking.jsonl")
    if not os.path.exists(p):
        return {}, 0
    events = []
    with open(p, encoding="utf-8") as fh:
        for n, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                warn(f"tracking.jsonl line {n}: not JSON, skipped")
                continue
            if not isinstance(ev, dict) or not ev.get("id"):
                warn(f"tracking.jsonl line {n}: no id, skipped")
                continue
            if ev.get("event") not in EVENT_STATUS:
                warn(f"tracking.jsonl line {n}: unknown event {ev.get('event')!r}, skipped")
                continue
            events.append((str(ev.get("at") or ""), n, ev))
    events.sort(key=lambda e: (e[0], e[1]))
    seed = {}
    for _at, _n, ev in events:
        rec = seed.setdefault(str(ev["id"]), {})
        rec["status"] = EVENT_STATUS[ev["event"]]
        if ev.get("link"):
            rec["link"] = str(ev["link"])
        if ev.get("notes"):
            rec["notes"] = str(ev["notes"])
    return seed, len(events)


def load_campaigns(ws):
    """Optional cross-week collections (campaigns/*.json), each {campaign, label,
    positioning, distribution[], office[], linkedin[]} in the week item schemas,
    rendered as its own tab. No campaigns/ dir means no extra tabs."""
    out = []
    for f in sorted(glob.glob(os.path.join(ws, "campaigns", "*.json"))):
        try:
            with open(f, encoding="utf-8") as fh:
                out.append(json.load(fh))
        except Exception as e:
            warn(f"skip campaign {_base(f)}: {e}")
    return out


# ---------------------------------------------------------------- page

def read_part(name):
    p = os.path.join(TPL_DIR, name)
    try:
        with open(p, encoding="utf-8") as fh:
            s = fh.read()
    except OSError as e:
        sys.stderr.write(f"missing dashboard part {p}: {e}\n")
        sys.exit(2)
    return s if s.endswith("\n") else s + "\n"


def json_for_script(obj):
    """JSON safe inside a <script> block: every '<' becomes \\u003c, so no
    payload can close the block or open a comment. Valid JSON either way."""
    return json.dumps(obj).replace("<", "\\u003c")


def render(ws, cfg, weeks, campaigns, seed):
    tokens = brand_tokens(cfg)
    byline = cfg.get("byline")
    if byline is None:
        byline = "by alexmuresan.com"
    primary = lane_label(cfg, "primary_lane", "Industry")
    secondary = lane_label(cfg, "secondary_lane", "Viral videos")
    leaders = cfg.get("leaders_header") or "From leaders you study"

    # The masthead prefers the full lockup; a mark-only install still gets a masthead
    # by falling back to the mark, then to the rings. The mark is inlined ONCE, on the
    # toolbar img with id="logo-mark"; app.js builds the favicon from that element.
    logo_mark = load_logo(ws, "logo-mark", "minimark", attrs=' id="logo-mark"')
    lockup = load_logo(ws, "logo", "lockup",
                       fallback=load_logo(ws, "logo-mark", "lockup", RINGS_MARK))
    if logo_mark is None:
        logo_mark = load_logo(ws, "logo", "minimark", RINGS_MARK, attrs=' id="logo-mark"')

    tokens.update({
        "__LOGOMARK__": lockup,
        "__LOGOMINI__": logo_mark,
        "__PRIMARY_LABEL__": primary,
        "__SECONDARY_LABEL__": secondary,
        "__LEADERS_HDR__": leaders,
        "__BYLINE__": byline,
        "__PARTNER__": PARTNER_HTML,
    })
    data = {
        "__WEEKS_JSON__": json_for_script(weeks),
        "__CAMPAIGNS_JSON__": json_for_script(campaigns),
        "__TRACKING_JSON__": json_for_script(seed),
        "__UI_JSON__": json_for_script({
            "primary_label": primary, "secondary_label": secondary, "leaders_hdr": leaders}),
    }

    html = (read_part("template.html")[:-1]
            .replace("__STYLE__\n", read_part("style.css"))
            .replace("__SCRIPT__\n", read_part("app.js")))
    for tok, val in tokens.items():
        html = html.replace(tok, val)
    left = sorted(set(re.findall(r"__[A-Z][A-Z_]+__", html)) - set(data))
    if left:
        warn("template tokens nobody filled: " + ", ".join(left))
    # data last: a week's text can never be token-substituted
    for tok, val in data.items():
        html = html.replace(tok, val)
    return html


def open_file(path):
    try:
        if sys.platform == "darwin":
            subprocess.Popen(["open", path])
        elif os.name == "nt":
            os.startfile(path)  # noqa
        else:
            subprocess.Popen(["xdg-open", path])
    except Exception as e:
        warn(f"could not open {path}: {e}")


# ---------------------------------------------------------------- main

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    ws = str(radar_home(argv))  # consumes --dir; exits 2 naming the places it looked
    ap = argparse.ArgumentParser(
        prog="build_dashboard.py",
        description="Build the workspace's dashboard.html from weeks/*.json.")
    ap.add_argument("--dir", metavar="PATH",
                    help="workspace (default: $YAPCUT_HOME, then cwd or ~/outlier-radar with a marker)")
    ap.add_argument("--open", action="store_true", help="open the built file with the OS opener")
    ap.add_argument("--strict", action="store_true",
                    help="refuse (exit 2) when a shown week has no gate stamp or a stale one")
    ap.add_argument("--all", action="store_true", help="also show weeks another week supersedes")
    args = ap.parse_args(argv)

    cfg = load_config(ws)
    weeks, bundled = load_weeks(ws, show_all=args.all)
    problems = [] if bundled else stamp_problems(weeks)
    if problems:
        warn(f"{len(problems)} week(s) without a current gate stamp (run radar_gate.py):")
        for name, why in problems:
            print(f"  {name}: {why}")
        if args.strict:
            print(f"FAIL --strict: refusing to build with {len(problems)} unstamped or stale week(s)")
            return 2
    seed, n_events = load_tracking(ws)
    campaigns = load_campaigns(ws)

    html = render(ws, cfg, [w for _f, w in weeks], campaigns, seed)
    dest = os.path.join(ws, "dashboard.html")
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write(html)
    tail = f", tracking seeded for {len(seed)} id(s) from {n_events} event(s)" if n_events else ""
    print(f"wrote {dest} from {len(weeks)} week(s){tail}")
    if args.open:
        open_file(dest)
    return 0


if __name__ == "__main__":
    sys.exit(main())

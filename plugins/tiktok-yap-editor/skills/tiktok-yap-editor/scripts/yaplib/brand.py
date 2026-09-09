#!/usr/bin/env python3
"""brand-config resolution for the whole editor, in one place.

Resolution order (Contract 2, 2026-09-09), first hit wins:
  1. an explicit path (--brand on the CLI, or brand.load(explicit=...))
  2. <workdir>/brand-config.json           (the build's own .yap_build)
  3. <home>/brand-config.json              home = yaplib.home.radar_home(required=False)
  4. scripts/brand-config.default.json     (ships with the plugin)
There is NO skill-root (<skill>/brand-config.json) fallback any more. That path
is what made evidence_card.py and cover.py paint the default orange for a
creator who kept the config in the workdir yapfull honoured first.

DEFAULTS below is the ONE default set. Every key a script reads is here, so a
half-filled brand-config.json still resolves every field. brand-config.default.json
must agree with it (python3 yaplib/brand.py --self-check).

CLI:
  python3 yaplib/brand.py --shell [--brand P] [--workdir WD] [--platform NAME]
      prints shell assignments for yapfull.sh / storyfull.sh to eval:
      CFONT CCASE ACCENT BASE INK HANDLE HFONT CONTACT HANIM HSTYLE PIPSTRICT
      BRANDCFG, plus PLATFORM PLATFORM_LEN_MIN PLATFORM_LEN_MAX PLATFORM_HOOK_ANIM
      PLATFORM_STATIC_FIRST_FRAME for the selected platform ($YAP_PLATFORM or
      --platform, default tiktok) and PLATFORM_<NAME>_* for every platform.
  python3 yaplib/brand.py --json [--brand P] [--workdir WD]     merged config
  python3 yaplib/brand.py --path [--brand P] [--workdir WD]     which file won
  python3 yaplib/brand.py --self-check
"""
import argparse
import copy
import json
import os
import shlex
import sys

try:
    from .home import radar_home
except ImportError:                       # run as a script: python3 yaplib/brand.py
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
    from home import radar_home

SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DEFAULT_FILE = os.path.join(SCRIPTS_DIR, "brand-config.default.json")
MARKER = "brand-config.json"

# Per-platform delivery targets. len = [min_s, max_s] band the finished video
# should land in (outside it is a WARN, rc 1, never a FAIL). hook_anim, when
# present, overrides the brand's hook_anim for that platform. static_first_frame
# means the platform's feed judges the first frame muted (LinkedIn autoplays
# silent and shows a poster frame), so the hook must be fully drawn at 0.00.
DEFAULT_PLATFORMS = {
    "tiktok":   {"len": [25, 40], "hook_anim": "none"},
    "reels":    {"len": [25, 40]},
    "shorts":   {"len": [25, 60]},
    "linkedin": {"len": [30, 60], "hook_anim": "none", "static_first_frame": True},
}

DEFAULTS = {
    "creator": "",
    "niche": "",
    "pillars": [],
    "accounts": [],
    "caption_font": "Montserrat Black",
    "label_font": "",                 # empty = same face as caption_font
    "caption_case": "on",             # on = ALL CAPS, off = sentence case
    "accent_hex": "none",             # single spark colour, or none
    "base_hex": "#FFFFFF",            # caption fill
    "ink_hex": "#000000",             # stroke / shadow
    "handle": "",
    "contact_lines": [],
    "cta_clip": "",
    "hook_anim": "none",              # none | typewriter (typewriter keeps line 1 static, see build_ass)
    "hook_style": "outline",          # outline | minimal
    "hook_display_font": "Anton",     # setup face for hook_styles.py 'branded'
    "pip_strict": False,              # receipts gate fatal (rc 2) instead of a report (rc 1)
    "platforms": DEFAULT_PLATFORMS,
    # The show / series identity (cover.py reads it). name is the cover kicker,
    # question_template shapes an episode title ("How does {subject} sell?"),
    # mark_png is an optional series mark drawn under the title rule (relative
    # paths resolve against <home>/assets/), pillars tag episodes.
    "series": {"name": "", "question_template": "", "mark_png": "", "pillars": []},
}

CASE_ON = ("on", "caps", "upper", "true", "1", "yes")


def _exists(p):
    return bool(p) and os.path.isfile(p)


def resolve(explicit=None, workdir=None, home_dir=None):
    """Return the brand-config path that wins, per the order in the module doc.
    home_dir may be passed to skip the workspace lookup (tests)."""
    if explicit:
        if not _exists(explicit):
            raise FileNotFoundError(f"brand-config not found: {explicit}")
        return os.path.abspath(explicit)
    if workdir and _exists(os.path.join(workdir, MARKER)):
        return os.path.abspath(os.path.join(workdir, MARKER))
    home = home_dir if home_dir is not None else radar_home(argv=[], required=False)
    if home and _exists(os.path.join(str(home), MARKER)):
        return os.path.abspath(os.path.join(str(home), MARKER))
    return DEFAULT_FILE


def _merge(base, over):
    out = copy.deepcopy(base)
    for k, v in (over or {}).items():
        if k.startswith("_"):
            continue                       # _README / _fields in the example file
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            if k == "platforms":
                merged = copy.deepcopy(out[k])
                for name, spec in v.items():
                    merged[name] = {**merged.get(name, {}), **(spec or {})}
                out[k] = merged
            else:
                out[k] = {**out[k], **v}
        else:
            out[k] = v
    return out


def load(explicit=None, workdir=None, home_dir=None):
    """Merged config: DEFAULTS updated by the resolved file. Adds _path (the
    file that won) and normalises the derived fields every script needs."""
    path = resolve(explicit, workdir, home_dir)
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)
    cfg = _merge(DEFAULTS, raw)
    cfg["_path"] = path
    if not cfg.get("label_font"):
        cfg["label_font"] = cfg["caption_font"]
    cfg["caption_case"] = "on" if str(cfg.get("caption_case", "on")).lower() in CASE_ON else "off"
    cfg["pip_strict"] = bool(cfg.get("pip_strict"))
    return cfg


def platform_spec(cfg, name):
    """The resolved platform dict for `name` (case-insensitive) or raise."""
    plats = cfg.get("platforms") or {}
    key = (name or "tiktok").strip().lower()
    if key not in plats:
        raise KeyError(f"unknown platform {name!r}; brand-config platforms: "
                       + ", ".join(sorted(plats)))
    spec = dict(plats[key])
    spec.setdefault("len", [0, 10 ** 6])
    spec["name"] = key
    return spec


def effective_hook_anim(cfg, platform=None):
    """The brand's hook_anim, unless the platform pins its own."""
    if platform:
        spec = platform_spec(cfg, platform)
        if spec.get("hook_anim"):
            return spec["hook_anim"]
    return cfg.get("hook_anim", "none")


def _q(v):
    return shlex.quote(str(v))


def shell_assignments(cfg, platform=None):
    """Lines of NAME=value for bash eval."""
    plat = (platform or os.environ.get("YAP_PLATFORM") or "tiktok").strip().lower()
    spec = platform_spec(cfg, plat)
    lo, hi = spec["len"][0], spec["len"][1]
    lines = [
        f"BRANDCFG={_q(cfg['_path'])}",
        f"CFONT={_q(cfg['caption_font'])}",
        f"CCASE={_q(cfg['caption_case'])}",
        f"ACCENT={_q(cfg['accent_hex'])}",
        f"BASE={_q(cfg['base_hex'])}",
        f"INK={_q(cfg['ink_hex'])}",
        f"HANDLE={_q(cfg['handle'])}",
        f"HFONT={_q(cfg['label_font'])}",
        f"CONTACT={_q(chr(10).join(cfg.get('contact_lines') or []))}",
        f"HANIM={_q(effective_hook_anim(cfg, plat))}",
        f"HSTYLE={_q(cfg['hook_style'])}",
        f"PIPSTRICT={1 if cfg['pip_strict'] else 0}",
        f"PLATFORM={_q(plat)}",
        f"PLATFORM_LEN_MIN={_q(lo)}",
        f"PLATFORM_LEN_MAX={_q(hi)}",
        f"PLATFORM_HOOK_ANIM={_q(spec.get('hook_anim') or '')}",
        f"PLATFORM_STATIC_FIRST_FRAME={1 if spec.get('static_first_frame') else 0}",
        f"PLATFORMS={_q(' '.join(sorted(cfg['platforms'])))}",
    ]
    for name in sorted(cfg["platforms"]):
        s = platform_spec(cfg, name)
        up = name.upper().replace("-", "_")
        lines += [
            f"PLATFORM_{up}_LEN_MIN={_q(s['len'][0])}",
            f"PLATFORM_{up}_LEN_MAX={_q(s['len'][1])}",
            f"PLATFORM_{up}_HOOK_ANIM={_q(s.get('hook_anim') or '')}",
            f"PLATFORM_{up}_STATIC_FIRST_FRAME={1 if s.get('static_first_frame') else 0}",
        ]
    return lines


def self_check():
    """brand-config.default.json must agree with DEFAULTS on every key it
    carries (the file is the on-disk starter, the dict is the code fallback)."""
    with open(DEFAULT_FILE, encoding="utf-8") as f:
        d = json.load(f)
    bad = []
    for k, v in d.items():
        if k.startswith("_"):
            continue
        if k not in DEFAULTS:
            bad.append(f"{k}: in default json, not in DEFAULTS")
        elif DEFAULTS[k] != v:
            bad.append(f"{k}: json={v!r} DEFAULTS={DEFAULTS[k]!r}")
    return bad


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--brand", default="", help="explicit brand-config.json")
    ap.add_argument("--workdir", default="", help="build workdir (.yap_build) to look in first")
    ap.add_argument("--dir", default="", help="workspace (else $YAPCUT_HOME / cwd marker / ~/outlier-radar)")
    ap.add_argument("--platform", default="", help="platform name (default $YAP_PLATFORM or tiktok)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--shell", action="store_true")
    g.add_argument("--json", action="store_true")
    g.add_argument("--path", action="store_true")
    g.add_argument("--self-check", action="store_true")
    a = ap.parse_args(argv)

    if a.self_check:
        bad = self_check()
        if bad:
            print("brand.py self-check FAILED: brand-config.default.json disagrees with DEFAULTS")
            for b in bad:
                print("  " + b)
            return 2
        print("brand.py self-check OK: brand-config.default.json agrees with DEFAULTS")
        return 0

    home_dir = None
    if a.dir:
        home_dir = radar_home(["--dir", a.dir], required=False)
    try:
        cfg = load(a.brand or None, a.workdir or None, home_dir)
    except FileNotFoundError as e:
        sys.stderr.write(f"brand: {e}\n")
        return 2
    if a.path:
        print(cfg["_path"])
    elif a.json:
        print(json.dumps(cfg, indent=1, ensure_ascii=False))
    else:
        try:
            print("\n".join(shell_assignments(cfg, a.platform or None)))
        except KeyError as e:
            sys.stderr.write(f"brand: {e.args[0]}\n")
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())

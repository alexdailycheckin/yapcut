#!/usr/bin/env python3
"""Build dashboard.html from the workspace's weeks/*.json.

Embeds all weekly data into one HTML file (web fonts load from Google Fonts
when online, system fonts otherwise). Your tracking (status, views you got,
posted link, notes) lives in the browser's localStorage keyed by stable item
id, so regenerating the dashboard each week never wipes what you logged.

All mutable data (radar-config.json, weeks/, dashboard.html) lives in a
workspace directory OUTSIDE the skill folder, so plugin updates never touch
it. Resolution order: --dir <path> | $OUTLIER_RADAR_HOME | ./radar-config.json
in the current dir | ~/outlier-radar | legacy: next to this script.

Run: python3 build_dashboard.py [--dir /path/to/workspace]
"""
import json, os, sys, glob

HERE = os.path.dirname(os.path.abspath(__file__))


def resolve_workspace():
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == "--dir" and i + 1 < len(argv):
            return os.path.abspath(os.path.expanduser(argv[i + 1]))
        if a.startswith("--dir="):
            return os.path.abspath(os.path.expanduser(a.split("=", 1)[1]))
    env = os.environ.get("OUTLIER_RADAR_HOME")
    if env:
        return os.path.abspath(os.path.expanduser(env))
    if os.path.exists(os.path.join(os.getcwd(), "radar-config.json")):
        return os.getcwd()
    home = os.path.join(os.path.expanduser("~"), "outlier-radar")
    if os.path.exists(os.path.join(home, "radar-config.json")):
        return home
    return HERE


WS = resolve_workspace()

# Optional radar-config.json (in the workspace) lets any installer name their
# two lanes and carry their brand. Defaults work with no config at all.
CFG = {}
_cfgp = os.path.join(WS, "radar-config.json")
if os.path.exists(_cfgp):
    try:
        CFG = json.load(open(_cfgp))
    except Exception as e:
        print("bad radar-config.json, using defaults:", e)


def _lane_label(key, default):
    v = CFG.get(key)
    if isinstance(v, dict):
        return v.get("label") or default
    return v or default


PRIMARY_LABEL = _lane_label("primary_lane", "Industry")
SECONDARY_LABEL = _lane_label("secondary_lane", "Viral videos")
LEADERS_HDR = CFG.get("leaders_header") or "From leaders you study"
BYLINE = CFG.get("byline") or ""

# Brand block: colors + fonts come from radar-config.json when present so the
# dashboard renders in the installer's own identity, not a generic theme.
# Fallbacks are deliberately NEUTRAL: a fresh install belongs to whoever
# installed it, so nothing here may default to the author's own identity.
BRAND = CFG.get("brand") or {}
_bc = BRAND.get("colors") or {}
_bf = BRAND.get("fonts") or {}
C_BG = _bc.get("bg") or "#FFFFFF"
C_INK = _bc.get("ink") or "#17191C"
C_ACCENT = _bc.get("accent") or "#0F766E"
F_DISPLAY = _bf.get("display") or "Inter"
F_BODY = _bf.get("body") or "Inter"
F_MONO = _bf.get("mono") or "Space Mono"
FONT_IMPORT = _bf.get("google_import") or (
    "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800"
    "&family=Space+Mono:wght@400;700&display=swap")


# Accent DERIVATIVES. These used to be hardcoded warm hexes next to a
# config-driven --accent, so a non-warm accent produced a dashboard whose
# headline emphasis and soft washes stayed the author's orange. Derive them
# instead: the text variants need contrast against the surface (darker on
# light, lighter on dark), and the soft wash is just the accent at low alpha.
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


# The card surfaces are part of the dashboard's own light/dark theme (there is a
# toggle in the header), NOT part of the brand block. A brand bg/ink pair that is
# inverted therefore paints a dark page while the cards stay light, and near-white
# ink on a white card is invisible. Accept a light brand bg, refuse a dark one and
# say why, rather than shipping an unreadable dashboard.
if _luma(_hex_rgb(C_BG)) < 0.5:
    print("radar-config brand.colors.bg is dark: ignoring bg/ink and using the "
          "dashboard's own theme (use the header toggle for dark mode). "
          "brand.colors.accent and brand.fonts still apply.")
    C_BG = "#FFFFFF"
    C_INK = "#17191C"

_ar = _hex_rgb(C_ACCENT)
ACCENT_RGB = ",".join(str(c) for c in _ar)
# light mode: pull toward black so it reads as text, not as a button fill
ACCENT_TEXT = _hex(_mix(_ar, (0, 0, 0), 0.18))
# dark mode: pull toward white so it clears a dark surface
ACCENT_TEXT_DARK = _hex(_mix(_ar, (255, 255, 255), 0.35))

# optional "in partnership with X" pill in the header (empty = hidden).
# Text only by design: a partner logo would mean bundling someone else's mark
# into this repo, so the config carries a name and nothing else.
PARTNER = (CFG.get("partner") or "").strip()
PARTNER_HTML = f'<span class="partner">with <b>{PARTNER}</b></span>' if PARTNER else ""

week_files = sorted(glob.glob(os.path.join(WS, "weeks", "*.json")), reverse=True)
if not week_files and WS != HERE:
    week_files = sorted(glob.glob(os.path.join(HERE, "weeks", "*.json")), reverse=True)
    if week_files:
        print("no weeks in the workspace yet: showing the bundled example week")
weeks = []
for f in week_files:
    try:
        weeks.append(json.load(open(f)))
    except Exception as e:
        print("skip", f, e)
# hide the bundled sample once real weeks exist
if len(weeks) > 1:
    weeks = [w for w in weeks if str(w.get("week", "")).lower() != "example"]

DATA = json.dumps(weeks)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Outlier Radar</title>
<style>
  @import url('__FONT_IMPORT__');
  :root{
    --bg:__C_BG__; --surface:#FFFFFF; --surface2:#F5F4EE; --surface3:#EDEBE3;
    --ink:__C_INK__; --muted:#6F6B62; --faint:#A9A498;
    --line:#E7E5DC; --line-strong:#D4D1C5;
    --accent:__C_ACCENT__; --accent-text:__ACCENT_TEXT__; --accent-soft:rgba(__ACCENT_RGB__,.08);
    --ok:#1B7F4D; --ok-soft:rgba(27,127,77,.1);
    --warn:#8A6D1F; --warn-soft:rgba(179,142,40,.12);
    --shadow:0 1px 2px rgba(35,35,35,.04),0 6px 24px rgba(35,35,35,.05);
    --shadow-lift:0 2px 6px rgba(35,35,35,.06),0 16px 48px rgba(35,35,35,.10);
    --display:'__F_DISPLAY__',-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    --body:'__F_BODY__',-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
    --mono:'__F_MONO__',ui-monospace,"SF Mono",Menlo,monospace;
  }
  :root[data-theme="dark"]{
    --bg:#161512; --surface:#1D1C18; --surface2:#242320; --surface3:#2C2B26;
    --ink:#F4F2EA; --muted:#A5A094; --faint:#6E6A5F;
    --line:#2A2924; --line-strong:#3B3A33;
    --accent:__C_ACCENT__; --accent-text:__ACCENT_TEXT_DARK__; --accent-soft:rgba(__ACCENT_RGB__,.13);
    --ok:#4DBE85; --ok-soft:rgba(77,190,133,.13);
    --warn:#D3B25C; --warn-soft:rgba(211,178,92,.13);
    --shadow:0 1px 2px rgba(0,0,0,.4);
    --shadow-lift:0 2px 8px rgba(0,0,0,.5),0 20px 60px rgba(0,0,0,.45);
  }
  *{box-sizing:border-box}
  html{scroll-behavior:smooth}
  body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 var(--body);-webkit-font-smoothing:antialiased;text-rendering:optimizeLegibility}
  ::selection{background:var(--accent-soft)}
  a{color:var(--accent-text)}
  .wrap{max-width:1080px;margin:0 auto;padding:0 24px 96px}
  .lab{font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}

  /* ---------- top bar ---------- */
  .topbar{position:sticky;top:0;z-index:40;background:color-mix(in srgb, var(--bg) 86%, transparent);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
  .topbar .in{max-width:1080px;margin:0 auto;padding:14px 24px;display:flex;align-items:center;gap:16px}
  .brand{display:flex;align-items:center;gap:11px;margin-right:auto}
  .mark{width:34px;height:34px;flex:none}
  .wordmark{font-family:var(--display);font-size:18px;font-weight:800;letter-spacing:-.01em;line-height:1.1}
  .byline{font-size:12.5px;color:var(--muted);line-height:1.2}
  .partner{display:inline-flex;align-items:center;gap:7px;font-family:var(--mono);font-size:10.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--muted);border:1px solid var(--line-strong);border-radius:999px;padding:7px 13px;white-space:nowrap;text-decoration:none}
  a.partner:hover{border-color:var(--faint);background:var(--surface2)}
  .partner b{color:var(--ink)}
  select{font:600 14px var(--body);color:var(--ink);background:var(--surface);border:1px solid var(--line-strong);border-radius:10px;padding:9px 12px;cursor:pointer}
  select:hover{border-color:var(--faint)}
  .iconbtn{width:38px;height:38px;flex:none;border-radius:10px;border:1px solid var(--line-strong);background:var(--surface);color:var(--ink);cursor:pointer;display:grid;place-items:center;font-size:15px}
  .iconbtn:hover{border-color:var(--faint);background:var(--surface2)}

  /* ---------- export menu ---------- */
  details.menu{position:relative}
  details.menu>summary{list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:8px;font:600 14px var(--body);color:var(--ink);background:var(--surface);border:1px solid var(--line-strong);border-radius:10px;padding:9px 14px}
  details.menu>summary::-webkit-details-marker{display:none}
  details.menu>summary:hover{border-color:var(--faint);background:var(--surface2)}
  details.menu[open]>summary{border-color:var(--faint)}
  .menupanel{position:absolute;right:0;top:calc(100% + 8px);width:330px;background:var(--surface);border:1px solid var(--line-strong);border-radius:14px;box-shadow:var(--shadow-lift);padding:6px;z-index:60}
  .menupanel button{display:block;width:100%;text-align:left;border:0;background:none;border-radius:10px;padding:11px 13px;cursor:pointer;font:inherit;color:var(--ink)}
  .menupanel button:hover{background:var(--surface2)}
  .menupanel button b{display:block;font-size:14px;font-weight:600}
  .menupanel button span{display:block;font-size:12.5px;color:var(--muted);margin-top:2px;line-height:1.4}

  /* ---------- hero ---------- */
  .hero{display:flex;align-items:flex-start;justify-content:space-between;gap:32px;padding:44px 0 8px}
  .eyebrow{display:inline-flex;align-items:center;gap:9px;font-family:var(--mono);font-size:11.5px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--accent-text)}
  .eyebrow .dot{width:7px;height:7px;border-radius:50%;background:var(--accent);animation:pulse 2.4s ease-in-out infinite}
  @keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
  h1{font-family:var(--display);font-size:clamp(30px,4.6vw,42px);font-weight:800;letter-spacing:-.025em;line-height:1.08;margin:14px 0 0}
  h1 em{font-style:normal;color:var(--accent-text)}
  .brief{margin:14px 0 0;max-width:640px}
  .briefclamp{color:var(--muted);font-size:15px;line-height:1.55;margin:0;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
  .briefclamp.open{display:block}
  .brieftoggle{border:0;background:none;padding:0;margin-top:6px;cursor:pointer;font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--accent-text)}
  .briefextra{display:none;margin-top:14px;border-left:2px solid var(--line-strong);padding-left:14px}
  .briefextra.show{display:block}
  .briefextra .bx{margin:0 0 12px}
  .briefextra .bx:last-child{margin-bottom:0}
  .briefextra p{margin:3px 0 0;font-size:14px;color:var(--muted);line-height:1.5}
  .ring{flex:none;text-align:center;padding-top:10px}
  .ring svg{display:block}
  .ring .rn{font-family:var(--display);font-weight:800;font-size:26px;letter-spacing:-.02em;fill:var(--ink)}
  .ring .rl{font-family:var(--mono);font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;fill:var(--muted);font-weight:700}

  /* ---------- stats ---------- */
  .stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:32px 0 0}
  .stat{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px;box-shadow:var(--shadow);display:flex;flex-direction:column;min-height:104px}
  .stat .n{font-family:var(--display);font-size:30px;font-weight:700;letter-spacing:-.02em;margin-top:8px}
  .stat .n.accent{color:var(--accent-text)}
  .stat .sub{font-size:12.5px;color:var(--muted);margin-top:auto;padding-top:8px}
  .intentbar{display:flex;gap:3px;margin-top:auto;padding-top:12px}
  .intentbar>div{height:5px;border-radius:3px;min-width:4px}
  .sga{background:var(--accent)} .sgb{background:var(--ink);opacity:.75} .sgc{background:var(--faint)}
  .barcap{font-size:11.5px;color:var(--muted);margin-top:6px}

  /* ---------- tabs ---------- */
  .tabs{display:flex;gap:4px;margin:36px 0 0;border-bottom:1px solid var(--line);flex-wrap:wrap}
  .tab{display:inline-flex;align-items:center;gap:8px;border:0;background:none;font:600 14px var(--body);color:var(--muted);cursor:pointer;padding:12px 14px;border-bottom:2px solid transparent;margin-bottom:-1px}
  .tab:hover{color:var(--ink)}
  .tab.on{color:var(--ink);border-bottom-color:var(--accent)}
  .tab .ti{width:15px;height:15px;flex:none;opacity:.85}
  .tab .cnt{font-family:var(--mono);font-size:10.5px;font-weight:700;padding:2px 7px;border-radius:999px;background:var(--surface3);color:var(--muted)}
  .tab.on .cnt{background:var(--accent);color:#FFF8F4}
  .tab .cnt:empty{display:none}
  .viewhead{display:flex;align-items:center;justify-content:space-between;gap:16px;margin:20px 0 16px;min-height:24px}
  .ignlab{font-size:13.5px;color:var(--muted);cursor:pointer;display:inline-flex;align-items:center;gap:7px}
  .ignlab input{accent-color:var(--accent)}

  /* ---------- cards ---------- */
  .card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:22px 24px;margin-bottom:16px;box-shadow:var(--shadow);transition:border-color .15s}
  .card:hover{border-color:var(--line-strong)}
  .card.done{opacity:.55}
  .cardtop{display:flex;gap:16px;align-items:flex-start}
  .idx{font-family:var(--mono);font-size:13px;font-weight:700;color:var(--faint);padding-top:5px;flex:none;width:26px}
  .cardtitle{flex:1;min-width:0}
  .ttl{font-family:var(--display);font-size:21px;font-weight:700;letter-spacing:-.015em;line-height:1.22;margin:0}
  .chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:9px}
  .chip{font-family:var(--mono);font-size:10.5px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;padding:3px 9px;border-radius:999px;background:var(--surface3);color:var(--muted)}
  .chip.qa{background:var(--ok-soft);color:var(--ok)}
  .chip.draft{background:var(--warn-soft);color:var(--warn)}
  .chip.sens{background:var(--warn-soft);color:var(--warn)}
  .chip.posted{background:var(--accent-soft);color:var(--accent-text)}
  .cardops{display:flex;gap:6px;flex:none}
  .premise{font-size:14px;color:var(--muted);line-height:1.55;margin:14px 0 0 42px;max-width:70ch}
  .premise b{color:var(--ink);font-weight:600}
  .hookgrid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:16px 0 0 42px}
  .hookcell{background:var(--surface2);border-radius:12px;padding:14px 16px}
  .hookcell .lab{margin-bottom:8px}
  .burn{font-family:var(--display);font-size:19px;font-weight:800;letter-spacing:-.01em;line-height:1.25}
  .hookcell p{margin:0;font-size:14px;line-height:1.5;color:var(--ink)}
  .alts{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
  .alt{font-size:12px;font-weight:600;padding:4px 10px;border-radius:999px;border:1px dashed var(--line-strong);color:var(--muted);cursor:pointer;background:none;font-family:var(--body)}
  .alt:hover{color:var(--ink);border-color:var(--faint)}
  .cardactions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:16px 0 0 42px}
  .btn{display:inline-flex;align-items:center;gap:7px;border:1px solid var(--line-strong);background:var(--surface);border-radius:10px;padding:8px 14px;font:600 13.5px var(--body);cursor:pointer;color:var(--ink)}
  .btn:hover{background:var(--surface2);border-color:var(--faint)}
  .btn svg{width:14px;height:14px;flex:none}
  .btn.primary{background:var(--ink);border-color:var(--ink);color:var(--bg)}
  .btn.primary:hover{opacity:.88}
  .btn.on{background:var(--accent-soft);border-color:var(--accent);color:var(--accent-text)}
  .btn.ghost{border-color:transparent;background:none;color:var(--muted)}
  .btn.ghost:hover{color:var(--ink);background:var(--surface2);border-color:transparent}
  .collapse{display:none}
  .collapse.show{display:block}
  .detail{margin:18px 0 0 42px;border-top:1px solid var(--line);padding-top:18px}

  /* ---------- script blocks ---------- */
  .block{margin:0 0 16px}
  .block:last-child{margin-bottom:0}
  .block .lab{margin-bottom:7px}
  .readbox{background:var(--surface2);border-radius:12px;padding:18px 20px}
  .scriptsec{margin:0 0 18px}
  .scriptsec:last-child{margin-bottom:0}
  .seclabel{font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:var(--accent-text);margin:0 0 8px}
  .seclabel .opt{font-weight:400;letter-spacing:.02em;text-transform:none;font-style:italic;opacity:.7;color:var(--muted)}
  .sent{margin:0 0 9px;font-size:15.5px;line-height:1.5}
  .sent:last-child{margin-bottom:0}
  .sent.hook{font-weight:700;font-size:17px;font-family:var(--display);letter-spacing:-.01em;line-height:1.35}
  .dirbox{background:var(--surface2);border-radius:12px;padding:14px 16px;white-space:pre-wrap;color:var(--muted);font-size:13.5px;line-height:1.55;border-left:3px solid var(--line-strong)}
  .valbox{background:var(--ok-soft);border-radius:12px;padding:13px 16px;font-size:14px;line-height:1.5;border-left:3px solid var(--ok)}
  .ctabox{background:var(--accent-soft);border-radius:12px;padding:13px 16px;font-size:14px;line-height:1.5;border-left:3px solid var(--accent)}
  .psy{font-size:13.5px;color:var(--muted);line-height:1.55;margin:0}
  .tinyline{font-family:var(--mono);font-size:11px;color:var(--faint);margin:0 0 16px}
  .srcs{font-size:13px;line-height:1.9}
  .srcs a{color:var(--accent-text);text-decoration:none}
  .srcs a:hover{text-decoration:underline}
  .srcs .sep{color:var(--faint);margin:0 7px}

  /* ---------- tables (shot list + beats) ---------- */
  .tblwrap{background:var(--surface2);border-radius:12px;padding:6px 16px;overflow-x:auto}
  table.tbl{width:100%;border-collapse:collapse;font-size:13.5px}
  .tbl th{text-align:left;font-family:var(--mono);font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:var(--muted);padding:10px 14px 8px 0}
  .tbl td{padding:9px 14px 9px 0;border-top:1px solid var(--line);vertical-align:top;line-height:1.45}
  .tbl td.bn{font-family:var(--mono);font-size:11.5px;font-weight:700;color:var(--accent-text);white-space:nowrap}
  .tbl td.bmut{color:var(--muted)}
  .tbl a{color:var(--accent-text);text-decoration:none;font-size:12.5px}
  .tbl a:hover{text-decoration:underline}

  /* ---------- tracker ---------- */
  .track{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:18px 0 0 42px;padding-top:16px;border-top:1px solid var(--line)}
  .seg{display:inline-flex;border:1px solid var(--line-strong);border-radius:10px;overflow:hidden;background:var(--surface)}
  .seg button{border:0;background:none;padding:8px 14px;font:600 13px var(--body);color:var(--muted);cursor:pointer;display:inline-flex;align-items:center;gap:7px}
  .seg button+button{border-left:1px solid var(--line)}
  .seg button .sdot{width:7px;height:7px;border-radius:50%;border:1.5px solid var(--faint);flex:none}
  .seg button[data-s="filmed"] .sdot,.seg button[data-s="scheduled"] .sdot{border-color:var(--muted)}
  .seg button[data-s="posted"] .sdot{border-color:var(--accent)}
  .seg button.on{background:var(--ink);color:var(--bg)}
  .seg button.on .sdot{border-color:transparent;background:var(--faint)}
  .seg button.on[data-s="filmed"] .sdot,.seg button.on[data-s="scheduled"] .sdot{background:var(--bg)}
  .seg button.on[data-s="posted"]{background:var(--accent);color:#FFF8F4}
  .seg button.on[data-s="posted"] .sdot{background:#FFF8F4}
  input.views,input.plink{background:var(--surface);color:var(--ink);border:1px solid var(--line-strong);border-radius:10px;padding:8px 12px;font:500 13.5px var(--body)}
  input.views{width:120px}
  input.plink{flex:1;min-width:170px}
  input.views::placeholder,input.plink::placeholder,textarea.notes::placeholder{color:var(--faint)}
  input.views:focus,input.plink:focus,textarea.notes:focus{outline:none;border-color:var(--accent)}
  textarea.notes{width:calc(100% - 42px);margin:10px 0 0 42px;background:var(--surface);color:var(--ink);border:1px solid var(--line);border-radius:10px;padding:9px 12px;font:500 13.5px var(--body);resize:vertical;min-height:38px}

  /* ---------- linkedin twin ---------- */
  .twin{margin:16px 0 0 42px}
  .twinbody{background:var(--surface2);border-radius:12px;padding:16px 18px;white-space:pre-wrap;font-size:14.5px;line-height:1.55;margin-top:10px}
  .twinmeta{margin-top:12px}
  .promptbox{background:var(--surface2);border-radius:10px;padding:12px 14px;white-space:pre-wrap;font-size:12.5px;color:var(--muted);line-height:1.5;margin-top:8px}

  /* ---------- inspiration ---------- */
  .inspgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
  .insp{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:var(--shadow);display:flex;flex-direction:column;gap:8px}
  .insp .who{font-family:var(--display);font-size:16px;font-weight:700;letter-spacing:-.01em}
  .insp .met{font-size:14px;font-weight:600;color:var(--accent-text)}
  .insp .mech{font-size:13px;color:var(--muted);line-height:1.5;flex:1}
  .insp a{font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;text-decoration:none;color:var(--ink)}
  .insp a:hover{color:var(--accent-text)}

  /* ---------- section header + empty state ---------- */
  .sechdr{font-family:var(--mono);font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--muted);margin:32px 0 14px}
  .sechdr:first-child{margin-top:0}
  .empty{text-align:center;padding:72px 24px;border:1px dashed var(--line-strong);border-radius:16px}
  .empty .lab{color:var(--faint)}
  .empty p{color:var(--muted);font-size:15px;margin:10px auto 0;max-width:44ch}

  /* ---------- film mode (teleprompter, always dark) ---------- */
  .film{position:fixed;inset:0;z-index:100;background:#141310;color:#F4F2EA;display:none;flex-direction:column}
  .film.show{display:flex}
  .filmbar{display:flex;align-items:center;gap:16px;padding:16px 28px;border-bottom:1px solid #2A2924;flex:none}
  .filmbar .lab{color:#A5A094}
  .filmtitle{font-family:var(--display);font-size:16px;font-weight:700;margin-right:auto;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .filmclose{border:1px solid #3B3A33;background:none;color:#F4F2EA;border-radius:10px;padding:8px 14px;font:600 13px var(--body);cursor:pointer}
  .filmclose:hover{background:#242320}
  .filmbody{flex:1;overflow-y:auto;padding:48px 28px 120px}
  .filmbody .in{max-width:720px;margin:0 auto}
  .filmburn{font-family:var(--display);font-size:clamp(22px,3.4vw,30px);font-weight:800;line-height:1.2;letter-spacing:-.015em;color:#FFF8F4;background:#242320;border-radius:14px;padding:20px 24px;margin:0 0 12px;text-align:center}
  .filmburncap{font-family:var(--mono);font-size:10px;font-weight:700;letter-spacing:.15em;text-transform:uppercase;color:#6E6A5F;text-align:center;margin:0 0 40px}
  .film .seclabel{color:var(--accent-text);font-size:11px;margin:0 0 16px}
  .film .fsec{margin:0 0 44px}
  .film .fsent{font-size:clamp(19px,2.6vw,23px);line-height:1.55;margin:0 0 18px;color:#E8E5DB}
  .film .fsent.fhook{font-family:var(--display);font-weight:700;font-size:clamp(22px,3vw,27px);color:#FFF8F4;line-height:1.4}
  .film .fextra{border-top:1px solid #2A2924;padding-top:32px;margin-top:8px}
  .film .fextra .lab{color:#A5A094;margin-bottom:8px}
  .film .fextra .dirbox{background:#1D1C18;border-left-color:#3B3A33;color:#A5A094}
  .film .fextra .tblwrap{background:#1D1C18}
  .film .fextra .tbl td{border-top-color:#2A2924}
  .film .fextra .tbl td.bn,.film .fextra .tbl a{color:var(--accent-text)}
  .film .fextra .tbl td.bmut{color:#A5A094}
  .film .fextra .valbox{background:rgba(77,190,133,.1);border-left-color:#4DBE85;color:#E8E5DB}
  .filmfoot{position:absolute;bottom:0;left:0;right:0;display:flex;align-items:center;gap:12px;justify-content:center;padding:16px 28px calc(16px + env(safe-area-inset-bottom));background:linear-gradient(to top,#141310 65%,transparent);flex:none}
  .filmfoot .btn{background:none;border-color:#3B3A33;color:#F4F2EA}
  .filmfoot .btn:hover{background:#242320;border-color:#6E6A5F}
  .filmfoot .btn.primary{background:#F4F2EA;border-color:#F4F2EA;color:#141310}
  .filmfoot .btn.accent{background:__C_ACCENT__;border-color:__C_ACCENT__;color:#FFF8F4}

  /* ---------- toast ---------- */
  .toast{position:fixed;bottom:28px;left:50%;transform:translate(-50%,16px);background:var(--ink);color:var(--bg);font:600 13.5px var(--body);padding:11px 18px;border-radius:12px;box-shadow:var(--shadow-lift);opacity:0;pointer-events:none;transition:all .25s;z-index:120;max-width:80vw;text-align:center}
  .toast.show{opacity:1;transform:translate(-50%,0)}

  @media(max-width:900px){
    .stats{grid-template-columns:repeat(2,1fr)}
    .inspgrid{grid-template-columns:repeat(2,1fr)}
    .hero{flex-direction:column;gap:8px}
    .ring{align-self:flex-end;margin-top:-72px}
  }
  @media(max-width:640px){
    .wrap{padding:0 16px 80px}
    .topbar .in{padding:12px 16px;flex-wrap:wrap;gap:10px}
    .hookgrid{grid-template-columns:1fr}
    .inspgrid{grid-template-columns:1fr}
    .premise,.hookgrid,.cardactions,.track,.detail,.twin{margin-left:0}
    textarea.notes{width:100%;margin-left:0}
    .idx{display:none}
    .ring{margin-top:0;align-self:flex-start}
  }
</style>
</head>
<body>

<div class="topbar"><div class="in">
  <div class="brand">
    <svg class="mark" viewBox="0 0 34 34" fill="none" aria-hidden="true">
      <circle cx="17" cy="17" r="15.5" stroke="currentColor" stroke-opacity=".25" stroke-width="1.5"/>
      <circle cx="17" cy="17" r="9.5" stroke="currentColor" stroke-opacity=".35" stroke-width="1.5"/>
      <path d="M17 17 L28.5 8.5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
      <circle cx="23.5" cy="21.5" r="3.2" fill="__C_ACCENT__"/>
      <circle cx="17" cy="17" r="1.8" fill="currentColor"/>
    </svg>
    <div><div class="wordmark">Outlier Radar</div><div class="byline">__BYLINE__</div></div>
  </div>
  __PARTNER__
  <select id="weekSel" onchange="render()" aria-label="Pick a week"></select>
  <details class="menu" id="exportMenu">
    <summary><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="M7 10l5 5 5-5"/><path d="M12 15V3"/></svg>Export</summary>
    <div class="menupanel">
      <button onclick="closeMenu();exportFilmed()"><b>Filmed scripts</b><span>Copy every script marked Filmed, with its edit spec, for the editor session.</span></button>
      <button onclick="closeMenu();exportForBlog()"><b>Week for blog</b><span>Save Filmed and Posted scripts to a JSON the weekly routine turns into an AEO post.</span></button>
      <button onclick="closeMenu();exportCarousels()"><b>Carousel queue</b><span>Save scripts flagged Carousel, then run build_carousels.py to render the PDFs.</span></button>
      <button onclick="closeMenu();exportPerformance()"><b>Performance</b><span>Save all tracking (status, views, notes) so the next radar run learns what worked.</span></button>
    </div>
  </details>
  <button class="iconbtn" id="themeBtn" onclick="toggleTheme()" title="Toggle light / dark" aria-label="Toggle theme">&#9790;</button>
</div></div>

<div class="wrap">
  <div class="hero">
    <div style="min-width:0">
      <div class="eyebrow"><span class="dot"></span><span id="eyebrowTxt">Weekly slate</span></div>
      <h1>This week <em>to film</em>.</h1>
      <div class="brief" id="brief"></div>
    </div>
    <div class="ring" id="ring"></div>
  </div>

  <div class="stats" id="stats"></div>

  <div class="tabs">
    <button class="tab on" data-t="dist" onclick="setTab('dist')"><svg class="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="14" height="12" rx="2"></rect><path d="m22 8-6 4 6 4V8Z"></path></svg>__PRIMARY_LABEL__ <span class="cnt" data-c="dist"></span></button>
    <button class="tab" data-t="office" onclick="setTab('office')"><svg class="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"></path></svg>__SECONDARY_LABEL__ <span class="cnt" data-c="office"></span></button>
    <button class="tab" data-t="filmed" onclick="setTab('filmed')"><svg class="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"></path><path d="M8 17v-4"></path><path d="M13 17V8"></path><path d="M18 17v-7"></path></svg>Filmed &amp; metrics <span class="cnt" data-c="filmed"></span></button>
    <button class="tab" data-t="linkedin" onclick="setTab('linkedin')"><svg class="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>LinkedIn <span class="cnt" data-c="linkedin"></span></button>
    <button class="tab" data-t="insp" onclick="setTab('insp')"><svg class="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3z"></path></svg>Inspiration <span class="cnt" data-c="insp"></span></button>
  </div>
  <div class="viewhead"><div id="ignrow" style="display:none"><label class="ignlab"><input type="checkbox" id="showIgnored" onchange="render()"> Show ignored scripts</label></div></div>
  <div id="view"></div>
</div>

<div class="film" id="film" role="dialog" aria-modal="true">
  <div class="filmbar"><span class="lab">Film mode</span><span class="filmtitle" id="filmTitle"></span><button class="filmclose" onclick="closeFilm()">Close &nbsp;esc</button></div>
  <div class="filmbody"><div class="in" id="filmBody"></div></div>
  <div class="filmfoot" id="filmFoot"></div>
</div>

<div class="toast" id="toast"></div>

<script>
const WEEKS = /*WEEKS_DATA*/;
const KEY = "outlier-radar-tracking";
let TAB = "dist";
let FILM_ID = null;
const track = JSON.parse(localStorage.getItem(KEY) || "{}");
function save(){localStorage.setItem(KEY, JSON.stringify(track));}
function t(id){return track[id] || {status:"idea", views:"", link:"", notes:"", carousel:false};}
function setT(id, patch){track[id] = Object.assign(t(id), patch); save(); render(); if(FILM_ID) syncFilmFoot();}
function toggleCarousel(id){setT(id,{carousel:!t(id).carousel}); toast(t(id).carousel?"Flagged for a carousel":"Carousel flag removed");}
function setTab(x){TAB=x; document.querySelectorAll(".tab").forEach(b=>b.classList.toggle("on", b.dataset.t===x)); render();}
function esc(s){return (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
function closeMenu(){const m=document.getElementById("exportMenu"); if(m) m.removeAttribute("open");}
document.addEventListener("click",e=>{const m=document.getElementById("exportMenu"); if(m&&m.hasAttribute("open")&&!m.contains(e.target)) m.removeAttribute("open");});

let toastTimer=null;
function toast(msg){
  const el=document.getElementById("toast"); el.textContent=msg; el.classList.add("show");
  clearTimeout(toastTimer); toastTimer=setTimeout(()=>el.classList.remove("show"), 2400);
}
function copyText(text, msg){
  const done=()=>toast(msg||"Copied");
  if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(text).then(done,()=>fallbackCopy(text,done));}
  else fallbackCopy(text,done);
}

function applyTheme(mode){
  if(mode==="dark") document.documentElement.setAttribute("data-theme","dark");
  else document.documentElement.removeAttribute("data-theme");
  const b=document.getElementById("themeBtn"); if(b) b.innerHTML = mode==="dark" ? "&#9728;" : "&#9790;";
  try{localStorage.setItem("yapcut-theme",mode);}catch(e){}
}
function toggleTheme(){ applyTheme(document.documentElement.getAttribute("data-theme")==="dark"?"light":"dark"); }

function officeOf(w){ return (w.office&&w.office.length)?w.office:(w.food||[]); }
function liPostsOf(w){ return (w.linkedin&&w.linkedin.length)?w.linkedin:(w.gtm_linkedin||[]); }
function poolCount(arr){return (arr||[]).filter(x=>{const s=t(x.id).status; return s!=="ignored"&&s!=="filmed"&&s!=="posted";}).length;}
function updateTabCounts(w){
  if(!w) return;
  const set=(c,n)=>{const e=document.querySelector('.cnt[data-c="'+c+'"]'); if(e) e.textContent=n?String(n):"";};
  const office=officeOf(w);
  const all=[].concat(w.distribution||[], office);
  set("dist", poolCount(w.distribution));
  set("office", poolCount(office));
  set("filmed", all.filter(x=>["filmed","posted"].includes(t(x.id).status)).length);
  set("linkedin", (w.distribution||[]).filter(x=>x.linkedin && t(x.id).status!=="ignored").length + liPostsOf(w).length);
  set("insp", (w.inspiration||[]).length);
}

function curWeek(){return WEEKS.find(w=>w.week===document.getElementById("weekSel").value) || WEEKS[0];}

function humanWeek(s){
  const d=new Date(s+"T00:00:00");
  if(isNaN(d)) return s;
  return d.toLocaleDateString("en-US",{month:"long",day:"numeric",year:"numeric"});
}

/* ---------------- exports (payload shapes are load-bearing downstream) ---------------- */
function exportFilmed(){
  const w=curWeek(); if(!w) return;
  const items=[].concat(w.distribution||[], officeOf(w)).filter(x=>t(x.id).status==="filmed");
  if(!items.length){alert("Nothing marked Filmed in this week yet.\n\nOn each video you shot, click 'Filmed', then export.");return;}
  let out=`FILMED THIS WEEK (week of ${w.week}) - ${items.length} clip(s). Edit each per its spec using the tiktok-yap-editor skill.\n\n`;
  items.forEach((x,i)=>{
    out+=`### ${i+1}. ${x.title||x.mechanic||x.text_hook}  [${x.id}]\n`;
    if(x.text_hook)   out+=`- TEXT HOOK (burn on screen, NOT spoken): ${x.text_hook}\n`;
    if(x.visual_hook) out+=`- VISUAL HOOK (show, first 1-2s): ${x.visual_hook}\n`;
    if(x.spoken_hook) out+=`- HOOK (say this, your opening 1-2 lines): ${x.spoken_hook}\n`;
    if(x.script)      out+=`- SCRIPT (read verbatim, follows the hook): ${x.script}\n`;
    if(x.directions)  out+=`- DIRECTIONS (do this, NOT spoken): ${x.directions}\n`;
    if(x.value)       out+=`- VALUE (the payoff to protect): ${x.value}\n`;
    if(x.cta)         out+=`- CTA (optional, say to end): ${x.cta}\n`;
    if(x.linkedin)    out+=`- LINKEDIN TWIN (post this version on LinkedIn if the video wins): ${x.linkedin.body.replace(/\n+/g,' ')}\n`;
    out+=`\n`;
  });
  window.__lastExport=out;
  copyText(out, `Copied ${items.length} filmed script(s). Paste into your editor session.`);
}
async function saveJson(json, fname, okMsg){
  if(window.showSaveFilePicker){
    try{
      const h=await window.showSaveFilePicker({suggestedName:fname, types:[{description:"JSON",accept:{"application/json":[".json"]}}]});
      const ws=await h.createWritable(); await ws.write(json); await ws.close();
      alert(okMsg); return true;
    }catch(e){ if(e.name==="AbortError") return false; }
  }
  const blob=new Blob([json],{type:"application/json"});
  const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download=fname;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(()=>URL.revokeObjectURL(a.href),2000);
  alert("Downloaded "+fname+".\n\n"+okMsg); return true;
}
async function exportForBlog(){
  const w=curWeek(); if(!w) return;
  const all=[].concat(w.distribution||[], officeOf(w));
  const items=all.filter(x=>["filmed","posted"].includes(t(x.id).status))
                 .map(x=>Object.assign({}, x, {tracking:t(x.id)}));
  if(!items.length){alert("Nothing marked Filmed or Posted in this week yet.\n\nMark the scripts you shot, then export.");return;}
  const payload={week:w.week, positioning:w.positioning||"", exported_at:new Date().toISOString(), items};
  await saveJson(JSON.stringify(payload,null,2), `blog-queue-${w.week}.json`,
    `Saved ${items.length} script(s) for the blog.\n\nKeep it in outlier-radar/blog-queue/ so the weekly routine finds it.`);
}
async function exportCarousels(){
  const w=curWeek(); if(!w) return;
  const all=[].concat(w.distribution||[], officeOf(w));
  const items=all.filter(x=>t(x.id).carousel);
  if(!items.length){alert("No scripts flagged for a carousel yet.\n\nClick 'Carousel' on any script card, then export.");return;}
  const payload={week:w.week, positioning:w.positioning||"", exported_at:new Date().toISOString(), items};
  await saveJson(JSON.stringify(payload,null,2), `carousel-queue-${w.week}.json`,
    `Saved ${items.length} script(s) to the carousel queue.\n\nSave it in outlier-radar/carousels/, then run:\n  python3 build_carousels.py\nto render the PDFs.`);
}
async function exportPerformance(){
  const weeksOut = WEEKS.map(w=>{
    const office=officeOf(w);
    const items=[].concat(w.distribution||[], office).map(x=>{
      const r=t(x.id);
      if(r.status==="idea" && !r.views && !r.notes && !r.link) return null;
      return {id:x.id, title:x.title||"", lane:office.includes(x)?"secondary":"primary",
              mechanic:x.mechanic||x.borrows||"", facet:x.facet||"", intent:x.intent||"",
              value:x.value||"", qa:x.qa||"", status:r.status, views:r.views||"",
              link:r.link||"", notes:r.notes||""};
    }).filter(Boolean);
    return items.length?{week:w.week, items}:null;
  }).filter(Boolean);
  if(!weeksOut.length){alert("No tracking logged yet.\n\nMark scripts Filmed or Posted and log views, then export. This file is what lets the next radar run learn from your results.");return;}
  const payload={exported_at:new Date().toISOString(), weeks:weeksOut};
  await saveJson(JSON.stringify(payload,null,2), `performance-${weeksOut[0].week}.json`,
    `Saved performance for ${weeksOut.length} week(s).\n\nSave it in your workspace's performance/ folder (default ~/outlier-radar/performance/) so the next radar run reads it and doubles down on what worked.`);
}
function fallbackCopy(text,cb){
  const ta=document.createElement("textarea");ta.value=text;document.body.appendChild(ta);ta.select();
  try{document.execCommand("copy");}catch(e){}
  document.body.removeChild(ta);cb&&cb();
}

/* ---------------- hero: brief + ring ---------------- */
function renderBrief(w){
  const el=document.getElementById("brief");
  document.getElementById("eyebrowTxt").textContent =
    String(w.week).toLowerCase()==="example" ? "Example week · sample data" : "Weekly slate · week of "+humanWeek(w.week);
  let extra="";
  if(w.method) extra+=`<div class="bx"><div class="lab">Method</div><p>${esc(w.method)}</p></div>`;
  if(w.coined_term&&w.coined_term.term) extra+=`<div class="bx"><div class="lab">Coined term · ${esc(w.coined_term.status||"")}</div><p><b>${esc(w.coined_term.term)}</b>. ${esc(w.coined_term.definition_beat||"")}</p></div>`;
  if(Array.isArray(w.signals)&&w.signals.length){
    extra+=`<div class="bx"><div class="lab">Signals this week</div>`+w.signals.map(s=>`<p><b>${esc(s.call||"")}</b> ${esc(s.shell||"")} ${s.your_version?"Your version: "+esc(s.your_version):""}</p>`).join("")+`</div>`;
  }
  el.innerHTML = (w.positioning?`<p class="briefclamp" id="briefTxt">${esc(w.positioning)}</p>`:"")
    + ((w.positioning||extra)?`<button class="brieftoggle" id="briefBtn" onclick="toggleBrief()">Read the brief</button>`:"")
    + (extra?`<div class="briefextra" id="briefExtra">${extra}</div>`:"");
}
function toggleBrief(){
  const txt=document.getElementById("briefTxt"), ex=document.getElementById("briefExtra"), b=document.getElementById("briefBtn");
  const open = txt ? txt.classList.toggle("open") : (ex && !ex.classList.contains("show"));
  if(ex) ex.classList.toggle("show", !!open);
  if(b) b.textContent = open ? "Collapse the brief" : "Read the brief";
}
function renderRing(w){
  const all=[].concat(w.distribution||[], officeOf(w)).filter(x=>t(x.id).status!=="ignored");
  const done=all.filter(x=>["filmed","posted"].includes(t(x.id).status)).length;
  const total=all.length||1;
  const R=44, C=2*Math.PI*R, off=C*(1-done/total);
  document.getElementById("ring").innerHTML =
    `<svg width="120" height="120" viewBox="0 0 120 120">
      <circle cx="60" cy="60" r="${R}" fill="none" stroke="var(--line)" stroke-width="7"/>
      <circle cx="60" cy="60" r="${R}" fill="none" stroke="var(--accent)" stroke-width="7" stroke-linecap="round"
        stroke-dasharray="${C}" stroke-dashoffset="${off}" transform="rotate(-90 60 60)" style="transition:stroke-dashoffset .5s ease"/>
      <text x="60" y="60" text-anchor="middle" dominant-baseline="central" class="rn">${done}/${all.length}</text>
      <text x="60" y="82" text-anchor="middle" class="rl">filmed</text>
    </svg>`;
}

/* ---------------- stats ---------------- */
function statsBar(){
  const w = curWeek(); if(!w) return;
  const dist=w.distribution||[], office=officeOf(w);
  let tofilm=0, filmed=0, posted=0, views=0, ignored=0;
  [].concat(dist, office).forEach(x=>{
    const s=t(x.id).status;
    if(s==="ignored") ignored++;
    else if(s==="posted"){posted++; views+=parseInt(t(x.id).views||0)||0;}
    else if(s==="filmed") filmed++;
    else tofilm++;
  });
  const isPool = x=>{const s=t(x.id).status; return s!=="ignored"&&s!=="filmed"&&s!=="posted";};
  const story = dist.filter(x=>isPool(x)&&x.intent==="storytelling").length;
  const edu   = dist.filter(x=>isPool(x)&&x.intent==="educational").length;
  const off   = office.filter(isPool).length;
  const tot   = story+edu+off;
  const seg=(v,cls)=>`<div class="${cls}" style="flex:${tot?(v||0.0001):1}"></div>`;
  const bar = `<div class="intentbar">${seg(story,'sga')}${seg(edu,'sgb')}${seg(off,'sgc')}</div>`
            + `<div class="barcap">story &middot; educational &middot; __SECONDARY_LABEL__</div>`;
  const cards=[
    {l:"To film", n:tofilm, extra:bar},
    {l:"Filmed", n:filmed, sub:"ready to post"},
    {l:"Posted", n:posted, sub:"live"},
    {l:"Views logged", n:views.toLocaleString("en-US"), sub:"across posted", accent:true},
    {l:"Ignored", n:ignored, sub:"skipped this week"},
  ];
  document.getElementById("stats").innerHTML = cards.map(c=>
    `<div class="stat"><div class="lab">${c.l}</div><div class="n${c.accent?' accent':''}">${c.n}</div>${c.extra||""}${c.sub?`<div class="sub">${c.sub}</div>`:""}</div>`).join("");
  renderRing(w);
}
function updateStats(){statsBar();}

/* ---------------- shared card pieces ---------------- */
function tracker(id, withLink, states){
  const r=t(id);
  const seg=(states||["idea","filmed","posted"]).map(s=>`<button data-s="${s}" class="${r.status===s?'on':''}" onclick="setT('${id}',{status:'${s}'})"><span class="sdot"></span>${s[0].toUpperCase()+s.slice(1)}</button>`).join("");
  return `<div class="track">
    <span class="seg">${seg}</span>
    <input class="views" type="number" placeholder="views I got" value="${esc(r.views)}" oninput="track['${id}']=Object.assign(t('${id}'),{views:this.value});save();updateStats()">
    ${withLink?`<input class="plink" placeholder="link to my posted video" value="${esc(r.link)}" oninput="track['${id}']=Object.assign(t('${id}'),{link:this.value});save()">`:""}
  </div>
  <textarea class="notes" placeholder="notes" oninput="track['${id}']=Object.assign(t('${id}'),{notes:this.value});save()">${esc(r.notes)}</textarea>`;
}

function block(label, val, boxCls){
  return val?`<div class="block"><div class="lab">${label}</div><div class="${boxCls||''}">${esc(val)}</div></div>`:"";
}

// split a spoken passage into sentences (one per line), without breaking on
// decimals ("1.76%") or lowercase abbreviations ("e.g.").
function splitSentences(text){
  if(!text) return [];
  return String(text).replace(/\s*\n+\s*/g," ")
    .split(/(?<=[.?!…])\s+(?=[A-Z"'‘“£$])/)
    .map(s=>s.trim()).filter(Boolean);
}
function readSections(x, sentCls, hookCls, secCls){
  function section(label, text, opt, bold){
    const lines=splitSentences(text);
    if(!lines.length) return "";
    const lab=`<div class="seclabel">${label}${opt?` <span class="opt">optional</span>`:""}</div>`;
    const body=lines.map(s=>`<p class="${sentCls}${bold?' '+hookCls:''}">${esc(s)}</p>`).join("");
    return `<div class="${secCls}">${lab}${body}</div>`;
  }
  return section("Hook", x.spoken_hook, false, true)
    + section("Script", x.script, false, false)
    + section("CTA", x.cta, true, false);
}
function readScript(x){
  const html=readSections(x, "sent", "hook", "scriptsec");
  if(!html.trim()) return "";
  return `<div class="block"><div class="lab">Read this out loud while recording</div><div class="readbox">${html}</div></div>`;
}

function shotTable(x){
  if(!Array.isArray(x.shot_list)||!x.shot_list.length) return "";
  const rows=x.shot_list.map(s=>`<tr><td class="bn">${esc(String(s.n!=null?s.n:""))}</td><td class="bmut">${esc(s.beat||"")}</td><td>${esc(s.shoot||"")}${s.url?` <a href="${esc(s.url)}" target="_blank">open &rarr;</a>`:""}</td></tr>`).join("");
  return `<div class="block"><div class="lab">Shot list · receipts to capture</div><div class="tblwrap"><table class="tbl"><thead><tr><th>#</th><th>Beat</th><th>Shoot this</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
}

// beats[] comes in two schemas:
//  - day-in-life-vo (Mode B): {role, text, b_roll, target_dur}
//  - no-VO format scripts: {t, on_screen, action} - captions carry the video
function beatsTable(x){
  if(!Array.isArray(x.beats)||!x.beats.length) return "";
  if(x.beats[0].on_screen!==undefined){
    const rows=x.beats.map(b=>`<tr><td class="bn">${esc(b.t)}</td><td>${esc(b.on_screen)||"<span class='bmut'>(no caption, face only)</span>"}</td><td class="bmut">${esc(b.action)}</td></tr>`).join("");
    return `<div class="block"><div class="lab">Beats · no-VO format, captions carry it</div><div class="tblwrap"><table class="tbl"><thead><tr><th>Time</th><th>On screen</th><th>Action</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
  }
  const rows=x.beats.map(b=>`<tr><td class="bn">${esc(b.role)}</td><td>${esc(b.text)}</td><td class="bmut">${esc(b.b_roll)}</td><td class="bmut">${b.target_dur?esc(String(b.target_dur))+"s":""}</td></tr>`).join("");
  return `<div class="block"><div class="lab">Beats · film these, VO to picture (editor Mode B)</div><div class="tblwrap"><table class="tbl"><thead><tr><th>Role</th><th>VO line</th><th>B-roll</th><th>Dur</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
}

function srcs(list){
  if(!list||!list.length) return "";
  const norm=list.map(s=> (typeof s==="string") ? {url:s, label:s.replace(/^https?:\/\/(www\.)?/,"").split("/")[0]} : s);
  const items=norm.map(s=> s.url?`<a href="${esc(s.url)}" target="_blank">${esc(s.label||s.url)}</a>`:esc(s.label)).join(`<span class="sep">&middot;</span>`);
  return `<div class="block"><div class="lab">Sources · check before posting</div><div class="srcs">${items}</div></div>`;
}

function captureLine(x){
  const c=x.capture; if(!c) return "";
  if(typeof c==="string") return `<p class="tinyline">capture: ${esc(c)}</p>`;
  const bits=[];
  if(c.mode) bits.push("capture: "+c.mode);
  if(c.fidelity!=null) bits.push("fidelity "+Math.round(c.fidelity*100)+"%");
  if(c.source) bits.push(c.source);
  return bits.length?`<p class="tinyline">${esc(bits.join(" · "))}</p>`:"";
}

function detailBlocks(x){
  let out = readScript(x)
    + shotTable(x)
    + beatsTable(x)
    + block("Directions · do this, do not read it", x.directions, "dirbox")
    + block("Value · what the viewer takes away", x.value, "valbox");
  // legacy fallback (pre-QA batches still on the old shape)
  if(!x.script && (x.hook || (x.beats&&!Array.isArray(x.beats)))){
    out = block("Hook (legacy)", x.hook, "readbox")
      + block("Script / beats (legacy, needs QA upgrade)", typeof x.beats==="string"?x.beats:x.script, "readbox")
      + out;
  }
  if(x.psych) out += `<div class="block"><div class="lab">Why this works</div><p class="psy">${esc(x.psych)}</p></div>`;
  if(x.note) out += `<div class="block"><div class="lab">Note</div><p class="psy">${esc(x.note)}</p></div>`;
  out += captureLine(x);
  if(x.source_origin) out += `<p class="tinyline">origin: ${esc(x.source_origin)}</p>`;
  out += srcs(x.sources);
  return out;
}

function chipRow(x, r){
  const chips=[];
  chips.push(x.qa==="passed" ? `<span class="chip qa">QA passed</span>` : `<span class="chip draft">Pre-QA</span>`);
  if(r.status==="posted") chips.push(`<span class="chip posted">Posted</span>`);
  if(x.post_type) chips.push(`<span class="chip">${esc(x.post_type)}</span>`);
  if(x.hook_family) chips.push(`<span class="chip">${esc(String(x.hook_family).replace(/^\d+\s*-\s*/,"").split("/")[0].trim())}</span>`);
  if(x.intent) chips.push(`<span class="chip">${esc(x.intent)}</span>`);
  if(x.script_class) chips.push(`<span class="chip">${esc(x.script_class)}</span>`);
  if(x.format) chips.push(`<span class="chip">${esc(x.format)}</span>`);
  if(x.sensitivity) chips.push(`<span class="chip sens">${esc(x.sensitivity)}</span>`);
  if(Array.isArray(x.hook_styles)) x.hook_styles.forEach(s=>chips.push(`<span class="chip">${esc(s)}</span>`));
  return chips.join("");
}

function scriptCard(x, isSecondLane, i){
  const r=t(x.id); const done=r.status==="posted";
  const title = x.title || x.mechanic || x.text_hook || "Untitled";
  const premise = (x.borrows||x.carries)
    ? `<p class="premise">${x.borrows?`<b>Borrows</b> ${esc(x.borrows)}`:""}${x.borrows&&x.carries?"<br>":""}${x.carries?`<b>Carries</b> ${esc(x.carries)}`:""}</p>`
    : (x.mechanic?`<p class="premise"><b>Mechanic</b> ${esc(x.mechanic)}</p>`:"");
  const alts = Array.isArray(x.text_hook_alts)&&x.text_hook_alts.length
    ? `<div class="alts">${x.text_hook_alts.map(a=>`<button class="alt" onclick="copyText(${JSON.stringify(a).replace(/"/g,'&quot;')},'Alt hook copied')" title="Alternate hook for hook testing. Click to copy.">${esc(a)}</button>`).join("")}</div>`:"";
  const hooks = (x.text_hook||x.visual_hook)?`<div class="hookgrid">
      ${x.text_hook?`<div class="hookcell"><div class="lab">Text hook · burn on screen</div><div class="burn">${esc(x.text_hook)}</div>${alts}</div>`:""}
      ${x.visual_hook?`<div class="hookcell"><div class="lab">Visual hook · show this</div><p>${esc(x.visual_hook)}</p></div>`:""}
    </div>`:"";
  const detail = detailBlocks(x);
  const hasDetail = detail.trim().length>0;
  const twin = (!isSecondLane && x.linkedin) ? `
    <div class="twin">
      <button class="btn ghost" onclick="const b=this.parentElement.querySelector('.twinwrap');b.classList.toggle('show');this.firstChild.textContent=b.classList.contains('show')?'Hide LinkedIn twin':'Show LinkedIn twin'"><span>Show LinkedIn twin</span></button>
      <div class="twinwrap collapse">
        <div class="twinbody">${esc(x.linkedin.body)}</div>
        <div class="twinmeta">
          <button class="btn" onclick="copyText(this.closest('.twin').querySelector('.twinbody').innerText,'LinkedIn twin copied')">Copy twin</button>
          ${visualBlock(x.linkedin.visual)}
        </div>
      </div>
    </div>`:"";
  return `<div class="card ${done?'done':''}">
    <div class="cardtop">
      <span class="idx">${String(i+1).padStart(2,"0")}</span>
      <div class="cardtitle">
        <h3 class="ttl">${esc(title)}</h3>
        <div class="chips">${chipRow(x,r)}</div>
      </div>
      <div class="cardops">
        <button class="btn ghost ${r.carousel?'on':''}" onclick="toggleCarousel('${x.id}')" title="Flag for a LinkedIn carousel PDF, then use Export &gt; Carousel queue">${r.carousel?'Carousel &#10003;':'Carousel'}</button>
        <button class="btn ghost" onclick="setT('${x.id}',{status:'${r.status==='ignored'?'idea':'ignored'}'})">${r.status==='ignored'?'Restore':'Ignore'}</button>
      </div>
    </div>
    ${premise}
    ${hooks}
    <div class="cardactions">
      ${hasDetail?`<button class="btn primary" onclick="openFilm('${x.id}')"><svg viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>Film mode</button>`:""}
      ${hasDetail?`<button class="btn" onclick="const c=this.closest('.card').querySelector('.detail');c.classList.toggle('show');this.lastChild.textContent=c.classList.contains('show')?'Hide full script':'Full script'"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/></svg><span>Full script</span></button>`:""}
      ${scriptText(x)?`<button class="btn" onclick="copyScript('${x.id}')" title="Copy the spoken read: hook + script + CTA"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy script</button>`:""}
    </div>
    ${hasDetail?`<div class="detail collapse">${detail}</div>`:""}
    ${twin}
    ${tracker(x.id, true)}
  </div>`;
}

function visualBlock(v){
  if(!v) return "";
  const meta=[v.format,v.model,v.aspect].filter(Boolean).map(esc).join(" · ");
  return `<div class="block" style="margin-top:14px"><div class="lab">Asset · ${meta}</div>${v.why?`<p class="psy">${esc(v.why)}</p>`:""}<div class="promptbox">${esc(v.prompt||"")}</div><button class="btn" style="margin-top:8px" onclick="copyText(this.previousElementSibling.innerText,'Higgsfield prompt copied')">Copy Higgsfield prompt</button></div>`;
}
const LI_STATES=["idea","scheduled","posted"];
function liCard(x, srcTitle, i){
  const r=t(x.id); const done=r.status==="posted";
  const title = srcTitle || x.title || x.type || "Post";
  const typeChip = (srcTitle||x.title) && x.type ? `<span class="chip">${esc(x.type)}</span>` : "";
  return `<div class="card ${done?'done':''}">
    <div class="cardtop">
      <span class="idx">${String(i+1).padStart(2,"0")}</span>
      <div class="cardtitle">
        <h3 class="ttl">${esc(title)}</h3>
        <div class="chips">${x.qa==="passed"?'<span class="chip qa">QA passed</span>':(x.qa?'<span class="chip draft">Pre-QA</span>':'')}${done?'<span class="chip posted">Posted</span>':''}${r.status==="scheduled"?'<span class="chip">Scheduled</span>':''}${typeChip}${x.hook_arch?`<span class="chip">${esc(x.hook_arch)}</span>`:""}</div>
      </div>
      <div class="cardops"><button class="btn" onclick="copyText(this.closest('.card').querySelector('.twinbody').innerText,'Post copied')">Copy post</button></div>
    </div>
    ${srcTitle?`<p class="premise"><b>Written twin of this week's video</b></p>`:""}
    <div class="twinbody" style="margin:14px 0 0 42px">${esc(x.body)}</div>
    <div style="margin-left:42px">${visualBlock(x.visual)}${srcs(x.sources)?`<div style="margin-top:14px">${srcs(x.sources)}</div>`:""}</div>
    ${tracker(x.id, true, LI_STATES)}
  </div>`;
}

function inspCard(x){
  return `<div class="insp">
    <div class="who">${esc(x.creator)}</div>
    <div class="met">${esc(x.metric)}${x.metric_confidence?` <span class="chip" style="vertical-align:1px">${esc(x.metric_confidence)}</span>`:""}</div>
    <div class="mech">${esc(x.mechanic)}</div>
    <div style="display:flex;justify-content:space-between;align-items:center;margin-top:2px"><span class="chip">${esc(x.platform)}</span><a href="${esc(x.link)}" target="_blank">Open &rarr;</a></div>
  </div>`;
}

function emptyState(msg){
  return `<div class="empty"><div class="lab">Nothing here</div><p>${msg}</p></div>`;
}

/* ---------------- film mode ---------------- */
function findItem(id){
  const w=curWeek(); if(!w) return null;
  return [].concat(w.distribution||[], officeOf(w)).find(x=>x.id===id) || null;
}
// the spoken read as plain text: hook + script + optional CTA. Skips the hook
// when the script already opens with it (most weeks duplicate that line).
function scriptText(x){
  const parts=[];
  const hook=(x.spoken_hook||"").trim(), script=(x.script||"").trim();
  if(hook && !script.startsWith(hook)) parts.push(hook);
  if(script) parts.push(script);
  if(!script){
    if(!hook && x.hook) parts.push(String(x.hook).trim());
    if(typeof x.beats==="string") parts.push(x.beats.trim());
  }
  if(x.cta) parts.push(String(x.cta).trim());
  return parts.filter(Boolean).join("\n\n");
}
function copyScript(id){
  const x=findItem(id); if(!x) return;
  const txt=scriptText(x); if(!txt){toast("No script text on this one");return;}
  copyText(txt, "Script copied");
}
function openFilm(id){
  const x=findItem(id); if(!x) return;
  FILM_ID=id;
  document.getElementById("filmTitle").textContent = x.title || x.mechanic || x.text_hook || "Untitled";
  let body="";
  if(x.text_hook) body+=`<div class="filmburn">${esc(x.text_hook)}</div><p class="filmburncap">Burned on screen · not spoken</p>`;
  const read=readSections(x, "fsent", "fhook", "fsec");
  body+= read || "";
  let extra = shotTable(x) + beatsTable(x)
    + block("Directions · do this, do not read it", x.directions, "dirbox")
    + block("Value · the payoff to protect", x.value, "valbox");
  if(extra.trim()) body+=`<div class="fextra">${extra}</div>`;
  document.getElementById("filmBody").innerHTML=body;
  syncFilmFoot();
  document.getElementById("film").classList.add("show");
  document.body.style.overflow="hidden";
  document.querySelector(".filmbody").scrollTop=0;
}
function syncFilmFoot(){
  if(!FILM_ID) return;
  const s=t(FILM_ID).status;
  document.getElementById("filmFoot").innerHTML =
    s==="posted" ? `<button class="btn" disabled>Posted &#10003;</button>`
    : s==="filmed"
      ? `<button class="btn accent" onclick="setT('${FILM_ID}',{status:'posted'});toast('Marked posted')">Mark as posted</button><button class="btn" onclick="setT('${FILM_ID}',{status:'idea'})">Back to idea</button>`
      : `<button class="btn primary" onclick="setT('${FILM_ID}',{status:'filmed'});toast('Marked filmed')">Mark as filmed</button>`;
}
function closeFilm(){
  FILM_ID=null;
  document.getElementById("film").classList.remove("show");
  document.body.style.overflow="";
}
document.addEventListener("keydown",e=>{ if(e.key==="Escape"&&FILM_ID) closeFilm(); });

/* ---------------- main render ---------------- */
function render(){
  const w=curWeek(); if(!w){document.getElementById("view").innerHTML=emptyState("No week data yet. Run the radar to generate your first slate.");return;}
  renderBrief(w);
  statsBar();
  updateTabCounts(w);
  const showIgn = document.getElementById("showIgnored") && document.getElementById("showIgnored").checked;
  document.getElementById("ignrow").style.display = (TAB==="dist"||TAB==="office")?"block":"none";
  const pool = arr => showIgn
    ? arr.filter(x=>t(x.id).status==="ignored")
    : arr.filter(x=>{const s=t(x.id).status; return s!=="ignored"&&s!=="filmed"&&s!=="posted";});
  const office = officeOf(w);
  let html="", empty="Nothing here this week.";
  if(TAB==="dist"){ html=pool(w.distribution||[]).map((x,i)=>scriptCard(x,false,i)).join(""); empty=showIgn?"No ignored scripts.":"Nothing left to film in this lane. Everything is filmed, posted, or ignored."; }
  else if(TAB==="office"){ html=pool(office).map((x,i)=>scriptCard(x,true,i)).join(""); empty=showIgn?"No ignored scripts.":"Nothing left to film in this lane. Everything is filmed, posted, or ignored."; }
  else if(TAB==="filmed"){ const items=[].concat(w.distribution||[], office).filter(x=>["filmed","posted"].includes(t(x.id).status)); html=items.map((x,i)=>scriptCard(x, office.includes(x), i)).join(""); empty="Nothing filmed yet. Mark a script Filmed and it lands here for metric tracking."; }
  else if(TAB==="linkedin"){
    const gtm = liPostsOf(w).filter(x=>t(x.id).status!=="ignored").map((x,i)=>liCard(x, "", i));
    const twinSrc = (w.distribution||[]).filter(x=>x.linkedin && t(x.id).status!=="ignored");
    const twins = twinSrc.map((x,i)=>liCard(x.linkedin, x.title, i));
    html = (gtm.length?`<div class="sechdr">__LEADERS_HDR__</div>`+gtm.join(""):"")
         + (twins.length?`<div class="sechdr">Twins of this week's videos</div>`+twins.join(""):"");
    empty="No LinkedIn posts this week.";
  }
  else if(TAB==="insp"){ const cards=(w.inspiration||[]).map(inspCard).join(""); html=cards?`<div class="inspgrid">${cards}</div>`:""; empty="No viral inspiration logged this week."; }
  document.getElementById("view").innerHTML = html || emptyState(empty);
}

(function init(){
  let savedTheme=null; try{savedTheme=localStorage.getItem("yapcut-theme");}catch(e){}
  if(!savedTheme) savedTheme=(window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches)?"light":"dark";
  applyTheme(savedTheme);
  const sel=document.getElementById("weekSel");
  sel.innerHTML = WEEKS.map(w=>`<option value="${w.week}">${String(w.week).toLowerCase()==="example"?"Example week (sample data)":"Week of "+w.week}</option>`).join("");
  render();
})();
</script>
</body>
</html>"""

out = (HTML.replace("/*WEEKS_DATA*/", DATA)
           .replace("__PRIMARY_LABEL__", PRIMARY_LABEL)
           .replace("__SECONDARY_LABEL__", SECONDARY_LABEL)
           .replace("__LEADERS_HDR__", LEADERS_HDR)
           .replace("__BYLINE__", BYLINE)
           .replace("__PARTNER__", PARTNER_HTML)
           .replace("__FONT_IMPORT__", FONT_IMPORT)
           .replace("__C_BG__", C_BG)
           .replace("__C_INK__", C_INK)
           .replace("__C_ACCENT__", C_ACCENT)
           .replace("__ACCENT_TEXT_DARK__", ACCENT_TEXT_DARK)
           .replace("__ACCENT_TEXT__", ACCENT_TEXT)
           .replace("__ACCENT_RGB__", ACCENT_RGB)
           .replace("__F_DISPLAY__", F_DISPLAY)
           .replace("__F_BODY__", F_BODY)
           .replace("__F_MONO__", F_MONO))
dest = os.path.join(WS, "dashboard.html")
open(dest, "w").write(out)
print(f"wrote {dest} from {len(weeks)} week(s)")

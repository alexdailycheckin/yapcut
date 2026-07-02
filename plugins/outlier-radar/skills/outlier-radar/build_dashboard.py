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
# two lanes. Defaults to the generic labels so it works with no config at all.
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
BYLINE = CFG.get("byline") or "by alexmuresan.com"
# optional "in partnership with X" pill in the header (empty = hidden)
PARTNER = (CFG.get("partner") or "").strip()
PARTNER_HTML = (f'<span class="partner">in partnership with <b>{PARTNER}</b></span>'
                if PARTNER else "")

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
  :root{
    --bg:#f6f7f9; --card:#ffffff; --ink:#16191d; --muted:#6b7280;
    --line:#e6e8eb; --accent:#0f766e; --accent-soft:#e6f3f1;
    --idea:#9ca3af; --filmed:#2563eb; --posted:#0f766e; --shadow:0 1px 2px rgba(16,25,40,.05),0 4px 16px rgba(16,25,40,.04);
  }
  *{box-sizing:border-box}
  body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;-webkit-font-smoothing:antialiased}
  .wrap{max-width:980px;margin:0 auto;padding:32px 20px 80px}
  header h1{font-size:26px;margin:0 0 2px;letter-spacing:-.02em}
  header p{margin:0;color:var(--muted)}
  .topbar{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap}
  select{font:inherit;padding:8px 12px;border:1px solid var(--line);border-radius:10px;background:#fff;color:var(--ink)}
  .stats{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin:22px 0 8px}
  .stat{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;box-shadow:var(--shadow)}
  .stat .n{font-size:24px;font-weight:680;letter-spacing:-.02em}
  .stat .l{font-size:12px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em}
  .tabs{display:flex;gap:6px;margin:24px 0 16px;border-bottom:1px solid var(--line)}
  .tab{padding:10px 14px;border:0;background:none;font:inherit;color:var(--muted);cursor:pointer;border-bottom:2px solid transparent;margin-bottom:-1px}
  .tab.on{color:var(--ink);border-bottom-color:var(--accent);font-weight:600}
  .card{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:18px;margin-bottom:14px;box-shadow:var(--shadow)}
  .card.done{opacity:.62}
  .ttl{font-size:17px;font-weight:650;margin:0 0 6px;letter-spacing:-.01em}
  .meta{font-size:12.5px;color:var(--muted);margin:0 0 10px}
  .meta b{color:#374151;font-weight:600}
  .hook{font-size:15.5px;font-weight:600;margin:0 0 8px}
  .body{white-space:pre-wrap;color:#2b3036;font-size:14.5px;margin:0 0 12px;display:none}
  .body.show{display:block}
  .link{color:var(--accent);text-decoration:none;font-size:13px}
  .link:hover{text-decoration:underline}
  .row{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-top:10px}
  .seg{display:inline-flex;border:1px solid var(--line);border-radius:10px;overflow:hidden}
  .seg button{border:0;background:#fff;padding:7px 12px;font:inherit;font-size:13px;color:var(--muted);cursor:pointer}
  .seg button.on[data-s="idea"]{background:var(--idea);color:#fff}
  .seg button.on[data-s="filmed"]{background:var(--filmed);color:#fff}
  .seg button.on[data-s="posted"]{background:var(--posted);color:#fff}
  input.views{width:110px;padding:7px 10px;border:1px solid var(--line);border-radius:10px;font:inherit;font-size:13px}
  input.plink{flex:1;min-width:160px;padding:7px 10px;border:1px solid var(--line);border-radius:10px;font:inherit;font-size:13px}
  textarea.notes{width:100%;margin-top:8px;padding:8px 10px;border:1px solid var(--line);border-radius:10px;font:inherit;font-size:13px;resize:vertical;min-height:34px}
  .btn{border:1px solid var(--line);background:#fff;border-radius:9px;padding:6px 11px;font:inherit;font-size:12.5px;cursor:pointer;color:#374151}
  .btn:hover{background:var(--accent-soft);border-color:var(--accent)}
  .btn.on{background:var(--accent);color:#fff;border-color:var(--accent)}
  .btn.on:hover{background:var(--accent);color:#fff}
  .toggle{cursor:pointer;color:var(--accent);font-size:12.5px;background:none;border:0;padding:0;font:inherit}
  .pill{font-size:11px;padding:2px 8px;border-radius:999px;background:#eef1f4;color:#4b5563;font-weight:600}
  .hide{display:none}
  .cardhead{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:6px}
  .badge{font-size:10.5px;font-weight:700;letter-spacing:.04em;padding:2px 8px;border-radius:999px;text-transform:uppercase}
  .badge.ready{background:#dcfce7;color:#166534}
  .badge.draft{background:#f1f5f9;color:#64748b}
  .block{margin:9px 0}
  .label{font-size:10.5px;font-weight:700;letter-spacing:.05em;color:var(--muted);text-transform:uppercase;margin-bottom:3px}
  .val{font-size:14.5px}
  .hookblk .val{font-weight:600;font-size:15px}
  .readbox .val{background:#eef5f4;border-left:3px solid var(--posted);padding:12px 14px;border-radius:8px;line-height:1.5}
  .readbox .scriptsec{margin:0 0 14px}
  .readbox .scriptsec:last-child{margin-bottom:0}
  .readbox .seclabel{font-size:10px;font-weight:800;letter-spacing:.13em;text-transform:uppercase;color:var(--muted);margin:0 0 5px}
  .readbox .seclabel .opt{font-weight:500;letter-spacing:0;text-transform:none;font-style:italic;opacity:.75}
  .readbox .sent{margin:0 0 7px}
  .readbox .sent:last-child{margin-bottom:0}
  .readbox .sent.hook{font-weight:800;font-size:16px;line-height:1.35}
  .dirbox .val{background:#f4f5f7;border-left:3px dashed #94a3b8;padding:10px 13px;border-radius:8px;white-space:pre-wrap;color:#475569;font-style:italic}
  .valblk .val{background:#f0faf3;border-left:3px solid #16a34a;padding:9px 12px;border-radius:8px}
  .ctablk .val{background:#eef3fb;border-left:3px solid #2563eb;padding:9px 12px;border-radius:8px}
  .collapse{display:none}
  .collapse.show{display:block}
  @media(max-width:680px){.stats{grid-template-columns:repeat(2,1fr)}}
</style>
<style>
  /* ---- YapCut design: dark theme (imported from the Claude Design) ---- */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Geist+Mono:wght@400;500;600&display=swap');
  :root{
    --bg:#141414; --card:#0f0f0f; --surface2:#191919; --ink:#f7f7f7; --muted:#a3a3a3; --dim:#d6d6d6;
    --line:#242424; --line-strong:#424242; --accent:#15b79e; --accent-deep:#107569; --accent-soft:rgba(21,183,158,.15);
    --idea:#5b5b5b; --filmed:#0ba5ec; --posted:#15b79e;
    --read-bg:#122120; --dir-bg:#181818; --val-bg:#0f1f16; --cta-bg:#101a24;
    --chip-bg:#242424; --chip-ink:#c9c9c9; --badge-ready-bg:rgba(21,183,158,.16); --badge-ready-ink:#5fe0c9;
    --badge-draft-bg:#242424; --badge-draft-ink:#9a9a9a; --input-bg:#141414; --seg-bg:#141414;
    --shadow:0 1px 2px rgba(0,0,0,.5);
    --font:'Inter',-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;
    --mono:'Geist Mono',ui-monospace,"SF Mono",Menlo,monospace;
  }
  :root[data-theme="light"]{
    --bg:#f6f7f9; --card:#ffffff; --surface2:#eef0f3; --ink:#16191d; --muted:#6b7280; --dim:#374151;
    --line:#e6e8eb; --line-strong:#d3d8de; --accent:#0f766e; --accent-deep:#0f766e; --accent-soft:#e6f3f1;
    --idea:#9ca3af; --filmed:#2563eb; --posted:#0f766e;
    --read-bg:#eef5f4; --dir-bg:#f4f5f7; --val-bg:#f0faf3; --cta-bg:#eef3fb;
    --chip-bg:#eef1f4; --chip-ink:#4b5563; --badge-ready-bg:#dcfce7; --badge-ready-ink:#166534;
    --badge-draft-bg:#f1f5f9; --badge-draft-ink:#64748b; --input-bg:#ffffff; --seg-bg:#ffffff;
    --shadow:0 1px 2px rgba(16,25,40,.05),0 4px 16px rgba(16,25,40,.04);
  }
  body{background:var(--bg);color:var(--ink);font-family:var(--font)}
  .wrap{max-width:1120px}
  /* brand bar */
  .brandbar{display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;padding:2px 0 22px;border-bottom:1px solid var(--line);margin-bottom:26px}
  .brand{display:flex;align-items:center;gap:12px}
  .logo{width:38px;height:38px;border-radius:10px;background:var(--accent-deep);display:grid;place-items:center;flex:none}
  .brandname{font-size:18px;font-weight:800;letter-spacing:-.01em}
  .byline{font-size:14px;color:var(--muted);font-weight:500}
  .brandright{display:flex;align-items:center;gap:10px}
  .partner{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);border:1px solid var(--line-strong);border-radius:999px;padding:6px 12px}
  .partner b{color:var(--ink);font-weight:700}
  .themetoggle{width:38px;height:38px;border-radius:10px;border:1px solid var(--line-strong);background:var(--card);color:var(--ink);cursor:pointer;font-size:16px;line-height:1}
  .themetoggle:hover{border-color:var(--accent)}
  /* hero */
  .eyebrow{display:inline-flex;align-items:center;gap:8px;font-family:var(--mono);font-size:12px;font-weight:600;letter-spacing:.14em;text-transform:uppercase;color:var(--accent)}
  .eyebrow .dot{width:7px;height:7px;border-radius:50%;background:var(--accent)}
  h1{font-size:36px;font-weight:700;letter-spacing:-.02em;margin:12px 0 0;color:var(--ink)}
  .sub{color:var(--muted);max-width:700px;margin:10px 0 0;font-size:15px;line-height:1.5}
  .actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:20px 0 0}
  /* buttons + select */
  .btn{background:var(--card);color:var(--dim);border:1px solid var(--line-strong);border-radius:8px;padding:8px 13px}
  .btn:hover{background:var(--accent-soft);border-color:var(--accent);color:var(--ink)}
  .btn.on,.btn.on:hover{background:var(--accent);border-color:var(--accent);color:#04120f}
  select{background:var(--card);color:var(--ink);border:1px solid var(--line-strong);border-radius:8px}
  /* stats */
  .stats{margin:26px 0 8px}
  .stat{background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow)}
  .stat .n{color:var(--ink);font-size:30px;font-weight:600;letter-spacing:-.02em}
  .stat .l{color:var(--muted);font-family:var(--mono);font-size:11px;letter-spacing:.06em}
  /* tabs as pills with count badges */
  .tabs{border-bottom:0;gap:6px;flex-wrap:wrap;margin:28px 0 18px}
  .tab{display:inline-flex;align-items:center;gap:8px;border:0;border-bottom:0;margin-bottom:0;border-radius:8px;padding:9px 13px;color:var(--muted);font-weight:600}
  .tab:hover{color:var(--ink)}
  .tab.on{background:var(--surface2);color:var(--ink);border-bottom:0;box-shadow:inset 0 0 0 1px var(--line-strong)}
  .tab .cnt{font-size:11px;font-weight:700;padding:1px 7px;border-radius:999px;background:var(--chip-bg);color:var(--muted)}
  .tab.on .cnt{background:var(--accent);color:#04120f}
  .tab .cnt:empty{display:none}
  /* cards + panels */
  .card{background:var(--card);border:1px solid var(--line);border-radius:12px;box-shadow:var(--shadow)}
  .ttl{color:var(--ink)}
  .meta{color:var(--muted)} .meta b{color:var(--dim)}
  .pill{background:var(--chip-bg);color:var(--chip-ink)}
  .badge.ready{background:var(--badge-ready-bg);color:var(--badge-ready-ink)}
  .badge.draft{background:var(--badge-draft-bg);color:var(--badge-draft-ink)}
  .label{font-family:var(--mono);color:var(--muted)}
  .readbox .val{background:var(--read-bg);border-left-color:var(--accent-deep)}
  .readbox .sent.hook{color:var(--ink)}
  .dirbox .val{background:var(--dir-bg);border-left-color:var(--line-strong);color:var(--muted)}
  .valblk .val{background:var(--val-bg);border-left-color:var(--posted)}
  .ctablk .val{background:var(--cta-bg);border-left-color:var(--filmed)}
  .body{color:var(--dim)}
  .link{color:var(--accent)}
  /* inputs + segmented control */
  .seg{border-color:var(--line-strong)}
  .seg button{background:var(--seg-bg);color:var(--muted)}
  .seg button.on[data-s="idea"]{background:var(--idea);color:#fff}
  .seg button.on[data-s="filmed"]{background:var(--filmed);color:#fff}
  .seg button.on[data-s="posted"]{background:var(--posted);color:#04120f}
  input.views,input.plink,textarea.notes{background:var(--input-bg);color:var(--ink);border-color:var(--line-strong)}
  input.views::placeholder,input.plink::placeholder,textarea.notes::placeholder{color:var(--muted)}
  .toggle{color:var(--accent)}
  /* icons in buttons + tabs */
  .btn{display:inline-flex;align-items:center;gap:7px}
  .btn svg{width:15px;height:15px;flex:none}
  .tab .ti{width:15px;height:15px;flex:none}
  /* header partner mark */
  .partner .pmark{border-radius:6px;display:block;flex:none}
  /* stat internals: label on top, number, then bar/sublabel */
  .stat{display:flex;flex-direction:column}
  .stat .l{margin:0 0 8px}
  .stat .n{margin:0;font-size:30px}
  .stat .n.accent{color:var(--accent)}
  .stat .sub{font-size:12.5px;color:var(--muted);margin-top:auto;padding-top:12px}
  .intentbar{display:flex;gap:4px;margin:14px 0 8px}
  .intentbar>div{height:5px;border-radius:3px;min-width:4px}
  .sga{background:var(--accent)} .sgb{background:var(--filmed)} .sgc{background:#ee46bc}
  .barcap{font-size:12px;color:var(--muted)}
  /* two-column hook row (text hook | visual hook), like the design */
  .hookgrid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:10px 0}
  .hookgrid .block{margin:0}
  @media(max-width:680px){.hookgrid{grid-template-columns:1fr}}
  /* beats table (day-in-life-vo scripts) */
  .beatswrap{background:var(--dir-bg);border-left:3px solid var(--accent-deep);padding:10px 13px;border-radius:8px;overflow-x:auto}
  .beats{width:100%;border-collapse:collapse;font-size:13.5px}
  .beats th{text-align:left;font-family:var(--mono);font-size:10.5px;text-transform:uppercase;letter-spacing:.05em;color:var(--muted);padding:4px 12px 4px 0}
  .beats td{padding:6px 12px 6px 0;border-top:1px solid var(--line);vertical-align:top}
  .beats td.bmut{color:var(--muted)}
  .beats td.brole{font-family:var(--mono);font-size:11px;text-transform:uppercase;color:var(--accent);white-space:nowrap}
</style>
</head>
<body>
<div class="wrap">
  <div class="brandbar">
    <div class="brand">
      <div class="logo"><svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="9" width="3" height="10" rx="1.5" fill="#fff"/><rect x="10.5" y="4" width="3" height="16" rx="1.5" fill="#fff"/><rect x="17.5" y="11" width="3" height="8" rx="1.5" fill="#fff"/></svg></div>
      <div><span class="brandname">YapCut</span> <span class="byline">__BYLINE__</span></div>
    </div>
    <div class="brandright">__PARTNER__<button class="themetoggle" id="themeBtn" onclick="toggleTheme()" title="Toggle light / dark" aria-label="Toggle theme">&#9790;</button></div>
  </div>
  <div class="hero">
    <div class="eyebrow"><span class="dot"></span> Weekly content batch</div>
    <h1>This week to film</h1>
    <p id="sub" class="sub"></p>
    <div class="actions">
      <button class="btn" onclick="exportFilmed()" title="Copy every script you marked Filmed, with its edit spec, to paste into the editor session"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><path d="M7 10l5 5 5-5"></path><path d="M12 15V3"></path></svg>Export filmed scripts</button>
      <button class="btn" onclick="exportForBlog()" title="Save everything you marked Filmed or Posted this week to a JSON file the weekly routine turns into an AEO blog post"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"></path><path d="M16 6l-4-4-4 4"></path><path d="M12 2v13"></path></svg>Export week for blog</button>
      <button class="btn" onclick="exportCarousels()" title="Save every script you flagged 'Carousel' to a queue file, then run build_carousels.py to render branded LinkedIn carousel PDFs"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 2 9 5-9 5-9-5 9-5Z"></path><path d="m3 12 9 5 9-5"></path></svg>Export carousel queue</button>
      <button class="btn" onclick="exportPerformance()" title="Save everything you tracked (status, views, notes) across all weeks so the next radar run learns what worked"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"></path><path d="m19 9-5 5-4-4-3 3"></path></svg>Export performance</button>
      <select id="weekSel" onchange="render()"></select>
    </div>
  </div>
  <div class="stats" id="stats"></div>
  <div class="tabs">
    <button class="tab on" data-t="dist" onclick="setTab('dist')"><svg class="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="6" width="14" height="12" rx="2"></rect><path d="m22 8-6 4 6 4V8Z"></path></svg>__PRIMARY_LABEL__ <span class="cnt" data-c="dist"></span></button>
    <button class="tab" data-t="office" onclick="setTab('office')"><svg class="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"></path></svg>__SECONDARY_LABEL__ <span class="cnt" data-c="office"></span></button>
    <button class="tab" data-t="filmed" onclick="setTab('filmed')"><svg class="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 3v18h18"></path><path d="M8 17v-4"></path><path d="M13 17V8"></path><path d="M18 17v-7"></path></svg>Filmed &amp; metrics <span class="cnt" data-c="filmed"></span></button>
    <button class="tab" data-t="linkedin" onclick="setTab('linkedin')"><svg class="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>LinkedIn posts <span class="cnt" data-c="linkedin"></span></button>
    <button class="tab" data-t="insp" onclick="setTab('insp')"><svg class="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12 3-1.9 5.8a2 2 0 0 1-1.3 1.3L3 12l5.8 1.9a2 2 0 0 1 1.3 1.3L12 21l1.9-5.8a2 2 0 0 1 1.3-1.3L21 12l-5.8-1.9a2 2 0 0 1-1.3-1.3z"></path></svg>Viral inspiration <span class="cnt" data-c="insp"></span></button>
  </div>
  <div id="ignrow" style="margin:-6px 0 14px;display:none"><label style="font-size:13px;color:var(--muted);cursor:pointer"><input type="checkbox" id="showIgnored" onchange="render()" style="vertical-align:middle"> show ignored scripts</label></div>
  <div id="view"></div>
</div>
<script>
const WEEKS = /*WEEKS_DATA*/;
const KEY = "outlier-radar-tracking";
let TAB = "dist";
const track = JSON.parse(localStorage.getItem(KEY) || "{}");
function save(){localStorage.setItem(KEY, JSON.stringify(track));}
function t(id){return track[id] || {status:"idea", views:"", link:"", notes:"", carousel:false};}
function setT(id, patch){track[id] = Object.assign(t(id), patch); save(); render();}
function toggleCarousel(id){setT(id,{carousel:!t(id).carousel});}
function setTab(x){TAB=x; document.querySelectorAll(".tab").forEach(b=>b.classList.toggle("on", b.dataset.t===x)); render();}
function esc(s){return (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}

function applyTheme(mode){
  if(mode==="light") document.documentElement.setAttribute("data-theme","light");
  else document.documentElement.removeAttribute("data-theme");
  const b=document.getElementById("themeBtn"); if(b) b.innerHTML = mode==="light" ? "&#9728;" : "&#9790;";
  try{localStorage.setItem("yapcut-theme",mode);}catch(e){}
}
function toggleTheme(){ applyTheme(document.documentElement.getAttribute("data-theme")==="light"?"dark":"light"); }

function poolCount(arr){return (arr||[]).filter(x=>{const s=t(x.id).status; return s!=="ignored"&&s!=="filmed"&&s!=="posted";}).length;}
function updateTabCounts(w){
  if(!w) return;
  const set=(c,n)=>{const e=document.querySelector('.cnt[data-c="'+c+'"]'); if(e) e.textContent=n?String(n):"";};
  const all=[].concat(w.distribution||[], w.office||[]);
  set("dist", poolCount(w.distribution));
  set("office", poolCount(w.office));
  set("filmed", all.filter(x=>["filmed","posted"].includes(t(x.id).status)).length);
  set("linkedin", (w.distribution||[]).filter(x=>x.linkedin && t(x.id).status!=="ignored").length + (w.linkedin||w.gtm_linkedin||[]).length);
  set("insp", (w.inspiration||[]).length);
}

function curWeek(){return WEEKS.find(w=>w.week===document.getElementById("weekSel").value) || WEEKS[0];}

function exportFilmed(){
  const w=curWeek(); if(!w) return;
  const items=[].concat(w.distribution||[], w.office||[]).filter(x=>t(x.id).status==="filmed");
  if(!items.length){alert("Nothing marked Filmed in this week yet.\\n\\nOn each video you shot, click the 'Filmed' button, then export.");return;}
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
  const done=()=>alert(`Copied ${items.length} filmed script(s) to your clipboard.\\n\\nPaste it into your editor session, then drop in the matching video files.`);
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(out).then(done,()=>fallbackCopy(out,done));
  } else { fallbackCopy(out,done); }
}
async function exportForBlog(){
  const w=curWeek(); if(!w) return;
  const all=[].concat(w.distribution||[], w.office||[]);
  const items=all.filter(x=>["filmed","posted"].includes(t(x.id).status))
                 .map(x=>Object.assign({}, x, {tracking:t(x.id)}));
  if(!items.length){alert("Nothing marked Filmed or Posted in this week yet.\\n\\nMark the scripts you shot, then export.");return;}
  const payload={week:w.week, positioning:w.positioning||"", exported_at:new Date().toISOString(), items};
  const json=JSON.stringify(payload,null,2);
  const fname=`blog-queue-${w.week}.json`;
  if(window.showSaveFilePicker){
    try{
      const h=await window.showSaveFilePicker({suggestedName:fname, types:[{description:"JSON",accept:{"application/json":[".json"]}}]});
      const ws=await h.createWritable(); await ws.write(json); await ws.close();
      alert(`Saved ${items.length} script(s) for the blog.\\n\\nKeep it in outlier-radar/blog-queue/ so the weekly routine finds it.`);
      return;
    }catch(e){ if(e.name==="AbortError") return; }
  }
  const blob=new Blob([json],{type:"application/json"});
  const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download=fname;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(()=>URL.revokeObjectURL(a.href),2000);
  alert(`Downloaded ${fname} (${items.length} script(s)).\\n\\nMove it into outlier-radar/blog-queue/ so the weekly routine finds it.`);
}
async function exportCarousels(){
  const w=curWeek(); if(!w) return;
  const all=[].concat(w.distribution||[], w.office||[]);
  const items=all.filter(x=>t(x.id).carousel);
  if(!items.length){alert("No scripts flagged for a carousel yet.\\n\\nClick the 'Carousel' button on any script card, then export.");return;}
  const payload={week:w.week, positioning:w.positioning||"", exported_at:new Date().toISOString(), items};
  const json=JSON.stringify(payload,null,2);
  const fname=`carousel-queue-${w.week}.json`;
  const note=`\\n\\nSave it in outlier-radar/carousels/, then run:\\n  python3 build_carousels.py\\nto render the PDFs.`;
  if(window.showSaveFilePicker){
    try{
      const h=await window.showSaveFilePicker({suggestedName:fname, types:[{description:"JSON",accept:{"application/json":[".json"]}}]});
      const ws=await h.createWritable(); await ws.write(json); await ws.close();
      alert(`Saved ${items.length} script(s) to the carousel queue.`+note);
      return;
    }catch(e){ if(e.name==="AbortError") return; }
  }
  const blob=new Blob([json],{type:"application/json"});
  const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download=fname;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(()=>URL.revokeObjectURL(a.href),2000);
  alert(`Downloaded ${fname} (${items.length} script(s)).`+note);
}
async function exportPerformance(){
  const weeksOut = WEEKS.map(w=>{
    const office=w.office||[];
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
  if(!weeksOut.length){alert("No tracking logged yet.\\n\\nMark scripts Filmed or Posted and log views, then export. This file is what lets the next radar run learn from your results.");return;}
  const payload={exported_at:new Date().toISOString(), weeks:weeksOut};
  const json=JSON.stringify(payload,null,2);
  const latest=weeksOut[0].week;
  const fname=`performance-${latest}.json`;
  const note=`\\n\\nSave it in your workspace's performance/ folder (default ~/outlier-radar/performance/) so the next radar run reads it and doubles down on what worked.`;
  if(window.showSaveFilePicker){
    try{
      const h=await window.showSaveFilePicker({suggestedName:fname, types:[{description:"JSON",accept:{"application/json":[".json"]}}]});
      const ws=await h.createWritable(); await ws.write(json); await ws.close();
      alert(`Saved performance for ${weeksOut.length} week(s).`+note);
      return;
    }catch(e){ if(e.name==="AbortError") return; }
  }
  const blob=new Blob([json],{type:"application/json"});
  const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download=fname;
  document.body.appendChild(a); a.click(); document.body.removeChild(a);
  setTimeout(()=>URL.revokeObjectURL(a.href),2000);
  alert(`Downloaded ${fname} (${weeksOut.length} week(s)).`+note);
}
function fallbackCopy(text,cb){
  const ta=document.createElement("textarea");ta.value=text;document.body.appendChild(ta);ta.select();
  try{document.execCommand("copy");}catch(e){}
  document.body.removeChild(ta);cb&&cb();
}

function statsBar(){
  const w = curWeek(); if(!w) return;
  const dist=w.distribution||[], office=w.office||[];
  let tofilm=0, filmed=0, posted=0, views=0, ignored=0;
  [].concat(dist, office).forEach(x=>{
    const s=t(x.id).status;
    if(s==="ignored") ignored++;
    else if(s==="posted"){posted++; views+=parseInt(t(x.id).views||0)||0;}
    else if(s==="filmed") filmed++;
    else tofilm++;
  });
  // intent bar under "To film": storytelling / educational / secondary lane
  const isPool = x=>{const s=t(x.id).status; return s!=="ignored"&&s!=="filmed"&&s!=="posted";};
  const story = dist.filter(x=>isPool(x)&&x.intent==="storytelling").length;
  const edu   = dist.filter(x=>isPool(x)&&x.intent==="educational").length;
  const off   = office.filter(isPool).length;
  const tot   = story+edu+off;
  const seg=(v,cls)=>`<div class="${cls}" style="flex:${tot?(v||0.0001):1}"></div>`;
  const bar = `<div class="intentbar">${seg(story,'sga')}${seg(edu,'sgb')}${seg(off,'sgc')}</div>`
            + `<div class="barcap">storytelling &middot; educational &middot; __SECONDARY_LABEL__</div>`;
  const cards=[
    {l:"To film", n:tofilm, extra:bar},
    {l:"Filmed", n:filmed, sub:"ready to post"},
    {l:"Posted", n:posted, sub:"live"},
    {l:"Views logged", n:views.toLocaleString(), sub:"across posted", accent:true},
    {l:"Ignored", n:ignored, sub:"skipped this week"},
  ];
  document.getElementById("stats").innerHTML = cards.map(c=>
    `<div class="stat"><div class="l">${c.l}</div><div class="n${c.accent?' accent':''}">${c.n}</div>${c.extra||""}${c.sub?`<div class="sub">${c.sub}</div>`:""}</div>`).join("");
}

function tracker(id, withLink){
  const r=t(id);
  const seg=["idea","filmed","posted"].map(s=>`<button data-s="${s}" class="${r.status===s?'on':''}" onclick="setT('${id}',{status:'${s}'})">${s[0].toUpperCase()+s.slice(1)}</button>`).join("");
  return `<div class="row">
    <span class="seg">${seg}</span>
    <input class="views" type="number" placeholder="views I got" value="${esc(r.views)}" oninput="track['${id}']=Object.assign(t('${id}'),{views:this.value});save();updateStats()">
    ${withLink?`<input class="plink" placeholder="link to my posted video" value="${esc(r.link)}" oninput="track['${id}']=Object.assign(t('${id}'),{link:this.value});save()">`:""}
  </div>
  <textarea class="notes" placeholder="notes" oninput="track['${id}']=Object.assign(t('${id}'),{notes:this.value});save()">${esc(r.notes)}</textarea>`;
}
function updateStats(){statsBar();}

function block(label, val, cls){return val?`<div class="block ${cls||''}"><div class="label">${label}</div><div class="val">${esc(val)}</div></div>`:"";}

// split a spoken passage into sentences (one per line), without breaking on
// decimals ("1.76%") or lowercase abbreviations ("e.g.").
function splitSentences(text){
  if(!text) return [];
  return String(text).replace(/\s*\n+\s*/g," ")
    .split(/(?<=[.?!…])\s+(?=[A-Z"'‘“£$])/)
    .map(s=>s.trim()).filter(Boolean);
}
// ONE read-aloud block, laid out like a movie script: a HOOK section (bolded,
// the opening 1-2 lines you say), then SCRIPT (the body), then CTA (optional)
// at the end. Every sentence lands on its own spaced line, teleprompter style.
function readScript(x){
  function section(label, text, opt, bold){
    const lines=splitSentences(text);
    if(!lines.length) return "";
    const lab=`<div class="seclabel">${label}${opt?` <span class="opt">optional</span>`:""}</div>`;
    const body=lines.map(s=>`<p class="sent${bold?' hook':''}">${esc(s)}</p>`).join("");
    return `<div class="scriptsec">${lab}${body}</div>`;
  }
  const html = section("Hook", x.spoken_hook, false, true)
    + section("Script", x.script, false, false)
    + section("CTA", x.cta, true, false);
  if(!html.trim()) return "";
  return `<div class="block readbox"><div class="label">Read this out loud while recording</div><div class="val">${html}</div></div>`;
}

// day-in-life-vo scripts carry beats[] (role / VO line / b-roll / duration):
// render them as a film-this table so Mode B is usable straight off the card.
function beatsTable(x){
  if(!x.beats||!x.beats.length) return "";
  const rows=x.beats.map(b=>`<tr><td class="brole">${esc(b.role)}</td><td>${esc(b.text)}</td><td class="bmut">${esc(b.b_roll)}</td><td class="bmut">${b.target_dur?esc(String(b.target_dur))+"s":""}</td></tr>`).join("");
  return `<div class="block"><div class="label">Beats - film these (VO to picture, editor Mode B)</div><div class="val beatswrap"><table class="beats"><thead><tr><th>Role</th><th>VO line</th><th>B-roll</th><th>Dur</th></tr></thead><tbody>${rows}</tbody></table></div></div>`;
}

function srcs(list){
  if(!list||!list.length) return "";
  const items=list.map(s=> s.url?`<a class="link" href="${esc(s.url)}" target="_blank">${esc(s.label)}</a>`:esc(s.label)).join(" &nbsp;&middot;&nbsp; ");
  return `<div class="block srcblk"><div class="label">Sources - check before posting</div><div class="val" style="font-size:13px">${items}</div></div>`;
}

function scriptCard(x, isSecondLane){
  const r=t(x.id); const done=r.status==="posted";
  const ready = x.qa==="passed";
  const meta = (x.borrows||x.carries)
    ? `<p class="meta"><b>Borrows:</b> ${esc(x.borrows)}<br><b>Carries:</b> ${esc(x.carries)}</p>`
    : (x.mechanic?`<p class="meta"><b>Mechanic:</b> ${esc(x.mechanic)}</p>`:"");
  const badge = ready?'<span class="badge ready">QA passed</span>':'<span class="badge draft">Pre-QA draft</span>';
  const title = x.title || x.mechanic || x.text_hook || "Untitled";
  // on-screen hooks always visible (these are SHOWN, not said); the full
  // spoken read (hook line + script) is one block, collapsed.
  const hooks = `<div class="hookgrid">${block("Text hook - write on the video", x.text_hook, "hookblk")}${block("Visual hook - show this", x.visual_hook, "hookblk")}</div>`;
  let collapsed = readScript(x)
    + beatsTable(x)
    + block("Directions - DO this, do not read it", x.directions, "dirbox")
    + block("Value - what the viewer takes away", x.value, "valblk");
  // legacy fallback (pre-QA b-batch still on the old shape)
  if(!x.script && (x.hook || x.beats)){
    collapsed = block("Hook (legacy)", x.hook, "hookblk")
      + block("Script / beats (legacy - needs QA upgrade)", x.beats||x.script, "readbox");
  }
  const hasCollapse = collapsed.trim().length>0;
  return `<div class="card ${done?'done':''}">
    <div class="cardhead"><p class="ttl" style="margin:0">${esc(title)}</p>${badge}${done?'<span class="pill">posted</span>':''}<span style="margin-left:auto;display:flex;gap:6px"><button class="btn ${r.carousel?'on':''}" onclick="toggleCarousel('${x.id}')" title="Flag this script for a LinkedIn carousel PDF, then use 'Export carousel queue'">${r.carousel?'Carousel ✓':'Carousel'}</button><button class="btn" onclick="setT('${x.id}',{status:'${r.status==='ignored'?'idea':'ignored'}'})">${r.status==='ignored'?'Restore':'Ignore'}</button></span></div>
    ${meta}
    ${srcs(x.sources)}
    ${hooks}
    ${hasCollapse?`<button class="toggle" onclick="const c=this.nextElementSibling;c.classList.toggle('show');this.textContent=c.classList.contains('show')?'Hide full script':'Show full script + value + CTA'">Show full script + value + CTA</button><div class="collapse">${collapsed}</div>`:""}
    ${(!isSecondLane && x.linkedin)?`<div class="block litwinwrap"><button class="toggle" onclick="const b=this.parentElement.querySelector('.litwin');b.classList.toggle('show');this.textContent=b.classList.contains('show')?'Hide LinkedIn twin':'Show LinkedIn twin'">Show LinkedIn twin</button> <button class="btn" onclick="navigator.clipboard.writeText(this.parentElement.querySelector('.litwin').innerText);this.textContent='Copied'">Copy twin</button><div class="litwin collapse readbox" style="margin-top:8px"><div class="val" style="white-space:pre-wrap">${esc(x.linkedin.body)}</div></div></div>`:""}
    ${tracker(x.id, true)}
  </div>`;
}

function liCard(x, srcTitle){
  const r=t(x.id); const done=r.status==="posted";
  const badge = x.qa==="passed"?'<span class="badge ready">QA passed</span>':(x.qa?'<span class="badge draft">Pre-QA draft</span>':'');
  return `<div class="card ${done?'done':''}">
    <div class="cardhead"><p class="ttl" style="margin:0">${esc(x.type)} · ${esc(x.hook_arch)}</p>${badge}${done?'<span class="pill">posted</span>':''}</div>
    ${srcTitle?`<p class="meta">Written twin of video: <b>${esc(srcTitle)}</b></p>`:""}
    ${srcs(x.sources)}
    <button class="btn" onclick="navigator.clipboard.writeText(this.nextElementSibling.innerText);this.textContent='Copied'">Copy post</button>
    <div class="body show" style="margin-top:10px">${esc(x.body)}</div>
    ${tracker(x.id, true)}
  </div>`;
}

function inspCard(x){
  const conf = x.metric_confidence?` <span class="pill">${esc(x.metric_confidence)}</span>`:"";
  return `<div class="card">
    <p class="ttl">${esc(x.creator)} <span class="pill">${esc(x.platform)}</span></p>
    <p class="meta"><b>${esc(x.metric)}</b>${conf} &nbsp;·&nbsp; mechanic: ${esc(x.mechanic)}</p>
    <a class="link" href="${esc(x.link)}" target="_blank">Open source &rarr;</a>
  </div>`;
}

function render(){
  const w=curWeek(); if(!w){document.getElementById("view").innerHTML="No data yet.";return;}
  document.getElementById("sub").textContent = w.positioning || "";
  statsBar();
  updateTabCounts(w);
  const showIgn = document.getElementById("showIgnored") && document.getElementById("showIgnored").checked;
  document.getElementById("ignrow").style.display = (TAB==="dist"||TAB==="office")?"block":"none";
  const pool = arr => showIgn
    ? arr.filter(x=>t(x.id).status==="ignored")
    : arr.filter(x=>{const s=t(x.id).status; return s!=="ignored"&&s!=="filmed"&&s!=="posted";});
  const office = w.office||[];
  let html="", empty="Nothing here this week.";
  if(TAB==="dist"){ html=pool(w.distribution||[]).map(x=>scriptCard(x,false)).join(""); empty=showIgn?"No ignored scripts.":"Nothing left to film here. All filmed, posted, or ignored."; }
  else if(TAB==="office"){ html=pool(office).map(x=>scriptCard(x,true)).join(""); empty=showIgn?"No ignored scripts.":"Nothing left to film here. All filmed, posted, or ignored."; }
  else if(TAB==="filmed"){ const items=[].concat(w.distribution||[], office).filter(x=>["filmed","posted"].includes(t(x.id).status)); html=items.map(x=>scriptCard(x, office.includes(x))).join(""); empty="Nothing filmed yet. Mark a script Filmed and it lands here for metric tracking."; }
  else if(TAB==="linkedin"){
    const hdr = s => `<h3 style="margin:24px 0 10px;font-size:14px;color:var(--muted);text-transform:uppercase;letter-spacing:.04em;font-weight:600">${s}</h3>`;
    const gtm = (w.linkedin||w.gtm_linkedin||[]).filter(x=>t(x.id).status!=="ignored").map(x=>liCard(x, ""));
    const twins = (w.distribution||[]).filter(x=>x.linkedin && t(x.id).status!=="ignored").map(x=>liCard(x.linkedin, x.title));
    html = (gtm.length?hdr("__LEADERS_HDR__")+gtm.join(""):"")
         + (twins.length?hdr("Twins of this week's videos")+twins.join(""):"");
    empty="No LinkedIn posts this week.";
  }
  else if(TAB==="insp") html=(w.inspiration||[]).map(inspCard).join("");
  document.getElementById("view").innerHTML = html || ("<p class='meta'>"+empty+"</p>");
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
           .replace("__PARTNER__", PARTNER_HTML))
dest = os.path.join(WS, "dashboard.html")
open(dest, "w").write(out)
print(f"wrote {dest} from {len(weeks)} week(s)")

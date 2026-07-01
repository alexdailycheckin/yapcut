#!/usr/bin/env python3
"""Build a self-contained dashboard.html from weeks/*.json.

Embeds all weekly data into one HTML file. Your tracking (status, views you got,
posted link, notes) lives in the browser's localStorage keyed by stable item id,
so regenerating the dashboard each week never wipes what you logged.

Run: python3 build_dashboard.py   ->   writes dashboard.html
"""
import json, os, glob

HERE = os.path.dirname(os.path.abspath(__file__))

# Optional radar-config.json lets any installer name their two lanes. Defaults
# to the generic product labels so it works with no config at all.
CFG = {}
_cfgp = os.path.join(HERE, "radar-config.json")
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

weeks = []
for f in sorted(glob.glob(os.path.join(HERE, "weeks", "*.json")), reverse=True):
    try:
        weeks.append(json.load(open(f)))
    except Exception as e:
        print("skip", f, e)

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
</head>
<body>
<div class="wrap">
  <div class="topbar">
    <header><h1>Outlier Radar</h1><p id="sub"></p></header>
    <div style="display:flex;gap:8px;align-items:center">
      <button class="btn" onclick="exportFilmed()" title="Copy every script you marked Filmed, with its edit spec, to paste into the editor session">Export filmed scripts</button>
      <button class="btn" onclick="exportForBlog()" title="Save everything you marked Filmed or Posted this week to a JSON file the weekly routine turns into an AEO blog post">Export week for blog</button>
      <select id="weekSel" onchange="render()"></select>
    </div>
  </div>
  <div class="stats" id="stats"></div>
  <div class="tabs">
    <button class="tab on" data-t="dist" onclick="setTab('dist')">__PRIMARY_LABEL__ (to film)</button>
    <button class="tab" data-t="office" onclick="setTab('office')">__SECONDARY_LABEL__ (to film)</button>
    <button class="tab" data-t="filmed" onclick="setTab('filmed')">Filmed &amp; metrics</button>
    <button class="tab" data-t="linkedin" onclick="setTab('linkedin')">LinkedIn posts</button>
    <button class="tab" data-t="insp" onclick="setTab('insp')">Viral inspiration</button>
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
function t(id){return track[id] || {status:"idea", views:"", link:"", notes:""};}
function setT(id, patch){track[id] = Object.assign(t(id), patch); save(); render();}
function setTab(x){TAB=x; document.querySelectorAll(".tab").forEach(b=>b.classList.toggle("on", b.dataset.t===x)); render();}
function esc(s){return (s||"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}

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
function fallbackCopy(text,cb){
  const ta=document.createElement("textarea");ta.value=text;document.body.appendChild(ta);ta.select();
  try{document.execCommand("copy");}catch(e){}
  document.body.removeChild(ta);cb&&cb();
}

function statsBar(){
  const w = curWeek(); if(!w) return;
  let tofilm=0, filmed=0, posted=0, views=0, ignored=0;
  [].concat(w.distribution||[], w.office||[]).forEach(x=>{
    const s=t(x.id).status;
    if(s==="ignored") ignored++;
    else if(s==="posted"){posted++; views+=parseInt(t(x.id).views||0)||0;}
    else if(s==="filmed") filmed++;
    else tofilm++;
  });
  const S=[["To film",tofilm],["Filmed",filmed],["Posted",posted],["Views logged",views.toLocaleString()],["Ignored",ignored]];
  document.getElementById("stats").innerHTML = S.map(([l,n])=>`<div class="stat"><div class="n">${n}</div><div class="l">${l}</div></div>`).join("");
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

function srcs(list){
  if(!list||!list.length) return "";
  const items=list.map(s=> s.url?`<a class="link" href="${esc(s.url)}" target="_blank">${esc(s.label)}</a>`:esc(s.label)).join(" &nbsp;&middot;&nbsp; ");
  return `<div class="block srcblk"><div class="label">Sources (check before posting)</div><div class="val" style="font-size:13px">${items}</div></div>`;
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
  const hooks = block("Text hook (write on the video, not spoken)", x.text_hook, "hookblk")
    + block("Visual hook (show this)", x.visual_hook, "hookblk");
  let collapsed = readScript(x)
    + block("Directions - DO this, do not read it", x.directions, "dirbox")
    + block("Value - what the viewer takes away", x.value, "valblk");
  // legacy fallback (pre-QA b-batch still on the old shape)
  if(!x.script && (x.hook || x.beats)){
    collapsed = block("Hook (legacy)", x.hook, "hookblk")
      + block("Script / beats (legacy - needs QA upgrade)", x.beats||x.script, "readbox");
  }
  const hasCollapse = collapsed.trim().length>0;
  return `<div class="card ${done?'done':''}">
    <div class="cardhead"><p class="ttl" style="margin:0">${esc(title)}</p>${badge}${done?'<span class="pill">posted</span>':''}<button class="btn" style="margin-left:auto" onclick="setT('${x.id}',{status:'${r.status==='ignored'?'idea':'ignored'}'})">${r.status==='ignored'?'Restore':'Ignore'}</button></div>
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
  return `<div class="card">
    <p class="ttl">${esc(x.creator)} <span class="pill">${esc(x.platform)}</span></p>
    <p class="meta"><b>${esc(x.metric)}</b> &nbsp;·&nbsp; mechanic: ${esc(x.mechanic)}</p>
    <a class="link" href="${esc(x.link)}" target="_blank">Open source &rarr;</a>
  </div>`;
}

function render(){
  const w=curWeek(); if(!w){document.getElementById("view").innerHTML="No data yet.";return;}
  document.getElementById("sub").textContent = w.positioning || "";
  statsBar();
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
    const gtm = (w.gtm_linkedin||[]).filter(x=>t(x.id).status!=="ignored").map(x=>liCard(x, ""));
    const twins = (w.distribution||[]).filter(x=>x.linkedin && t(x.id).status!=="ignored").map(x=>liCard(x.linkedin, x.title));
    html = (gtm.length?hdr("__LEADERS_HDR__")+gtm.join(""):"")
         + (twins.length?hdr("Twins of this week's videos")+twins.join(""):"");
    empty="No LinkedIn posts this week.";
  }
  else if(TAB==="insp") html=(w.inspiration||[]).map(inspCard).join("");
  document.getElementById("view").innerHTML = html || ("<p class='meta'>"+empty+"</p>");
}

(function init(){
  const sel=document.getElementById("weekSel");
  sel.innerHTML = WEEKS.map(w=>`<option value="${w.week}">Week of ${w.week}</option>`).join("");
  render();
})();
</script>
</body>
</html>"""

out = (HTML.replace("/*WEEKS_DATA*/", DATA)
           .replace("__PRIMARY_LABEL__", PRIMARY_LABEL)
           .replace("__SECONDARY_LABEL__", SECONDARY_LABEL)
           .replace("__LEADERS_HDR__", LEADERS_HDR))
open(os.path.join(HERE, "dashboard.html"), "w").write(out)
print(f"wrote dashboard.html from {len(weeks)} week(s)")

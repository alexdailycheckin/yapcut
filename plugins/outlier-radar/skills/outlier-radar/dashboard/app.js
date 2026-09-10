/* Data arrives in <script type="application/json"> blocks the build writes; nothing
   here is substituted by Python, so this file is plain JS that node --check can read. */
function readJson(id, fallback){
  const el=document.getElementById(id); if(!el) return fallback;
  try { const v=JSON.parse(el.textContent); return v==null ? fallback : v; }
  catch(e) { console.error("dashboard: bad JSON in #"+id, e); return fallback; }
}
const WEEKS = readJson("weeks-data", []);
const CAMPAIGNS = readJson("campaigns-data", []);
const SEED = readJson("tracking-seed", {});
const UI = readJson("ui-config", {});
const KEY = "outlier-radar-tracking";
const SEED_KEY = KEY+":seeded";
const AMMO_KEY = "outlier-radar-ammo";
const BLANK = {status:"idea", views:"", link:"", notes:"", carousel:false};
let TAB = "dist";
let FILM_ID = null;
/* Both tracking calls are guarded. The theme calls below always were; these two
   were not, and they are the ones the whole UI depends on. Where localStorage
   throws (Safari on a file:// origin, a browser set to block site data, private
   mode quota) the unguarded setItem took setT() down before it reached render(),
   so a click changed nothing on screen: the exact "the button does nothing"
   report, with no error anywhere a user would look. The read is guarded too,
   which also covers a corrupted value that no longer parses. */
const track = (function(){
  let local={}, seeded={};
  try { local = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch(e) { local = {}; }
  try { seeded = JSON.parse(localStorage.getItem(SEED_KEY) || "{}") || {}; } catch(e) { seeded = {}; }
  const out={};
  Object.keys(SEED).forEach(id=>{ out[id]=Object.assign({}, BLANK, SEED[id]); });
  Object.keys(local).forEach(id=>{
    /* tracking.jsonl is the truth on disk; the browser is an overlay on it. An entry
       that still equals what the last build seeded was never touched here, so a newer
       seed wins over it. Anything edited in the browser wins over the seed. */
    const untouched = seeded[id] && JSON.stringify(local[id])===JSON.stringify(seeded[id]);
    if(untouched && SEED[id]) return;
    out[id]=Object.assign({}, out[id]||BLANK, local[id]);
  });
  return out;
})();
let STORAGE_DEAD = false;
function save(){
  try {
    localStorage.setItem(KEY, JSON.stringify(track));
    const snap={}; Object.keys(SEED).forEach(id=>{ snap[id]=Object.assign({}, BLANK, SEED[id]); });
    localStorage.setItem(SEED_KEY, JSON.stringify(snap));
  }
  catch(e) {
    /* Swallow so render() still runs and the click visibly does something, but
       say so once: tracking that silently fails to persist is worse than a
       tracker that admits it cannot. */
    if(!STORAGE_DEAD){
      STORAGE_DEAD = true;
      try { toast("Browser storage is blocked, so filmed and ignored marks will not survive a reload"); } catch(_){}
    }
  }
}
function t(id){return track[id] || Object.assign({}, BLANK);}
function setT(id, patch){track[id] = Object.assign(t(id), patch); save(); render(); if(FILM_ID) syncFilmFoot();}
function toggleCarousel(id){setT(id,{carousel:!t(id).carousel}); toast(t(id).carousel?"Flagged for a carousel":"Carousel flag removed");}
function setTab(x){TAB=x; document.querySelectorAll(".tab").forEach(b=>b.classList.toggle("on", b.dataset.t===x)); render();}
function esc(s){return String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));}
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
/* Three sources feed the LinkedIn tab and they are not interchangeable.
   soloPosts  = linkedin[], written for the feed alone, no video behind them.
   leaderPosts= gtm_linkedin[], mined from the leaders the creator studies.
   twins      = a video script's twin, and only when it earned a slot. A twin the
                selector cut still lives in the week file so the script keeps its
                LinkedIn draft, but it is not part of this week's feed plan. */
function soloPostsOf(w){ return (w.linkedin||[]).filter(x=>x.banked!==true); }
function bankedPostsOf(w){ return (w.linkedin||[]).filter(x=>x.banked===true); }
function leaderPostsOf(w){ return w.gtm_linkedin||[]; }
function liveTwinsOf(w){
  return (w.distribution||[]).filter(x=>x.linkedin && x.linkedin.twin_cut!==true
                                        && t(x.id).status!=="ignored");
}
function poolCount(arr){return (arr||[]).filter(x=>{const s=t(x.id).status; return s!=="ignored"&&s!=="filmed"&&s!=="posted";}).length;}
function updateTabCounts(w){
  if(!w) return;
  const set=(c,n)=>{const e=document.querySelector('.cnt[data-c="'+c+'"]'); if(e) e.textContent=n?String(n):"";};
  const office=officeOf(w);
  const all=[].concat(w.distribution||[], office);
  set("dist", poolCount(w.distribution));
  set("office", poolCount(office));
  set("filmed", all.filter(x=>["filmed","posted"].includes(t(x.id).status)).length);
  set("linkedin", liveTwinsOf(w).length + soloPostsOf(w).length + leaderPostsOf(w).length);
  set("insp", (w.inspiration||[]).length);
  set("ammo", ammoRounds(w).filter((r,i)=>!isSpent(w,r,i)).length);
  CAMPAIGNS.forEach((c,i)=>set("camp:"+i,
    poolCount([].concat(c.distribution||[], c.office||[], c.linkedin||[]))));
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
/* The merged view: what tracking.jsonl seeded plus what changed in this browser.
   Payload shape is load-bearing downstream (log_perf.py --import). */
async function exportPerformance(){
  const row=(x,lane)=>{
    if(!x||!x.id) return null;
    const r=t(x.id);
    if(r.status==="idea" && !r.views && !r.notes && !r.link) return null;
    return {id:x.id, title:x.title||"", lane,
            mechanic:x.mechanic||x.borrows||"", facet:x.facet||"", intent:x.intent||"",
            value:x.value||"", qa:x.qa||"", status:r.status, views:r.views||"",
            link:r.link||"", notes:r.notes||""};
  };
  const weeksOut = WEEKS.map(w=>{
    const office=officeOf(w);
    const vids=[].concat(w.distribution||[], office).map(x=>row(x, office.includes(x)?"secondary":"primary"));
    const twins=(w.distribution||[]).filter(x=>x.linkedin&&x.linkedin.id).map(x=>x.linkedin);
    const posts=[].concat(w.linkedin||[], leaderPostsOf(w), twins).map(x=>row(x,"linkedin"));
    const items=vids.concat(posts).filter(Boolean);
    return items.length?{week:w.week, items}:null;
  }).filter(Boolean);
  if(!weeksOut.length){alert("No tracking logged yet.\n\nMark scripts Filmed or Posted and log views, then export. This file is what lets the next radar run learn from your results.");return;}
  const payload={exported_at:new Date().toISOString(), source:"dashboard", weeks:weeksOut};
  await saveJson(JSON.stringify(payload,null,2), `performance-${weeksOut[0].week}.json`,
    `Saved the merged tracking for ${weeksOut.length} week(s).\n\nSave the file, then run:\n  python3 log_perf.py --import <file>\nso tracking.jsonl carries it and the next build seeds from it.`);
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
    + (extra?`<div class="briefextra" id="briefExtra">${extra}</div>`:"")
    + experimentLine(w);
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
            + `<div class="barcap">story &middot; educational &middot; ${esc(UI.secondary_label||"Viral videos")}</div>`;
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
  const rows=x.shot_list.map(s=>`<tr><td class="bn">${esc(String(s.n!=null?s.n:""))}</td><td class="bmut">${esc(s.beat||"")}</td><td>${esc(s.what||s.shoot||"")}${s.url?` <a href="${esc(s.url)}" target="_blank">open &rarr;</a>`:""}</td></tr>`).join("");
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

/* Three states, not two. The chip used to be binary on qa==="passed", so a post
   that had cleared the gate and was only waiting on the creator's yes rendered as
   "Pre-QA", indistinguishable from one nothing had ever read. "Pre-QA" now fires
   only on a qa value the engine does not define, which is a bug worth seeing. */
function qaChip(qa){
  if(qa==="passed") return `<span class="chip qa">QA passed</span>`;
  if(qa==="pending-approval") return `<span class="chip draft">Awaiting approval</span>`;
  return qa ? `<span class="chip draft">Pre-QA</span>` : "";
}

function chipRow(x, r){
  const chips=[];
  chips.push(qaChip(x.qa) || `<span class="chip draft">Pre-QA</span>`);
  if(r.status==="posted") chips.push(`<span class="chip posted">Posted</span>`);
  if(x.post_type) chips.push(`<span class="chip">${esc(x.post_type)}</span>`);
  if(x.hook_family) chips.push(`<span class="chip">${esc(String(x.hook_family).replace(/^\d+\s*-\s*/,"").split("/")[0].trim())}</span>`);
  if(x.intent) chips.push(`<span class="chip">${esc(x.intent)}</span>`);
  if(x.script_class) chips.push(`<span class="chip">${esc(x.script_class)}</span>`);
  if(x.proof && x.proof.kind) chips.push(proofChip(x.proof));
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
        <div class="twinbody">${esc(linkedinText(x.linkedin.body))}</div>
        <div class="twinmeta">
          <button class="btn" onclick="copyText(linkedinText(this.closest('.twin').querySelector('.twinbody').innerText),'LinkedIn twin copied, formatted for paste')">Copy twin</button>
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
/* A calendar cell has to say WHICH post, and a solo LinkedIn post carries no title, so the
   old fallback chain ended at x.type and printed "text" or "single-image" in the slot. A
   format label is never the answer to "which one is this": the whole week reads as a column
   of "text, single image, text". Fall through to the hook, then the opening line of the
   body, and only ever say "Post" when the item is genuinely empty. */
function postName(x){
  if(x.title) return x.title;
  if(x.text_hook) return x.text_hook;
  const b=(x.body||"").trim();
  if(b){
    const first=b.split("\n").find(l=>l.trim());
    if(first) return first.length>72 ? first.slice(0,69).trimEnd()+"..." : first;
  }
  return "Post";
}

/* ---------- LinkedIn-ready text ---------- */
/* LinkedIn strips every kind of rich formatting on paste, so "copy" has to hand over text
   that is ALREADY styled at the character level. Markers in the body are converted here
   rather than stored converted, because the stored body has to stay real text: the gates
   read it, spoken_lint reads it, and a body full of Mathematical Sans-Serif Bold would
   defeat all of them.

   USE BOLD SPARINGLY, and never on a number or the central claim. Unicode bold is not
   text. Screen readers announce it as gibberish or skip it, and parsers handle it badly,
   which for a creator whose subject is AI search visibility is an own goal: the sentence
   you most want quoted is the one you just made unreadable to the thing quoting it. */
function liBold(t){
  return t.replace(/[A-Za-z0-9]/g, c => {
    const u = c.codePointAt(0);
    if (u >= 65 && u <= 90)  return String.fromCodePoint(0x1D5D4 + u - 65);
    if (u >= 97 && u <= 122) return String.fromCodePoint(0x1D5EE + u - 97);
    if (u >= 48 && u <= 57)  return String.fromCodePoint(0x1D7EC + u - 48);
    return c;
  });
}
function liItalic(t){
  return t.replace(/[A-Za-z]/g, c => {
    const u = c.codePointAt(0);
    if (u >= 65 && u <= 90)  return String.fromCodePoint(0x1D608 + u - 65);
    if (u >= 97 && u <= 122) return String.fromCodePoint(0x1D622 + u - 97);
    return c;
  });
}
/* Markers: **bold**, *italic*, and a leading "- " or "* " becomes the arrow bullet the
   creator already uses in his published posts. Numbered lists keep their numerals, per the
   numeral law. */
function linkedinText(t){
  return (t || "")
    .replace(/\*\*([^*\n]+)\*\*/g, (_, x) => liBold(x))
    .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, (_, p, x) => p + liItalic(x))
    .split("\n")
    .map(l => l.replace(/^\s*[-*]\s+/, "↳ "))
    .join("\n")
    .replace(/\n{3,}/g, "\n\n");
}

/* ---------- posting calendar ---------- */
const CAL_DOW=["Sun","Mon","Tue","Wed","Thu","Fri","Sat"];
const CAL_MON=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];

function isoParts(iso){
  const p=String(iso||"").split("-");
  return (p.length===3 && p.every(v=>v.length && !isNaN(+v))) ? p.map(Number) : null;
}
/* Parsed as UTC on purpose: a local-time parse of a bare ISO date shifts the weekday
   by one west of Greenwich, which would print the wrong day name. */
function fmtDay(iso){
  const p=isoParts(iso); if(!p) return "";
  return CAL_DOW[new Date(Date.UTC(p[0],p[1]-1,p[2])).getUTCDay()]+" "+p[2]+" "+CAL_MON[p[1]-1];
}
function todayIso(){
  const n=new Date();
  return `${n.getFullYear()}-${String(n.getMonth()+1).padStart(2,"0")}-${String(n.getDate()).padStart(2,"0")}`;
}

/* Renders whatever select_linkedin.py assigned. No day in the week file means no
   calendar, so older weeks degrade to the plain card list instead of showing a fake week. */
function calendarBlock(w){
  const rows=[];
  liveTwinsOf(w).forEach(x=>{
    if(x.linkedin.post_day) rows.push({p:x.linkedin, title:x.title||x.linkedin.title||"Post"});
  });
  soloPostsOf(w).concat(leaderPostsOf(w)).forEach(x=>{
    if(x.post_day && t(x.id).status!=="ignored") rows.push({p:x, title:postName(x)});
  });
  if(!rows.length) return "";

  const used=[...new Set(rows.map(r=>r.p.post_day))].sort();
  const first=isoParts(used[0]);
  const week=[];
  if(first){
    let d=new Date(Date.UTC(first[0],first[1]-1,first[2]));
    while(week.length<5){
      if(d.getUTCDay()>=1 && d.getUTCDay()<=5) week.push(d.toISOString().slice(0,10));
      d=new Date(d.getTime()+86400000);
    }
  }
  const today=todayIso();
  const cols=[...new Set(week.concat(used))].sort().map(iso=>{
    const mine=rows.filter(r=>r.p.post_day===iso)
                   .sort((a,b)=>(a.p.post_slot||99)-(b.p.post_slot||99));
    const cells = mine.length ? mine.map(r=>{
      const posted=t(r.p.id).status==="posted";
      return `<button class="calslot ${posted?'posted':''}" onclick="jumpToPost('${r.p.id}')">
        <span class="n">${String(r.p.post_slot||"").padStart(2,"0")} &middot; 9am${posted?" &middot; posted":""}</span>
        <span class="h">${esc(r.title)}</span>
        ${r.p.post_day_locked?'<span class="chip">Pinned</span>':""}
        <span class="why">${esc(r.p.post_why||"")}</span>
      </button>`;
    }).join("") : `<div class="calempty">open</div>`;
    const isToday = iso===today;
    return `<div class="calday">
      <div class="caldate ${isToday?'today':''}">${fmtDay(iso)}${isToday?" &middot; today":""}</div>
      ${cells}</div>`;
  }).join("");

  return `<div class="sechdr">Posting week &middot; ordered by urgency</div>
    <div class="cal">${cols}</div>
    <p class="calnote">Order is decay order, not quality order: the item that loses value
    soonest goes first, score only breaks a tie. Re-run
    <code>scripts/select_linkedin.py</code> to reassign, or set
    <code>"post_day_locked": true</code> on a twin to pin it.</p>`;
}

function jumpToPost(id){
  const el=document.getElementById("licard-"+id);
  if(!el) return;
  el.scrollIntoView({behavior:"smooth", block:"center"});
  el.style.borderColor="var(--accent)";
  setTimeout(()=>{ el.style.borderColor=""; }, 1400);
}

function liCard(x, srcTitle, i){
  const r=t(x.id); const done=r.status==="posted";
  const title = srcTitle || x.title || x.type || "Post";
  /* The FEED shape, assigned by select_linkedin.py from the substance and persisted to
     `shape`. Never read linkedin_format here: that key is the human override the selector
     reads as an instruction, so echoing it back would be circular. Falls back to x.type
     only for weeks built before the selector existed, where that field still held whatever
     the video happened to be. */
  const shape = x.shape ? x.shape.replace(/^F\d_/,"") : x.type;
  const typeChip = shape ? `<span class="chip">${esc(shape)}</span>` : "";
  const jobChip = x.job ? `<span class="chip">${esc(x.job)}</span>` : "";
  const cutChip = x.twin_cut===true ? `<span class="chip">not twinned</span>`
                : x.banked===true ? `<span class="chip">banked</span>` : "";
  const dayChip = x.post_day ? `<span class="chip">${fmtDay(x.post_day)} 9am</span>` : "";
  return `<div class="card ${done?'done':''}" id="licard-${x.id}">
    <div class="cardtop">
      <span class="idx">${String(i+1).padStart(2,"0")}</span>
      <div class="cardtitle">
        <h3 class="ttl">${esc(title)}</h3>
        <div class="chips">${dayChip}${qaChip(x.qa)}${done?'<span class="chip posted">Posted</span>':''}${r.status==="scheduled"?'<span class="chip">Scheduled</span>':''}${cutChip}${typeChip}${jobChip}${x.hook_arch?`<span class="chip">${esc(x.hook_arch)}</span>`:""}</div>
      </div>
      <div class="cardops"><button class="btn" onclick="copyText(linkedinText(this.closest('.card').querySelector('.twinbody').innerText),'Post copied, formatted for paste')">Copy post</button></div>
    </div>
    ${srcTitle?`<p class="premise"><b>Written twin of this week's video</b></p>`:""}
    <div class="twinbody" style="margin:14px 0 0 42px">${esc(linkedinText(x.body))}</div>
    <div style="margin-left:42px">${visualBlock(x.visual)}${srcs(x.sources)?`<div style="margin-top:14px">${srcs(x.sources)}</div>`:""}</div>
    ${replyBlock(x)}
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
  const w=curWeek();
  let it = w ? [].concat(w.distribution||[], officeOf(w)).find(x=>x.id===id) : null;
  if(!it) for(const c of CAMPAIGNS){
    it=[].concat(c.distribution||[], c.office||[], c.linkedin||[]).find(x=>x.id===id);
    if(it) break;
  }
  return it || null;
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

/* ---------------- proof chip ---------------- */
/* Three neutral looks (solid, outlined, dashed), none of them a verdict: own,
   reach and public are provenance, not quality. */
function proofChip(p){
  const kind=String(p.kind||"").toLowerCase();
  const cls=["own","reach","public"].includes(kind)?"proof-"+kind:"";
  return `<span class="chip proof ${cls}" title="${esc(p.ref||"")}">proof &middot; ${esc(p.kind)}</span>`;
}

/* ---------------- reply block (LinkedIn) ---------------- */
/* held[] are the receipts kept OUT of the post for the comments; reply_stance is
   the one line to hold when the thread pushes back. Collapsed by default: the
   post is what gets copied, the block is what gets read before replying. */
function replyBlock(x){
  const held=Array.isArray(x.held)?x.held.filter(h=>h&&(h.fact||h.source)):[];
  if(!held.length && !x.reply_stance) return "";
  const rows=held.map(h=>`<li>${esc(h.fact||"")}${h.source?` <a href="${esc(h.source)}" target="_blank" rel="noopener">source &rarr;</a>`:""}</li>`).join("");
  return `<div class="reply">
    <button class="btn ghost" onclick="const b=this.parentElement.querySelector('.replywrap');b.classList.toggle('show');this.firstChild.textContent=b.classList.contains('show')?'Hide reply block':'Reply block'"><span>Reply block</span>${held.length?`<span class="chip">${held.length} held</span>`:""}</button>
    <div class="replywrap collapse">
      ${x.reply_stance?`<div class="block"><div class="lab">Reply stance</div><p class="psy">${esc(x.reply_stance)}</p></div>`:""}
      ${rows?`<div class="block"><div class="lab">Held receipts &middot; for the comments, not the post</div><ul class="held">${rows}</ul></div>`:""}
    </div>
  </div>`;
}

/* ---------------- experiment line ---------------- */
function experimentLine(w){
  const e=w.experiment; if(!e || !e.question) return "";
  const arms=e.arms||{}; const n=k=>Array.isArray(arms[k])?arms[k].length:0;
  return `<p class="expline"><b>This week's question:</b> ${esc(e.question)} <span class="expdim">(${esc(e.dim||"dim")}: A ${n("a")} vs B ${n("b")})</span></p>`;
}

/* ---------------- promises ---------------- */
function promisesBlock(w){
  const list=Array.isArray(w.promised)?w.promised.filter(p=>p&&p.text):[];
  if(!list.length) return "";
  const open=list.filter(p=>!p.paid_in).length;
  const rows=list.map(p=>{
    const paid=!!p.paid_in;
    return `<li class="${paid?'paid':'open'}"><span class="pst">${paid?'&#10003; paid '+esc(p.paid_in):'due '+esc(p.due_week||"open")}</span><span class="ptx">${esc(p.text)}</span>${p.made_in?`<span class="pmade">made ${esc(p.made_in)}</span>`:""}</li>`;
  }).join("");
  return `<div class="promises"><div class="lab">Promises &middot; ${open} open</div><ul>${rows}</ul></div>`;
}

/* ---------------- ammo ---------------- */
/* A round is a fact with a number and a source. Spent state lives in localStorage
   under its own key; a round the week file already marks spent_on starts spent. */
let AMMO = (function(){ try { return JSON.parse(localStorage.getItem(AMMO_KEY) || "{}") || {}; } catch(e) { return {}; } })();
function ammoRounds(w){ return Array.isArray(w&&w.ammo)?w.ammo.filter(r=>r&&(r.fact||r.number)):[]; }
function ammoKey(w,r,i){ return String(w.week)+"|"+(r.id||r.fact||i); }
function isSpent(w,r,i){ const k=ammoKey(w,r,i); return AMMO[k]!==undefined ? !!AMMO[k] : !!r.spent_on; }
function toggleSpent(i){
  const w=curWeek(); const r=ammoRounds(w)[i]; if(!w||!r) return;
  const k=ammoKey(w,r,i); AMMO[k]=!isSpent(w,r,i);
  try { localStorage.setItem(AMMO_KEY, JSON.stringify(AMMO)); } catch(e) {}
  render(); toast(AMMO[k]?"Round marked spent":"Round back in the clip");
}
function copyAmmo(i){
  const w=curWeek(); const r=ammoRounds(w)[i]; if(!r) return;
  copyText([r.fact, r.number?`(${r.number})`:"", r.source||""].filter(Boolean).join(" "), "Round copied");
}
function ammoCard(w, r, i){
  const spent=isSpent(w,r,i);
  const lanes=Array.isArray(r.lanes)?r.lanes.map(l=>`<span class="chip">${esc(l)}</span>`).join(""):"";
  const src=r.source?`<a href="${esc(r.source)}" target="_blank" rel="noopener">${esc(String(r.source).replace(/^https?:\/\/(www\.)?/,"").split("/")[0])} &rarr;</a>`:"";
  const fileSpent = spent && r.spent_on && AMMO[ammoKey(w,r,i)]===undefined;
  return `<div class="card ammo ${spent?'done':''}">
    <div class="cardtop">
      <span class="idx">${String(i+1).padStart(2,"0")}</span>
      <div class="cardtitle">
        <h3 class="ttl">${esc(r.fact||"")}</h3>
        <div class="chips">${spent?`<span class="chip posted">Spent${fileSpent?' &middot; '+esc(r.spent_on):''}</span>`:""}${lanes}</div>
      </div>
      <div class="cardops">
        <button class="btn ghost ${spent?'on':''}" onclick="toggleSpent(${i})">${spent?'Spent &#10003;':'Spent'}</button>
        <button class="btn" onclick="copyAmmo(${i})" title="Copy fact, number and source"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></svg>Copy</button>
      </div>
    </div>
    <div class="ammobody">${r.number?`<span class="ammonum">${esc(r.number)}</span>`:""}${src}</div>
  </div>`;
}

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
  if(TAB==="dist"){
    const cards=pool(w.distribution||[]).map((x,i)=>scriptCard(x,false,i)).join("");
    empty=showIgn?"No ignored scripts.":"Nothing left to film in this lane. Everything is filmed, posted, or ignored.";
    html = promisesBlock(w) + (cards || emptyState(empty));
  }
  else if(TAB==="office"){ html=pool(office).map((x,i)=>scriptCard(x,true,i)).join(""); empty=showIgn?"No ignored scripts.":"Nothing left to film in this lane. Everything is filmed, posted, or ignored."; }
  else if(TAB==="filmed"){ const items=[].concat(w.distribution||[], office).filter(x=>["filmed","posted"].includes(t(x.id).status)); html=items.map((x,i)=>scriptCard(x, office.includes(x), i)).join(""); empty="Nothing filmed yet. Mark a script Filmed and it lands here for metric tracking."; }
  else if(TAB==="linkedin"){
    /* Cards follow the selector's posting order so the list agrees with the calendar
       above it. Anything without an assigned slot keeps its file order, at the end. */
    const bySlot=(a,b)=>((a.post_slot||99)-(b.post_slot||99));
    const solo = soloPostsOf(w).filter(x=>t(x.id).status!=="ignored")
                            .slice().sort(bySlot).map((x,i)=>liCard(x, "", i));
    const gtm = leaderPostsOf(w).filter(x=>t(x.id).status!=="ignored")
                            .slice().sort(bySlot).map((x,i)=>liCard(x, "", i));
    const twins = liveTwinsOf(w).slice().sort((a,b)=>bySlot(a.linkedin,b.linkedin))
                            .map((x,i)=>liCard(x.linkedin, x.title, i));
    /* Cut twins render last and muted. They are still worth reading (the script films
       and ships elsewhere), but they are not part of this week's five. */
    const cutSrc = (w.distribution||[]).filter(x=>x.linkedin && x.linkedin.twin_cut===true
                                                  && t(x.id).status!=="ignored");
    const cuts = cutSrc.map((x,i)=>liCard(x.linkedin, x.title, i));
    const banked = bankedPostsOf(w).filter(x=>t(x.id).status!=="ignored")
                            .map((x,i)=>liCard(x, "", i));
    html = calendarBlock(w)
         + (solo.length?`<div class="sechdr">Written for LinkedIn only</div>`+solo.join(""):"")
         + (twins.length?`<div class="sechdr">Twins of this week's videos</div>`+twins.join(""):"")
         + (gtm.length?`<div class="sechdr">${esc(UI.leaders_hdr||"From leaders you study")}</div>`+gtm.join(""):"")
         + (cuts.length?`<div class="sechdr">Not twinned this week &middot; films and ships on other platforms</div>`
             +`<div style="opacity:.55">`+cuts.join("")+`</div>`:"")
         + (banked.length?`<div class="sechdr">Banked &middot; written and holding for a future week</div>`
             +`<div style="opacity:.55">`+banked.join("")+`</div>`:"");
    empty="No LinkedIn posts this week.";
  }
  else if(TAB==="insp"){ const cards=(w.inspiration||[]).map(inspCard).join(""); html=cards?`<div class="inspgrid">${cards}</div>`:""; empty="No viral inspiration logged this week."; }
  else if(TAB==="ammo"){ html=ammoRounds(w).map((r,i)=>ammoCard(w,r,i)).join(""); empty="No comment ammo this week. A round is one fact with a number and a source; the sentence stays yours."; }
  else if(TAB.startsWith("camp:")){
    /* A campaign tab renders its own items regardless of the selected week.
       Video pieces reuse scriptCard (film mode, tracker, twins all work);
       written pieces and assets reuse liCard. Tracking stays keyed by id in
       the same localStorage, so campaign items are logged like week items. */
    const c=CAMPAIGNS[+TAB.slice(5)];
    if(c){
      const alive=arr=>(arr||[]).filter(x=>t(x.id).status!=="ignored");
      const vids=alive([].concat(c.distribution||[], c.office||[]));
      const posts=alive(c.linkedin||[]);
      html = (c.positioning?`<p class="calnote" style="margin:0 0 18px">${esc(c.positioning)}</p>`:"")
        + (vids.length?`<div class="sechdr">To film</div>`+vids.map((x,i)=>scriptCard(x,false,i)).join(""):"")
        + (posts.length?`<div class="sechdr">Posts &amp; assets</div>`+posts.map((x,i)=>liCard(x,"",i)).join(""):"");
    }
    empty="This campaign is empty.";
  }
  document.getElementById("view").innerHTML = html || emptyState(empty);
}

(function init(){
  let savedTheme=null; try{savedTheme=localStorage.getItem("yapcut-theme");}catch(e){}
  if(!savedTheme) savedTheme=(window.matchMedia&&window.matchMedia("(prefers-color-scheme: light)").matches)?"light":"dark";
  applyTheme(savedTheme);
  const sel=document.getElementById("weekSel");
  sel.innerHTML = WEEKS.map(w=>`<option value="${w.week}">${String(w.week).toLowerCase()==="example"?"Example week (sample data)":"Week of "+w.week}</option>`).join("");
  const tabsRow=document.querySelector(".tabs");
  if(WEEKS.some(w=>ammoRounds(w).length)){
    const b=document.createElement("button");
    b.className="tab"; b.dataset.t="ammo"; b.onclick=()=>setTab("ammo");
    b.innerHTML=`<svg class="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>Ammo <span class="cnt" data-c="ammo"></span>`;
    tabsRow.appendChild(b);
  }
  /* The mark's bytes are inlined once, on #logo-mark; the tab icon points at that. */
  const mark=document.getElementById("logo-mark");
  if(mark && mark.tagName==="IMG" && mark.getAttribute("src")){
    const l=document.createElement("link"); l.rel="icon"; l.href=mark.getAttribute("src"); document.head.appendChild(l);
  }
  CAMPAIGNS.forEach((c,i)=>{
    const b=document.createElement("button");
    b.className="tab"; b.dataset.t="camp:"+i; b.onclick=()=>setTab("camp:"+i);
    b.innerHTML=`<svg class="ti" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>${esc(c.label||c.campaign||"Campaign")} <span class="cnt" data-c="camp:${i}"></span>`;
    tabsRow.appendChild(b);
  });
  const tb=document.getElementById("toolbar"), mh=document.querySelector(".masthead");
  if(tb&&mh&&"IntersectionObserver" in window){
    new IntersectionObserver(es=>tb.classList.toggle("scrolled",!es[0].isIntersecting),{threshold:0}).observe(mh);
  }
  render();
})();

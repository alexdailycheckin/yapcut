/* YapCut dashboard, 3.20. Data arrives in <script type="application/json"> blocks the build
   writes; nothing here is substituted by Python, so this file is plain JS that node --check reads.

   Three tabs. Film is the landing page: pick a lane, read the scripts, film. Post holds what is
   ready to go out (the posting gap, the week's calendar, the LinkedIn posts, comment ammo).
   Results holds what was filmed and how it landed. The tracking, the exports and their payload
   shapes are unchanged from 3.19: they are load-bearing downstream. */
function readJson(id, fallback){
  const el=document.getElementById(id); if(!el) return fallback;
  try { const v=JSON.parse(el.textContent); return v==null ? fallback : v; }
  catch(e) { console.error("dashboard: bad JSON in #"+id, e); return fallback; }
}
const WEEKS = readJson("weeks-data", []);
const CAMPAIGNS = readJson("campaigns-data", []);
const SEED = readJson("tracking-seed", {});
const PERF = readJson("perf-data", {cadence:[], perf:[], median:0});
const UI = readJson("ui-config", {});
const KEY = "outlier-radar-tracking";
const SEED_KEY = KEY+":seeded";
const AMMO_KEY = "outlier-radar-ammo";
const TAB_KEY = "yapcut-tab";
const THEME_KEY = "yapcut-theme";
const BLANK = {status:"idea", views:"", link:"", notes:"", carousel:false, body:null};
/* body: the post as it actually went out. An edit here overrides the embedded text everywhere
   the page reads it, and Export > Week file writes it back to disk so the next build inherits it. */

/* ---------------- tracking: tracking.jsonl is the truth on disk, the browser an overlay ---------------- */
/* Both reads and writes are guarded: where localStorage throws (Safari on file://, blocked site
   data, a full quota) an unguarded call took the whole click down with no visible error. */
const track = (function(){
  let local={}, seeded={};
  try { local = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch(e) { local = {}; }
  try { seeded = JSON.parse(localStorage.getItem(SEED_KEY) || "{}") || {}; } catch(e) { seeded = {}; }
  const out={};
  Object.keys(SEED).forEach(id=>{ out[id]=Object.assign({}, BLANK, SEED[id]); });
  Object.keys(local).forEach(id=>{
    /* An entry that still equals what the last build seeded was never touched here, so a newer
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
  } catch(e) {
    if(!STORAGE_DEAD){ STORAGE_DEAD = true; toast("Browser storage is blocked, so filmed and ignored marks will not survive a reload"); }
  }
}
function t(id){ return track[id] || Object.assign({}, BLANK); }
function bodyOf(x){ const b=t(x.id).body; return (b==null||b==="") ? (x._copy||x.body||"") : b; }
function setQuiet(id, patch){ track[id]=Object.assign(t(id), patch); save(); }
function setT(id, patch){ setQuiet(id, patch); renderAll(); if(FILM) drawFilm(); }
const isDone = x => ["filmed","posted"].includes(t(x.id).status);
const isOpen = x => !isDone(x) && t(x.id).status!=="ignored";

/* ---------------- small helpers ---------------- */
const $ = id => document.getElementById(id);
function esc(s){ return String(s==null?"":s).replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
const fmt = n => Number(n||0).toLocaleString("en-US",{maximumFractionDigits:1});
const MONTHS=["January","February","March","April","May","June","July","August","September","October","November","December"];
const ordinal = n => `${n}${n%100>=11&&n%100<=13?"th":({1:"st",2:"nd",3:"rd"})[n%10]||"th"}`;
const isIso = s => /^\d{4}-\d{2}-\d{2}/.test(String(s||""));
/* "2026-10-05" -> "October 5th": dates are written the way they are said. */
const spoken = iso => { if(!isIso(iso)) return String(iso||""); const [,m,d]=String(iso).slice(0,10).split("-").map(Number); return `${MONTHS[m-1]} ${ordinal(d)}`; };
const plural = (n, one, many) => `${n} ${n===1?one:(many||one+"s")}`;
const listText = a => a.length<=1 ? a.join("") : a.slice(0,-1).join(", ")+" and "+a[a.length-1];
const DOW=["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"];
/* Parsed as UTC on purpose: a local parse of a bare ISO date shifts the weekday west of Greenwich. */
const addDays = (iso, n) => { const d=new Date(String(iso).slice(0,10)+"T00:00:00Z"); d.setUTCDate(d.getUTCDate()+n); return d.toISOString().slice(0,10); };
const dow = iso => isIso(iso) ? DOW[new Date(String(iso).slice(0,10)+"T00:00:00Z").getUTCDay()] : "";
const daysBetween = (a, b) => Math.round((Date.parse(String(b).slice(0,10)+"T00:00:00Z")-Date.parse(String(a).slice(0,10)+"T00:00:00Z"))/86400000);
function todayIso(){ const n=new Date(); return `${n.getFullYear()}-${String(n.getMonth()+1).padStart(2,"0")}-${String(n.getDate()).padStart(2,"0")}`; }
const rangeText = (a, b) => { const [ma]=spoken(a).split(" "), [mb, db]=spoken(b).split(" "); return ma===mb ? `${spoken(a)} to ${db}` : `${spoken(a)} to ${mb} ${db}`; };
const help = (title, text) => `<button class="help" type="button" aria-label="What is this? ${esc(title)}: ${esc(text)}">?<span class="bubble" role="tooltip"><b>${esc(title)}</b>${esc(text)}</span></button>`;
/* Card header: kicker and a title that states the takeaway on the left, controls on the right. */
const head = (kick, title, ctl) => `<div class="card-h"><div>${kick?`<div class="kick">${kick}</div>`:""}<h3>${title}</h3></div>${ctl?`<div class="ctl">${ctl}</div>`:""}</div>`;
let toastTimer=0;
function toast(msg){ const el=$("toast"); if(!el) return; el.textContent=msg; el.hidden=false; clearTimeout(toastTimer); toastTimer=setTimeout(()=>{el.hidden=true;}, 2600); }
function copyText(text, msg){
  const done=()=>toast(msg||"Copied");
  if(navigator.clipboard&&navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done,()=>fallbackCopy(text,done));
  else fallbackCopy(text,done);
}
function fallbackCopy(text,cb){
  const ta=document.createElement("textarea"); ta.value=text; document.body.appendChild(ta); ta.select();
  try{document.execCommand("copy");}catch(e){}
  document.body.removeChild(ta); cb&&cb();
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

/* ---------------- LinkedIn-ready text ---------------- */
/* LinkedIn strips rich formatting on paste, so copy hands over text already styled at the
   character level. The stored body stays real text: the gates read it. Use bold sparingly and
   never on a number or the central claim: Unicode bold is unreadable to screen readers and parsers. */
function liBold(t){
  return t.replace(/[A-Za-z0-9]/g, c => { const u=c.codePointAt(0);
    if(u>=65&&u<=90) return String.fromCodePoint(0x1D5D4+u-65);
    if(u>=97&&u<=122) return String.fromCodePoint(0x1D5EE+u-97);
    if(u>=48&&u<=57) return String.fromCodePoint(0x1D7EC+u-48);
    return c; });
}
function liItalic(t){
  return t.replace(/[A-Za-z]/g, c => { const u=c.codePointAt(0);
    if(u>=65&&u<=90) return String.fromCodePoint(0x1D608+u-65);
    if(u>=97&&u<=122) return String.fromCodePoint(0x1D622+u-97);
    return c; });
}
function linkedinText(t){
  return (t||"")
    .replace(/\*\*([^*\n]+)\*\*/g, (_, x) => liBold(x))
    .replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, (_, p, x) => p + liItalic(x))
    .split("\n").map(l => l.replace(/^\s*[-*]\s+/, "↳ ")).join("\n")
    .replace(/\n{3,}/g, "\n\n");
}

/* ---------------- the week ---------------- */
let WI = 0;
const W = () => WEEKS[WI];
const curWeek = W;
const isExample = w => String(w&&w.week).toLowerCase()==="example";
function officeOf(w){ return (w.office&&w.office.length)?w.office:(w.food||[]); }
const LANES = [
  {k:"show", src:w=>w.distribution||[], help:"One news story a week, told as a teardown. The freshest story films first."},
  {k:"viral", src:officeOf, help:"Insider jokes riding a format that is rising right now. One person, one seat."},
  {k:"explainers", src:w=>w.explainers||[], label:"Explainers", help:"A how-to you learn first and explain second. It ships with your own step-by-step guide."},
  {k:"moments", src:w=>w.moments||[], label:"Moments", help:"Filmed, not read. A capture list for a day in the life or a 5-minute break."},
  {k:"days", src:w=>w.days||[], label:"Five days", help:"One short video a day, Monday to Friday, each in its own format."},
];
function laneLabel(L, w){
  if(L.label) return L.label;
  if(L.k==="viral") return UI.secondary_label || "Viral videos";
  return UI.primary_label || ((w.distribution||[])[0]||{}).franchise || "Industry";
}
/* Every video item in the week, in lane order. Everything that counts, finds or exports videos reads this. */
function videosOf(w){ return [].concat(w.distribution||[], officeOf(w), w.explainers||[], w.moments||[], w.days||[]); }
/* soloPosts = written for the feed alone; leaderPosts = mined from leaders the creator studies;
   twins = a video's twin, only when it earned a slot (a cut twin still lives in the file). */
function soloPostsOf(w){ return (w.linkedin||[]).filter(x=>x.banked!==true); }
function bankedPostsOf(w){ return (w.linkedin||[]).filter(x=>x.banked===true); }
function leaderPostsOf(w){ return w.gtm_linkedin||[]; }
function liveTwinsOf(w){ return (w.distribution||[]).filter(x=>x.linkedin && x.linkedin.twin_cut!==true && t(x.id).status!=="ignored"); }
function cutTwinsOf(w){ return (w.distribution||[]).filter(x=>x.linkedin && x.linkedin.twin_cut===true && t(x.id).status!=="ignored"); }
function findItem(id){
  const w=W();
  let it = w ? videosOf(w).find(x=>x.id===id) : null;
  if(!it && w) it=[].concat(w.linkedin||[], leaderPostsOf(w)).find(x=>x.id===id) || (w.distribution||[]).map(x=>x.linkedin).find(x=>x&&x.id===id);
  if(!it) for(const c of CAMPAIGNS){
    it=[].concat(c.distribution||[], c.office||[], c.linkedin||[]).find(x=>x.id===id);
    if(it) break;
  }
  return it || null;
}
function weekStartOf(w){ if(!w||!isIso(w.week)) return null; const s=String(w.week).slice(0,10); return dow(s)==="Sunday" ? addDays(s,1) : s; }
function weekLabel(w){
  if(isExample(w)) return "Example week";
  const s=weekStartOf(w); if(!s) return String(w.week);
  const d=daysBetween(s, todayIso());
  if(d>=0&&d<7) return "This week"; if(d>=7&&d<14) return "Last week"; if(d>=14&&d<21) return "2 weeks ago";
  return spoken(s);
}
const cleanTitle = x => String(x.title||x.text_hook||x.mechanic||"Untitled").replace(/^.*?\bEp\s?\d+:\s*/i,"");
/* A calendar cell has to say WHICH post, and a solo post carries no title: fall through to the
   hook, then the body's first line. A format label is never the answer to "which one is this". */
function postName(x){
  if(x.title) return x.title;
  if(x.text_hook) return x.text_hook;
  const b=bodyOf(x).trim();
  if(b){ const first=b.split("\n").find(l=>l.trim()); if(first) return first.length>72 ? first.slice(0,69).trimEnd()+"..." : first; }
  return "Post";
}
const statusName = {idea:"To film", filmed:"Filmed", posted:"Posted", ignored:"Ignored", scheduled:"Scheduled"};

/* ---------------- reading a script ---------------- */
/* One sentence per line, without breaking on decimals ("1.76%") or lowercase abbreviations. */
function splitSentences(text){
  if(!text) return [];
  return String(text).replace(/\s*\n+\s*/g," ").split(/(?<=[.?!…])\s+(?=[A-Z"'‘“£$€0-9])/).map(s=>s.trim()).filter(Boolean);
}
/* Move 2: the sentence naming what the viewer already believes, marked in place, because WHERE
   it sits is the thing worth seeing (a belief below the numbers is the 2026-09-07 failure). */
function beliefKey(s){ return String(s||"").toLowerCase().replace(/[^a-z0-9 ]/g,"").trim(); }
function opinionIdeas(x){ const o=x&&x.opinion; return (o&&Array.isArray(o.ideas)) ? o.ideas.filter(v=>typeof v==="string"&&v.trim()).slice(0,3) : []; }
function opinionLabel(){ return UI.opinion_label || "[YOUR OPINION, IF ANY]"; }
function readHtml(x){
  const bk=beliefKey(x.belief);
  const sec=(label, text, hk)=>{ const lines=splitSentences(text); return lines.length ? `<div class="sec2"><div class="lab">${label}</div>${lines.map(l=>{ const b=bk&&beliefKey(l)===bk; return `<p class="${hk?"hk":""}${b?" belief":""}"${b?' title="Move 2: the belief. Everything after this exists to break it."':""}>${esc(l)}</p>`; }).join("")}</div>` : ""; };
  const ideas=opinionIdeas(x);
  let h = sec("Hook", x.spoken_hook, true) + sec("Script", x.script)
    + (ideas.length ? `<div class="sec2"><div class="lab">${esc(opinionLabel())}, optional</div><p class="note">Off the cuff, your words. Take one, your own, or none and stop on the line above.</p><ul class="ideas">${ideas.map(v=>`<li>${esc(v)}</li>`).join("")}</ul></div>` : "")
    + sec("CTA, optional", x.cta);
  /* legacy fallback: pre-QA batches still on the old shape */
  if(!x.script && (x.hook || typeof x.beats==="string")) h = sec("Hook (legacy)", x.hook, true) + sec("Script (legacy)", typeof x.beats==="string"?x.beats:"") + h;
  return h;
}
/* The spoken read as plain text: hook + script + optional CTA. Skips the hook when the script
   already opens with it (most weeks duplicate that line). */
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
  const ideas=opinionIdeas(x);
  if(ideas.length) parts.push(opinionLabel()+"\nNot script: the take is said off the cuff, or skipped. Ideas: "+ideas.join(" / "));
  return parts.filter(Boolean).join("\n\n");
}
const table = (hd, rows) => `<div class="tablewrap"><table><thead><tr>${hd.map(h=>`<th>${h}</th>`).join("")}</tr></thead><tbody>${rows.join("")}</tbody></table></div>`;
function srcList(list){
  if(!list||!list.length) return "";
  const norm=list.map(s=>(typeof s==="string") ? {url:s, label:s.replace(/^https?:\/\/(www\.)?/,"").split("/")[0]} : s);
  return `<div><div class="lab">Sources: check before posting</div><div class="srcs">${norm.map(s=>s.url?`<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.label||s.url)}</a>`:`<span>${esc(s.label||"")}</span>`).join("")}</div></div>`;
}
function guideHtml(x){
  const g=x.guide; if(!g||typeof g!=="object") return "";
  const ul=a=>`<ul>${a.map(v=>`<li>${esc(v)}</li>`).join("")}</ul>`;
  return `<div class="guide">
    ${g.what_it_is?`<p><b>What it is.</b> ${esc(g.what_it_is)}</p>`:""}${g.who_its_for?`<p><b>Explained for.</b> ${esc(g.who_its_for)}</p>`:""}
    ${(g.you_need||[]).length?`<p><b>You need</b></p>${ul(g.you_need)}`:""}
    ${(g.steps||[]).length?`<p><b>Step by step</b></p><ol>${g.steps.map(s=>typeof s==="string"?`<li>${esc(s)}</li>`:`<li>${esc(s.do||"")}${s.why?` <small>${esc(s.why)}</small>`:""}${s.url?` <a href="${esc(s.url)}" target="_blank" rel="noopener">docs</a>`:""}</li>`).join("")}</ol>`:""}
    ${(g.say_it_simply||[]).length?`<p><b>Say it simply</b></p>${ul(g.say_it_simply)}`:""}
    ${g.watch_out?`<p><b>Watch out.</b> ${esc(g.watch_out)}</p>`:""}${g.try_it_first?`<p><b>Try it yourself first.</b> ${esc(g.try_it_first)}</p>`:""}</div>`;
}
function captureLine(x){
  const c=x.capture; if(!c) return "";
  if(typeof c==="string") return `capture: ${c}`;
  const bits=[]; if(c.mode) bits.push("capture: "+c.mode); if(c.fidelity!=null) bits.push("fidelity "+Math.round(c.fidelity*100)+"%"); if(c.source) bits.push(c.source);
  return bits.join(" · ");
}
function detail(x){
  let h="";
  const read=readHtml(x); if(read) h+=`<div class="read">${read}</div>`;
  if(x.guide) h+=`<div><div class="lab">Your guide: learn it before you film it</div>${guideHtml(x)}</div>`;
  if(Array.isArray(x.clips)&&x.clips.length){
    h+=`<div><div class="lab">Capture these${x.film_on?` on ${dow(x.film_on)}, ${spoken(x.film_on)}`:""}</div>${table(["Time","Moment","Shot"], x.clips.map(c=>typeof c==="string"?`<tr><td></td><td>${esc(c)}</td><td></td></tr>`:`<tr><td>${esc(c.t||"")}</td><td>${esc(c.moment||"")}</td><td>${esc(c.shot||"")}</td></tr>`))}</div>`;
    if(Array.isArray(x.vo)&&x.vo.length) h+=`<div><div class="lab">Voiceover, optional</div><ul class="ideas">${x.vo.map(v=>`<li>${esc(v)}</li>`).join("")}</ul></div>`;
  }
  if(Array.isArray(x.shot_list)&&x.shot_list.length) h+=`<div><div class="lab">Shot list: the receipts to capture</div>${table(["#","Beat","Shoot this"], x.shot_list.map(s=>`<tr><td>${esc(s.n!=null?s.n:"")}</td><td>${esc(s.beat||"")}</td><td>${esc(s.shoot||s.what||"")}${s.url?` <a href="${esc(s.url)}" target="_blank" rel="noopener">open</a>`:""}</td></tr>`))}</div>`;
  if(Array.isArray(x.beats)&&x.beats.length){
    const noVo=x.beats[0].on_screen!==undefined;
    h+=`<div><div class="lab">${noVo?"Beats: no voiceover, the captions carry it":"Beats: film these, voiceover to picture"}</div>${table(noVo?["Time","On screen","Action"]:["Role","Line","B-roll","Length"], x.beats.map(b=>noVo?`<tr><td>${esc(b.t)}</td><td>${esc(b.on_screen)||"(no caption, face only)"}</td><td>${esc(b.action)}</td></tr>`:`<tr><td>${esc(b.role)}</td><td>${esc(b.text)}</td><td>${esc(b.b_roll)}</td><td>${b.target_dur?esc(String(b.target_dur))+"s":""}</td></tr>`))}</div>`;
  }
  const notes=[["Directions, do not read",x.directions],["What they take away",x.story_line?x.value:""],["Edit",x.edit],["Why it works",x.psych],["Note",x.note]].filter(p=>p[1]);
  if(notes.length) h+=`<div class="two">${notes.map(([k,v])=>`<p class="note"><b>${k}.</b> ${esc(v)}</p>`).join("")}</div>`;
  const tiny=[captureLine(x), x.source_origin?"origin: "+x.source_origin:""].filter(Boolean);
  if(tiny.length) h+=`<p class="how">${esc(tiny.join(" · "))}</p>`;
  h+=srcList(x.sources);
  return h;
}
/* Three states, not two: "Awaiting approval" is a post that cleared the gate and waits on a yes. */
function qaPill(qa){
  if(qa==="passed") return `<span class="pill good">QA passed</span>`;
  if(qa==="pending-approval") return `<span class="pill">Awaiting approval</span>`;
  return qa ? `<span class="pill warn">Pre-QA</span>` : "";
}
/* Three neutral looks, none a verdict: own, reach and public are provenance, not quality. */
function proofPill(p){
  if(!p||!p.kind) return "";
  const k=String(p.kind).toLowerCase();
  return `<span class="pill${["reach","public"].includes(k)?" proof-"+k:""}" title="${esc(p.ref||"")}">${esc(p.kind)} proof</span>`;
}

/* ---------------- Film ---------------- */
let LANE = "all", SHOW_DONE = false;
const OPEN = new Set();
function lanes(){
  const w=W();
  const wk=LANES.map(L=>({k:L.k, label:laneLabel(L,w), help:L.help, items:L.src(w)})).filter(L=>L.items.length);
  const camps=CAMPAIGNS.map((c,i)=>({k:"camp:"+i, camp:true, label:c.label||c.campaign||"Campaign", help:c.positioning||"Runs across weeks.", items:[].concat(c.distribution||[], c.office||[])})).filter(L=>L.items.length);
  return wk.concat(camps);
}
function laneStat(L){
  const all=L.items.filter(x=>t(x.id).status!=="ignored");
  const posted=all.filter(x=>t(x.id).status==="posted").length, filmed=all.filter(x=>t(x.id).status==="filmed").length;
  return Object.assign({}, L, {total:all.length, posted, filmed, done:posted+filmed, left:all.length-posted-filmed});
}
const strip = (posted, filmed, total) => `<span class="strip" role="img" aria-label="${posted} posted, ${filmed} filmed, ${total-posted-filmed} to film">${posted?`<span class="p" style="flex:${posted}"></span>`:""}${filmed?`<span class="f" style="flex:${filmed}"></span>`:""}${total-posted-filmed>0?`<span style="flex:${total-posted-filmed}"></span>`:""}</span>`;
function queue(){
  const ls=lanes();
  const pick = LANE==="all" ? ls.filter(L=>!L.camp) : ls.filter(L=>L.k===LANE);
  return pick.flatMap(L=>L.items.map(x=>({x, L}))).filter(({x})=>SHOW_DONE || isOpen(x));
}
function promisesBlock(w){
  const list=Array.isArray(w.promised)?w.promised.filter(p=>p&&p.text):[];
  if(!list.length) return "";
  const open=list.filter(p=>!p.paid_in).length;
  return `<div class="promises"><div class="lab">Promises: ${open} open</div><ul>${list.map(p=>{ const paid=!!p.paid_in; return `<li class="${paid?"paid":"open"}"><span class="pst">${paid?"Paid "+esc(p.paid_in):"Due "+esc(p.due_week||"open")}</span><span>${esc(p.text)}</span>${p.made_in?`<span class="pmade">made ${esc(p.made_in)}</span>`:""}</li>`; }).join("")}</ul></div>`;
}
function hasBrief(w){ return !!(w.positioning||w.method||(w.coined_term&&w.coined_term.term)||(Array.isArray(w.signals)&&w.signals.length)||(w.experiment&&w.experiment.question)||(Array.isArray(w.promised)&&w.promised.length)); }
function renderFilm(){
  const w=W(); if(!w){ $("p-film").innerHTML=`<div class="empty">No week data yet. Run the radar to generate your first slate.</div>`; return; }
  const ls=lanes().map(laneStat);
  if(LANE!=="all" && !ls.some(L=>L.k===LANE)) LANE="all";
  const wk=ls.filter(L=>!L.camp), sum=k=>wk.reduce((a,L)=>a+L[k],0);
  const tiles=[{k:"all", label:"All lanes", help:"Every lane this week.", left:sum("left"), total:sum("total"), posted:sum("posted"), filmed:sum("filmed"), done:sum("done")}].concat(ls);
  const cur=tiles.find(L=>L.k===LANE)||tiles[0];
  const inLane=(LANE==="all"?wk:ls.filter(L=>L.k===LANE)).flatMap(L=>L.items);
  const doneN=inLane.filter(isDone).length, ignN=inLane.filter(x=>t(x.id).status==="ignored").length;
  const parts=String(w.positioning||"").split(/This week's lens:\s*/i);
  const lens=parts[1] ? `<b>This week's lens.</b> ${esc(parts[1].charAt(0).toUpperCase()+parts[1].slice(1))}` : (w.positioning?`<b>This week.</b> ${esc(w.positioning)}`:"");
  const title = LANE==="all" ? (cur.left?`${plural(cur.left,"script")} left to film`:"Everything is filmed")
    : cur.left ? `${cur.left} left in ${cur.label}` : `${cur.label}: all filmed`;
  const q=queue();
  $("p-film").innerHTML=`<section class="sec" aria-labelledby="h-q">
    ${(lens||hasBrief(w))?`<p class="lensline"><span>${lens}</span>${hasBrief(w)?`<button class="linkbtn" type="button" data-act="brief">Read the brief</button>`:""}</p>`:""}
    ${promisesBlock(w)}
    <div class="lanepick" role="group" aria-label="Pick a lane">${tiles.map(L=>`<button type="button" class="lt${LANE===L.k?" on":""}${L.left?"":" clear"}${L.camp?" camp":""}" data-lane="${esc(L.k)}" aria-pressed="${LANE===L.k}" title="${esc(L.help||"")}">
        <span class="lt-h">${esc(L.label)}</span>
        <span class="lt-n"><b>${L.left}</b>to film</span>
        ${strip(L.posted, L.filmed, L.total)}
        <span class="lt-s">${L.left?`${L.done} of ${L.total} filmed`:"All filmed"}</span></button>`).join("")}</div>
    <div class="qhead"><h2 id="h-q">${esc(title)}</h2><label class="chk" for="showDone"><input type="checkbox" id="showDone"${SHOW_DONE?" checked":""}>Show filmed (${doneN})${ignN?` and ignored (${ignN})`:""}</label></div>
    <div class="queue">${q.length ? q.map(({x,L},i)=>scriptCard(x,L,i)).join("") : `<div class="empty">Nothing left to film here. Every script in this lane is filmed, posted or ignored. Tick Show filmed to see them, or pick another lane.</div>`}</div>
  </section>`;
}
function scriptCard(x, L, i){
  const r=t(x.id), s=r.status, w=W();
  const isMoment = Array.isArray(x.clips) && x.clips.length;
  const kick=[esc(L.label), x.episode?`Episode ${esc(x.episode)}`:"", x.company?esc(x.company):"", isIso(x.news_date)?`news from ${spoken(x.news_date)}`:"",
    isIso(x.film_on)?`film on ${dow(x.film_on)}, ${spoken(x.film_on)}`:"", x.post_day&&!x.film_on?`posts ${esc(String(x.post_day).split(",")[0])}`:"", x.day?esc(x.day):""].filter(Boolean).join(" · ");
  const alts=Array.isArray(x.text_hook_alts)?x.text_hook_alts.map(a=>`<button type="button" class="alt" data-copy="${esc(a)}" title="Alternate hook for hook testing. Click to copy.">${esc(a)}</button>`).join(""):"";
  const seg=["idea","filmed","posted"].map(v=>`<button type="button" data-st="${v}" data-id="${esc(x.id)}" aria-pressed="${s===v}">${statusName[v]}</button>`).join("");
  const side = x.story_line ? ["The story", x.story_line] : (x.borrows||x.carries) ? ["Borrows", [x.borrows, x.carries?"Carries: "+x.carries:""].filter(Boolean).join(". ")] : x.mechanic ? ["Mechanic", x.mechanic] : x.value ? ["What they take away", x.value] : null;
  const tags=[qaPill(x.qa), ...(x.hook_styles||[]).map(v=>`<span class="pill">${esc(v)}</span>`), proofPill(x.proof), x.length?`<span class="pill">${esc(x.length)}</span>`:"", x.format&&!x.length?`<span class="pill">${esc(x.format)}</span>`:"",
    x.sensitivity?`<span class="pill warn">${esc(x.sensitivity)}</span>`:"", x.linkedin&&x.linkedin.twin_cut!==true?`<span class="pill on">LinkedIn twin</span>`:"", s==="posted"?`<span class="pill on">Posted</span>`:""].join("");
  const shots=(x.shot_list||[]).length, srcs=(x.sources||[]).length;
  const hasDetail = !!(readHtml(x)||x.guide||isMoment||shots||(Array.isArray(x.beats)&&x.beats.length)||x.directions||x.psych||srcs);
  return `<article class="card scard${isDone(x)?" isdone":""}${s==="ignored"?" ign":""}" id="c-${esc(x.id)}">
    ${head(`<span class="no">${String(i+1).padStart(2,"0")}</span> ${kick}`, esc(cleanTitle(x)), `<div class="seg" role="group" aria-label="Status">${seg}</div>`)}
    <div class="hookrow">
      <div><div class="lab">${isMoment?"On screen":"Text hook"}${help("Text hook","Burned on screen for sound-off viewers. A cold scroller should get what the video is about in one look.")}</div>
        <p class="burn">${esc(x.text_hook||cleanTitle(x))}</p>${alts?`<div class="alts">${alts}</div>`:""}
        ${x.visual_hook?`<p class="vis"><b>Show this first.</b> ${esc(x.visual_hook)}</p>`:""}</div>
      <div class="story">${side?`<div><div class="lab">${side[0]}</div><p>${esc(side[1])}</p></div>`:""}<div class="tags">${tags}</div></div>
    </div>
    <div class="foot-row">
      <div class="btns">
        ${hasDetail?`<button class="btn" type="button" data-act="film:${esc(x.id)}">${isMoment?"Capture list":"Film mode"}</button>`:""}
        ${hasDetail?`<button class="btn line" type="button" data-more="${esc(x.id)}" aria-expanded="${OPEN.has(x.id)}">${OPEN.has(x.id)?"Hide full script":"Full script"}</button>`:""}
        ${scriptText(x)?`<button class="btn line" type="button" data-act="copy:${esc(x.id)}">Copy script</button>`:""}
        ${x.guide?`<button class="btn line" type="button" data-act="guide:${esc(x.id)}">Your guide</button>`:""}
        <button class="btn line" type="button" data-act="carousel:${esc(x.id)}" aria-pressed="${!!r.carousel}" title="Flag for a carousel PDF, then Export > Carousel queue">${r.carousel?"Carousel ✓":"Carousel"}</button>
      </div>
      <div class="meta">${shots?`<span>${plural(shots,"shot")}</span>`:""}${srcs?`<span>${plural(srcs,"source")}</span>`:""}<button class="linkbtn" type="button" data-st="${s==="ignored"?"idea":"ignored"}" data-id="${esc(x.id)}">${s==="ignored"?"Restore":"Ignore"}</button></div>
    </div>
    ${OPEN.has(x.id)?`<div class="detail">${detail(x)}</div>`:""}
  </article>`;
}

/* Film mode: the read, full screen, one sentence per line. */
let FILM = null;
function openFilm(id){
  const ids=queue().map(q=>q.x.id);
  if(!ids.includes(id)) ids.unshift(id);
  FILM={ids, i:ids.indexOf(id)};
  drawFilm(); $("film").hidden=false; document.body.style.overflow="hidden";
}
function drawFilm(){
  const x=findItem(FILM.ids[FILM.i]); if(!x){ closeFilm(); return; }
  const L=lanes().find(L=>L.items.includes(x)), s=t(x.id).status;
  let body="";
  if(x.text_hook) body+=`<div><div class="lab">Text hook: burned on screen, not spoken</div><p class="burn">${esc(x.text_hook)}</p></div>`;
  if(x.visual_hook) body+=`<p class="note"><b>Show this first.</b> ${esc(x.visual_hook)}</p>`;
  if(x.story_line) body+=`<p class="note"><b>The story in one line.</b> ${esc(x.story_line)}</p>`;
  const read=readHtml(x); if(read) body+=`<div class="read">${read}</div>`;
  if(Array.isArray(x.clips)&&x.clips.length) body+=detail({clips:x.clips, film_on:x.film_on, vo:x.vo, edit:x.edit});
  else body+=detail({shot_list:x.shot_list, beats:x.beats, directions:x.directions, value:x.value, story_line:x.story_line});
  $("film").innerHTML=`<div class="filmbar"><div><div class="kick">Film mode · ${esc(L?L.label:"")} · ${FILM.i+1} of ${FILM.ids.length}</div><h3>${esc(cleanTitle(x))}</h3></div><button class="x" type="button" data-film-close aria-label="Close film mode">×</button></div>
    <div class="filmbody"><div class="in">${body}</div></div>
    <div class="filmfoot"><div class="seg" role="group" aria-label="Status">${["idea","filmed","posted"].map(v=>`<button type="button" data-st="${v}" data-id="${esc(x.id)}" aria-pressed="${s===v}">${statusName[v]}</button>`).join("")}</div>
      <span class="hint">Arrow keys move between scripts. Esc closes.</span>
      <div class="btns"><button class="btn line sm" type="button" data-film-step="-1"${FILM.i?"":" disabled"}>Previous</button><button class="btn sm" type="button" data-film-step="1"${FILM.i<FILM.ids.length-1?"":" disabled"}>Next script</button></div></div>`;
  $("film").querySelector(".filmbody").scrollTop=0;
}
function closeFilm(){ $("film").hidden=true; document.body.style.overflow=""; FILM=null; }

/* ---------------- Post ---------------- */
/* Everything with a day this week: LinkedIn posts, live twins, the five daily videos, and the
   moments' shoot days. Days come from select_linkedin.py; a week without them shows no calendar. */
function weekItems(w){
  const s=weekStartOf(w), out=[];
  const days=s ? [...Array(7)].map((_,i)=>addDays(s,i)) : [];
  const byName={}; days.forEach(d=>{ byName[dow(d)]=d; });
  const slot=x=>x.post_slot==null?"":(typeof x.post_slot==="number"?"slot "+x.post_slot:String(x.post_slot));
  soloPostsOf(w).concat(leaderPostsOf(w)).filter(x=>t(x.id).status!=="ignored").forEach(x=>{ if(isIso(x.post_day)) out.push({x, day:String(x.post_day).slice(0,10), cls:"li", what:["LinkedIn",slot(x),x.post_day_locked?"pinned":""].filter(Boolean).join(" · "), title:postName(x)}); });
  liveTwinsOf(w).forEach(v=>{ const tw=v.linkedin; if(isIso(tw.post_day)) out.push({x:tw, day:String(tw.post_day).slice(0,10), cls:"li", what:["LinkedIn twin",slot(tw),tw.post_day_locked?"pinned":""].filter(Boolean).join(" · "), title:cleanTitle(v)}); });
  (w.days||[]).filter(x=>t(x.id).status!=="ignored").forEach(x=>{ const d=isIso(x.post_day)?String(x.post_day).slice(0,10):byName[String(x.post_day||"").split(",")[0]]; if(d) out.push({x, day:d, cls:"vid", what:"Video · "+(x.day||"Five days"), title:cleanTitle(x)}); });
  (w.moments||[]).filter(x=>t(x.id).status!=="ignored").forEach(x=>{ if(isIso(x.film_on)) out.push({x, day:String(x.film_on).slice(0,10), cls:"shoot", what:"Shoot"+(x.length?" · "+x.length:""), title:cleanTitle(x)}); });
  const cols=days.length ? days : [...new Set(out.map(e=>e.day))].sort();
  return {days:cols, items:out.filter(e=>cols.includes(e.day))};
}
function calendar(cal){
  const today=todayIso();
  return `<div class="cal">${cal.days.map(d=>{
    const evs=cal.items.filter(e=>e.day===d);
    return `<div class="day${d===today?" today":d<today?" past":""}"><h5><span>${dow(d).slice(0,3)}${d===today?" · today":""}</span><b>${Number(d.slice(8))}</b></h5>
      <div class="evs">${evs.length?evs.map(e=>{ const st=t(e.x.id).status, done=e.cls==="shoot"?["filmed","posted"].includes(st):st==="posted";
        return `<button type="button" class="ev ${e.cls}${done?" done":""}" data-act="${e.cls==="li"?"post:":"film:"}${esc(e.x.id)}"><small>${esc(e.what)}</small><span>${esc(e.title)}</span></button>`; }).join(""):`<span class="emptyday">Nothing planned</span>`}</div></div>`;
  }).join("")}</div>`;
}
const LI_STATES=["idea","scheduled","posted"];
function visualBlock(v){
  if(!v||!v.prompt) return "";
  const meta=[v.format,v.model,v.aspect].filter(Boolean).map(esc).join(" · ");
  return `<div><div class="lab">Asset${meta?": "+meta:""}</div>${v.why?`<p class="note">${esc(v.why)}</p>`:""}<div class="promptbox">${esc(v.prompt)}</div><div class="btns" style="margin-top:8px"><button class="btn line sm" type="button" data-copy="${esc(v.prompt)}">Copy image prompt</button></div></div>`;
}
/* Where the built asset lives on disk. Reads the canonical `assets` written by add_post.py, and the
   two hand-written shapes week files carried before anything consumed them: a bare `carousel`
   path and `visual.path`. Relative paths are stored against the workspace root. */
function assetsPath(x){
  if(!x) return "";
  const a=x.assets;
  if(typeof a==="string"&&a.trim()) return a.trim();
  if(a&&typeof a==="object"&&a.path) return String(a.path).trim();
  if(typeof x.carousel==="string"&&x.carousel.trim()) return x.carousel.trim();
  if(x.visual&&typeof x.visual.path==="string"&&x.visual.path.trim()) return x.visual.path.trim();
  return "";
}
function assetsBlock(x){
  const rel=assetsPath(x); if(!rel) return "";
  const root=(UI.workspace||"").replace(/\/+$/,"");
  const abs=(rel.startsWith("/")||/^[a-zA-Z]:[\\/]/.test(rel)) ? rel : (root?root+"/"+rel:rel);
  const label=(x.assets&&x.assets.label)||abs.replace(/\/+$/,"").split("/").pop()||abs;
  /* file:// so the browser opens the folder. Chrome refuses some file:// navigation silently, so
     the path is copyable too: Cmd+Shift+G in Finder always works. */
  return `<div><div class="lab">Assets</div><p class="note"><a href="${esc("file://"+encodeURI(abs).replace(/#/g,"%23"))}" target="_blank" rel="noopener">${esc(label)}</a></p><div class="btns" style="margin-top:8px"><button class="btn line sm" type="button" data-copy="${esc(abs)}">Copy path</button></div></div>`;
}
/* held[] are the receipts kept OUT of the post for the comments; reply_stance is the one line to
   hold when the thread pushes back. Read before replying, never copied with the post. */
function replyBlock(x){
  const held=Array.isArray(x.held)?x.held.filter(h=>h&&(h.fact||h.source)):[];
  if(!held.length && !x.reply_stance) return "";
  return `<div class="ctxbox">${x.reply_stance?`<p class="note"><b>Reply stance.</b> ${esc(x.reply_stance)}</p>`:""}${held.length?`<div><div class="lab">Held receipts: for the comments, not the post</div><ul class="ideas">${held.map(h=>`<li>${esc(h.fact||"")}${h.source?` <a href="${esc(h.source)}" target="_blank" rel="noopener">source</a>`:""}</li>`).join("")}</ul></div>`:""}</div>`;
}
function liCard(x, title, opts){
  opts=opts||{};
  const r=t(x.id), s=r.status;
  const slot=x.post_slot==null?"":(typeof x.post_slot==="number"?"slot "+x.post_slot:String(x.post_slot));
  const when=isIso(x.post_day) ? `${dow(x.post_day)}, ${spoken(x.post_day)}${slot?" · "+slot:""}${x.post_day_locked?" · pinned":""}` : "No day set";
  const shape=x.shape ? String(x.shape).replace(/^F\d_/,"") : (x.medium||x.type||"");
  const kick=[when, x.series||x.kind||"", shape, x.job||"", x.twin_cut===true?"not twinned":"", x.banked===true?"banked":""].filter(Boolean).map(esc).join(" · ");
  const more=visualBlock(x.visual)+assetsBlock(x)+srcList(x.sources)+replyBlock(x);
  return `<article class="card s6 pcard${s==="posted"?" done":""}${opts.muted?" muted":""}" id="licard-${esc(x.id)}">
    ${head(kick, esc(title||postName(x)), `<div class="seg" role="group" aria-label="Status">${LI_STATES.map(v=>`<button type="button" data-st="${v}" data-id="${esc(x.id)}" aria-pressed="${s===v}">${v==="idea"?"Draft":statusName[v]}</button>`).join("")}</div>`)}
    ${opts.twinOf?`<p class="note">Written twin of the video "${esc(opts.twinOf)}".</p>`:""}
    <div class="body" id="tb-${esc(x.id)}">${esc(linkedinText(bodyOf(x)))}</div>
    ${r.body!=null&&r.body!==""?`<p class="edited">Edited here, not yet in the week file. Export > Week file saves it.</p>`:""}
    <div class="foot-row"><div class="btns">
      <button class="btn" type="button" data-act="copyli:${esc(x.id)}">Copy for LinkedIn</button>
      <button class="btn line" type="button" data-expand="tb-${esc(x.id)}">Read all</button>
      <button class="btn line" type="button" data-act="edit:${esc(x.id)}">Edit</button>
      ${x._notes?`<button class="btn line" type="button" data-act="notes:${esc(x.id)}">Posting notes</button>`:""}
      ${more?`<button class="btn line" type="button" data-expand="mo-${esc(x.id)}">Details</button>`:""}
    </div><div class="tags">${qaPill(x.qa)}</div></div>
    ${more?`<div class="more" id="mo-${esc(x.id)}" hidden>${more}</div>`:""}
  </article>`;
}
/* Edit the post body in place. Textarea, not contenteditable: the body is plain text with hard
   line breaks, and contenteditable turns pasted text into markup. */
function editBody(id){
  const host=$("tb-"+id); if(!host||host.dataset.editing) return;
  const item=findItem(id)||{id};
  const ta=document.createElement("textarea"); ta.className="bodyedit"; ta.value=bodyOf(item);
  host.dataset.editing="1"; host.hidden=true; host.parentNode.insertBefore(ta, host.nextSibling);
  const bar=document.createElement("div"); bar.className="btns";
  bar.innerHTML='<button class="btn sm" type="button" data-a="save">Save</button><button class="btn line sm" type="button" data-a="revert">Revert to week file</button><button class="btn line sm" type="button" data-a="cancel">Cancel</button>';
  ta.parentNode.insertBefore(bar, ta.nextSibling); ta.focus();
  bar.onclick=e=>{
    const a=e.target.dataset&&e.target.dataset.a; if(!a) return;
    e.stopPropagation();
    if(a==="save"){ const v=ta.value.trim(); setT(id,{body: v===((item._copy||item.body||"").trim())?null:v}); toast("Saved in this browser. Export > Week file puts it on disk."); }
    else if(a==="revert"){ setT(id,{body:null}); toast("Back to the week file text"); }
    else { host.dataset.editing=""; host.hidden=false; ta.remove(); bar.remove(); }
  };
}
/* ---------------- ammo ---------------- */
/* A round is a fact with a number and a source. Spent state lives in localStorage under its own
   key; a round the week file already marks spent_on starts spent. */
let AMMO=(function(){ try { return JSON.parse(localStorage.getItem(AMMO_KEY)||"{}")||{}; } catch(e) { return {}; } })();
function ammoRounds(w){ return Array.isArray(w&&w.ammo)?w.ammo.filter(r=>r&&(r.fact||r.number)):[]; }
function ammoKey(w,r,i){ return String(w.week)+"|"+(r.id||r.fact||i); }
function isSpent(w,r,i){ const k=ammoKey(w,r,i); return AMMO[k]!==undefined ? !!AMMO[k] : !!r.spent_on; }
function toggleSpent(i){
  const w=W(), r=ammoRounds(w)[i]; if(!w||!r) return;
  const k=ammoKey(w,r,i); AMMO[k]=!isSpent(w,r,i);
  try { localStorage.setItem(AMMO_KEY, JSON.stringify(AMMO)); } catch(e) {}
  renderAll(); toast(AMMO[k]?"Marked spent":"Back in the list");
}
function ammoRow(w, r, i){
  const sp=isSpent(w,r,i), src=String(r.source||"");
  const lanesP=Array.isArray(r.lanes)?r.lanes.map(l=>`<span class="pill">${esc(l)}</span>`).join(""):"";
  return `<div class="arow${sp?" spent":""}"><p>${esc(r.fact||"")}${r.number?` <b>${esc(r.number)}</b>`:""}</p>
    <small>${src.startsWith("http")?`<a href="${esc(src)}" target="_blank" rel="noopener">${esc(src.replace(/^https?:\/\/(www\.)?/,"").split("/")[0])}</a>`:esc(src)}${lanesP}${sp&&r.spent_on&&AMMO[ammoKey(w,r,i)]===undefined?`<span>spent ${esc(r.spent_on)}</span>`:""}</small>
    <div class="btns"><button class="btn line sm" type="button" data-act="copyammo:${i}">Copy</button><button class="btn ghost sm" type="button" data-act="spend:${i}" aria-pressed="${sp}">${sp?"Spent":"Mark spent"}</button></div></div>`;
}
const PLATFORM={linkedin:"LinkedIn", tiktok:"TikTok", instagram:"Instagram", youtube:"YouTube", x:"X"};
const poss = n => n+(/s$/.test(n)?"'":"'s");
function multOf(i){ const m=String(i.metric||"").match(/\(([\d.]+)x\)/); return m?Number(m[1]):null; }
function linkOf(i){ const m=String(i.link||"").match(/https?:\/\/\S+/); return m?m[0]:""; }
function renderPost(){
  const w=W(); if(!w){ $("p-post").innerHTML=""; return; }
  const cal=weekItems(w), solo=soloPostsOf(w).filter(x=>t(x.id).status!=="ignored");
  const byDay=(a,b)=>String(a.post_day||"9").localeCompare(String(b.post_day||"9"))||((+a.post_slot||99)-(+b.post_slot||99));
  const vids=videosOf(w), waiting=vids.filter(x=>t(x.id).status==="filmed").length, postedV=vids.filter(x=>t(x.id).status==="posted").length, made=waiting+postedV;
  const liN=cal.items.filter(e=>e.cls==="li").length, vidN=cal.items.filter(e=>e.cls==="vid").length, shootN=cal.items.filter(e=>e.cls==="shoot").length;
  const nextLi=cal.items.filter(e=>e.cls==="li"&&t(e.x.id).status!=="posted").sort((a,b)=>a.day.localeCompare(b.day))[0];
  const postedLi=solo.filter(x=>t(x.id).status==="posted").length;
  const ammo=ammoRounds(w), insp=w.inspiration||[], best=insp.filter(multOf).sort((a,b)=>multOf(b)-multOf(a))[0];
  const legend=`<div class="lkey"><span><i style="background:var(--blue)"></i>LinkedIn</span><span><i style="background:var(--b3)"></i>Video</span><span><i style="border:1px dashed var(--mute-line)"></i>Shoot</span></div>`;
  const section=(id, h, inner)=>inner?`<section class="sec" aria-labelledby="${id}"><div class="sec-h"><h2 id="${id}">${h}</h2></div>${inner}</section>`:"";
  const grid=cards=>cards.length?`<div class="grid">${cards.join("")}</div>`:"";
  const campPosts=CAMPAIGNS.map((c,i)=>({c, posts:(c.linkedin||[]).filter(x=>t(x.id).status!=="ignored")})).filter(o=>o.posts.length);
  $("p-post").innerHTML=`
    <section class="sec" aria-label="Headline numbers"><div class="grid">
      <div class="card kpi s6" style="align-content:space-between">
        <div class="foot-row"><div class="kick" style="margin:0">Videos posted this week</div>${waiting?`<button class="btn" type="button" data-act="fixPost">Fix it</button>`:""}</div>
        <div class="val${postedV?"":" zero"}">${postedV} <span>of ${made} filmed</span></div>
        ${strip(postedV, waiting, made||1)}
        <div class="lkey"><span><i style="background:var(--blue)"></i>Posted ${postedV}</span><span><i style="background:var(--b3)"></i>Filmed, not posted ${waiting}</span></div>
        <p class="small">${waiting?`${plural(waiting,"video")} ${waiting===1?"is":"are"} filmed and waiting to be cut.`:made?"Everything filmed is posted.":"Nothing filmed yet this week."}</p>
      </div>
      <div class="card mids s6">
        <div class="mid"><div class="kick">On the calendar</div><div class="val">${liN+vidN}</div><p class="small">${plural(liN,"LinkedIn post")}, ${plural(vidN,"daily video")}${shootN?` and ${plural(shootN,"shoot")}`:""}.${nextLi?` Next post: ${esc(nextLi.title)}, ${dow(nextLi.day)}.`:""}</p></div>
        <div class="mid"><div class="kick">LinkedIn posts out</div><div class="val${postedLi||!solo.length?"":" zero"}">${postedLi}</div><p class="small">Of ${plural(solo.length,"post")} written for this week, twins not counted.</p></div>
        ${PERF.perf&&PERF.perf.length?`<div class="mid"><div class="kick">Typical LinkedIn post${help("Median","The middle post: half did better, half did worse. One viral post can't drag it up the way it drags an average.")}</div><div class="val">${fmt(PERF.median)}</div><p class="small">Impressions, the median across ${PERF.perf.length} measured posts.</p></div>`
          :`<div class="mid"><div class="kick">Comment ammo</div><div class="val">${ammo.filter((r,i)=>!isSpent(w,r,i)).length}</div><p class="small">Facts with a source, unused this week.</p></div>`}
      </div>
    </div></section>
    ${cal.days.length?section("h-cal","The week ahead",`<div class="grid"><div class="card s12">${head(rangeText(cal.days[0],cal.days[cal.days.length-1]), `${plural(liN+vidN,"post")} and ${plural(shootN,"shoot")}`, legend)}${calendar(cal)}<p class="how">Days come from <code>select_linkedin.py</code>, in decay order: the item that loses value soonest goes first. Re-run it to reassign, or set <code>"post_day_locked": true</code> on a post to pin it.</p></div></div>`):""}
    ${section("h-li","Written for LinkedIn", grid(solo.slice().sort(byDay).map(x=>liCard(x, postName(x)))))}
    ${section("h-tw","Twins of your videos", grid(liveTwinsOf(w).slice().sort((a,b)=>byDay(a.linkedin,b.linkedin)).map(v=>liCard(v.linkedin, v.linkedin.title||cleanTitle(v), {twinOf:cleanTitle(v)}))))}
    ${section("h-ld", esc(UI.leaders_hdr||"From leaders you study"), grid(leaderPostsOf(w).filter(x=>t(x.id).status!=="ignored").slice().sort(byDay).map(x=>liCard(x, postName(x)))))}
    ${section("h-cut","Not twinned this week", grid(cutTwinsOf(w).map(v=>liCard(v.linkedin, v.linkedin.title||cleanTitle(v), {twinOf:cleanTitle(v), muted:true}))))}
    ${section("h-bank","Banked for a future week", grid(bankedPostsOf(w).filter(x=>t(x.id).status!=="ignored").map(x=>liCard(x, postName(x), {muted:true}))))}
    ${campPosts.map((o,k)=>section("h-camp"+k, esc(o.c.label||o.c.campaign||"Campaign"), (o.c.positioning?`<p class="note">${esc(o.c.positioning)}</p>`:"")+grid(o.posts.map(x=>liCard(x, postName(x)))))).join("")}
    ${insp.length?section("h-insp","What worked for others",`<div class="grid"><div class="card s12">${head("Posts that beat their creator's median", best?`${esc(poss(best.creator))} top post hit ${multOf(best).toFixed(1)} times the usual`:"Posts worth a look this week")}
      <div class="rows">${insp.map(i=>{ const m=multOf(i); return `<div class="irow"><div class="x">${m?m.toFixed(1)+"x":"n/a"}<small>${esc(PLATFORM[i.platform]||i.platform||"")}</small></div><div><b>${esc(i.creator||"")}</b><p>${esc(i.metric||"")}${i.metric_confidence?` (${esc(i.metric_confidence)})`:""}</p><p>${esc(i.mechanic||"")}</p></div>${linkOf(i)?`<a class="btn line sm" href="${esc(linkOf(i))}" target="_blank" rel="noopener">Open</a>`:""}</div>`; }).join("")}</div></div></div>`):""}
    ${ammo.length?section("h-am","Comment ammo",`<div class="grid"><div class="card s12">${head(`Facts with a number and a source${help("Ammo","A fact with a number and a source, ready for your comments. The sentence stays yours.")}`, `${plural(ammo.filter((r,i)=>!isSpent(w,r,i)).length,"fact")} unused out of ${ammo.length}`)}<div class="rows">${ammo.map((r,i)=>ammoRow(w,r,i)).join("")}</div></div></div>`):""}`;
}

/* ---------------- Results ---------------- */
let PERF_ALL=false;
function renderResults(){
  const w=W(), c=PERF.cadence||[], perf=PERF.perf||[];
  const filmed=c.reduce((a,r)=>a+r.filmed,0), posted=c.reduce((a,r)=>a+r.posted,0);
  const top=perf[0];
  const med=a=>{ if(!a.length) return 0; const s=a.map(p=>p.impressions).sort((x,y)=>x-y), m=s.length>>1; return s.length%2?s[m]:Math.round((s[m-1]+s[m])/2); };
  const mine=perf.filter(p=>p.radar), own=perf.filter(p=>!p.radar);
  const done=w?videosOf(w).filter(x=>isDone(x)):[];
  $("p-results").innerHTML=`
    <section class="sec" aria-label="Headline numbers"><div class="grid">
      <div class="card kpi s7">
        <div class="kick" style="margin:0">${c.length?`Filmed since ${spoken(c[0].week)}`:"Filmed"}</div>
        <div class="row1"><div class="val">${filmed}</div>${c.length?`<span class="badge${posted<filmed/2?" down":""}">${posted} posted</span>`:""}</div>
        ${c.length>1?`<div class="chart" id="cadence"></div><div class="legend"><span><i class="ln" style="background:var(--b3)"></i>Filmed</span><span><i class="ln" style="background:var(--blue)"></i>Posted</span></div>`:`<p class="small">The weekly chart starts once two weeks of Filmed and Posted marks are in performance/tracking.jsonl.</p>`}
      </div>
      <div class="card mids s5">
        <div class="mid"><div class="kick">Measured posts</div><div class="val">${perf.length}</div><p class="small">${perf.length?"The latest measurement of each post you logged.":"None yet. log_perf.py logs a post's numbers."}</p></div>
        ${perf.length?`<div class="mid"><div class="kick">Typical post${help("Median","The middle post: half did better, half did worse. One viral post can't drag it up the way it drags an average.")}</div><div class="val">${fmt(PERF.median)}</div><p class="small">Impressions.${mine.length&&own.length?` From YapCut ${fmt(med(mine))}, your own ${fmt(med(own))}.`:""}</p></div>
        <div class="mid"><div class="kick">Top post</div><div class="val">${fmt(top.impressions)}</div><p class="small">${esc(top.title)}.</p></div>`:""}
      </div>
    </div></section>
    ${perf.length?`<section class="sec" aria-labelledby="h-perf"><div class="sec-h"><h2 id="h-perf">Every measured post</h2></div>
      <div class="grid"><div class="card s12" id="perfCard">${head(`Impressions, latest measurement per post${help("Early","Measured less than a week after posting, so the number is still growing.")}`, PERF.median?`Your top post reached ${Math.round(top.impressions/PERF.median)} times the typical one`:"Your measured posts", `<button class="linkbtn" type="button" id="perfTbl" aria-expanded="false">Show table</button>`)}
        <div class="legend"><span><i style="background:var(--blue)"></i>From YapCut</span><span><i style="background:var(--mute)"></i>Your own</span></div>
        <div class="bars" id="perfBars"></div>
        <div class="tablewrap" id="perfTable" hidden>${table(["Post","Impressions","Reactions","Comments","Measured"], perf.map(p=>`<tr><td>${esc(p.title)}</td><td>${fmt(p.impressions)}</td><td>${fmt(p.reactions)}</td><td>${fmt(p.comments)}</td><td>${esc(p.measured?spoken(p.measured):"")}</td></tr>`))}</div>
        <div class="foot-row"><button class="linkbtn" type="button" id="perfMore">${perf.length>12?`Show all ${perf.length}`:""}</button><span class="how">A log, not a verdict. Early means under a week old.</span></div>
      </div></div></section>`:""}
    <section class="sec" aria-labelledby="h-fl"><div class="sec-h"><h2 id="h-fl">This week's filmed videos</h2></div>
      <div class="grid"><div class="card s12">${head("Log views and the link once a video is live", done.length?`${plural(done.filter(x=>t(x.id).status==="posted").length,"video")} posted out of ${done.length} filmed`:"Nothing filmed this week yet")}
        ${done.length?`<div><div class="trow hd"><div>Video</div><div>Status</div><div>Views</div><div>Link to the post</div><div>Notes</div></div>${done.map(x=>{ const L=lanes().find(L=>L.items.includes(x)); return `<div class="trow"><div><b>${esc(cleanTitle(x))}</b><small>${esc(L?L.label:"")}</small></div><div><div class="seg" role="group" aria-label="Status">${["filmed","posted"].map(v=>`<button type="button" data-st="${v}" data-id="${esc(x.id)}" aria-pressed="${t(x.id).status===v}">${statusName[v]}</button>`).join("")}</div></div><div><input type="number" inputmode="numeric" placeholder="Views" value="${esc(t(x.id).views)}" data-field="views" data-id="${esc(x.id)}" aria-label="Views"></div><div><input placeholder="Paste the link" value="${esc(t(x.id).link)}" data-field="link" data-id="${esc(x.id)}" aria-label="Link"></div><div><input placeholder="Notes" value="${esc(t(x.id).notes)}" data-field="notes" data-id="${esc(x.id)}" aria-label="Notes"></div></div>`; }).join("")}</div>`:""}
        <p class="how">Views, links and notes stay in this browser until Export > Performance writes them for <code>log_perf.py --import</code>.</p>
      </div></div></section>`;
  drawResults();
}
function drawResults(){
  if($("p-results").hidden) return;
  const c=PERF.cadence||[];
  if($("cadence")) lineChart($("cadence"), {dates:c.map(r=>r.week), series:[{name:"Filmed", values:c.map(r=>r.filmed), color:css("--b3")},{name:"Posted", values:c.map(r=>r.posted), color:css("--blue"), you:true}], height:220});
  if($("perfBars")){
    const rows=(PERF_ALL?PERF.perf:PERF.perf.slice(0,12)), max=Math.max(1,...PERF.perf.map(p=>p.impressions));
    $("perfBars").innerHTML=rows.map((p,i)=>`<div class="brow"><span class="r">${i+1}</span><span class="n" title="${esc(p.title)}">${esc(p.title+(p.mature?"":" (early)"))}</span><span class="t"><span style="width:${Math.max(p.impressions>0?2:0,p.impressions/max*100).toFixed(1)}%;background:${p.radar?"var(--blue)":"var(--mute)"}"></span></span><span class="v">${fmt(p.impressions)}</span></div>`).join("");
    if($("perfMore")&&PERF.perf.length>12) $("perfMore").textContent=PERF_ALL?"Show top 12":`Show all ${PERF.perf.length}`;
  }
}
/* A line chart drawn to one scale, with a hover readout. */
const css = v => getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const NS="http://www.w3.org/2000/svg";
function svgEl(tag, attrs){ const e=document.createElementNS(NS, tag); for(const k in attrs) e.setAttribute(k, attrs[k]); return e; }
function niceMax(v){ if(v<=0) return 1; const p=Math.pow(10,Math.floor(Math.log10(v))), n=v/p; return (n<=1?1:n<=2?2:n<=2.5?2.5:n<=5?5:10)*p; }
const sd = iso => { const [,m,d]=String(iso).slice(0,10).split("-").map(Number); return MONTHS[m-1].slice(0,3)+" "+d; };
function lineChart(host, {dates, series, height}){
  if(!host||!host.clientWidth||!dates.length) return;
  host.innerHTML="";
  const W=Math.max(280, host.clientWidth), H=height||220, endW=Math.min(130, W*.24), P={l:44, r:endW, t:12, b:28};
  const iw=W-P.l-P.r, ih=H-P.t-P.b, n=dates.length;
  const vmax=niceMax(Math.max(...series.flatMap(s=>s.values), 1));
  const x=i=>P.l+(n===1?iw/2:i/(n-1)*iw), y=v=>P.t+ih-v/vmax*ih;
  const svg=svgEl("svg",{width:W, height:H, role:"img", "aria-label":series.map(s=>s.name).join(" and ")+" per week"});
  const ink3=css("--ink-3"), line=css("--line"), font="-apple-system, Helvetica Neue, Arial, sans-serif";
  [0,.5,1].forEach(f=>{ const yy=y(vmax*f); svg.appendChild(svgEl("line",{x1:P.l, x2:W-P.r+4, y1:yy, y2:yy, stroke:line})); const tx=svgEl("text",{x:P.l-10, y:yy+4, "text-anchor":"end", fill:ink3, "font-size":11, "font-family":font}); tx.textContent=fmt(Math.round(vmax*f)); svg.appendChild(tx); });
  const xi=n>2?[0,Math.floor((n-1)/2),n-1]:[...Array(n).keys()];
  xi.forEach((i,k)=>{ const tx=svgEl("text",{x:x(i), y:H-6, "text-anchor":k===0?"start":k===xi.length-1?"end":"middle", fill:ink3, "font-size":11, "font-family":font}); tx.textContent=sd(dates[i]); svg.appendChild(tx); });
  series.forEach(s=>{
    const d=s.values.map((v,i)=>`${i?"L":"M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join("");
    svg.appendChild(svgEl("path",{d, fill:"none", stroke:s.color, "stroke-width":s.you?3:2, "stroke-linejoin":"round", "stroke-linecap":"round"}));
    svg.appendChild(svgEl("circle",{cx:x(n-1), cy:y(s.values[n-1]), r:4.5, fill:s.color, stroke:css("--panel"), "stroke-width":2}));
  });
  const labs=series.map(s=>({s, y:y(s.values[n-1])})).sort((a,b)=>a.y-b.y);
  for(let i=1;i<labs.length;i++) if(labs[i].y-labs[i-1].y<15) labs[i].y=labs[i-1].y+15;
  labs.forEach(({s,y:yy})=>{ const tx=svgEl("text",{x:W-P.r+12, y:yy+4, fill:s.you?css("--ink"):css("--ink-2"), "font-size":12, "font-weight":s.you?700:500, "font-family":font}); tx.textContent=`${s.name} ${fmt(s.values[n-1])}`; svg.appendChild(tx); });
  const hit=svgEl("rect",{x:P.l, y:P.t, width:iw, height:ih, fill:"transparent"});
  hit.addEventListener("mousemove", ev=>{
    const i=Math.max(0,Math.min(n-1,Math.round((ev.clientX-svg.getBoundingClientRect().left-P.l)/iw*(n-1))));
    const tip=$("tip"); tip.innerHTML=`<div class="d">Week of ${spoken(dates[i])}</div>${series.map(s=>`<div class="r"><span><i style="background:${s.color}"></i>${esc(s.name)}</span><b>${fmt(s.values[i])}</b></div>`).join("")}`;
    tip.hidden=false; tip.style.left=Math.min(ev.clientX+14, innerWidth-180)+"px"; tip.style.top=Math.max(8, ev.clientY-80)+"px";
  });
  hit.addEventListener("mouseleave", ()=>{ $("tip").hidden=true; });
  svg.appendChild(hit);
  host.appendChild(svg);
}

/* ---------------- exports (payload shapes are load-bearing downstream) ---------------- */
function exportFilmed(){
  const w=curWeek(); if(!w) return;
  const items=videosOf(w).filter(x=>t(x.id).status==="filmed");
  if(!items.length){alert("Nothing marked Filmed in this week yet.\n\nOn each video you shot, click 'Filmed', then export.");return;}
  let out=`FILMED THIS WEEK (week of ${w.week}) - ${items.length} clip(s). Edit each per its spec using the tiktok-yap-editor skill.\n\n`;
  items.forEach((x,i)=>{
    out+=`### ${i+1}. ${x.title||x.mechanic||x.text_hook}  [${x.id}]\n`;
    if(x.text_hook)   out+=`- TEXT HOOK (burn on screen, NOT spoken): ${x.text_hook}\n`;
    if(x.visual_hook) out+=`- VISUAL HOOK (show, first 1-2s): ${x.visual_hook}\n`;
    if(x.spoken_hook) out+=`- HOOK (say this, your opening 1-2 lines): ${x.spoken_hook}\n`;
    if(x.belief)      out+=`- BELIEF (move 2, said before any receipt): ${x.belief}\n`;
    if(x.script)      out+=`- SCRIPT (read verbatim, follows the hook): ${x.script}\n`;
    if(x.directions)  out+=`- DIRECTIONS (do this, NOT spoken): ${x.directions}\n`;
    if(x.value)       out+=`- VALUE (the payoff to protect): ${x.value}\n`;
    if(x.cta)         out+=`- CTA (optional, say to end): ${x.cta}\n`;
    if(x.linkedin)    out+=`- LINKEDIN TWIN (post this version on LinkedIn if the video wins): ${String(x.linkedin.body||"").replace(/\n+/g,' ')}\n`;
    out+=`\n`;
  });
  window.__lastExport=out;
  copyText(out, `Copied ${items.length} filmed script(s). Paste into your editor session.`);
}
async function exportForBlog(){
  const w=curWeek(); if(!w) return;
  const items=videosOf(w).filter(x=>["filmed","posted"].includes(t(x.id).status)).map(x=>Object.assign({}, x, {tracking:t(x.id)}));
  if(!items.length){alert("Nothing marked Filmed or Posted in this week yet.\n\nMark the scripts you shot, then export.");return;}
  const payload={week:w.week, positioning:w.positioning||"", exported_at:new Date().toISOString(), items};
  await saveJson(JSON.stringify(payload,null,2), `blog-queue-${w.week}.json`,
    `Saved ${items.length} script(s) for the blog.\n\nKeep it in blog-queue/ in your workspace so the weekly routine finds it.`);
}
async function exportCarousels(){
  const w=curWeek(); if(!w) return;
  const items=videosOf(w).filter(x=>t(x.id).carousel);
  if(!items.length){alert("No scripts flagged for a carousel yet.\n\nClick 'Carousel' on any script card, then export.");return;}
  const payload={week:w.week, positioning:w.positioning||"", exported_at:new Date().toISOString(), items};
  await saveJson(JSON.stringify(payload,null,2), `carousel-queue-${w.week}.json`,
    `Saved ${items.length} script(s) to the carousel queue.\n\nSave it in carousels/ in your workspace, then run:\n  python3 build_carousels.py\nto render the PDFs.`);
}
/* The merged view: what tracking.jsonl seeded plus what changed in this browser.
   Payload shape is load-bearing downstream (log_perf.py --import). */
async function exportPerformance(){
  const row=(x,lane)=>{
    if(!x||!x.id) return null;
    const r=t(x.id);
    if(r.status==="idea" && !r.views && !r.notes && !r.link) return null;
    return {id:x.id, title:x.title||"", lane, mechanic:x.mechanic||x.borrows||"", facet:x.facet||"", intent:x.intent||"",
            value:x.value||"", qa:x.qa||"", status:r.status, views:r.views||"", link:r.link||"", notes:r.notes||""};
  };
  const weeksOut=WEEKS.map(w=>{
    const second=[].concat(officeOf(w), w.moments||[], w.days||[]);
    const vids=videosOf(w).map(x=>row(x, second.includes(x)?"secondary":"primary"));
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
/* Write the edited bodies back into the week file. The page is a file:// document with no server,
   so this hands the filesystem a rebuilt week JSON. Fields the build added for display (they start
   with "_", like the carousel copy pulled in from post.md) are stripped first. */
async function saveWeekFile(){
  const w=curWeek(); if(!w) return;
  const out=JSON.parse(JSON.stringify(w));
  const strip_=o=>{ if(o&&typeof o==="object") Object.keys(o).forEach(k=>{ if(k.startsWith("_")&&k!=="_comment") delete o[k]; }); };
  let n=0;
  ["linkedin","gtm_linkedin","distribution","office","food"].forEach(lane=>{
    (out[lane]||[]).forEach(item=>{
      strip_(item);
      const b=track[item.id]&&track[item.id].body;
      if(b!=null&&b!==""){ item.body=b; n++; }
      const tw=item.linkedin;
      if(tw&&tw.id){ strip_(tw); const tb=track[tw.id]&&track[tw.id].body; if(tb!=null&&tb!==""){ tw.body=tb; n++; } }
    });
  });
  if(!n){alert("No edited post text in this week yet.\n\nClick Edit on a post, change it, then Save.");return;}
  await saveJson(JSON.stringify(out,null,2)+"\n", w.week+".json",
    n+" edited post(s) written. Put this file at weeks/"+w.week+".json, then rerun build_dashboard.py.");
}

/* ---------------- drawers ---------------- */
let lastFocus=null;
function openDrawer(html){ lastFocus=document.activeElement; const d=$("drawer"); d.innerHTML=html; d.hidden=false; $("dbg").hidden=false; d.scrollTop=0; document.body.style.overflow="hidden"; const x=d.querySelector(".x"); if(x) x.focus(); }
function closeDrawer(){ const d=$("drawer"); if(d.hidden) return; d.hidden=true; $("dbg").hidden=true; document.body.style.overflow=""; if(lastFocus&&lastFocus.focus) lastFocus.focus(); }
const drawerHead=(h,p)=>`<div class="drawer-h"><div><h3>${h}</h3>${p?`<p>${p}</p>`:""}</div><button class="x" type="button" aria-label="Close">×</button></div>`;
function exportDrawer(){
  const rows=[
    ["Filmed scripts","Copies every script marked Filmed, with its edit spec, for the editor session.","exportFilmed","Copy"],
    ["Week for blog","Saves Filmed and Posted scripts to a file the weekly routine turns into an AEO post.","exportForBlog","Save"],
    ["Carousel queue","Saves the scripts flagged Carousel, for build_carousels.py.","exportCarousels","Save"],
    ["Performance","Saves your tracking (the seed plus your edits here) for log_perf.py --import.","exportPerformance","Save"],
    ["Week file","Writes post text you edited here back into weeks/<week>.json, so the next build keeps it.","saveWeekFile","Save"],
  ];
  openDrawer(drawerHead("Export","Everything that leaves this page, in one place.")+`<div class="wq">${rows.map(([h,p,a,b])=>`<div class="act split"><div><b>${h}</b><p>${esc(p)}</p></div><button class="btn sm" type="button" data-act="${a}">${b}</button></div>`).join("")}</div>`);
}
function fixPostDrawer(){
  const w=W(), f=videosOf(w).filter(x=>t(x.id).status==="filmed");
  openDrawer(drawerHead(`${plural(f.length,"video")} filmed, not posted`, "Three steps get them live.")
    +`<div class="wq"><div class="act"><span class="no">1</span><p>Copy the filmed scripts with their edit specs. <button class="btn sm" type="button" data-act="exportFilmed" style="margin-left:8px">Copy</button></p></div>
      <div class="act"><span class="no">2</span><p>Open an editor session, paste them and drop the clips. tiktok-yap-editor cuts each one to the words you said.</p></div>
      <div class="act"><span class="no">3</span><p>When a video is live, mark it Posted and paste the link under Results, then Export > Performance.</p></div></div>
      <div class="ctxbox"><h4>Waiting to be cut</h4>${f.map(x=>{ const L=lanes().find(L=>L.items.includes(x)); return `<p class="note"><b>${esc(cleanTitle(x))}</b> · ${esc(L?L.label:"")}</p>`; }).join("")}</div>`);
}
function briefDrawer(){
  const w=W(); let h="";
  if(w.positioning) h+=`<div class="ctxbox"><h4>Positioning</h4><p class="note">${esc(w.positioning)}</p></div>`;
  if(w.method) h+=`<div class="ctxbox"><h4>Method</h4><p class="note">${esc(w.method)}</p></div>`;
  if(w.coined_term&&w.coined_term.term) h+=`<div class="ctxbox"><h4>Coined term${w.coined_term.status?", "+esc(w.coined_term.status):""}</h4><p class="note"><b>${esc(w.coined_term.term)}.</b> ${esc(w.coined_term.definition_beat||"")}</p></div>`;
  if(Array.isArray(w.signals)&&w.signals.length) h+=`<div class="ctxbox"><h4>Signals this week</h4>${w.signals.map(s=>`<p class="note"><b>${esc(s.call||"")}</b> ${esc(s.shell||"")}${s.your_version?" Your version: "+esc(s.your_version):""}</p>`).join("")}</div>`;
  const e=w.experiment;
  if(e&&e.question){ const arms=e.arms||{}, n=k=>Array.isArray(arms[k])?arms[k].length:0; h+=`<div class="ctxbox"><h4>This week's question</h4><p class="note">${esc(e.question)} (${esc(e.dim||"dim")}: A ${n("a")} vs B ${n("b")})</p></div>`; }
  h+=promisesBlock(w);
  openDrawer(drawerHead("The brief", isExample(w)?"Example week":"Week of "+spoken(weekStartOf(w)||w.week))+h);
}

/* ---------------- wiring ---------------- */
function act(a){
  const i=a.indexOf(":"), k=i<0?a:a.slice(0,i), v=i<0?"":a.slice(i+1);
  if(k==="film") return openFilm(v);
  if(k==="copy"){ const x=findItem(v); return x&&copyText(scriptText(x),"Script copied"); }
  if(k==="guide"){ const x=findItem(v); return x&&openDrawer(drawerHead("Your guide", esc(cleanTitle(x)))+`<div class="ctxbox">${guideHtml(x)}</div>`); }
  if(k==="carousel"){ setT(v,{carousel:!t(v).carousel}); return toast(t(v).carousel?"Flagged for a carousel":"Carousel flag removed"); }
  if(k==="copyli"){ const x=findItem(v); return x&&copyText(linkedinText(bodyOf(x)),"Copied, formatted for LinkedIn"); }
  if(k==="edit") return editBody(v);
  if(k==="notes"){ const x=findItem(v); return x&&openDrawer(drawerHead("Posting notes", esc(postName(x)))+`<div class="ctxbox"><p class="note" style="white-space:pre-wrap">${esc(x._notes)}</p>${x._copy_from?`<p class="how">From ${esc(x._copy_from)}</p>`:""}</div>`); }
  if(k==="post"){ showTab("tab-post"); const el=$("licard-"+v); if(el){ el.scrollIntoView({behavior:"smooth", block:"center"}); el.style.borderColor="var(--blue)"; setTimeout(()=>{el.style.borderColor="";},1400); } return; }
  if(k==="copyammo"){ const r=ammoRounds(W())[+v]; return r&&copyText([r.fact, r.number?`(${r.number})`:"", r.source||""].filter(Boolean).join(" "),"Fact and source copied"); }
  if(k==="spend") return toggleSpent(+v);
  if(k==="brief") return briefDrawer();
  if(k==="fixPost") return fixPostDrawer();
  const fns={exportFilmed, exportForBlog, exportCarousels, exportPerformance, saveWeekFile};
  if(fns[k]) return fns[k]();
}
document.addEventListener("click", e=>{
  const b=e.target.closest("button, a"); if(!b) return;
  if(b.closest(".x")&&b.closest("#drawer")) return closeDrawer();
  if(b.dataset.w!==undefined){ WI=+b.dataset.w; OPEN.clear(); renderAll(); return; }
  if(b.dataset.lane){ LANE=b.dataset.lane; renderFilm(); return; }
  if(b.id==="exportBtn") return exportDrawer();
  if(b.id==="theme") return applyTheme(document.documentElement.dataset.mode==="dark"?"light":"dark");
  if(b.id==="perfMore"){ PERF_ALL=!PERF_ALL; drawResults(); return; }
  if(b.id==="perfTbl"){ const tb=$("perfTable"); tb.hidden=!tb.hidden; b.textContent=tb.hidden?"Show table":"Hide table"; b.setAttribute("aria-expanded",String(!tb.hidden)); return; }
  if(b.dataset.st){ setT(b.dataset.id,{status:b.dataset.st}); toast("Marked "+statusName[b.dataset.st].toLowerCase()); return; }
  if(b.dataset.more){ const id=b.dataset.more; OPEN.has(id)?OPEN.delete(id):OPEN.add(id); renderFilm(); return; }
  if(b.dataset.expand){ const el=$(b.dataset.expand); if(!el) return; if(el.classList.contains("body")){ el.classList.toggle("open"); b.textContent=el.classList.contains("open")?"Collapse":"Read all"; } else { el.hidden=!el.hidden; b.textContent=el.hidden?"Details":"Hide details"; } return; }
  if(b.dataset.copy) return copyText(b.dataset.copy, "Copied");
  if(b.dataset.filmClose!==undefined) return closeFilm();
  if(b.dataset.filmStep){ FILM.i=Math.max(0,Math.min(FILM.ids.length-1, FILM.i+(+b.dataset.filmStep))); drawFilm(); return; }
  if(b.dataset.act){ const k=b.dataset.act.split(":")[0]; if(!["spend","copyammo","exportFilmed","copy"].includes(k)) closeDrawer(); act(b.dataset.act); }
});
document.addEventListener("change", e=>{
  if(e.target.id==="showDone"){ SHOW_DONE=e.target.checked; renderFilm(); }
  if(e.target.id==="olderSel"&&e.target.value!==""){ WI=+e.target.value; OPEN.clear(); renderAll(); }
});
document.addEventListener("input", e=>{ const i=e.target; if(i.dataset&&i.dataset.field) setQuiet(i.dataset.id, {[i.dataset.field]:i.value}); });
$("dbg").addEventListener("click", closeDrawer);
document.addEventListener("keydown", e=>{
  if(e.key==="Escape"){ if(FILM) closeFilm(); else closeDrawer(); return; }
  if(!FILM) return;
  if(e.key==="ArrowRight"&&FILM.i<FILM.ids.length-1){ FILM.i++; drawFilm(); }
  if(e.key==="ArrowLeft"&&FILM.i>0){ FILM.i--; drawFilm(); }
});

/* ---------------- tabs, theme, week control ---------------- */
const HELLO={"tab-film":"Pick a lane and start filming.", "tab-post":"Here's what's ready to post.", "tab-results":"Here's what you filmed and how it landed."};
function showTab(id, remember){
  document.querySelectorAll('.tabs [role="tab"]').forEach(tb=>{ const on=tb.id===id; tb.setAttribute("aria-selected",String(on)); const p=$(tb.getAttribute("aria-controls")); if(p) p.hidden=!on; });
  $("hello2").textContent=HELLO[id]||HELLO["tab-film"];
  if(remember!==false){ try{ localStorage.setItem(TAB_KEY,id); }catch(e){} }
  if(id==="tab-results") drawResults();
}
document.querySelectorAll('.tabs [role="tab"]').forEach(tb=>tb.addEventListener("click", ()=>{ showTab(tb.id); window.scrollTo({top:0}); }));
function applyTheme(mode){
  document.documentElement.dataset.mode=mode;
  const b=$("theme"); if(b){ b.textContent=mode==="dark"?"Light mode":"Dark mode"; b.setAttribute("aria-pressed",String(mode==="dark")); }
  try{ localStorage.setItem(THEME_KEY,mode); }catch(e){}
  drawResults();
}
function renderWeekCtl(){
  const w=W(); if(!w) return;
  $("weekSeg").innerHTML=WEEKS.slice(0,3).map((wk,i)=>`<button type="button" data-w="${i}" aria-pressed="${i===WI}">${esc(weekLabel(wk))}</button>`).join("");
  const older=$("olderSel");
  if(WEEKS.length>3){
    older.hidden=false;
    older.innerHTML=`<option value="">Older weeks</option>`+WEEKS.slice(3).map((wk,j)=>`<option value="${j+3}"${WI===j+3?" selected":""}>${esc(isIso(wk.week)?"Week of "+spoken(wk.week):String(wk.week))}</option>`).join("");
  }
  const s=weekStartOf(w);
  $("range").textContent = isExample(w) ? "Example week, sample data" : s ? "Week of "+rangeText(s, addDays(s,6)) : "Week "+w.week;
}
function renderAll(){
  renderWeekCtl(); renderFilm(); renderPost(); renderResults();
  $("foot").innerHTML=`<p><b>Sources.</b> Weeks from weeks/, Filmed and Posted marks from performance/tracking.jsonl${(PERF.perf||[]).length?", LinkedIn numbers from performance/performance.jsonl":""}. Built ${esc(spoken(UI.built||""))}.</p><p>Marks you change here live in this browser until Export > Performance writes them to disk.</p>`;
}

(function init(){
  let saved=null; try{ saved=localStorage.getItem(THEME_KEY); }catch(e){}
  applyTheme(saved==="dark"?"dark":"light");
  /* The mark's bytes are inlined once, on #logo-mark; the tab icon points at that. */
  const mark=$("logo-mark");
  if(mark&&mark.tagName==="IMG"&&mark.getAttribute("src")){ const l=document.createElement("link"); l.rel="icon"; l.href=mark.getAttribute("src"); document.head.appendChild(l); }
  renderAll();
  let start=null; const hash=location.hash.slice(1);
  if(hash&&$("tab-"+hash)) start="tab-"+hash;
  if(!start){ try{ const s=localStorage.getItem(TAB_KEY); if(s&&$(s)) start=s; }catch(e){} }
  showTab(start||"tab-film", false);
  let rt=0; addEventListener("resize", ()=>{ clearTimeout(rt); rt=setTimeout(drawResults,150); });
})();

<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=1080, height=1920" />
    <title>{{TITLE}}</title>
    <script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
    <style>
{{FONT_FACES}}
      * { margin: 0; padding: 0; box-sizing: border-box; }
      html, body { width: 1080px; height: 1920px; overflow: hidden; background: #17181B; }
      #root { position: relative; width: 100%; height: 100%; overflow: hidden; }
      #camera { position: absolute; inset: 0; transform-origin: 50% 38%; will-change: transform; }
      #aroll { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
      #caps-host { position: absolute; inset: 0; }
      #star { position: absolute; left: 470px; top: 92px; width: 140px; height: 140px; }
      #hook { position: absolute; left: 60px; width: 960px; top: 236px; text-align: center; }
      .hl { display: block; white-space: nowrap; }
      #hnum { display: inline-block; font-variant-numeric: tabular-nums; }
      .card { position: absolute; will-change: transform, opacity; }
      .top { top: 150px; } .w940 { left: 70px; width: 940px; }
      .under { left: 190px; width: 700px; top: 1430px; }
      .shot { display: block; width: 100%; height: auto; }
      .wipe { overflow: hidden; }
      .foot { display: flex; justify-content: space-between; align-items: center; gap: 16px; margin-top: 22px; }
      .flowrow { display: flex; align-items: center; justify-content: center; gap: 0.34em; margin-top: 26px; font-size: 30px; }
      .node { display: inline-block; white-space: nowrap; transform-origin: 50% 50%; position: relative; }
      .node img { height: 1.3em; width: auto; vertical-align: middle; margin-right: 10px; border-radius: 8px; }
      .logochip { display: inline-flex; transform-origin: 50% 50%; }
      .logochip img { display: block; height: 3.2em; width: auto; }
      .arrow { width: 1.4em; height: 0.8em; flex: 0 0 auto; }
      .arrow path { fill: none; stroke-linecap: round; stroke-linejoin: round; }
      .ripple { position: absolute; left: 50%; top: 50%; width: 120px; height: 120px; margin: -60px 0 0 -60px; border-radius: 50%; }
      .strike { position: absolute; left: -8px; top: 50%; width: calc(100% + 16px); height: 20px; margin-top: -10px; overflow: visible; }
      .strike path { fill: none; stroke-width: 7; stroke-linecap: round; }
      .strike.big { left: 2%; width: 96%; height: 60px; margin-top: -30px; }
      .strike.big path { stroke-width: 9; }
      .title { text-align: center; text-wrap: balance; margin-top: 10px; }
      .chipcard { position: absolute; left: 390px; top: 170px; width: 300px; text-align: center; will-change: transform, opacity; }
      .chipcard img { width: 250px; height: auto; display: block; margin: 0 auto 18px; }
      .iconcard { position: absolute; will-change: transform, opacity; }
      .iconcard img { width: 100%; height: 100%; object-fit: contain; display: block; filter: drop-shadow(0 10px 18px rgba(0,0,0,.22)); }
      .takepill { position: absolute; left: 70px; top: 120px; display: inline-flex; align-items: center; gap: 14px; padding: 12px 26px 12px 12px; border-radius: 999px; background: var(--sand, #EFE3CE); color: var(--ink, #17181B); font-size: 34px; font-weight: 700; will-change: transform, opacity; }
      .takechip { display: inline-flex; align-items: center; justify-content: center; width: 50px; height: 50px; border-radius: 999px; background: {{ACCENT}}; color: {{ONACCENT}}; font-size: 30px; }
      .stamp { position: absolute; left: 70px; top: 140px; display: flex; flex-direction: column; align-items: flex-start; gap: 6px; padding: 18px 28px; border-radius: 26px; background: var(--card, #FFFFFF); color: var(--ink, #17181B); will-change: transform, opacity; }
      .stampclock { font-size: 64px; font-weight: 800; font-variant-numeric: tabular-nums; line-height: 1; }
      .stamplab { font-size: 28px; font-weight: 600; opacity: .7; }
      .stat { display: block; white-space: nowrap; text-align: center; font-variant-numeric: tabular-nums; transform-origin: 50% 60%; line-height: 1.28 !important; margin-bottom: 0 !important; }
      .whead { display: flex; align-items: center; gap: 22px; }
      .whead img { width: 150px; height: auto; }
      .bars { position: relative; margin-top: 8px; }
      .brow { display: flex; align-items: center; gap: 18px; margin-top: 18px; }
      .bname { flex: 0 0 250px; } .bval { flex: 0 0 200px; text-align: right; white-space: nowrap; }
      .track { flex: 1 1 auto; min-width: 0; height: 34px; border-radius: 17px; overflow: hidden; }
      .fill { display: block; width: 100%; height: 100%; border-radius: 17px; transform-origin: left center; }
      .limit { position: absolute; top: 4px; bottom: -8px; left: calc(268px + (100% - 486px) * var(--lx)); width: 0; }
      .limline { position: absolute; left: -3px; top: 10px; bottom: 0; width: 6px; border-radius: 3px; }
      .limlabel { position: absolute; left: 0; bottom: 100%; white-space: nowrap; translate: -50% 0; }
      .q { text-align: center; text-wrap: balance; }
      .em { position: relative; display: inline-block; white-space: nowrap; }
      .ul { position: absolute; left: -2%; bottom: -16px; width: 104%; height: 22px; overflow: visible; }
      .ul path { fill: none; stroke-width: 8; stroke-linecap: round; }
      .by { text-align: center; margin-top: 16px; }
      .sheet { position: relative; display: grid; grid-template-columns: repeat(var(--cols), 1fr); gap: 10px; margin-top: 24px; }
      .cell { display: block; height: 46px; border-radius: 9px; transform-origin: 50% 50%; }
      .fanrow { display: flex; align-items: center; gap: 22px; margin-top: 26px; font-size: 32px; }
      .dots { flex: 1 1 auto; display: grid; grid-template-columns: repeat(25, 1fr); gap: 7px; }
      .dot { display: block; width: 100%; aspect-ratio: 1; border-radius: 50%; transform-origin: 50% 50%; }
      .net { position: relative; height: 380px; margin-top: 10px; font-size: 32px; }
      .netlines { position: absolute; inset: 0; width: 100%; height: 100%; overflow: visible; }
      .netlines path, .rlines path { fill: none; stroke-linecap: round; }
      .person { position: absolute; width: 48px; height: 48px; margin: -24px 0 0 -24px; border-radius: 50%; transform-origin: 50% 50%; }
      .netcenter { position: absolute; left: 50%; top: 50%; translate: -50% -50%; }
      .convrow { display: flex; align-items: center; justify-content: center; gap: 70px; margin-top: 30px; font-size: 32px; }
      .cbox { position: relative; display: flex; align-items: center; gap: 16px; padding: 26px 26px 22px; border-radius: 26px; }
      .cboxlabel { position: absolute; top: -15px; left: 26px; padding: 0 10px; white-space: nowrap; }
      .slot { display: inline-block; width: 150px; height: 1.9em; border-radius: 999px; }
      .rsource { text-align: center; margin-top: 22px; font-size: 32px; }
      .rlines { display: block; width: 100%; height: 80px; overflow: visible; }
      .rrow { display: grid; justify-items: center; align-items: center; font-size: 28px; }
      .list { margin-top: 8px; }
      .litem { display: flex; align-items: center; gap: 22px; margin-top: 22px; }
      .lmark { width: 52px; height: 52px; flex: 0 0 auto; }
      .lmark path { fill: none; stroke-width: 4.5; stroke-linecap: round; stroke-linejoin: round; }
      .tline { position: relative; display: flex; justify-content: space-around; margin-top: 30px; }
      .trule { position: absolute; left: 6%; right: 6%; top: 17px; height: 6px; border-radius: 3px; transform-origin: left center; }
      .tick { position: relative; display: flex; flex-direction: column; align-items: center; gap: 10px; transform-origin: 50% 20%; }
      .tdot { display: block; width: 40px; height: 40px; border-radius: 50%; }
      #contact { position: absolute; left: 0; width: 1080px; top: 1712px; text-align: center; }
{{THEME_CSS}}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="main" data-start="0" data-width="1080" data-height="1920" data-duration="{{DUR}}">
      <div id="camera">
        <video id="aroll" class="clip" src="assets/footage.mp4" data-start="0" data-duration="{{DUR}}" data-track-index="0" muted playsinline></video>
      </div>
      <audio id="voice" src="assets/voice.m4a" data-start="0" data-duration="{{DUR}}" data-track-index="10" data-volume="1"></audio>
      {{BED}}
      {{SFX}}

      {{STAR}}
      {{HOOK}}

{{CARDS}}

      <div id="caps-host" class="clip" data-track-kind="captions" data-composition-id="captions" data-composition-src="compositions/captions.html" data-start="0" data-duration="{{DUR}}" data-track-index="5" data-width="1080" data-height="1920"></div>

      {{CONTACT}}
    </div>

    <script>
      document.fonts.ready.then(function () {
        // FIT, before anything is timed: nothing leaves its card. Flow rows scale their type
        // down to the room inside the card's padding; hook lines, stats and titles scale down
        // to their own box. Counters hold their widest text while this runs.
        document.querySelectorAll(".flowrow").forEach(function (row) {
          var cs = getComputedStyle(row), gap = parseFloat(cs.columnGap) || 0, kids = Array.from(row.children);
          var need = kids.reduce(function (w, k) { return w + k.getBoundingClientRect().width; }, 0) + gap * (kids.length - 1);
          var room = row.clientWidth - 24;
          if (need > room) row.style.fontSize = (parseFloat(cs.fontSize) * room / need).toFixed(2) + "px";
        });
        document.querySelectorAll(".hl, .stat, .ltitle, .title").forEach(function (el) {
          if (el.scrollWidth > el.clientWidth + 1)
            el.style.fontSize = (parseFloat(getComputedStyle(el).fontSize) * el.clientWidth / el.scrollWidth * 0.97).toFixed(2) + "px";
        });
        document.querySelectorAll("[data-start-text]").forEach(function (el) { el.textContent = el.getAttribute("data-start-text"); });

        var DUR = {{DUR}}, FPS = 30, ACCENT = "{{ACCENT}}", ONACC = "{{ONACCENT}}";
        var q = function (s) { return document.querySelector(s); };
        var tl = gsap.timeline({ paused: true });

        function cardIn(sel, at) {
          if (at <= 0.05) { tl.fromTo(sel, { opacity: 1, y: 0, scale: 1 }, { opacity: 1, duration: 0.01 }, 0); return; }
          gsap.set(sel, { opacity: 0 });
          tl.fromTo(sel, { opacity: 0, y: 28, scale: 0.94 }, { opacity: 1, y: 0, scale: 1, duration: 0.45, ease: "power3.out", immediateRender: false }, at); }
        function cardOut(sel, at) { if (at < DUR - 0.05) tl.to(sel, { opacity: 0, y: -18, duration: 0.25, ease: "power2.in" }, at - 0.25); }
        function pop(sel, at) { gsap.set(sel, { opacity: 0 });
          tl.fromTo(sel, { opacity: 0, scale: 0 }, { opacity: 1, scale: 1, duration: 0.4, ease: "power3.out", immediateRender: false }, at); }
        function draw(id, at, dur) { var p = document.getElementById(id), len = p.getTotalLength();
          p.style.strokeDasharray = len; p.style.strokeDashoffset = len;
          tl.to(p, { strokeDashoffset: 0, duration: dur || 0.3, ease: "power2.out" }, at); }
        function num(f, v) { var s = f.dec ? v.toFixed(f.dec) : Math.round(v).toLocaleString("en-US"); return (f.pre || "") + s + (f.suf || ""); }
        function count(sel, t0, t1, f, hook) {
          var el = q(sel), n = Math.max(1, Math.round((t1 - t0) * FPS)), e = gsap.parseEase(hook ? "power2.out" : "power3.out"), a = f.from || 0;
          for (var k = 0; k <= n; k++) tl.set(el, { textContent: num(f, a + (f.to - a) * e(k / n)) }, t0 + (t1 - t0) * k / n);
          if (f.final) tl.set(el, { textContent: f.final }, t1 + 0.05);
          if (hook) {
            tl.to(el, { color: ACCENT, duration: 0.12 }, t1 + 0.05);
            tl.fromTo(el, { scale: 1.12 }, { scale: 1, duration: 0.3, ease: "power3.out", immediateRender: false }, t1 + 0.05);
          } else tl.fromTo(el, { scale: 0.6 }, { scale: 1, duration: t1 - t0, ease: "power3.out", immediateRender: false }, t0); }
        function slide(mover, slot, at) {
          // the mover lands in the slot, and the row re-centres on the box it now sits in
          var mv = q(mover), row = mv.parentElement, box = row.firstElementChild;
          var m = mv.getBoundingClientRect(), s = q(slot).getBoundingClientRect(), b = box.getBoundingClientRect();
          tl.fromTo(mover, { x: 0 }, { x: s.left + s.width / 2 - (m.left + m.width / 2), duration: 0.7, ease: "power3.inOut", immediateRender: false }, at);
          tl.fromTo(row, { x: 0 }, { x: (m.right - b.right) / 2, duration: 0.7, ease: "power3.inOut", immediateRender: false }, at); }

        // camera: push-ins on the lines that carry the belief, with a bounded drift throughout
        var cam = q("#camera"), phase = { s: 1 }, drift = { p: 0 };
        {{PUSHES}}.forEach(function (p) {
          tl.to(phase, { s: p[2], duration: p[1] - p[0], ease: "sine.inOut" }, p[0]);
          tl.to(phase, { s: 1, duration: 0.45, ease: "power2.inOut" }, p[1]);
        });
        tl.fromTo(drift, { p: 0 }, { p: Math.PI * 6, duration: DUR, ease: "none", onUpdate: function () {
          cam.style.transform = "translate(" + (Math.sin(drift.p) * 3).toFixed(2) + "px," + (Math.sin(drift.p * 1.3) * 2.5).toFixed(2) + "px) scale(" + phase.s.toFixed(4) + ")";
        } }, 0);

        {{STAR_JS}}
        {{HOOK_JS}}

        {{CARDS_JS}}

        if (q("#contact")) { gsap.set("#contact", { opacity: 0 }); tl.to("#contact", { opacity: 1, duration: 0.3, ease: "power2.out" }, Math.max(0.5, DUR - 9.7)); }

        tl.seek(0);
        window.__timelines = window.__timelines || {};
        window.__timelines["main"] = tl;
      });
    </script>
  </body>
</html>

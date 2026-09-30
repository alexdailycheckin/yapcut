<!doctype html>
<html lang="en">
  <head><meta charset="UTF-8" /><title>Captions</title></head>
  <body>
    <template>
      <div id="root" data-composition-id="captions" data-width="1080" data-height="1920" data-duration="{{DUR}}">
        <style>
          #root { position: absolute; inset: 0; pointer-events: none; }
          #captions-band { position: absolute; left: 60px; width: 960px; top: 1256px; height: 130px; }
          #captions-band .capgroup { position: absolute; inset: 0; display: flex; justify-content: center;
            align-items: center; gap: 0.42em; font-family: var(--font-display, system-ui), sans-serif; font-size: 86px;
            line-height: 1; white-space: nowrap; }
          #captions-band .cw { display: inline-block; transform-origin: 50% 60%; color: #FFFFFB;
            -webkit-text-stroke: 12px #232323; paint-order: stroke fill; text-shadow: 0 5px 14px rgba(20, 20, 20, 0.35); }
{{CAP_CSS}}
        </style>
        <div id="captions-band">{{CAPTIONS}}</div>
        <script>
          (function () {
            // frame.md: three words a group, the spoken word scales to 110%, no colour highlight
            var CAPS = {{CAPDATA}};
            var tl = gsap.timeline({ paused: true });
            CAPS.forEach(function (g) {
              var el = document.getElementById(g.id);
              gsap.set(el, { opacity: 0 });
              tl.set(el, { opacity: 1 }, g.t0);
              tl.set(el, { opacity: 0 }, g.t1);
              g.words.forEach(function (w) {
                var we = document.getElementById(w.id);
                tl.fromTo(we, { scale: 1 }, { scale: 1.1, duration: 0.08, ease: "power2.out", immediateRender: false }, w.t0);
                tl.to(we, { scale: 1, duration: 0.14, ease: "power2.out" }, w.t1);
              });
            });
            tl.seek(0);
            window.__timelines["captions"] = tl;
          })();
        </script>
      </div>
    </template>
  </body>
</html>

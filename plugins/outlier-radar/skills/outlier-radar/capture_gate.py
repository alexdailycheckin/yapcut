#!/usr/bin/env python3
"""capture_gate.py: capture a page as a receipt, or refuse and say why.

Replaces the capture half of receipts_build.py + cards_from_raws.py (both deprecated). Those tried
to REPAIR a broken capture (crop above the consent modal, stretch the dimming
back out) and so manufactured plausible-looking cards from pages that never
rendered. On 2026-08-02 that shipped 21 junk receipts across 7 videos: cookie
walls, a 404 page, a Cloudflare challenge, a "30% OFF" popup, and several nav
lists cropped in place of a headline.

The rule here is REJECT, NEVER REPAIR. Two changes make that affordable:

  * The verdict reads the DOM, not pixels. Ink-density heuristics cannot tell a
    headline from a cookie banner (the banner is the most text-dense thing on the
    page, so "pick the texty region" walks straight into it). Page text can, and
    it catches classes nobody predicted for free.
  * The crop is the headline's own bounding box, from getBoundingClientRect. No
    band-sliding, so "cropped the wrong region" stops being a failure mode
    instead of being mitigated.

Consent walls are removed BEFORE the verdict runs (JS remover + CMP hosts nulled
at the resolver, see cdp.py), so most of them become clean captures rather than
rejections. What survives that is a real refusal, and the caller falls back to a
typeset card built from the headline text this returns.

Usage:
  python3 capture_gate.py --week weeks/2026-08-02.json \
      --out show/receipts/2026-08-02-v2 [--episode d-20260802-3] [--json verdicts.json]
  python3 capture_gate.py --url https://example.com/story --out /tmp/x

Exit 1 if any shot was rejected, so a build step can gate on it.
"""
import argparse
import json
import pathlib
import re
import sys
import urllib.parse

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from cdp import Browser  # noqa: E402

try:
    from PIL import Image, ImageStat
except ImportError:
    sys.exit("Pillow required: pip3 install Pillow")

# --- verdict markers -------------------------------------------------------
# Ordered most-specific first; the first hit names the rejection.
BOT = [
    "just a moment", "verifying you are human", "checking your browser",
    "enable javascript and cookies", "attention required", "access denied",
    "are you a robot", "security verification", "unusual traffic",
    "please verify you are a human", "ddos protection", "ray id",
]
NOTFOUND = [
    "page you are looking for cannot be found", "page not found",
    "page cannot be found", "404 error", "no longer available",
    "we can't find that page", "we couldn't find", "this page doesn't exist",
]
CONSENT = [
    "we value your privacy", "we use cookies", "accept all cookies",
    "manage my choices", "your privacy choices", "manage preferences",
    "this website uses cookies", "consent to the use of cookies",
    "we and our partners", "store and/or access information on a device",
    "reject all", "cookie settings", "cookie policy and privacy policy",
]
PAYWALL = [
    "subscribe to continue", "subscribers only", "already a subscriber",
    "create a free account to continue", "to continue reading",
    "this article is for subscribers",
]
PROMO = [
    "get my discount", "sign up for our newsletter", "% off", "join our mailing",
    "enter your email", "subscribe to our newsletter",
]

STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "with", "at",
    "by", "from", "as", "is", "are", "was", "were", "be", "been", "it", "its",
    "that", "this", "these", "those", "has", "have", "had", "not", "but",
    "news", "story", "stories", "article", "amp", "html", "index", "www", "com",
    "co", "uk", "sites", "tech", "business", "blog", "posts", "post", "20",
}

# --- the page-side script --------------------------------------------------
# Removes consent/promo overlays, undoes the dimming they leave behind, then
# reports the headline block's geometry in PAGE coordinates so the screenshot
# clip is the headline itself.
PREP_JS = r"""
(() => {
  const KILL = /consent|cookie|gdpr|ccpa|onetrust|optanon|truste|didomi|sp_message|sp-message|qc-cmp|quantcast|osano|cmpbox|klaro|cc-window|usercentrics|iubenda|privacy-?(banner|notice|modal|prompt)|newsletter|subscri|paywall|promo|interstitial|backdrop|lightbox|dimmer|overlay-?(bg|mask)/i;
  const removed = [];
  const vp = Math.max(1, innerWidth * innerHeight);

  const nameOf = el => ((el.id || '') + ' ' +
    (typeof el.className === 'string' ? el.className : '') + ' ' +
    (el.getAttribute('aria-label') || '') + ' ' +
    (el.getAttribute('data-testid') || '')).trim().replace(/\s+/g, ' ');

  for (const el of Array.from(document.querySelectorAll('body *'))) {
    if (!el.isConnected || el === document.body) continue;
    let cs; try { cs = getComputedStyle(el); } catch (e) { continue; }
    const pos = cs.position;
    if (pos !== 'fixed' && pos !== 'sticky' && pos !== 'absolute') continue;
    const r = el.getBoundingClientRect();
    if (r.width < 40 || r.height < 24) continue;
    const area = r.width * r.height;
    const z = parseInt(cs.zIndex) || 0;
    const nm = nameOf(el);
    const named   = KILL.test(nm) && area > vp * 0.02;
    const bigWall = pos === 'fixed' && area > vp * 0.10 && z >= 50;
    const dimmer  = pos === 'fixed' && area > vp * 0.45 &&
                    /^rgba?\(.*0?\.\d+\)$/.test(cs.backgroundColor || '');
    if (named || bigWall || dimmer) { removed.push(nm.slice(0, 70)); el.remove(); }
  }
  // consent iframes (TrustArc, Sourcepoint) live outside the DOM we can walk
  for (const f of Array.from(document.querySelectorAll('iframe'))) {
    const s = (f.src || '') + ' ' + nameOf(f);
    if (KILL.test(s)) { removed.push('iframe ' + s.slice(0, 50)); f.remove(); }
  }
  // the wall is gone; undo what it did to the page it was sitting on
  for (const el of [document.documentElement, document.body]) {
    el.style.setProperty('overflow', 'visible', 'important');
    el.style.setProperty('filter', 'none', 'important');
    el.style.setProperty('-webkit-filter', 'none', 'important');
  }
  document.querySelectorAll('[style*="filter"],[style*="blur"]').forEach(el => {
    el.style.setProperty('filter', 'none', 'important');
  });

  // nudge lazy content, then settle back to the top
  const y = scrollY; scrollTo(0, 1200); scrollTo(0, y);

  const vis = el => {
    if (!el) return false;
    const r = el.getBoundingClientRect();
    if (r.width < 30 || r.height < 10) return false;
    const cs = getComputedStyle(el);
    return cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity > 0.1;
  };

  // headline: the real one, not a section label or a card in a rail
  let h = null;
  for (const s of ['article h1', 'main h1', '[itemprop="headline"]',
                   'h1.headline', 'header h1', 'h1']) {
    const c = Array.from(document.querySelectorAll(s))
      .filter(e => vis(e) && e.innerText.trim().length > 12);
    if (c.length) { h = c[0]; break; }
  }

  const txt = el => (el ? el.innerText.trim().replace(/\s+/g, ' ') : '');
  const meta = n => {
    const e = document.querySelector(`meta[property="${n}"],meta[name="${n}"]`);
    return e ? (e.getAttribute('content') || '').trim() : '';
  };

  // date: structured first, visible <time> second
  let date = meta('article:published_time') || meta('datePublished') ||
             meta('publish-date') || meta('date');
  if (!date) {
    for (const s of document.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        const j = JSON.parse(s.textContent);
        const arr = Array.isArray(j) ? j : [j, ...(j['@graph'] || [])];
        for (const o of arr) if (o && o.datePublished) { date = o.datePublished; break; }
      } catch (e) {}
      if (date) break;
    }
  }
  const tEl = document.querySelector('time[datetime]');
  if (!date && tEl) date = tEl.getAttribute('datetime');
  const dateText = tEl ? txt(tEl) : '';

  // byline
  let by = meta('author');
  if (!by) {
    const b = document.querySelector('[rel="author"],[itemprop="author"],.byline,.author-name,[class*="byline"]');
    if (vis(b)) by = txt(b).slice(0, 90);
  }

  // block to shoot: the headline, plus the short lines directly under it
  // (dek / byline / date) while they stay close and stay short.
  let box = null, dek = '';
  if (h) {
    const r = h.getBoundingClientRect();
    let x0 = r.left, x1 = r.right, y0 = r.top, y1 = r.bottom;
    let el = h.nextElementSibling, taken = 0;
    while (el && taken < 3) {
      if (vis(el)) {
        const rr = el.getBoundingClientRect();
        const t = txt(el);
        if (rr.top - y1 > 90 || rr.height > 190 || t.length > 320) break;
        if (t) {
          if (!dek && t.length > 40) dek = t.slice(0, 300);
          x0 = Math.min(x0, rr.left); x1 = Math.max(x1, rr.right);
          y1 = Math.max(y1, rr.bottom); taken++;
        }
      }
      el = el.nextElementSibling;
    }
    if (!dek) dek = meta('og:description') || meta('description');
    const pad = 22;
    box = {
      x: Math.max(0, x0 + scrollX - pad),
      y: Math.max(0, y0 + scrollY - pad),
      width:  Math.min(innerWidth, x1 - x0 + pad * 2),
      height: Math.min(700, y1 - y0 + pad * 2),
    };
  }

  // is a consent wall STILL up? some are server-rendered inline, not a CDN script.
  let consentLeft = '';
  const PH = /we value your privacy|we use cookies|accept all cookies|manage my choices|manage preferences|store and\/or access information|this website uses cookies|reject all/i;
  for (const el of Array.from(document.querySelectorAll('body *'))) {
    if (!vis(el)) continue;
    const r = el.getBoundingClientRect();
    if (r.width * r.height < vp * 0.06) continue;
    const t = (el.innerText || '').slice(0, 600);
    if (PH.test(t) && el.querySelectorAll('*').length < 60) { consentLeft = t.slice(0, 140); break; }
  }

  return {
    finalUrl: location.href,
    title: (document.title || '').trim(),
    h1: txt(h),
    dek: (dek || '').trim(),
    byline: (by || '').trim(),
    date: (date || '').trim(),
    dateText: dateText,
    site: meta('og:site_name'),
    box: box,
    removed: removed.slice(0, 12),
    consentLeft: consentLeft,
    bodyText: (document.body.innerText || '').slice(0, 6000),
    docHeight: document.documentElement.scrollHeight,
  };
})()
"""


def words(s: str) -> set:
    return {w for w in re.split(r"[^a-z0-9]+", (s or "").lower())
            if len(w) > 2 and w not in STOP}


def slug_words(url: str) -> set:
    path = urllib.parse.urlparse(url).path
    last = [p for p in path.split("/") if p][-1:] or [""]
    stem = re.sub(r"\.(html?|php|aspx?)$", "", last[0])
    return {w for w in words(stem) if not w.isdigit()}


def hit(text: str, markers) -> str:
    low = (text or "").lower()
    for m in markers:
        if m in low:
            return m
    return ""


def verdict(info: dict, url: str, status_note: str = "") -> dict:
    """PASS, or a named refusal. Order matters: the most specific cause wins."""
    body = info.get("bodyText", "")
    head = f"{info.get('title','')} {info.get('h1','')}"

    m = hit(head + " " + body[:1500], BOT)
    if m:
        return {"ok": False, "reason": "bot_challenge", "detail": m}
    m = hit(head, NOTFOUND) or hit(body[:600], NOTFOUND)
    if m:
        return {"ok": False, "reason": "not_found", "detail": m}
    if info.get("consentLeft"):
        return {"ok": False, "reason": "consent_wall",
                "detail": info["consentLeft"][:90]}
    m = hit(head + " " + body[:800], PAYWALL)
    if m:
        return {"ok": False, "reason": "paywall", "detail": m}
    h1 = info.get("h1", "")
    if len(h1) < 15:
        return {"ok": False, "reason": "no_headline",
                "detail": f"h1={h1!r} (page may be a hub or a nav shell)"}
    if not info.get("box"):
        return {"ok": False, "reason": "no_headline_geometry", "detail": ""}
    # did we land on the article the URL promised? cheap, and it catches soft
    # 404s and redirects-to-homepage that return HTTP 200 with a real headline.
    sw = slug_words(info.get("finalUrl") or url)
    if len(sw) >= 4:
        overlap = len(sw & words(h1 + " " + info.get("dek", ""))) / len(sw)
        if overlap < 0.25:
            return {"ok": False, "reason": "headline_mismatch",
                    "detail": f"slug/headline overlap {overlap:.0%}: {h1[:70]!r}"}
    if hit(head, PROMO):
        return {"ok": False, "reason": "promo_modal", "detail": hit(head, PROMO)}
    return {"ok": True, "reason": "", "detail": status_note}


def pixel_check(png: pathlib.Path) -> dict:
    """Last line of defence: a capture that is flat or near-black is not a
    receipt whatever the DOM said."""
    im = Image.open(png).convert("RGB")
    g = im.convert("L")
    st = ImageStat.Stat(g)
    small = g.resize((48, 48))
    return {
        "w": im.width, "h": im.height,
        "stddev": round(st.stddev[0], 2),
        "mean": round(st.mean[0], 1),
        "flat": ImageStat.Stat(small).stddev[0] < 8.0,
        "dark": st.mean[0] < 70,
    }


def grab(page, url: str, dest: pathlib.Path) -> dict:
    """Navigate, de-wall, judge, and only then shoot."""
    loaded = page.goto(url)
    try:
        info = page.eval(PREP_JS)
    except RuntimeError as e:
        return {"ok": False, "reason": "js_error", "detail": str(e)[:140],
                "info": {}}
    if not isinstance(info, dict):
        return {"ok": False, "reason": "no_dom", "detail": "prep returned nothing",
                "info": {}}
    v = verdict(info, url, "" if loaded else "load event timed out")
    meta = {k: info.get(k) for k in
            ("finalUrl", "title", "h1", "dek", "byline", "date", "dateText",
             "site", "removed", "docHeight")}
    if not v["ok"]:
        return {**v, "info": meta}
    box = dict(info["box"])
    box["scale"] = 2                      # retina: the card gets downscaled later
    try:
        png = page.screenshot(clip=box)
    except Exception as e:
        return {"ok": False, "reason": "screenshot_failed",
                "detail": str(e)[:140], "info": meta}
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(png)
    px = pixel_check(dest)
    if px["flat"]:
        return {"ok": False, "reason": "flat_capture",
                "detail": f"stddev {px['stddev']}", "info": meta, "px": px}
    if px["dark"]:
        return {"ok": False, "reason": "dark_capture",
                "detail": f"mean luma {px['mean']}", "info": meta, "px": px}
    return {"ok": True, "reason": "", "detail": v["detail"], "info": meta,
            "px": px, "file": str(dest)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week")
    ap.add_argument("--episode")
    ap.add_argument("--url", help="one-off: capture a single URL")
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", default=None, help="verdicts JSON (default <out>/verdicts.json)")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=2200)
    a = ap.parse_args()

    out = pathlib.Path(a.out)
    (out / "raw").mkdir(parents=True, exist_ok=True)

    jobs = []
    if a.url:
        jobs.append(("adhoc", "1", a.url, ""))
    else:
        if not a.week:
            sys.exit("need --week or --url")
        wk = json.load(open(a.week))
        for it in wk.get("distribution", []):
            if a.episode and it["id"] != a.episode:
                continue
            for s in it.get("shot_list", []):
                sid = str(s.get("n", s.get("shot", s.get("id"))))
                u = (s.get("url") or "").strip()
                what = s.get("what") or s.get("shoot") or ""
                if u.startswith("http"):
                    jobs.append((it["id"], sid, u, what))
                elif u:
                    jobs.append((it["id"], sid, "", what))   # device shot etc

    results, rejected = [], 0
    with Browser(width=a.width, height=a.height) as b:
        page = b.page()
        for ep, sid, url, what in jobs:
            base = f"{ep}_{sid}"
            if not url:
                print(f"{base}: skip (no http url)")
                continue
            dest = out / "raw" / f"{base}.png"
            try:
                r = grab(page, url, dest)
            except Exception as e:
                r = {"ok": False, "reason": "capture_error",
                     "detail": f"{type(e).__name__}: {e}"[:160], "info": {}}
                page = b.page()          # a dead tab poisons every later shot
            r.update({"episode": ep, "shot": sid, "url": url, "what": what})
            results.append(r)
            if r["ok"]:
                print(f"{base}: PASS  {r['info'].get('h1','')[:64]!r}"
                      + (f"  [-{len(r['info'].get('removed') or [])} overlay]"
                         if r["info"].get("removed") else ""))
            else:
                rejected += 1
                print(f"{base}: REJECT {r['reason']}  {r['detail'][:70]}")

    jpath = pathlib.Path(a.json) if a.json else out / "verdicts.json"
    jpath.write_text(json.dumps(results, indent=2))
    ok = sum(1 for r in results if r["ok"])
    print(f"\n{ok} pass / {rejected} reject  ->  {jpath}")
    if rejected:
        by = {}
        for r in results:
            if not r["ok"]:
                by.setdefault(r["reason"], []).append(f"{r['episode']}_{r['shot']}")
        for k, v in sorted(by.items(), key=lambda kv: -len(kv[1])):
            print(f"  {k:22} {len(v):2}  {', '.join(v)}")
        print("\nRejected shots need a source swap or a typeset card "
              "(evidence_card.py) built from the headline in verdicts.json.")
    return 1 if rejected else 0


if __name__ == "__main__":
    sys.exit(main())

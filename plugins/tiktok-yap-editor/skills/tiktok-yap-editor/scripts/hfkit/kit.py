"""hfkit: package a finished talking-head cut as a HyperFrames composition.

One Episode per video. The spec (a short Python file, see example_spec.py) anchors every card
to the words said on camera, so timing comes from the cut's own transcript, never from guessed
seconds:

    from hfkit.kit import Episode
    ep = Episode("episode-01", words="words.json", footage="cut.mp4", voice="voice.m4a", show=True)
    ep.hook(["Acme just", "bought a spreadsheet"], spark="spreadsheet")
    ep.headline("headline.png", "techcrunch.com", "24 Sep 2026", 0.3, 5.3)
    ep.flow("Where the answer lands", [dict(text="Ask the agent", at=ep.t("inside the agent")), ...],
            ep.t("so now"), ep.t("the next line"), src="example.com", date="25 Sep 2026")
    run(ep)   # build, carve the bed, check, snapshot every card, render

Rules the kit enforces:
- Nothing leaves its card: rows are sized in em and scaled down after fonts load, and hook
  lines, stats and titles shrink to their own box.
- Sounds come from the tagged library by what the event means (library.json tags).
- Receipts sit in the band above the speaker's head; the frame-one receipt sits under the captions.
- Captions scale the spoken word, never recolour it.
- The creator's own take (the opinion slot) is labelled as theirs, and brand objects from their
  icon kit pop in on the line that names them (icon, take, stamp: 3.6.0).
"""
import html as _h, json, math, os, re, shutil, subprocess, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
_norm = lambda s: re.sub(r"[^a-z0-9.%#$]", "", s.lower()).rstrip(".")
esc = lambda s: _h.escape(str(s))


def icon_library(home=None):
    """The creator's icon kit: <workspace>/assets/icons/library.json, {icons: [{name, file, tags}]}.
    None when the workspace has no kit."""
    if home is None:
        try:
            from yaplib.home import radar_home
        except ImportError:
            return None
        home = radar_home(argv=[], required=False)
    path = os.path.join(str(home), "assets", "icons", "library.json") if home else None
    if not path or not os.path.exists(path):
        return None
    lib = json.load(open(path))
    lib["_dir"] = os.path.dirname(path)
    return lib


def find_icon(name, lib=None):
    """A kit icon's PNG path by name ("check"), or by a tag it answers to ("growth")."""
    if name and os.path.exists(str(name)):
        return str(name)
    lib = lib or icon_library()
    if not lib:
        raise SystemExit(f"no icon kit in this workspace (assets/icons/library.json) for {name!r}")
    want = str(name).lower().strip()
    for it in lib.get("icons", []):
        if it.get("name") == want:
            return os.path.join(lib["_dir"], it["file"])
    for it in lib.get("icons", []):
        if want in [t.lower() for t in it.get("tags", [])]:
            return os.path.join(lib["_dir"], it["file"])
    raise SystemExit(f"no icon named or tagged {name!r} in {lib['_dir']}/library.json")


FMT = {"money": {"pre": "$"}, "int": {}, "mult": {"suf": "x"}, "pct": {"suf": "%"}, "rank": {"pre": "#", "from": 100}}
ARROW = '<svg class="arrow" viewBox="0 0 44 24"><path id="{id}" d="M4 12 H36 M28 4 L37 12 L28 20" /></svg>'


def _fmt(fmt, value, frm=None, final=None):
    f = dict(FMT[fmt]) if isinstance(fmt, str) else dict(fmt)
    f["to"] = value
    if frm is not None:
        f["from"] = frm
    if final:
        f["final"] = final
    return f


def _num(f, v):
    s = f"{v:.{f['dec']}f}" if f.get("dec") else f"{round(v):,}"
    return f.get("pre", "") + s + f.get("suf", "")


def _widest(f):
    c = [_num(f, f.get("from", 0)), _num(f, f["to"])] + ([f["final"]] if f.get("final") else [])
    return max(c, key=len)


class Episode:
    def __init__(self, name, words, footage, voice, theme=None, show=False, duration=None,
                 project_root=None, library=None, contact=None, star=None, bed="bed_corporate", core=None):
        self.name, self.show = name, show
        self.W = json.load(open(words))
        self.TOK = [_norm(w["w"]) for w in self.W]
        self.footage, self.voice = footage, voice
        self.dur = duration or round(float(subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", footage],
            capture_output=True, text=True).stdout.strip()), 2)
        if theme is None:
            from hfkit.themes.cards import from_brand
            theme = from_brand({})
        self.theme = theme if isinstance(theme, dict) else importlib.import_module(f"hfkit.themes.{theme}").THEME
        self.root = project_root or os.path.join(os.path.dirname(HERE), name)
        self.library = library or os.path.join(os.path.dirname(os.path.dirname(HERE)), "assets", "sfx-library", "library.json")
        if not os.path.exists(self.library):
            raise SystemExit(f"no sound library at {self.library}: run scripts/hfkit/sfx_library.py fetch (HeyGen) or offline (no account)")
        self.contact = contact if contact is not None else self.theme.get("contact")
        self.star = star or self.theme.get("star")
        self.bed, self.core = bed, core
        self.cards, self.js, self.sfx, self.images, self.pushes, self.snaps = [], [], [], {}, [], []
        self._hook, self._n = None, 0

    # ------------------------------------------------------------ anchors
    def _at(self, phrase, after=0):
        p = [_norm(x) for x in phrase.split()]
        for i in range(after, len(self.TOK) - len(p) + 1):
            if self.TOK[i:i + len(p)] == p:
                return i
        raise SystemExit(f"{self.name}: phrase not found in the cut: {phrase!r}")

    def t(self, phrase, after=0):
        """Start of the first word of the phrase, in the cut's own seconds."""
        return round(self.W[self._at(phrase, after)]["t0"], 2)

    def tw(self, phrase, k, after=0):
        """Start of the k-th word (0-based) inside the phrase, for a word that repeats elsewhere."""
        return round(self.W[self._at(phrase, after) + k]["t0"], 2)

    def e(self, phrase, after=0):
        """End of the last word of the phrase."""
        return round(self.W[self._at(phrase, after) + len(phrase.split()) - 1]["t1"], 2)

    # ------------------------------------------------------------ internals
    def _id(self, kind):
        self._n += 1
        return f"{kind}{self._n}"

    def _img(self, path):
        base = os.path.basename(path)
        if base in self.images:  # a second <img> of the same file trips duplicate_media_discovery_risk
            stem, ext = os.path.splitext(base)
            k = 2
            while f"{stem}_{k}{ext}" in self.images:
                k += 1
            base = f"{stem}_{k}{ext}"
        self.images[base] = path
        return f"assets/img/{base}"

    def _foot(self, src, date):
        if not src:
            return ""
        return f'<div class="foot"><span class="src">{esc(src)}</span><span class="date">{esc(date or "")}</span></div>'

    def sound(self, tag, at, vol=None, secs=None, offset=0):
        self.sfx.append((tag, round(at, 2), vol, secs, offset))

    def _card(self, cid, t0, t1, inner, cls="card top w940", snd="card_in", style=""):
        st = f' style="{style}"' if style else ""
        self.cards.append(f'      <div class="{cls}" id="{cid}"{st}>{inner}</div>')
        self.js.append(f'cardIn("#{cid}", {t0}); cardOut("#{cid}", {t1});')
        self.snaps.append(round(min(t1, self.dur) - 0.4, 2))
        if snd and t0 > 0.05:
            self.sound(snd, t0)

    # ------------------------------------------------------------ frame zero
    def hook(self, lines, spark=None, count=None, out=4.8, sizes=None):
        """lines: 1-3 strings; line one is on screen at 0.00. spark: the word in accent.
        count: dict(line, token, value, fmt, from, final) counts that token up as its line lands.
        sizes: px per line when the claim is not on line two (the theme default sizes line two biggest)."""
        self._hook = dict(lines=lines, spark=spark, count=count, out=out, sizes=sizes)

    # ------------------------------------------------------------ cards
    def headline(self, img, src, date, t0, t1, pos="under"):
        cid = self._id("hd")
        cls = "card under" if pos == "under" else "card top w940 plain"
        self._card(cid, t0, t1, f'<img class="shot" src="{self._img(img)}" alt="" />{self._foot(src, date)}', cls=cls, snd="headline")

    def image(self, img, t0, t1, src=None, date=None, wipe_at=None, width=760, kicker=None):
        cid = self._id("im")
        k = f'<div class="kicker" style="margin:4px 0 14px">{esc(kicker)}</div>' if kicker else ""
        self._card(cid, t0, t1, f'{k}<div class="wipe" id="{cid}w"><img class="shot" src="{self._img(img)}" alt="" /></div>{self._foot(src, date)}',
                   cls="card top plain", style=f"left:{(1080 - width) // 2}px;width:{width}px")
        if wipe_at is not None:
            self.js.append(f'gsap.set("#{cid}w", {{clipPath: "inset(0 100% 0 0)"}}); tl.fromTo("#{cid}w", {{clipPath: "inset(0 100% 0 0)"}}, '
                           f'{{clipPath: "inset(0 0% 0 0)", duration: 1.2, ease: "power2.out", immediateRender: false}}, {wipe_at});')
            self.sound("sweep", wipe_at)

    def title(self, text, t0, t1, kicker=None, slam_at=None):
        cid = self._id("ti")
        slam = t0 + 0.05 if slam_at is None else slam_at
        k = f'<div class="kicker">{esc(kicker)}</div>' if kicker else ""
        self._card(cid, t0, t1, f'{k}<div class="title" id="{cid}t">{esc(text)}</div>', snd="card_in" if slam - t0 > 0.3 else None)
        self.js.append(f'gsap.set("#{cid}t", {{opacity: 0}}); tl.fromTo("#{cid}t", {{opacity: 0, scale: 1.4}}, '
                       f'{{opacity: 1, scale: 1, duration: 0.32, ease: "power4.out", immediateRender: false}}, {slam});')
        self.sound("slam", slam)

    def chip(self, img, tag, t0, t1):
        cid = self._id("ch")
        self.cards.append(f'      <div class="chipcard" id="{cid}"><img src="{self._img(img)}" alt="" /><span class="tagpill">{esc(tag)}</span></div>')
        self.js.append(f'pop("#{cid}", {t0}); tl.to("#{cid}", {{opacity: 0, duration: 0.25, ease: "power2.in"}}, {t1 - 0.25});')
        self.snaps.append(round(t1 - 0.4, 2))
        self.sound("pop", t0)

    def flow(self, kicker, nodes, t0, t1, sub=None, sub_at=None, src=None, date=None):
        """nodes: [dict(text, at, hot, img, strike, light, ripple, sfx)], arrows drawn between them."""
        cid = self._id("fl")
        cells, js = [], []
        for j, n in enumerate(nodes):
            nid = f"{cid}n{j}"
            if j:
                cells.append(ARROW.format(id=f"{cid}a{j}"))
                js.append(f'draw("{cid}a{j}", {n["at"] - 0.25}, 0.25);')
            img = f'<img src="{self._img(n["img"])}" alt="" />' if n.get("img") else ""
            rip = f'<span class="ripple" id="{nid}r"></span>' if n.get("ripple") else ""
            strike = (f'<svg class="strike" viewBox="0 0 100 20" preserveAspectRatio="none"><path id="{nid}s" d="M2 12 Q 50 4 98 10" /></svg>'
                      if n.get("strike") else "")
            cells.append(f'<span class="node{" hot" if n.get("hot") else ""}" id="{nid}">{img}{esc(n["text"])}{rip}{strike}</span>')
            js.append(f'pop("#{nid}", {n["at"]});')
            self.sound(n.get("sfx", "pop"), n["at"])
            if n.get("ripple"):
                js.append(f'gsap.set("#{nid}r", {{opacity: 0}}); tl.fromTo("#{nid}r", {{scale: 0.3, opacity: 0.9}}, '
                          f'{{scale: 2.2, opacity: 0, duration: 0.6, ease: "power2.out", immediateRender: false}}, {n["at"] + 0.1});')
            if n.get("strike"):
                js.append(f'draw("{nid}s", {n["strike"]}, 0.35); tl.to("#{nid}", {{opacity: 0.45, duration: 0.3}}, {n["strike"] + 0.35});')
                self.sound("strike", n["strike"], secs=1.0)
            if n.get("light"):
                js.append(f'tl.to("#{nid}", {{backgroundColor: ACCENT, borderColor: ACCENT, color: ONACC, duration: 0.3}}, {n["light"]});'
                          f'tl.fromTo("#{nid}", {{scale: 1}}, {{scale: 1.08, duration: 0.25, ease: "power3.out", immediateRender: false}}, {n["light"]});'
                          f'tl.to("#{nid}", {{scale: 1, duration: 0.3}}, {n["light"] + 0.3});')
                self.sound("chime_short", n["light"])
        parts = [f'<div class="kicker">{esc(kicker)}</div>', f'<div class="flowrow">{"".join(cells)}</div>']
        if sub:
            parts.append(f'<div class="sub" id="{cid}sub">{esc(sub)}</div>')
            if sub_at is not None:
                js.append(f'gsap.set("#{cid}sub", {{opacity: 0}}); tl.fromTo("#{cid}sub", {{opacity: 0, y: 12}}, '
                          f'{{opacity: 1, y: 0, duration: 0.35, immediateRender: false}}, {sub_at});')
        parts.append(self._foot(src, date))
        self._card(cid, t0, t1, "".join(parts))
        self.js.extend(js)

    def chips(self, kicker, items, t0, t1, src=None, date=None):
        """items: [dict(text or img, at, hot)], no arrows: a set, not a sequence."""
        cid = self._id("cs")
        cells, js = [], []
        for j, it in enumerate(items):
            iid = f"{cid}i{j}"
            if it.get("img"):
                cells.append(f'<span class="logochip" id="{iid}"><img src="{self._img(it["img"])}" alt="" /></span>')
            else:
                cells.append(f'<span class="node{" hot" if it.get("hot") else ""}" id="{iid}">{esc(it["text"])}</span>')
            js.append(f'pop("#{iid}", {it["at"]});')
            self.sound(it.get("sfx", "pop_small"), it["at"])
        self._card(cid, t0, t1, f'<div class="kicker">{esc(kicker)}</div><div class="flowrow">{"".join(cells)}</div>{self._foot(src, date)}')
        self.js.extend(js)

    def counter(self, value, fmt, count_at, land_at, t0, t1, label, src=None, date=None, frm=None, final=None, land_sfx=None):
        """fmt: money | int | mult | pct | rank, or a dict(pre, suf, dec, from). rank counts down from 100."""
        cid = self._id("ct")
        f = _fmt(fmt, value, frm, final)
        self._card(cid, t0, t1, f'<span class="stat" id="{cid}v" data-start-text="{esc(_num(f, f.get("from", 0)))}">{esc(_widest(f))}</span>'
                                f'<div class="kicker center">{esc(label)}</div>{self._foot(src, date)}', snd="card_in_heavy")
        self.js.append(f'count("#{cid}v", {count_at}, {land_at}, {json.dumps(f)}, false);')
        self.sound("counter", count_at, secs=round(land_at - count_at, 2))
        self.sound(land_sfx or ("money" if f.get("pre") == "$" else "win"), land_at)

    def bars(self, kicker, bars, t0, t1, img=None, src=None, date=None, limit=None):
        """bars: [dict(name, frac, at, value, accent)]; limit: dict(frac, label, at) drops a stop line."""
        cid = self._id("br")
        head = (f'<div class="whead"><img src="{self._img(img)}" alt="" /><span class="kicker">{esc(kicker)}</span></div>'
                if img else f'<div class="kicker">{esc(kicker)}</div>')
        rows, js = [], []
        for j, b in enumerate(bars):
            fid = f"{cid}f{j}"
            rows.append(f'<div class="brow"><span class="bname">{esc(b["name"])}</span><span class="track">'
                        f'<span class="fill {"f2" if b.get("accent") else "f1"}" id="{fid}"></span></span>'
                        f'<span class="bval" id="{fid}v">{esc(b.get("value", ""))}</span></div>')
            js.append(f'gsap.set("#{fid}", {{scaleX: 0}}); tl.to("#{fid}", {{scaleX: {b["frac"]}, duration: 0.8, ease: "power2.out"}}, {b["at"]});')
            if b.get("value"):
                js.append(f'gsap.set("#{fid}v", {{opacity: 0}}); tl.fromTo("#{fid}v", {{opacity: 0, x: -16}}, '
                          f'{{opacity: 1, x: 0, duration: 0.35, immediateRender: false}}, {b["at"] + 0.6});')
            self.sound(b.get("sfx", "sweep"), b["at"])
        lim = ""
        if limit:
            lim = (f'<div class="limit" id="{cid}lim" style="--lx:{limit["frac"]}"><span class="limline"></span>'
                   f'<span class="limlabel">{esc(limit["label"])}</span></div>')
            js.append(f'gsap.set("#{cid}lim", {{opacity: 0}}); tl.fromTo("#{cid}lim", {{opacity: 0, y: -12}}, '
                      f'{{opacity: 1, y: 0, duration: 0.3, ease: "power3.out", immediateRender: false}}, {limit["at"]});')
            self.sound("thud", limit["at"])
        self._card(cid, t0, t1, f'{head}<div class="bars">{"".join(rows)}{lim}</div>{self._foot(src, date)}')
        self.js.extend(js)

    def quote(self, text, emphasis, draw_at, t0, t1, src=None, date=None, by=None, size=None):
        cid = self._id("qt")
        i = text.lower().find(emphasis.lower())
        if i < 0:
            raise SystemExit(f"{self.name}: emphasis {emphasis!r} not in quote")
        body = (f'{esc(text[:i])}<span class="em">{esc(text[i:i + len(emphasis)])}<svg class="ul" viewBox="0 0 300 22" '
                f'preserveAspectRatio="none"><path id="{cid}u" d="M4 15 C 70 7, 170 19, 296 9" /></svg></span>{esc(text[i + len(emphasis):])}')
        st = f' style="font-size:{size}px"' if size else ""
        b = f'<div class="by">{esc(by)}</div>' if by else ""
        self._card(cid, t0, t1, f'<div class="q"{st}>{body}</div>{b}{self._foot(src, date)}')
        self.js.append(f'draw("{cid}u", {draw_at}, 0.55);')
        self.sound("tick", draw_at)

    def grid(self, kicker, t0, t1, strike_at, rows=4, cols=5, sub=None):
        """A spreadsheet, struck through: the thing the promise says you stop living in."""
        cid = self._id("gr")
        cells = "".join('<span class="cell"></span>' for _ in range(rows * cols))
        s = f'<div class="sub">{esc(sub)}</div>' if sub else ""
        self._card(cid, t0, t1, f'<div class="kicker">{esc(kicker)}</div><div class="sheet" style="--cols:{cols}">{cells}'
                                f'<svg class="strike big" viewBox="0 0 100 20" preserveAspectRatio="none"><path id="{cid}s" d="M2 16 Q 50 2 98 6" /></svg></div>{s}')
        self.js.append(f'gsap.set("#{cid} .cell", {{opacity: 0}}); tl.fromTo("#{cid} .cell", {{opacity: 0, scale: 0.6}}, '
                       f'{{opacity: 1, scale: 1, duration: 0.3, ease: "power3.out", stagger: 0.015, immediateRender: false}}, {t0 + 0.15});'
                       f'draw("{cid}s", {strike_at}, 0.45); tl.to("#{cid} .cell", {{opacity: 0.35, duration: 0.3}}, {strike_at + 0.4});')
        self.sound("strike", strike_at, secs=1.0)

    def fan(self, kicker, left, sub, t0, t1, fan_at, count=100):
        """One source, then a field of copies: build it once, sell it many times."""
        cid = self._id("fn")
        dots = "".join('<span class="dot"></span>' for _ in range(count))
        self._card(cid, t0, t1, f'<div class="kicker">{esc(kicker)}</div><div class="fanrow"><span class="node hot" id="{cid}l">{esc(left)}</span>'
                                f'{ARROW.format(id=cid + "a")}<div class="dots">{dots}</div></div><div class="sub" id="{cid}sub">{esc(sub)}</div>')
        self.js.append(f'pop("#{cid}l", {t0 + 0.2}); draw("{cid}a", {fan_at - 0.3}, 0.3); gsap.set(["#{cid} .dot", "#{cid}sub"], {{opacity: 0}});'
                       f'tl.fromTo("#{cid} .dot", {{opacity: 0, scale: 0}}, {{opacity: 1, scale: 1, duration: 0.2, ease: "power3.out", stagger: 0.006, immediateRender: false}}, {fan_at});'
                       f'tl.fromTo("#{cid}sub", {{opacity: 0, y: 12}}, {{opacity: 1, y: 0, duration: 0.35, immediateRender: false}}, {fan_at + 0.2});')
        self.sound("pop", t0 + 0.2)
        self.sound("sweep", fan_at)

    def network(self, kicker, center, t0, t1, spread_at, n=8, sub=None):
        """Word of mouth: a centre node, then people around it, each line drawing out.
        Drawn in the card's own pixels (868 x 380) so the stroke dash matches the path length."""
        cid = self._id("nw")
        W, H, cx, cy = 868, 380, 434, 190
        pts = [(cx + 330 * math.cos(2 * math.pi * k / n - math.pi / 2), cy + 150 * math.sin(2 * math.pi * k / n - math.pi / 2)) for k in range(n)]
        lines = "".join(f'<path id="{cid}p{k}" d="M{cx} {cy} L{x:.1f} {y:.1f}" />' for k, (x, y) in enumerate(pts))
        people = "".join(f'<span class="person" id="{cid}d{k}" style="left:{x / W * 100:.2f}%;top:{y / H * 100:.2f}%"></span>' for k, (x, y) in enumerate(pts))
        s = f'<div class="sub">{esc(sub)}</div>' if sub else ""
        self._card(cid, t0, t1, f'<div class="kicker">{esc(kicker)}</div><div class="net"><svg class="netlines" viewBox="0 0 {W} {H}">{lines}</svg>'
                                f'{people}<span class="node hot netcenter">{esc(center)}</span></div>{s}')
        for k in range(n):
            self.js.append(f'draw("{cid}p{k}", {spread_at + k * 0.07:.2f}, 0.3); pop("#{cid}d{k}", {spread_at + 0.2 + k * 0.07:.2f});')
        self.sound("pop_small", spread_at + 0.2)
        self.sound("notify_double", spread_at + 0.5)

    def converge(self, kicker, box, inside, mover, t0, t1, move_at, pulse_at=None):
        """A box with the person in it and an empty slot; the thing slides into the slot."""
        cid = self._id("cv")
        self._card(cid, t0, t1, f'<div class="kicker">{esc(kicker)}</div><div class="convrow"><div class="cbox" id="{cid}b"><span class="cboxlabel">{esc(box)}</span>'
                                f'<span class="node">{esc(inside)}</span><span class="slot" id="{cid}s"></span></div><span class="node hot" id="{cid}m">{esc(mover)}</span></div>')
        self.js.append(f'slide("#{cid}m", "#{cid}s", {move_at});')
        self.sound("whip", move_at)
        if pulse_at:
            self.js.append(f'tl.to("#{cid}b", {{borderColor: ACCENT, duration: 0.25}}, {pulse_at});')
            self.sound("chime_short", pulse_at)

    def route(self, kicker, source, targets, t0, t1, at, src=None, date=None):
        """One source feeding several targets; the hot target gets the line, the rest dim."""
        cid = self._id("rt")
        n = len(targets)
        cells = []
        for j, tg in enumerate(targets):
            img = f'<img src="{self._img(tg["img"])}" alt="" />' if tg.get("img") else ""
            cells.append(f'<span class="node{" hot" if tg.get("hot") else ""}" id="{cid}t{j}">{img}{esc(tg["text"])}</span>')
        paths = "".join(f'<path id="{cid}l{j}" class="{"hotline" if tg.get("hot") else ""}" d="M434 4 L{(j + 0.5) * 868 / n:.1f} 76" />' for j, tg in enumerate(targets))
        self._card(cid, t0, t1, f'<div class="kicker">{esc(kicker)}</div><div class="rsource"><span class="node" id="{cid}src">{esc(source)}</span></div>'
                                f'<svg class="rlines" viewBox="0 0 868 80">{paths}</svg>'
                                f'<div class="rrow" style="grid-template-columns:repeat({n},1fr)">{"".join(cells)}</div>{self._foot(src, date)}')
        self.js.append(f'pop("#{cid}src", {t0 + 0.15});')
        for j, tg in enumerate(targets):
            self.js.append(f'pop("#{cid}t{j}", {t0 + 0.3 + j * 0.08:.2f});')
            if tg.get("hot"):
                self.js.append(f'draw("{cid}l{j}", {at}, 0.4); tl.fromTo("#{cid}t{j}", {{scale: 1}}, {{scale: 1.12, duration: 0.25, ease: "power3.out", immediateRender: false}}, {at + 0.35});'
                               f'tl.to("#{cid}t{j}", {{scale: 1, duration: 0.3}}, {at + 0.6});')
            else:
                self.js.append(f'gsap.set("#{cid}l{j}", {{opacity: 0}}); tl.to("#{cid}t{j}", {{opacity: 0.4, duration: 0.3}}, {at + 0.35});')
        self.sound("sweep", at)
        self.sound("chime_short", at + 0.35)

    def list(self, title, items, t0, t1, mark="tick", red_title=False, slam=True):
        cid = self._id("ls")
        rows = []
        icon = '<path d="M11 19 L16 24 L26 12" />' if mark == "tick" else '<path d="M12 12 L24 24 M24 12 L12 24" />'
        for j, it in enumerate(items):
            iid = f"{cid}i{j}"
            rows.append(f'<div class="litem" id="{iid}"><svg class="lmark {mark}" viewBox="0 0 36 36"><rect x="1" y="1" width="34" height="34" rx="10" />{icon}</svg>'
                        f'<span class="ltext">{esc(it["text"])}</span></div>')
            self.js.append(f'gsap.set("#{iid}", {{opacity: 0}}); tl.fromTo("#{iid}", {{opacity: 0, x: -24}}, '
                           f'{{opacity: 1, x: 0, duration: 0.35, ease: "power3.out", immediateRender: false}}, {it["at"]});')
            self.sound("tick" if mark == "tick" else "pop_small", it["at"])
        self._card(cid, t0, t1, f'<div class="ltitle{" red" if red_title else ""}" id="{cid}t">{esc(title)}</div><div class="list">{"".join(rows)}</div>', snd=None)
        if slam and t0 > 0.05:
            self.js.append(f'tl.fromTo("#{cid}t", {{scale: 1.25}}, {{scale: 1, duration: 0.3, ease: "power4.out", immediateRender: false}}, {t0});')
            self.sound("slam", t0)

    def pairs(self, heads, rows, t0, t1, kicker=None, src=None, date=None):
        """A two-sided chart that builds row by row as it is said (3.7.0): heads ("If you want",
        "You need") over two columns, rows [dict(left, right, at, right_at)]. A row's left cell
        lands on `at` (the start of "if you want..."), its right cell on `right_at` (the start of
        "you need...", default at + 0.6). The newest right cell shows in the accent and the one
        before it settles to ink. A row said before the card lands is drawn with the card. Cells
        are one line each; the whole chart scales its type down together if any cell would wrap,
        so the rows stay level. Sized for the band above the head: keep each cell under about
        26 characters, five rows at most."""
        cid = self._id("pr")
        head = (f'<div class="prow phead"><span class="pcell">{esc(heads[0])}</span><span></span>'
                f'<span class="pcell">{esc(heads[1])}</span></div>')
        cells, prev = [], None
        for j, r in enumerate(rows):
            rid, xid, hid = f"{cid}r{j}", f"{cid}x{j}", f"{cid}h{j}"
            cells.append(f'<div class="prow" id="{rid}"><span class="pcell pl">{esc(r["left"])}</span>'
                         f'{ARROW.format(id=f"{cid}a{j}")}'
                         f'<span class="pcell pr" id="{xid}"><span class="prink">{esc(r["right"])}</span>'
                         f'<span class="prhot" id="{hid}">{esc(r["right"])}</span></span></div>')
            at = round(r["at"], 2)
            rat = round(r.get("right_at", at + 0.6), 2)
            if at > t0 + 0.05:
                self.js.append(f'gsap.set("#{rid}", {{opacity: 0}}); tl.fromTo("#{rid}", {{opacity: 0, x: -24}}, '
                               f'{{opacity: 1, x: 0, duration: 0.35, ease: "power3.out", immediateRender: false}}, {at});')
                self.sound("pop_small", at)
            if rat > t0 + 0.05:
                self.js.append(f'gsap.set("#{xid}", {{opacity: 0}}); tl.fromTo("#{xid}", {{opacity: 0, x: 24}}, '
                               f'{{opacity: 1, x: 0, duration: 0.35, ease: "power3.out", immediateRender: false}}, {rat});')
                self.sound("tick", rat)
            on = max(rat, t0)
            self.js.append(f'gsap.set("#{hid}", {{opacity: 0}}); tl.set("#{hid}", {{opacity: 1}}, {on});')
            if prev is not None:
                self.js.append(f'tl.set("#{prev}", {{opacity: 0}}, {on});')
            prev = hid
        kick = f'<div class="kicker">{esc(kicker)}</div>' if kicker else ""
        self._card(cid, t0, t1, f'{kick}<div class="pairs">{head}{"".join(cells)}</div>{self._foot(src, date)}',
                   cls="card top w940 tight")

    def timeline(self, kicker, ticks, t0, t1, src=None, date=None):
        """Dated steps on a rule: ticks [dict(label, sub, at)]."""
        cid = self._id("tm")
        cells = "".join(f'<div class="tick" id="{cid}k{j}"><span class="tdot"></span><span class="tlabel">{esc(k["label"])}</span>'
                        f'<span class="tsub">{esc(k.get("sub", ""))}</span></div>' for j, k in enumerate(ticks))
        self._card(cid, t0, t1, f'<div class="kicker">{esc(kicker)}</div><div class="tline"><span class="trule" id="{cid}r"></span>{cells}</div>{self._foot(src, date)}')
        self.js.append(f'gsap.set("#{cid}r", {{scaleX: 0}}); tl.to("#{cid}r", {{scaleX: 1, duration: 0.7, ease: "power2.out"}}, {t0 + 0.2});')
        for j, k in enumerate(ticks):
            self.js.append(f'pop("#{cid}k{j}", {k["at"]});')
            self.sound("pop_small", k["at"])

    # ------------------------------------------------------------ the brand objects (3.6.0)
    def icon(self, name, t0, t1, x=None, y=None, size=300, tilt=0, sfx="pop"):
        """A transparent brand object from the creator's icon kit, popped in on its line.
        name: a kit name ("check", "arrow-trend-up"), a tag ("growth"), or a PNG path. Default
        spot is the right side of the band above the head; x, y place the object's centre. One
        object per beat, never over the face or the caption line."""
        path = find_icon(name)
        cid = self._id("ic")
        cx = (1080 - 70 - size // 2) if x is None else x
        cy = 300 if y is None else y
        style = (f"left:{cx - size // 2}px;top:{cy - size // 2}px;width:{size}px;height:{size}px;"
                 f"transform:rotate({tilt}deg)")
        self.cards.append(f'      <div class="iconcard" id="{cid}" style="{style}"><img src="{self._img(path)}" alt="" /></div>')
        self.js.append(f'pop("#{cid}", {t0}); tl.to("#{cid}", {{opacity: 0, scale: 0.6, duration: 0.22, ease: "power2.in"}}, {t1 - 0.22});')
        self.snaps.append(round(min(t1, self.dur) - 0.4, 2))
        if sfx and t0 > 0.05:
            self.sound(sfx, t0)

    def take(self, t0, t1=None, label="My take"):
        """The opinion slot: the creator's own take, said off the cuff after the reported story.
        A pill on the band above the head names it as theirs for as long as it runs, the way a
        newspaper labels its opinion page. t1 defaults to the end of the cut."""
        cid = self._id("tk")
        t1 = self.dur if t1 is None else t1
        self.cards.append(f'      <div class="takepill" id="{cid}"><span class="takechip">&rarr;</span>{esc(label)}</div>')
        self.js.append(f'pop("#{cid}", {t0}); tl.to("#{cid}", {{opacity: 0, duration: 0.25, ease: "power2.in"}}, {max(t0, t1 - 0.25)});')
        self.snaps.append(round(min(t0 + 1.0, self.dur - 0.1), 2))
        self.sound("pop", t0)

    def stamp(self, clock, t0, t1, label=None):
        """A time stamp for day-in-the-life and break clips: the clock time big, what is happening
        small, top left. One per clip, in at the cut, out before the next stamp."""
        cid = self._id("st")
        sub = f'<span class="stamplab">{esc(label)}</span>' if label else ""
        self.cards.append(f'      <div class="stamp" id="{cid}"><span class="stampclock">{esc(clock)}</span>{sub}</div>')
        self.js.append(f'cardIn("#{cid}", {t0}); cardOut("#{cid}", {t1});')
        self.snaps.append(round(min(t1, self.dur) - 0.3, 2))
        if t0 > 0.05:
            self.sound("tick", t0)

    def push(self, t0, t1, scale=1.06):
        """Slow camera push-in on a line that carries the belief."""
        self.pushes.append((round(t0, 2), round(t1, 2), scale))

    def riser_into(self, at):
        self.sound("riser", at - 2.0)

    # ------------------------------------------------------------ build
    def _hook_parts(self):
        h = self._hook
        if not h:
            return "", ""
        c = h["count"]
        f = _fmt(c["fmt"], c["value"], c.get("from"), c.get("final")) if c else None
        spans, js = [], []
        for i, line in enumerate(h["lines"]):
            txt = esc(line)
            if c and c["line"] == i:
                txt = txt.replace(esc(c["token"]), f'<span id="hnum" data-start-text="{esc(_num(f, f.get("from", 0)))}">{esc(_widest(f))}</span>', 1)
            elif h["spark"] and esc(h["spark"]) in txt:
                txt = txt.replace(esc(h["spark"]), f'<span class="spark">{esc(h["spark"])}</span>', 1)
            st = f' style="font-size:{h["sizes"][i]}px"' if h.get("sizes") else ""
            spans.append(f'<span class="hl" id="hl{i}"{st}>{txt}</span>')
        t = 0.15
        for i in range(1, len(h["lines"])):
            js.append(f'gsap.set("#hl{i}", {{opacity: 0}}); tl.set("#hl{i}", {{opacity: 1, y: 60}}, {t:.2f}); tl.to("#hl{i}", {{y: 0, duration: 0.18, ease: "power4.out"}}, {t:.2f});')
            if c and c["line"] == i:
                js.append(f'count("#hnum", {t + 0.03:.2f}, {t + 0.98:.2f}, {json.dumps(f)}, true);')
                self.sound("counter", t + 0.03, secs=0.95)
                self.sound("money" if f.get("pre") == "$" else "win", t + 1.03)
                t += 1.0
            else:
                t += 0.22
        js.append(f'tl.to("#hook", {{opacity: 0, duration: 0.25, ease: "power2.in"}}, {h["out"]});')
        return f'<div id="hook">{"".join(spans)}</div>', "\n        ".join(js)

    def _captions(self):
        W = self.W
        groups, cur, chars = [], [], 0
        for i, w in enumerate(W):
            n = len(re.sub(r"[.,;:]+$", "", w["w"]))
            if cur and (len(cur) >= 3 or chars + n + 1 > 16):
                groups.append(cur); cur, chars = [], 0
            cur.append(i); chars += n + 1
            if w["w"].rstrip()[-1:] in ".?!":
                groups.append(cur); cur, chars = [], 0
        if cur:
            groups.append(cur)
        html, data = [], []
        for g, idx in enumerate(groups):
            spans = " ".join(f'<span class="cw" id="cw{i}">{esc(re.sub(r"[.,;:!?]+$", "", W[i]["w"]))}</span>' for i in idx)
            html.append(f'<div class="capgroup" id="cg{g}">{spans}</div>')
            g1 = W[groups[g + 1][0]]["t0"] if g + 1 < len(groups) else self.dur
            data.append({"id": f"cg{g}", "t0": round(max(0, W[idx[0]]["t0"] - 0.02), 3), "t1": round(min(g1, W[idx[-1]]["t1"] + 0.6, self.dur), 3),
                         "words": [{"id": f"cw{i}", "t0": W[i]["t0"], "t1": max(W[i]["t1"], W[i]["t0"] + 0.12)} for i in idx]})
        return "\n".join(html), data

    def _audio(self, lib):
        files, out = {}, []
        for k, (tag, at, vol, secs, off) in enumerate(sorted(self.sfx, key=lambda s: s[1])):
            if tag not in lib or at >= self.dur - 0.2:
                continue
            item = lib[tag]
            fname = os.path.basename(item["file"])
            files[fname] = item["file"]
            d = round(min(secs or item["seconds"], self.dur - max(0, at)), 2)
            v = vol if vol is not None else self.theme["sfx_volume"].get(tag, 0.24)
            out.append(f'<audio id="sx{k}" src="assets/lib/{fname}" data-start="{max(0, at):.2f}" data-duration="{d}" '
                       f'data-media-start="{off}" data-track-index="{20 + k % 6}" data-volume="{v}"></audio>')
        return "\n      ".join(out), files

    def _scaffold(self):
        os.makedirs(self.root, exist_ok=True)
        for d in ("assets/img", "assets/lib", "compositions"):
            os.makedirs(os.path.join(self.root, d), exist_ok=True)
        pkg = os.path.join(self.root, "package.json")
        if not os.path.exists(pkg):
            v = "0.8.96"
            json.dump({"name": self.name, "private": True, "type": "module",
                       "scripts": {k: f"npx --yes hyperframes@{v} {k if k != 'dev' else 'preview'}" for k in ("dev", "check", "render")}},
                      open(pkg, "w"), indent=2)
            json.dump({"id": self.name, "name": self.name}, open(os.path.join(self.root, "meta.json"), "w"), indent=2)
            json.dump({"$schema": "https://hyperframes.heygen.com/schema/hyperframes.json",
                       "paths": {"blocks": "compositions", "components": "compositions/components", "assets": "assets"}},
                      open(os.path.join(self.root, "hyperframes.json"), "w"), indent=2)
            open(os.path.join(self.root, ".gitignore"), "w").write("node_modules/\n.hyperframes/\nsnapshots/\nassets/\n*.mp4\n")

    def build(self):
        if getattr(self, "_built", False):
            raise SystemExit("build() runs once per Episode: sounds and hook timings would double")
        self._built = True
        self._scaffold()
        shutil.copy2(self.footage, os.path.join(self.root, "assets/footage.mp4"))
        shutil.copy2(self.voice, os.path.join(self.root, "assets/voice.m4a"))
        lib = json.load(open(self.library))
        libdir = os.path.dirname(os.path.abspath(self.library))
        home = os.path.dirname(os.path.dirname(libdir))  # older libraries list paths from the workspace root
        where = lambda rel: rel if os.path.isabs(rel) else next((p for p in (os.path.join(libdir, rel), os.path.join(home, rel)) if os.path.exists(p)), os.path.join(libdir, rel))
        star = ""
        if self.show and self.star:
            star = f'<img id="star" src="{self._img(self.star)}" alt="" />'
            self.sound("sting", 0.0)
        hook_html, hook_js = self._hook_parts()
        audio, files = self._audio(lib)
        files[os.path.basename(lib[self.bed]["file"])] = lib[self.bed]["file"]
        for fname, rel in files.items():
            shutil.copy2(where(rel), os.path.join(self.root, "assets/lib", fname))
        for base, path in self.images.items():
            shutil.copy2(path, os.path.join(self.root, "assets/img", base))
        carved = os.path.join(self.root, ".bed.carved.html")
        bedfile = os.path.basename(lib[self.bed]["file"])
        bed = (open(carved).read() if os.path.exists(carved) else
               f'<audio id="bed" src="assets/lib/{bedfile}" data-start="0" data-duration="{self.dur}" data-track-index="11" data-volume="{self.theme["bed_volume"]}"></audio>')
        caps_html, caps_data = self._captions()
        star_js = ('tl.fromTo("#star", {scale: 0.82, rotation: -14, opacity: 1}, {scale: 1, rotation: 0, opacity: 1, duration: 0.5, ease: "power3.out"}, 0);'
                   'tl.to("#star", {opacity: 0, scale: 0.9, duration: 0.25, ease: "power2.in"}, 1.25);') if star else ""
        contact = ""
        if self.contact:
            head, *rest = self.contact
            contact = (f'<div id="contact"><div class="h"><span class="plus">+</span> {esc(head)}</div>' +
                       "".join(f'<div class="s">{esc(x)}</div>' for x in rest) + "</div>")
        pushes = sorted(self.pushes)
        for a, b in zip(pushes, pushes[1:]):
            if b[0] < a[1] + 0.5:
                raise SystemExit(f"{self.name}: push-ins overlap: {a} {b}")
        rep = {"TITLE": esc(self.name), "THEME_CSS": self.theme["css"], "FONT_FACES": self.theme.get("font_faces", ""),
               "DUR": f"{self.dur}", "BED": bed, "SFX": audio, "STAR": star, "HOOK": hook_html, "CARDS": "\n".join(self.cards),
               "CONTACT": contact, "ACCENT": self.theme["accent"], "ONACCENT": self.theme["on_accent"],
               "PUSHES": json.dumps(pushes), "STAR_JS": star_js, "HOOK_JS": hook_js, "CARDS_JS": "\n        ".join(self.js)}
        out = re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: rep[m.group(1)], open(os.path.join(HERE, "base.tpl")).read())
        open(os.path.join(self.root, "index.html"), "w").write(out)
        cap = (open(os.path.join(HERE, "captions.tpl")).read().replace("{{CAPTIONS}}", caps_html).replace("{{CAPDATA}}", json.dumps(caps_data))
               .replace("{{DUR}}", f"{self.dur}").replace("{{CAP_CSS}}", self.theme["cap_css"]))
        open(os.path.join(self.root, "compositions/captions.html"), "w").write(cap)
        print(f"{self.name}: {len(self.cards)} cards, {len(self.sfx)} sounds, {len(caps_data)} caption groups, {self.dur}s -> {self.root}")
        return self.root

    def carve(self, version="0.8.96"):
        """Carve the music bed around the voice once; the carved tag is kept for every rebuild.
        Needs the hyperframes-audio skill (npx skills add heygen-com/hyperframes) and @hyperframes/core,
        which is installed into the project on first use. Without them the bed stays flat and low."""
        script = os.path.expanduser("~/.claude/skills/hyperframes-audio/scripts/carve.mjs")
        if not os.path.exists(script):
            print("carve: hyperframes-audio skill not installed, bed stays flat at the theme volume")
            return False
        core = self.core
        if not core:
            core = self.root
            if not os.path.isdir(os.path.join(core, "node_modules", "@hyperframes", "core")):
                subprocess.run(["npm", "i", "-D", f"@hyperframes/core@{version}", "--no-audit", "--no-fund"], cwd=core, capture_output=True)
        idx = os.path.join(self.root, "index.html")
        r = subprocess.run(["node", script, "--comp", idx, "--bed", "bed", "--voice", "voice", "--core", core], capture_output=True, text=True)
        m = re.search(r'<audio id="bed"[^>]*></audio>', open(idx).read())
        if r.returncode or not m or "data-fx-carve" not in m.group(0):
            print(r.stdout[-800:], r.stderr[-800:])
            return False
        open(os.path.join(self.root, ".bed.carved.html"), "w").write(m.group(0))
        return True

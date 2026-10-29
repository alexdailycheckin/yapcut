#!/usr/bin/env python3
"""Cross-window restart scan: the repetition gate for a restart the transcript reads once.

stutter_check.py reads one transcript of the whole cut, and restart_scan.py reads 30s and 6s
windows. At every one of those lengths whisper tidies a short restart into a single clean
phrase, so both gates can pass a cut with an audible stumble in it. On 2026-09-30 a take
carried "It's the same bet we made. It's the same bet we made at <company>": the first pass
trailed off, 0.22s of quiet, then the clean pass. stutter_check.py, restart_scan.py and the
segmenter all read it as one phrase, and it was caught by ear.

What caught it: transcribe the cut in very short windows (1.1s and 1.6s, 0.45s hop), which
give whisper no room to smooth, and look for the same words in two windows that do NOT
overlap and start within 3s of each other. Two disjoint pieces of audio that decode to the
same trigram (or a bigram carrying a content word) are two utterances. Adjacent repeats
inside one window ("we must we must") are reported too; that is the check that found two
missed restarts on 2026-09-18.

Most hits are not restarts. A script says its own nouns more than once ("the work. They get
the work back"), and short windows mis-decode numbers, initialisms and names. So every hit is
checked against the cut's own transcript (--words), and only one shape is MEDIUM:

  the transcript says the repeated words exactly ONCE across the span where two disjoint
  windows heard them. The audio has two passes and the transcript merged them.

Everything else is LOW and only reported: the transcript says it twice too (a scripted
repeat, and stutter_check.py already reads that transcript), the transcript never says it
(a short-window mis-decode), or it carries a number, a number word or a single letter. A
MEDIUM is a decision like the other two detectors': cut it in the clause plan, or listen and
add one of its printed keys to the shared accept-file (<out>_stutter_ok.json).

Decoding is the whole cost: about 1.2s of whisper per window on an Apple M4 whatever the
window's length (whisper encodes 30s of audio for every window; --audio-ctx makes it 2x faster
and rewrote 41 of 60 real windows, some into repeats of their own, so it stays off). Until 3.9.0
every 0.45s of a cut was decoded, 500 to 900 windows a video, 13 to 30 minutes of GPU, and on
the 2026-10-25 batch a prescan lane ran half an hour ahead of each video. Now the audio says
where to look first (yaplib/repeats.py): the same phrase said twice leaves two stretches whose
MFCC frames line up at one lag, found in about a second with no whisper at all, and only the
windows around those stretches are decoded. On the October 25th Anthropic take that is 11
candidate stretches, every restart the transcript shows and the one it merged ("vice president
of" twice), for about 120 windows instead of 884. Three more things keep decoding off the
critical path (3.8.0):

  - every decode is cached by the audio it decoded (window_key), so any window whose audio is
    unchanged is never decoded twice
  - with --keeps the windows inside each keep are cut from the SOURCE take on the take's own
    fixed grid and cached per take in --store-dir (xwin_src/). A re-cut of the same takes moves
    the keeps, not the grid: on 2026-10-24 a 1.1x re-cut of five videos paid 13 to 22 minutes of
    whisper each for audio decoded the night before. The repeats are heard in the take too
    (a sped-up cut blurs a short repeat, and a restart split by a join sits whole in the take),
    with both passes inside the keeps, so a restart the clause plan already removed costs
    nothing. Only the cut's first and last window are decoded from the cut.
  - --prescan decodes the takes' windows inside the clause plans before the cut exists, so
    yapbatch runs it in a background lane while the cut and the previous render run.
Running two whisper processes side by side is slower than one after the other (they share the
GPU), so every decode takes a lock in the store directory.

The script settles what it says itself (--script): a gram the script says twice within 15 words
is LOW, never MEDIUM, before the opinion slot (--free-from).

--everywhere decodes the whole grid as before 3.9.0 (for a scan the acoustic finder cannot be
trusted on: a dub, a voice changer, a take where the second pass is sung).

Usage: xwin_scan.py --video cut.mp4 --words w_<out>.json
                    [--keeps keeps_full_<out>.json --speed 1.1 --workdir .yap_build]
                    [--accept-file <out>_stutter_ok.json] [--cache xwin_<out>.json]
                    [--store-dir .yap_build/xwin_src] [--script <out>_script.txt]
                    [--free-from <s>] [--windows 1.1,1.6] [--hop 0.45] [--show-low] [--everywhere]
       xwin_scan.py --prescan clauses_<out>.json [...] --store-dir .yap_build/xwin_src
Exit: 0 clean, only LOW hits, or every MEDIUM accepted; 2 a MEDIUM needs a decision.
"""
import argparse, hashlib, json, math, os, re, subprocess, sys, tempfile, time, wave

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from stutter_check import accept_key, load_accepted  # noqa: E402
from yaplib import repeats, rules  # noqa: E402
from yaplib import words as ywords  # noqa: E402
from yaplib import script as yscript  # noqa: E402

MODEL = ywords.whisper_model()   # the same model as the cut's words, or two wordings read as a restart
RATE = 16000
RW = rules.get("repetition")["windows"]
RA = rules.get("repetition")["acoustic"]
WINDOWS = tuple(RW["sizes_s"])  # measured 2026-09-18: 1.1s caught both restarts, 1.6s one, 3s none
HOP = RW["hop_s"]
LEAD_PAD = 0.25           # silence before and after each window: whisper decodes a clip
TAIL_PAD = 0.4            # that starts or ends on a word badly without it
MIN_AUDIO = 0.3           # the last window must carry at least this much audio
DECODE_CHUNK = 120        # windows per whisper-cli call (progress prints between calls)
SCRIPT_NEAR = 15          # script tokens within which the script saying a gram twice settles it
MAX_START_GAP = RW["max_start_gap_s"]   # two windows further apart than this are not one restart
SPAN_PAD = 0.6            # transcript words counted this far either side of a hit
THRESHOLD = 0.6           # MEDIUM at or above; only the merged shape (score()) gets there
MAX_WPS = 7.0             # a window decoding more words than this (plus 2 edge fragments) is a
                          # hallucination: the last 1.1s of a cut once came back as 25 words
STOP = set("a an the and or but so to of in on at it its it's is was be i you we they he "
           "she me my your our their this that these those for with as by do does did "
           "have has had not no yes".split())
NUMBER_WORDS = set("zero one two three four five six seven eight nine ten eleven twelve "
                   "twenty thirty forty fifty sixty seventy eighty ninety hundred hundreds "
                   "thousand thousands million millions billion billions trillion percent "
                   "first second third half".split())


def norm_words(text):
    return [w for w in re.sub(r"[^a-z0-9' ]", " ", text.lower()).split() if w.strip("'")]


def decode_prone(tokens):
    """Short windows mis-decode numbers, initialisms and names (measured 2026-09-18:
    "February 1st to 28th, 2027" came back "28th, 20th, 20th", "the AE" came back
    "the A.E.E."). A hit on a digit, a number word or a single letter (an initialism
    decodes as letters) is reported, never gated. A misheard name needs no rule: the
    transcript never says the misheard form, so score() reports it LOW."""
    return any(re.search(r"\d", t) or t in NUMBER_WORDS or (len(t) == 1 and t not in ("a", "i"))
               for t in tokens)


def read_pcm(path, tmpdir):
    """16 kHz mono s16 PCM of any media file."""
    wav = os.path.join(tmpdir, hashlib.sha1(os.path.abspath(path).encode()).hexdigest()[:12] + ".wav")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", path, "-vn",
                    "-ar", str(RATE), "-ac", "1", "-c:a", "pcm_s16le", wav], check=True)
    w = wave.open(wav, "rb")
    data = w.readframes(w.getnframes())
    w.close()
    return data


def read_wav(video, tmpdir):
    return read_pcm(video, tmpdir)


def source_pcm(src, workdir, tmpdir):
    """A source take's PCM. yapcut.py already wrote <workdir>/audio/<clip>.wav at 16 kHz mono;
    read that when it is there and newer than the clip, else decode the clip."""
    wav = os.path.join(workdir, "audio", os.path.splitext(os.path.basename(src))[0] + ".wav") if workdir else ""
    if wav and os.path.isfile(wav) and os.path.getmtime(wav) >= os.path.getmtime(src):
        w = wave.open(wav, "rb")
        if w.getframerate() == RATE and w.getnchannels() == 1 and w.getsampwidth() == 2:
            data = w.readframes(w.getnframes())
            w.close()
            return data
        w.close()
    return read_pcm(src, tmpdir)


def window_bytes(pcm, t, win):
    """The audio whisper decodes for one window: lead silence, the slice, tail silence."""
    a, b = int(t * RATE) * 2, min(len(pcm), int((t + win) * RATE) * 2)
    return (b"\x00\x00" * int(LEAD_PAD * RATE)) + pcm[a:b] + (b"\x00\x00" * int(TAIL_PAD * RATE))


def window_key(audio):
    """Content address of a window decode: the exact audio plus everything that changes what
    whisper returns for it. The same audio decodes the same wherever it sits, so a key computed
    from a source take survives every re-cut of that take."""
    h = hashlib.sha1(audio)
    h.update(json.dumps([LEAD_PAD, TAIL_PAD, os.path.basename(MODEL)]).encode())
    return h.hexdigest()[:24]


class Store:
    """Window decodes by content key ({key: text}, "" for a window with no speech), in one json
    file. save() merges with what is on disk, so two scans sharing a file lose nothing."""

    def __init__(self, path):
        self.path, self.w, self.new = path, {}, {}
        if path and os.path.isfile(path):
            try:
                d = json.load(open(path))
                self.w = d.get("windows", {}) if isinstance(d, dict) and d.get("store") == 1 else {}
            except (OSError, ValueError):
                self.w = {}

    def get(self, key):
        return self.new.get(key, self.w.get(key))

    def put(self, key, text):
        self.new[key] = text

    def save(self):
        if not self.path or not self.new:
            return
        cur = Store(self.path).w
        cur.update(self.w); cur.update(self.new)
        os.makedirs(os.path.dirname(os.path.abspath(self.path)), exist_ok=True)
        tmp = self.path + ".tmp"
        json.dump({"store": 1, "model": os.path.basename(MODEL), "windows": cur}, open(tmp, "w"), indent=0)
        os.replace(tmp, self.path)
        self.w, self.new = cur, {}


def clean_text(segs):
    # a looping decode repeats a whole segment verbatim; that is whisper, not speech
    segs = [s for i, s in enumerate(segs) if s and (i == 0 or s != segs[i - 1])]
    txt = " ".join(segs).strip()
    return "" if (not txt or "BLANK_AUDIO" in txt or not norm_words(txt)) else txt


class whisper_lock:
    """One whisper decode at a time across processes (3.8.0): yapbatch runs the next video's
    prescan beside the current video's cut and render, and two whisper-cli processes on one GPU
    are slower together than one after the other. A mkdir lock beside the window store, taken
    per chunk; a lock whose owner is gone is taken over."""

    def __init__(self, store_dir):
        self.dir = os.path.join(store_dir, ".whisper.lock") if store_dir else ""

    def __enter__(self):
        if not self.dir:
            return self
        os.makedirs(os.path.dirname(self.dir), exist_ok=True)
        waited = 0
        while True:
            try:
                os.mkdir(self.dir)
                open(os.path.join(self.dir, "pid"), "w").write(str(os.getpid()))
                return self
            except FileExistsError:
                try:
                    pid = int(open(os.path.join(self.dir, "pid")).read() or 0)
                    os.kill(pid, 0)
                except (OSError, ValueError):
                    if waited >= 2:                       # gone or never wrote a pid: take it over
                        subprocess.run(["rm", "-rf", self.dir])
                        continue
                if waited == 0:
                    print("  waiting for another whisper decode to finish", flush=True)
                time.sleep(1); waited += 1

    def __exit__(self, *exc):
        if self.dir:
            subprocess.run(["rm", "-rf", self.dir])


LOCK_DIR = ""


def decode_batch(jobs, tmpdir, label=""):
    """jobs: [(store, key, audio)]. Decodes every key not yet in its store, in ONE whisper-cli
    call per chunk (the model loads once; each window is still its own -f input, so nothing
    smooths across windows), and puts the text in the store."""
    todo, seen = [], set()
    for st, key, audio in jobs:
        if st.get(key) is None and key not in seen:
            seen.add(key); todo.append((st, key, audio))
    if not todo:
        return 0
    t0 = time.time()
    for c in range(0, len(todo), DECODE_CHUNK):
        part = todo[c:c + DECODE_CHUNK]
        files = []
        for st, key, audio in part:
            f = os.path.join(tmpdir, key + ".wav")
            o = wave.open(f, "wb"); o.setnchannels(1); o.setsampwidth(2); o.setframerate(RATE)
            o.writeframes(audio); o.close()
            files.append(f)
        cmd = ["whisper-cli", "-m", MODEL, "-oj", "-np"]
        for f in files:
            cmd += ["-f", f]
        with whisper_lock(LOCK_DIR):
            r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            # a scan that could not run must never read as a clean zero
            sys.stderr.write((r.stderr or "")[-600:])
            sys.exit(f"xwin_scan: whisper-cli failed (rc {r.returncode}) on {label or 'the'} windows; "
                     "nothing was scanned, so the gate cannot pass")
        for (st, key, _a), f in zip(part, files):
            try:
                segs = [s.get("text", "").strip() for s in json.load(open(f + ".json"))["transcription"]]
            except (OSError, ValueError, KeyError):
                segs = []
            st.put(key, clean_text(segs))
        done = min(c + DECODE_CHUNK, len(todo))
        print(f"  {label}decoded {done}/{len(todo)} windows ({time.time() - t0:.0f}s)", flush=True)
    return len(todo)


def pcm_array(pcm):
    """int16 numpy view of a PCM byte string."""
    return repeats.np.frombuffer(pcm, dtype=repeats.np.int16)


def heard_twice(pcm, spans, max_lag, label=""):
    """Where this audio says something twice (yaplib/repeats.py), kept to the repeats whose two
    passes both sit mostly inside `spans` [(lo, hi)]: the stretches a scan decodes. Returns
    ([(lo, hi)] padded and merged, [Repeat])."""
    evs = repeats.find(pcm_array(pcm), max_lag=max_lag)

    def inside(a, b):
        return sum(max(0.0, min(b, hi) - max(a, lo)) for lo, hi in spans) >= 0.6 * (b - a)
    kept = [e for e in evs if inside(e.t0, e.t1) and inside(*e.pass2)]
    out = repeats.spans_of(kept, RA["window_pad_s"])
    print(f"  repeats{label}: {len(kept)} stretch(es) heard twice"
          + (f" ({len(evs) - len(kept)} outside the cut)" if len(evs) > len(kept) else "")
          + f", {sum(hi - lo for lo, hi in out):.1f}s of audio to decode")
    return out, kept


def clip_spans(spans, lo, hi):
    """The parts of `spans` inside [lo, hi]."""
    return [(max(lo, a), min(hi, b)) for a, b in spans if a < hi and b > lo]


def grid_times(lo, hi, win, hop):
    """Window starts on the fixed grid k*hop whose whole window lies inside [lo, hi]. The grid
    is anchored at 0 of the timeline it lives on, so the same take always yields the same
    windows whatever the cut keeps of it."""
    k = max(0, math.ceil((lo - 1e-6) / hop))
    out = []
    while k * hop + win <= hi + 0.02:
        out.append(round(k * hop, 2)); k += 1
    return out


def cut_grid(dur, win, hop):
    out, k = [], 0
    while k * hop + MIN_AUDIO < dur:
        out.append(round(k * hop, 2)); k += 1
    return out


def load_decodes(video, cache, windows, hop, everywhere=False):
    """No keeps (a Mode B voice track, a cut with no keeps file): grid windows of the cut itself,
    around the stretches the cut's own audio says twice. -> ({win: [[t, text, dur]]}, dur)."""
    st = Store(cache)
    with tempfile.TemporaryDirectory(prefix="xwin_") as td:
        pcm = read_wav(video, td)
        dur = len(pcm) / 2 / RATE
        if everywhere:
            spans = [(0.0, dur)]
        else:
            spans, _ = heard_twice(pcm, [(0.0, dur)], RA["max_lag_s"])
        plan = {}
        for w in windows:
            ts = {t for lo, hi in spans for t in grid_times(lo, hi, w, hop)}
            ts |= {t for t in cut_grid(dur, w, hop) if t == 0.0 or t == cut_grid(dur, w, hop)[-1]}
            plan[f"{w:g}"] = [(t, window_key(window_bytes(pcm, t, w)), window_bytes(pcm, t, w)) for t in sorted(ts)]
        n = decode_batch([(st, k, a) for rows in plan.values() for _t, k, a in rows], td)
    st.save()
    total = sum(len(v) for v in plan.values())
    print(f"  window decodes: {total - n} cached, {n} decoded ({os.path.basename(cache) if cache else 'no cache'})")
    decodes = {w: [[t, st.get(k), float(w)] for t, k, _a in rows if st.get(k)] for w, rows in plan.items()}
    return decodes, dur


def source_store(store_dir, src):
    base = os.path.splitext(os.path.basename(src))[0]
    return Store(os.path.join(store_dir, f"{base}.{hashlib.sha1(os.path.abspath(src).encode()).hexdigest()[:8]}.json"))


def load_keeps_decodes(video, keeps_path, speed, cache, store_dir, workdir, windows, hop, everywhere=False):
    """Keeps mode (3.8.0): the cut is the source takes' kept spans laid end to end, so a window
    that lies wholly inside one keep is decoded from the SOURCE take, on the take's own fixed
    grid, and cached per take in store_dir. A re-cut of the same takes moves the keeps but not
    the grid, so nearly every window is already decoded; on 2026-10-24 a 1.1x re-cut of five
    videos paid 13 to 22 minutes of whisper each for audio it had decoded the night before.

    Which windows (3.9.0): the take's audio is searched for anything said twice
    (yaplib/repeats.py, up to repetition.acoustic.take_max_lag_s apart, because the pause between
    two passes is still in the take) and only the grid windows around a repeat whose two passes
    both sit inside the keeps are decoded. A restart the clause plan already removed costs
    nothing; one split by a join is found whole in the take. The cut's first and last window are
    decoded from the cut (cached by content in `cache`), where a loop in whisper's decode shows
    up as 25 words. --everywhere decodes the whole grid inside the keeps as 3.8.x did.

    speed: the cut plays at this rate (YAP_SPEED); keeps carry source a and b = a + cut length,
    as yapfull writes them, so a keep's source span is a .. a + (b - a) * speed."""
    keeps = json.load(open(keeps_path))
    cst = Store(cache)
    with tempfile.TemporaryDirectory(prefix="xwin_") as td:
        cut = read_wav(video, td)
        dur = len(cut) / 2 / RATE
        srcs, spans = {}, {}
        for k in keeps:
            if k["src"] not in srcs:
                srcs[k["src"]] = (source_pcm(k["src"], workdir, td), source_store(store_dir, k["src"]))
            spans.setdefault(k["src"], []).append((float(k["a"]), float(k["a"]) + (float(k["b"]) - float(k["a"])) * speed))
        where = {}
        for src, (pcm, _st) in srcs.items():
            if everywhere:
                where[src] = spans[src]
            else:
                where[src], _ = heard_twice(pcm, spans[src], RA["take_max_lag_s"], label=f" in {os.path.basename(src)}")
        plan = {f"{w:g}": [] for w in windows}      # win -> [(cut_t, store, key, audio, cut_dur)]
        c0 = 0.0
        for k in keeps:
            a, clen = float(k["a"]), float(k["b"]) - float(k["a"])
            pcm, sst = srcs[k["src"]]
            for w in windows:
                ts = {t for lo, hi in clip_spans(where[k["src"]], a, a + clen * speed)
                      for t in grid_times(lo, hi, w, hop)}
                for t in sorted(ts):
                    aud = window_bytes(pcm, t, w)
                    plan[f"{w:g}"].append((round(c0 + (t - a) / speed, 3), sst, window_key(aud), aud, w / speed))
            c0 += clen
        for w in windows:
            for t in sorted({0.0, max(0.0, round(dur - w, 3))}):
                aud = window_bytes(cut, t, w)
                plan[f"{w:g}"].append((t, cst, window_key(aud), aud, w))
        jobs = [(st, key, aud) for rows in plan.values() for _t, st, key, aud, _d in rows]
        n = decode_batch(jobs, td)
    for _pcm, sst in srcs.values():
        sst.save()
    cst.save()
    total = len(jobs)
    print(f"  window decodes: {total} windows ({len(keeps) - 1} joins, {len(srcs)} take(s)): "
          f"{total - n} cached, {n} decoded")
    decodes = {w: sorted([t, st.get(key), d] for t, st, key, _a, d in rows if st.get(key))
               for w, rows in plan.items()}
    return decodes, dur


def prescan(plan_paths, store_dir, workdir, windows, hop, pad=0.15, everywhere=False):
    """Decode the source grid ahead of the gate (3.8.0). Each path is a clause plan (its spans,
    padded by yapcut's left pad and a little: a keep starts at most 0.1s before its clause) or a
    1x keeps file (exactly the spans the gate will read, for a rerun on an existing cut). Since
    3.9.0 only the windows around what the take says twice inside those spans are decoded, so a
    prescan is a minute or two, not half an hour."""
    spans = {}
    for p in plan_paths:
        for c in json.load(open(p)):
            if "a" in c and "b" in c:
                spans.setdefault(c["src"], []).append((float(c["a"]), float(c["b"])))
            else:
                spans.setdefault(c["src"], []).append((max(0.0, float(c["start"]) - pad), float(c["end"]) + pad))
    with tempfile.TemporaryDirectory(prefix="xwin_pre_") as td:
        jobs, stores = [], []
        for src, sp in spans.items():
            pcm, sst = source_pcm(src, workdir, td), source_store(store_dir, src)
            stores.append(sst)
            where = sp if everywhere else heard_twice(pcm, sp, RA["take_max_lag_s"], label=f" in {os.path.basename(src)}")[0]
            ts = {(w, t) for lo, hi in where for w in windows for t in grid_times(lo, hi, w, hop)}
            for w, t in sorted(ts):
                aud = window_bytes(pcm, t, w)
                jobs.append((sst, window_key(aud), aud))
        n = decode_batch(jobs, td, label="prescan: ")
    for sst in stores:
        sst.save()
    print(f"prescan: {len(jobs)} windows over {len(spans)} take(s): {len(jobs) - n} cached, {n} decoded -> {store_dir}")


def grams_of(tokens):
    """Trigrams, plus bigrams that carry at least one content word ("we made", never "it is")."""
    g = {tuple(tokens[i:i + 3]) for i in range(len(tokens) - 2)}
    g |= {tuple(tokens[i:i + 2]) for i in range(len(tokens) - 1)
          if not (tokens[i] in STOP and tokens[i + 1] in STOP)}
    return g


def transcript_tokens(words_path):
    """[(start_s, token)] from the cut's own word transcript (the one stutter_check reads)."""
    out = []
    for s, _e, t in ywords.load_words(words_path):
        if t.startswith("["):
            continue
        out.extend((s, n) for n in norm_words(t))
    return out


def transcript_count(toks, gram, lo, hi):
    """How often the transcript says gram with its first word inside [lo, hi]. Spaces between
    the words are optional, so a window's "chat gpt" still matches the transcript's "ChatGPT"."""
    seq = " ".join(n for t, n in toks if lo <= t <= hi)
    pat = r"(?<![a-z0-9'])" + r" ?".join(re.escape(x) for x in gram) + r"(?![a-z0-9'])"
    return len(re.findall(pat, seq))


def find_hits(decodes, max_gap=MAX_START_GAP):
    """Raw hits: (kind, gram, lo, hi, win, t1, t2, text1, text2). lo..hi is the audio the
    two passes live in."""
    hits = []
    for key, rows in decodes.items():
        win = float(key)
        # a row is [t, text] (a cache from before 3.8.0) or [t, text, length in the cut]: a
        # window decoded from a source take covers win / speed seconds of a sped-up cut
        rows = sorted((r[0], r[1], r[2] if len(r) > 2 else win) for r in rows)
        toks = [(t, txt, d, norm_words(txt)) for t, txt, d in rows]
        toks = [x for x in toks if len(x[3]) <= MAX_WPS * win + 2]
        for i, (t1, x1, d1, w1) in enumerate(toks):
            g1 = grams_of(w1)
            for t2, x2, d2, w2 in toks[i + 1:]:
                if t2 - t1 > max_gap:
                    break
                if t2 < t1 + d1 - 1e-6:           # overlapping windows share audio
                    continue
                for g in g1 & grams_of(w2):
                    hits.append(("x-window", g, t1, t2 + d2, win, t1, t2, x1, x2))
            for n in (1, 2, 3):                   # the same words twice inside one window
                for j in range(len(w1) - 2 * n + 1):
                    if w1[j:j + n] == w1[j + n:j + 2 * n]:
                        hits.append(("in-window", tuple(w1[j:j + n]), t1, t1 + d1, win,
                                     t1, t1, x1, x1))
    return hits


def score(event, toks, script=None, free=None):
    """(confidence 0..1, why). Only the merged shape reaches the MEDIUM threshold, and not when
    the script says the same words twice right there (3.8.0): then two passes are what the
    creator was meant to say, and the transcript merging them is its usual tidying."""
    grams = event["grams"]
    scripted = bool(script) and (free is None or event["lo"] < free)
    lo, hi = event["lo"] - SPAN_PAD, event["hi"] + SPAN_PAD
    best, why = 0.0, ""
    for g in sorted(grams, key=lambda g: (-len(g), g)):
        prone = decode_prone(g)
        c = transcript_count(toks, g, lo, hi)
        doubled = transcript_count(toks, g + g, lo, hi) if event["kind"] == "in-window" else 0
        if prone:
            conf, w = 0.2, "a number, number word or single letter: short windows mis-decode those, re-check at 3s"
        elif doubled or c >= 2:
            conf, w = 0.3, "the cut's transcript says it twice too: a scripted repeat, or one stutter_check.py already reads"
        elif c == 0:
            conf, w = 0.25, "the cut's transcript never says it: most likely a short-window mis-decode"
        elif scripted and yscript.says_twice_near(script, [yscript.norm(x) for x in g], SCRIPT_NEAR):
            conf, w = 0.35, "the script says it twice here: two passes are the script, not a restart"
        else:
            conf = 0.6
            conf += 0.2 if len(g) >= 3 else 0.1
            conf += 0.2 if len(event["wins"]) > 1 else (0.1 if len(event["pairs"]) > 1 else 0.0)
            if event["kind"] == "in-window" and len(g) == 1:
                conf = min(conf, 0.5)             # "the the" in 1.1s is often a boundary echo
            w = ("the cut's transcript says it once, where two separate pieces of audio both say it: "
                 "two passes the transcript merged")
        if conf > best:
            best, why = conf, w
    return round(min(best, 1.0), 2), why


def take_events(keeps_path, speed, workdir, toks):
    """Restarts the take's own transcript hears that the captions merged (3.9.4).

    yapcut.py transcribes every take whole (yaplib/gaps.span_words, cached in
    audio/<take>.spans.json). That is a second hearing of the kept audio, made before the cut,
    and it hears what the cut's transcript tidies away: on the 2026-10-29 Honest Genius take it
    read "a lot more of it in the near in the coming years", the captions read "a lot more of
    in the coming years", and neither window size decoded a repeat there, so "in the near"
    shipped. The take's words inside the keeps, laid on the cut's clock, go through
    stutter_check's detector; a repeat or restart whose words the captions say fewer times
    across the same span is a MEDIUM, the shape score() calls merged."""
    from stutter_check import find_flags, norm as snorm
    keeps, c0, laid = json.load(open(keeps_path)), 0.0, []
    for k in keeps:                   # (src, source a, source b, cut start)
        clen = float(k["b"]) - float(k["a"])
        laid.append((k["src"], float(k["a"]), float(k["a"]) + clen * speed, c0))
        c0 += clen
    heard = []
    for src in dict.fromkeys(k[0] for k in laid):
        stem = os.path.splitext(os.path.basename(src))[0]
        try:
            spans = json.load(open(os.path.join(workdir, "audio", stem + ".spans.json")))["spans"]
        except (OSError, ValueError, KeyError):
            spans = {}
        whole = [s for s in spans if s.startswith("0.000-")]
        for s, e, t in (spans[max(whole, key=lambda s: float(s.split("-")[1]))] if whole else []):
            # a word whose loose times straddle a join is laid once, in the keep holding most of it,
            # and only when that keep holds at least half of it: on the Undistracted take the
            # stammer "get us" the cut removed started 0.04s before a keep's end
            on = [(min(e, b) - max(s, a), a, b, c) for x, a, b, c in laid if x == src and s < b and e > a]
            if on and max(on)[0] >= 0.5 * (e - s):
                _o, a, b, c = max(on)
                heard.append((c + (max(s, a) - a) / speed, c + (min(e, b) - a) / speed, t, snorm(t)))
    heard.sort()
    evs = []
    for i, s, kind, _conf, text, t0, t1 in find_flags(heard):
        if not (kind.startswith("repeat") or kind.startswith("restart")):
            continue                  # a distant re-read is the cut transcript's job (stutter_check.py)
        L = 1 if kind.startswith("repeat") else int(re.match(r"restart (\d+)w", kind).group(1))
        gram = tuple(n for x in heard[i:i + L] for n in norm_words(x[2]))
        said = sum(1 for j in range(i, s + L) if tuple(n for x in heard[j:j + L] for n in norm_words(x[2])) == gram)
        lo, hi = heard[i][0], heard[min(s + L, len(heard)) - 1][1]
        if decode_prone(gram) or transcript_count(toks, gram, lo - SPAN_PAD, hi + SPAN_PAD) >= said:
            continue
        evs.append({"kind": "take", "lo": lo, "hi": hi, "grams": {gram}, "words": set(gram), "wins": set(),
                    "pairs": set(), "texts": (text, ""), "conf": 0.8, "keys": [accept_key(text)],
                    "why": f"the take's own transcript says '{' '.join(gram)}' {said}x here, the captions "
                           f"fewer: a restart the captions merged"})
    return evs


def events_of(hits):
    """Hits that overlap in time and share a word are one event (a restart shows up as
    several grams across several window pairs and both window sizes)."""
    evs = []
    for kind, g, lo, hi, win, t1, t2, x1, x2 in sorted(hits, key=lambda h: (h[2], h[3])):
        for e in evs:
            if e["kind"] == kind and lo <= e["hi"] and hi >= e["lo"] and set(g) & e["words"]:
                e["lo"], e["hi"] = min(e["lo"], lo), max(e["hi"], hi)
                e["grams"].add(g); e["words"] |= set(g); e["wins"].add(win)
                e["pairs"].add((win, t1, t2))
                break
        else:
            evs.append({"kind": kind, "lo": lo, "hi": hi, "grams": {g}, "words": set(g),
                        "wins": {win}, "pairs": {(win, t1, t2)}, "texts": (x1, x2)})
    return evs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--video", help="the cut (full_<out>.mp4)")
    ap.add_argument("--words",
                    help="the cut's word transcript (w_<out>.json); every hit is judged against it")
    ap.add_argument("--keeps", default="",
                    help="keeps_full_<out>.json: decode windows inside each keep from the source take "
                         "(cached per take in --store-dir) and only the joins from the cut (3.8.0)")
    ap.add_argument("--speed", type=float, default=1.0, help="the cut's playback rate (YAP_SPEED)")
    ap.add_argument("--store-dir", default="",
                    help="per-take window decodes (default: xwin_src/ beside --cache)")
    ap.add_argument("--workdir", default="",
                    help=".yap_build: reuse yapcut's 16 kHz take audio from <workdir>/audio/")
    ap.add_argument("--prescan", nargs="+", metavar="PLAN",
                    help="decode the take windows inside these clause plans (or 1x keeps files) now and exit; no gate")
    ap.add_argument("--script", default="",
                    help="<out>_script.txt: a gram the script says twice nearby is not a restart")
    ap.add_argument("--free-from", type=float, default=None,
                    help="seconds where the unscripted opinion slot starts")
    ap.add_argument("--accept-file", default="",
                    help="JSON list of repeats already listened to and judged deliberate, "
                         "shared with stutter_check.py and restart_scan.py")
    ap.add_argument("--cache", default="",
                    help="window decodes by content (xwin_<out>.json); any window whose audio is unchanged is reused")
    ap.add_argument("--windows", default=",".join(f"{w:g}" for w in WINDOWS))
    ap.add_argument("--hop", type=float, default=HOP)
    ap.add_argument("--threshold", type=float, default=THRESHOLD,
                    help="confidence at or above which a hit is MEDIUM (a decision)")
    ap.add_argument("--show-low", action="store_true", help="print the words of every LOW hit too")
    ap.add_argument("--everywhere", action="store_true",
                    help="decode the whole grid, not only around what the audio says twice (3.8.x behaviour)")
    a = ap.parse_args()
    windows = tuple(float(w) for w in a.windows.split(",") if w.strip())
    base_dir = os.path.dirname(os.path.abspath(a.cache)) if a.cache else (a.workdir or os.getcwd())
    store_dir = a.store_dir or os.path.join(base_dir, "xwin_src")
    workdir = a.workdir or (os.path.dirname(os.path.abspath(a.keeps)) if a.keeps else "")
    global LOCK_DIR
    LOCK_DIR = store_dir
    if a.prescan:
        prescan(a.prescan, store_dir, workdir or base_dir, windows, a.hop, everywhere=a.everywhere)
        return
    if not a.video or not a.words:
        ap.error("--video and --words are required (or --prescan)")
    if a.keeps and os.path.isfile(a.keeps):
        decodes, dur = load_keeps_decodes(a.video, a.keeps, a.speed, a.cache, store_dir, workdir,
                                          windows, a.hop, everywhere=a.everywhere)
    else:
        decodes, dur = load_decodes(a.video, a.cache, windows, a.hop, everywhere=a.everywhere)
    script = yscript.load(a.script)
    toks = transcript_tokens(a.words)
    if len(toks) >= 3 and a.everywhere and not any(decodes.values()):
        print("xwin_scan: the cut has words but no window decoded to speech; nothing was "
              "scanned, so the gate cannot pass (check whisper-cli and $WHISPER_MODEL)")
        sys.exit(2)
    evs = events_of(find_hits(decodes))
    for e in evs:
        e["conf"], e["why"] = score(e, toks, script, a.free_from)
        e["keys"] = sorted({accept_key(" ".join(g)) for g in e["grams"]}, key=lambda k: (-len(k), k))
    if a.keeps and os.path.isfile(a.keeps) and workdir:
        evs += take_events(a.keeps, a.speed, workdir, toks)
    accepted = load_accepted(a.accept_file)
    med = [e for e in evs if e["conf"] >= a.threshold]
    low = [e for e in evs if e["conf"] < a.threshold]
    unjudged = [e for e in med if not accepted & set(e["keys"])]
    print(f"cross-window scan ({'/'.join(f'{w:g}s' for w in windows)} windows, {a.hop:g}s hop, "
          f"{dur:.1f}s): {len(med)} MEDIUM, {len(low)} LOW (reported only, below {a.threshold:g})")
    for e in sorted(med + (low if a.show_low else []), key=lambda e: e["lo"]):
        conf = "MEDIUM" if e in med else "LOW"
        act = ("ok'd" if accepted & set(e["keys"]) else "JUDGE") if e in med else ""
        if e["kind"] == "take":
            print(f"  [{conf:6}] {e['lo']:6.2f}-{e['hi']:6.2f}s  take      '{e['keys'][0]}' {act}\n"
                  f"           {e['why']}")
            continue
        print(f"  [{conf:6}] {e['lo']:6.2f}-{e['hi']:6.2f}s  {e['kind']:9} '{e['keys'][0]}' "
              f"conf {e['conf']:.2f} ({len(e['pairs'])} window pair(s), {'/'.join(f'{w:g}s' for w in sorted(e['wins']))}) {act}")
        print(f"           | {e['texts'][0]} || {e['texts'][1]}" if e["kind"] == "x-window" else f"           | {e['texts'][0]}")
        print(f"           {e['why']}")
    if low and not a.show_low:
        print("  LOW: " + "; ".join(f"{e['lo']:.1f}s '{e['keys'][0]}'" for e in sorted(low, key=lambda e: e["lo"])))
    if unjudged:
        print(f"\n{len(unjudged)} repeat(s) need a decision. LISTEN to each span in the cut. A real "
              "restart: cut the first pass in the clause plan. Deliberate: add one of its keys to "
              "the accept-file" + (f" ({a.accept_file})" if a.accept_file else " (--accept-file)") + ":")
        print(json.dumps([e["keys"][0] for e in unjudged], indent=2))
        sys.exit(2)


if __name__ == "__main__":
    main()

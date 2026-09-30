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

Window decodes are cached beside the accept-file keyed on the cut's audio, so a
YAP_FROM_CUT=1 rebuild skips the whisper pass. A fresh scan costs about 1s of whisper per
window on an Apple M4 (a 55s cut is about 235 windows, 4 minutes); running whisper
processes side by side is slower, not faster, because they share the GPU.

Usage: xwin_scan.py --video cut.mp4 --words w_<out>.json
                    [--accept-file <out>_stutter_ok.json] [--cache xwin_<out>.json]
                    [--windows 1.1,1.6] [--hop 0.45] [--show-low]
Exit: 0 clean, only LOW hits, or every MEDIUM accepted; 2 a MEDIUM needs a decision.
"""
import argparse, hashlib, json, os, re, subprocess, sys, tempfile, wave

sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
from stutter_check import accept_key, load_accepted  # noqa: E402
from yaplib import words as ywords  # noqa: E402

MODEL = os.environ.get("WHISPER_MODEL",
                       os.path.expanduser("~/.whisper-models/ggml-small.en.bin"))
RATE = 16000
WINDOWS = (1.1, 1.6)      # measured 2026-09-18: 1.1s caught both restarts, 1.6s one, 3s none
HOP = 0.45
LEAD_PAD = 0.25           # silence before and after each window: whisper decodes a clip
TAIL_PAD = 0.4            # that starts or ends on a word badly without it
MIN_AUDIO = 0.3           # the last window must carry at least this much audio
MAX_START_GAP = 3.0       # two windows further apart than this are not one restart
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


def read_wav(video, tmpdir):
    wav = os.path.join(tmpdir, "all.wav")
    subprocess.run(["ffmpeg", "-nostdin", "-y", "-v", "error", "-i", video, "-vn",
                    "-ar", str(RATE), "-ac", "1", "-c:a", "pcm_s16le", wav], check=True)
    w = wave.open(wav, "rb")
    data = w.readframes(w.getnframes())
    w.close()
    return data


def signature(pcm, windows, hop):
    h = hashlib.sha1(pcm)
    h.update(json.dumps([list(windows), hop, LEAD_PAD, TAIL_PAD, MIN_AUDIO,
                         os.path.basename(MODEL)]).encode())
    return h.hexdigest()


def decode_windows(pcm, win, hop, tmpdir):
    """[[t, text], ...] for every window of length win that decoded to speech. ONE
    whisper-cli call with every window as its own -f input: the model loads once and
    each window is still decoded on its own, so nothing smooths across windows."""
    dur = len(pcm) / 2 / RATE
    lead = b"\x00\x00" * int(LEAD_PAD * RATE)
    tail = b"\x00\x00" * int(TAIL_PAD * RATE)
    files, k = [], 0
    while k * hop + MIN_AUDIO < dur:
        t = round(k * hop, 2)
        a, b = int(t * RATE) * 2, min(len(pcm), int((t + win) * RATE) * 2)
        f = os.path.join(tmpdir, f"w{win:.2f}_{t:08.2f}.wav")
        o = wave.open(f, "wb"); o.setnchannels(1); o.setsampwidth(2); o.setframerate(RATE)
        o.writeframes(lead + pcm[a:b] + tail); o.close()
        files.append((t, f)); k += 1
    cmd = ["whisper-cli", "-m", MODEL, "-oj", "-np"]
    for _, f in files:
        cmd += ["-f", f]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        # a scan that could not run must never read as a clean zero
        sys.stderr.write((r.stderr or "")[-600:])
        sys.exit(f"xwin_scan: whisper-cli failed (rc {r.returncode}) on the {win:g}s windows; "
                 "nothing was scanned, so the gate cannot pass")
    out = []
    for t, f in files:
        try:
            segs = [s.get("text", "").strip() for s in json.load(open(f + ".json"))["transcription"]]
        except (OSError, ValueError, KeyError):
            continue
        # a looping decode repeats a whole segment verbatim; that is whisper, not speech
        segs = [s for i, s in enumerate(segs) if s and (i == 0 or s != segs[i - 1])]
        txt = " ".join(segs).strip()
        if not txt or "BLANK_AUDIO" in txt or not norm_words(txt):
            continue
        out.append([t, txt])
    return out


def load_decodes(video, cache, windows, hop):
    with tempfile.TemporaryDirectory(prefix="xwin_") as td:
        pcm = read_wav(video, td)
        sig = signature(pcm, windows, hop)
        if cache and os.path.isfile(cache):
            try:
                c = json.load(open(cache))
                if c.get("sig") == sig:
                    print(f"  window decodes: cached ({os.path.basename(cache)})")
                    return c["decodes"], len(pcm) / 2 / RATE
            except (OSError, ValueError):
                pass
        decodes = {}
        for win in windows:
            decodes[f"{win:g}"] = decode_windows(pcm, win, hop, td)
            print(f"  {win:g}s windows: {len(decodes[f'{win:g}'])} decoded")
        if cache:
            json.dump({"sig": sig, "video": os.path.abspath(video), "decodes": decodes},
                      open(cache, "w"), indent=0)
        return decodes, len(pcm) / 2 / RATE


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
        rows = sorted(rows)
        toks = [(t, txt, norm_words(txt)) for t, txt in rows]
        toks = [x for x in toks if len(x[2]) <= MAX_WPS * win + 2]
        for i, (t1, x1, w1) in enumerate(toks):
            g1 = grams_of(w1)
            for t2, x2, w2 in toks[i + 1:]:
                if t2 - t1 > max_gap:
                    break
                if t2 < t1 + win - 1e-6:          # overlapping windows share audio
                    continue
                for g in g1 & grams_of(w2):
                    hits.append(("x-window", g, t1, t2 + win, win, t1, t2, x1, x2))
            for n in (1, 2, 3):                   # the same words twice inside one window
                for j in range(len(w1) - 2 * n + 1):
                    if w1[j:j + n] == w1[j + n:j + 2 * n]:
                        hits.append(("in-window", tuple(w1[j:j + n]), t1, t1 + win, win,
                                     t1, t1, x1, x1))
    return hits


def score(event, toks):
    """(confidence 0..1, why). Only the merged shape reaches the MEDIUM threshold."""
    grams = event["grams"]
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
    ap.add_argument("--video", required=True, help="the cut (full_<out>.mp4)")
    ap.add_argument("--words", required=True,
                    help="the cut's word transcript (w_<out>.json); every hit is judged against it")
    ap.add_argument("--accept-file", default="",
                    help="JSON list of repeats already listened to and judged deliberate, "
                         "shared with stutter_check.py and restart_scan.py")
    ap.add_argument("--cache", default="", help="window decodes, reused while the cut's audio is unchanged")
    ap.add_argument("--windows", default=",".join(f"{w:g}" for w in WINDOWS))
    ap.add_argument("--hop", type=float, default=HOP)
    ap.add_argument("--threshold", type=float, default=THRESHOLD,
                    help="confidence at or above which a hit is MEDIUM (a decision)")
    ap.add_argument("--show-low", action="store_true", help="print the words of every LOW hit too")
    a = ap.parse_args()
    windows = tuple(float(w) for w in a.windows.split(",") if w.strip())
    decodes, dur = load_decodes(a.video, a.cache, windows, a.hop)
    toks = transcript_tokens(a.words)
    if len(toks) >= 3 and not any(decodes.values()):
        print("xwin_scan: the cut has words but no window decoded to speech; nothing was "
              "scanned, so the gate cannot pass (check whisper-cli and $WHISPER_MODEL)")
        sys.exit(2)
    evs = events_of(find_hits(decodes))
    for e in evs:
        e["conf"], e["why"] = score(e, toks)
        e["keys"] = sorted({accept_key(" ".join(g)) for g in e["grams"]}, key=lambda k: (-len(k), k))
    accepted = load_accepted(a.accept_file)
    med = [e for e in evs if e["conf"] >= a.threshold]
    low = [e for e in evs if e["conf"] < a.threshold]
    unjudged = [e for e in med if not accepted & set(e["keys"])]
    print(f"cross-window scan ({'/'.join(f'{w:g}s' for w in windows)} windows, {a.hop:g}s hop, "
          f"{dur:.1f}s): {len(med)} MEDIUM, {len(low)} LOW (reported only, below {a.threshold:g})")
    for e in sorted(med + (low if a.show_low else []), key=lambda e: e["lo"]):
        conf = "MEDIUM" if e in med else "LOW"
        act = ("ok'd" if accepted & set(e["keys"]) else "JUDGE") if e in med else ""
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

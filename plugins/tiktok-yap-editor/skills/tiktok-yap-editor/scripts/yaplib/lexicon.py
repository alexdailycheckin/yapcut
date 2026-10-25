"""Words the caption gate can let through without asking (3.9.0).

The caption gate used to flag every burned word the script never contained. On the 2026-10-25
Warhound cut that was 80 words, and the agent's own read was that 78 of them were ad-libs:
"bear with me", "60 times this week", "came out of stealth". Each one cost a decision, and
a scripted video stopped at this gate on four of the nine cuts that day. Whisper's large model
does not mis-hear "stealth" or "opinion"; what it mis-hears is a name, a brand, a number. So
an ad-lib that is an ordinary English word in its ordinary spelling is accepted and printed
for the line audit, and the gate asks only about what can be a garble: a word in no
dictionary, a capitalised word mid-sentence (whisper's own sign that it heard a name), a
number the script never said.

Three dictionaries, in order:
  - the system word list (/usr/share/dict/words on a Mac), with inflections (plurals, -ed,
    -ing, -er, -ly, doubled consonants, -ies) and contractions folded to their base
  - a short list of words that list predates (startup, app, podcast) and the irregular
    verb forms it leaves out (heard, bought, written)
  - the creator's own lexicon, <workspace>/caption-lexicon.json: every word they ever
    accepted at the gate and every word of every script they read, learned as the gate
    passes. `python3 yaplib/lexicon.py seed <folder>...` fills it from existing builds.

A capitalised word is a name until the script says it, so nothing here accepts one.
"""
import json
import os
import re
import sys

try:
    from .home import radar_home
except ImportError:                       # run as a script
    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
    from home import radar_home

DICT_PATHS = ("/usr/share/dict/words", "/usr/dict/words")
FILE = "caption-lexicon.json"

MODERN = set("""
startup startups app apps chatbot chatbots crypto bitcoin blockchain online offline email emails
internet website websites webpage podcast podcasts blog blogs vlog vlogs spreadsheet spreadsheets
selfie selfies hashtag hashtags meme memes emoji emojis okay gonna wanna gotta kinda sorta gotcha
guys bro dude sus vibe vibes hype legit awesome clickbait influencer influencers unfollow follower
followers subscriber subscribers download downloads upload uploads login logout wifi laptop laptops
smartphone smartphones browser browsers software hardware database databases algorithm algorithms
saas b2b b2c roi kpi kpis ceo ceos cfo cfos cmo cmos cto ctos vp vps hr ipo ipos vc vcs founder
founders cofounder cofounders fundraise fundraising funding valuation valuations unicorn unicorns
pivot pivoted bootstrapped burn runway churn onboarding offboarding freemium upsell upsells outbound
inbound prospecting demo demos webinar webinars newsletter newsletters dm dms inbox outreach lead
leads pipeline quota quotas closer closers deck decks pitch pitches roadmap backlog sprint sprints
standup standups retro async remote hybrid livestream livestreams streaming streamer streamers gamer
gamers gaming esports nft nfts web3 metaverse vr ar drone drones ev evs llm llms prompt prompts
prompting token tokens gpu gpus cybersecurity fintech biotech edtech healthtech deeptech robotics
automation automate automated workflow workflows integration integrations api apis plugin plugins
dashboard dashboards analytics metrics attribution conversion conversions funnel funnels signup
signups waitlist beta launch launches relaunch rebrand repost reposts reshare retweet retweets
yeah yep nope nah hmm uh um huh wow whoa oops ugh lol omg btw fyi asap tbh idk ok fomo
tech techie techies cloud computing compute dataset datasets rollout rollouts rebuild rebuilds
scalable monetize monetized monetization gamify gamified virality viral ecommerce marketplace
marketplaces subscription subscriptions paywall paywalls freelancer freelancers gig gigs crowdfunding
sponsor sponsors sponsored sponsorship sponsorships creator creators content creators niche niches
sidebar sidebars thumbnail thumbnails screenshot screenshots screenshotted scroll scrolled scrolling
swipe swiped swiping tap tapped tapping click clicked clicking unsubscribe unsubscribed trending
trend trends hustle hustler hustling bandwidth teleprompter timestamp timestamps multitask
""".split())

IRREGULAR = set("""
heard said went gone got gotten made took taken came saw seen gave given knew known thought told
found felt kept left met paid put ran read sent set sold spent stood taught understood won wore worn
wrote written ate eaten began begun bought brought built caught chose chosen cut dealt did done drew
drawn drove driven fell fallen fought flew flown forgot forgotten froze frozen grew grown held hid
hidden hit hurt led lent lost meant rode ridden rose risen sang sung sat shook shaken shot showed
shown shut slept spoke spoken sprang sprung stole stolen struck swore sworn swam swum threw thrown
woke woken was were been had has does says goes is am are being doing having better best worse
worst more most less least children people men women feet teeth mice geese lay lain laid bent
bound bled bred broke broken burnt dug fed fled flung forgave forgiven hung kneeled knelt lit
overcame overcome rang rung sank sunk sought sewn shone slid slung spun spat split spread
stuck stung stank stunk strode stridden strove striven swept swung tore torn trod wept wound
wrung bade bidden beat beaten become became begot bit bitten blew blown clung crept dove forbade
forbidden foresaw foreseen forsook forsaken ground hewn leapt mistook mistaken outgrew outgrown
overthrew overthrown partook partaken proved proven quit rid shed shrank shrunk slain slew smote
sped spilt spoilt stove sunburnt swelled swollen undid undone upheld upset withdrew withdrawn
withheld withstood wove woven
""".split())

CONTRACTIONS = {"won't": "will", "shan't": "shall", "ain't": "is", "can't": "can", "i'm": "i",
                "let's": "let", "y'all": "you", "o'clock": "clock"}
SUFFIXES = (("ies", "y"), ("ied", "y"), ("ier", "y"), ("iest", "y"), ("ing", ""), ("est", ""),
            ("es", ""), ("ed", ""), ("er", ""), ("ly", ""), ("s", ""), ("d", ""))

_dict = None


def _load_system():
    for p in DICT_PATHS:
        if os.path.isfile(p):
            with open(p, encoding="utf-8", errors="ignore") as f:
                return {w.strip().lower() for w in f if w.strip() and w.strip().islower()}
    return set()


def dictionary():
    """Every ordinary lowercase word: the system list plus the two short lists above."""
    global _dict
    if _dict is None:
        _dict = _load_system() | MODERN | IRREGULAR
    return _dict


def bare(w):
    return re.sub(r"[^a-z0-9']", "", (w or "").lower().replace("’", "'"))


def contraction_base(w):
    """'you've' -> 'you', "can't" -> 'can', "it's" -> 'it'. A word with no apostrophe is itself."""
    w = bare(w)
    if w in CONTRACTIONS:
        return CONTRACTIONS[w]
    for suf in ("n't", "'ve", "'ll", "'re", "'d", "'m", "'s"):
        if w.endswith(suf) and len(w) > len(suf):
            return w[:-len(suf)]
    return w.replace("'", "")


def bases(w):
    """The forms an inflected word may be listed under: itself, then each suffix stripped, with
    the dropped final e (handling -> handle), the doubled consonant (running -> run) and the
    -ies plural (companies -> company) put back."""
    w = contraction_base(w)
    out = [w]
    for suf, rep in SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 2:
            b = w[:-len(suf)] + rep
            out += [b, b + "e"]
            if len(b) >= 3 and b[-1] == b[-2] and not rep:
                out.append(b[:-1])
    return out


def is_word(w, extra=()):
    """True when w (any case, punctuation ignored) is an ordinary word, an inflection of one, or
    one of `extra` (lowercase) or an inflection of one of those."""
    d = dictionary()
    ex = set(extra)
    return any(b and (b in d or b in ex) for b in bases(w))


def phonetic(w):
    """A rough sound key: 'Claude', 'cloud' and 'clod' share one, 'Anduril' and 'Andriel' share one.
    Lowercase letters only; digraphs first; vowels and h/w/y dropped after the first letter;
    consonants folded into classes; repeats collapsed; a trailing s dropped."""
    s = re.sub(r"[^a-z]", "", (w or "").lower())
    if not s:
        return ""
    s = re.sub(r"s$", "", s) if len(s) > 3 else s
    for a, b in (("ph", "f"), ("ck", "k"), ("qu", "k"), ("wh", "w"), ("ch", "x"), ("sh", "x"), ("th", "0"),
                 ("gh", "")):
        s = s.replace(a, b)
    cls = {"b": "P", "p": "P", "d": "T", "t": "T", "c": "K", "k": "K", "q": "K", "g": "K", "j": "K",
           "f": "F", "v": "F", "s": "S", "z": "S", "x": "X", "m": "N", "n": "N", "l": "L", "r": "R", "0": "0"}
    out = s[0].upper() if s[0] in "aeiouhwy" else cls.get(s[0], "")
    for ch in s[1:]:
        c = cls.get(ch, "")
        if c and (not out or out[-1] != c):
            out += c
    return out


def learned_path(home=None):
    h = home if home is not None else radar_home(argv=[], required=False)
    return os.path.join(str(h), FILE) if h else None


def learned(home=None):
    p = learned_path(home)
    if not p or not os.path.isfile(p):
        return set()
    try:
        d = json.load(open(p, encoding="utf-8"))
        return {bare(w) for w in d.get("words", []) if bare(w)}
    except (OSError, ValueError):
        return set()


def learn(words, home=None):
    """Add lowercase forms of `words` to the creator's lexicon. Capitalised words are learned
    only when they start a sentence in a script or were accepted by hand: the caller decides what
    to pass. Returns how many were new, 0 with no workspace."""
    p = learned_path(home)
    if not p:
        return 0
    have = learned(home)
    new = {bare(w) for w in words if bare(w) and not re.search(r"\d", bare(w))} - have
    if not new:
        return 0
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump({"_about": "Words the caption gate accepted or the creator's scripts contain; yaplib/lexicon.py",
               "words": sorted(have | new)}, open(p, "w", encoding="utf-8"), indent=0, ensure_ascii=False)
    return len(new)


def known(w, extra=(), home=None, learned_words=None):
    """The one question the caption gate asks of an ad-lib: is this an ordinary word?"""
    lw = learned(home) if learned_words is None else learned_words
    return is_word(w, extra=set(extra) | lw)


def seed(paths, home=None):
    """Learn every word of every *_script.txt and *_capqa_ok.json under the given folders."""
    words = set()
    for root in paths:
        for d, _dirs, files in os.walk(root):
            for f in files:
                p = os.path.join(d, f)
                try:
                    if f.endswith("_script.txt"):
                        words |= {w for w in re.findall(r"[A-Za-z][A-Za-z'’]*", open(p, encoding="utf-8").read())}
                    elif f.endswith("_capqa_ok.json"):
                        words |= {str(w) for w in json.load(open(p, encoding="utf-8")) if isinstance(w, str)}
                except (OSError, ValueError):
                    continue
    return learn(words, home), len(words)


if __name__ == "__main__":
    argv = sys.argv[1:]
    if argv and argv[0] == "seed" and len(argv) > 1:
        n, total = seed(argv[1:])
        print(f"lexicon: {n} new word(s) from {total} seen -> {learned_path()}")
    elif argv and argv[0] == "check":
        for w in argv[1:]:
            print(f"{w}: {'known' if known(w) else 'UNKNOWN'} (bases {bases(w)}, sound {phonetic(w)})")
    else:
        sys.exit("usage: lexicon.py seed <folder>... | lexicon.py check <word>...")

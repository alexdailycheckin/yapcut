# Shorts craft, 2026 delta

_Researched 2026-07-26 after the creator judged the batch "not a good output". This file holds
only what the existing docs MISS. Structure theory lives in
video-scripting-as-a-science.md; this is what changed since it was compiled, plus the
two failure modes our batch actually has. Sources at the bottom._

## 1. The window is 1 second now, not 3

The 3-second rule was built for 2018-2022 discovery feeds. On a swipeable feed the
keep-or-swipe decision is reflexive, at or before ~1 second, and the algorithm's own
judgment window is ~1.5s (34,635-clip Opus study, Jan-Mar 2026). The first FRAME
(text_hook + face) plus the first SPOKEN WORDS carry everything.

**Gate: the first spoken line must contain the payload, never the setup.** The payload
is one of: the number, the quote, the contradiction, or the identity call. Openers that
died in 2026 pattern analysis: "Let me tell you about the time..." and any variant of
"today we're going to talk about". Our retold-conversation scripts drift into exactly
this shape when they open chronologically ("A friend of mine just took a job in New
York"). The capture protocol already allows promoting the sharpest line to position
one. USE IT AGGRESSIVELY. Real conversations start slow; feeds do not.

Hook types ranked by the 2026 data (avg views, 34k clips): outcome/receipt shown
first (~2x the bottom), authority-plus-gap ("I've done X for 12 years. Nobody tells
you this"), contrarian ("Everyone says X. It's wrong."), specific number, imperative.
**Identity call ("If you're a [specific person]...") scores highest on RETENTION for
small accounts**, because specificity beats reach when nobody knows you. Most
creators starting this engine are small accounts. Use 1-2 per batch.

## 2. The ending is a loop, not a button (the big one we were missing)

Rewatch/loop rate is the single strongest distribution signal on TikTok in 2026,
ahead of completion and shares. Benchmark: 20-30% rewatch on short clips is strong.

So the last line's job changed. A clean hard-stop button pays the loop; a LOOPING
last line gets the rewatch: it points back at the first frame, resolves something
only visible on second watch, or lands a callback the viewer wants to re-hear.
Hoyos's "satisfied, but surprised" is the same instinct: end on the twist, and the
twist recontextualises the open.

**Gate: the last line either calls back to the first line, or plants a second-pass
reward. A summary ending is a fail. A trailing-off ending is a fail.** ("Vary the
button" in script-anatomy still applies to WHICH callback, not whether.)

## 3. Answer first, prove second (educational lane)

2026 tactic with a twin benefit: clips that state the answer in line one and spend
the rest proving it hold better AND get quoted by AI assistants more reliably.
For `educational` scripts: the do-this is the HOOK, not the payoff. The proof is
the body. This inverts the old tension-then-prescription order.

## 4. What the robotic-script research confirms

The five tells of machine scripts (corporate phrasing, perfect grammar, no personal
voice, identical structure, emotional flatness) and the fixes (train on the creator's
transcripts, voice notes instead of typing, inject stories AI cannot invent) are
EXACTLY the capture-first rebuild. No change needed; the fingerprint gates cover it.
One addition: rhythm variation is named the #1 tell, which our stdev gate already
measures.

## 5. LinkedIn twin note

LinkedIn video is now dwell-time gated at ~8 seconds for secondary distribution,
autoplays muted, and judges the first frame on the burned caption. The twin's hook
line should be burned as the opening caption of the video version too.

## Applying it: the per-script checklist (adds to QA step 7)

1. First spoken line contains the number, the quote, the contradiction, or the
   identity call. If it is context, swap it with the sharpest line below it.
2. Last line loops to the first, or lands a callback punchline. Never a summary,
   never a trail-off. If the capture has no ending, ASK for one more line; do not
   ship the trail-off.
3. Educational: answer in line one, proof in the body.
4. 1-2 identity-call hooks per batch.
5. Text hook is readable in one fixation and is NOT the same words as the spoken
   first line (two channels, two chances).

## Sources

- [OpusClip, 34,635-clip hook study, Jan-Mar 2026](https://www.opus.pro/blog/tiktok-hooks-that-go-viral-2026)
- [vidiq, Shorts hooks 2026 (1-second rule, identity calls)](https://vidiq.com/blog/post/viral-video-hooks-youtube-shorts/)
- [Darkroom, TikTok algorithm 2026 (rewatch as top signal, loop tactics)](https://www.darkroomagency.com/observatory/how-tiktok%E2%80%99s-algorithm-works-in-2026-and-15-tactics-to-go-viral)
- [Marketing Examined, Hoyos playbook (foreshadow, satisfied-but-surprised)](https://www.marketingexamined.com/blog/jenny-hoyos-short-form-video-playbook)
- [ScriptZen, why AI scripts sound robotic](https://scriptzen.io/blog/why-ai-scripts-sound-robotic)
- [Influencers Time, LinkedIn B2B talking-head reach 2026](https://www.influencers-time.com/linkedin-video-algorithm-how-to-win-b2b-talking-head-reach/)

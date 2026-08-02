# Show mode: the company-teardown franchise (template)

_A recurring weekly SHOW where the creator breaks down how a company in this week's
news actually operates, through the creator's own lens. The format that proved this:
"How [Company] Actually Sells" (a GTM/distribution lens). Yours takes YOUR lens: how
does [company] actually hire, price, ship, cook, train, design. One company per
episode, receipts on screen for every claim, one copyable move per episode._

## Why a show

A recognisable franchise compounds where one-off scripts don't: same skeleton, same
two spoken devices, fresh company every episode. Viewers learn the shape, search
engines and answer engines learn the phrase ("how does [company] X"), and every
episode advertises the series.

## The config block (written by the first-run interview)

```json
"show": {
  "enabled": true,
  "name": "How [Company] Actually Sells",
  "turn_line": "So how does [company] actually sell?",
  "steal_line": "Here's the steal.",
  "lens": "one line: the angle every verdict lands on (e.g. 'distribution beats product')",
  "episodes_per_week": 5,
  "news_picks": 3,
  "wildcards": 2,
  "beats": ["industries/story types to sweep, e.g. tech, AI, consumer brands, sports business"],
  "wildcard_taste": "what makes a wildcard for this creator: jaw-drop numbers, David vs Goliath, absurd mechanics",
  "receipts_strict": true
}
```

## The interview (run once, inside first-run discovery)

1. **The lens.** "When you look at a company, what's the question you can't help
   asking?" That one line becomes the verdict engine and generates the show name and
   the turn line (offer 2-3 options derived from their answer; they pick, exact
   wording locks forever).
2. **The beats.** Which industries and story types should the weekly news sweep cover?
   Tech only? Anything with a viral story? Their own industry always included?
3. **Cadence.** Episodes per week, and the news/wildcard split (default 3 + 2).
4. **Wildcard taste.** What jaw-drop stories do they personally love? This steers the
   2 wildcards, which exist purely for viral ceiling.
5. **The steal beat.** Confirm the teach line (default "Here's the steal.") or rename
   it to fit their voice. Exact wording, every episode.

## The fixed skeleton (the recognisable shape)

| Beat | Time | Job |
|---|---|---|
| 1. The news open | 0-4s | Headline screenshot ON SCREEN in frame one. One varied jab about what happened. Never the same syntax two episodes running. |
| 2. The turn | 4-8s | The franchise line from config, exact wording every time. Title card lands on the same beat. |
| 3. The assumption | 8-15s | What everyone thinks the answer is, stated as if true. Then crack it. |
| 4. The receipts walk | 15-45s | 2-3 moves maximum, but/therefore chained, escalating. Every number, brand and claim gets its artifact on screen within a second of being spoken. |
| 5. The steal | 45-55s | One mechanism the viewer can copy, in plain words. The steal line from config, exact wording. |
| 6. The verdict close | 55-65s | The creator's POV through their lens, one line, then end on a punchline or a callback. Hard stop on the payoff. No CTA by default. |

## The receipts law (hard)

Every spoken brand, number, or claim carries an on-screen artifact: the article
headline, the product page, the pricing page, the chart, the platform itself. Each
episode ships with a numbered SHOT LIST (`shot_list` in the week JSON): what to
screenshot, the exact URL, and which beat it lands on. A claim that cannot be
screenshotted or sourced gets CUT from the script, never softened.

Build the cards with `receipts_build.py` (skill folder):

```bash
python3 receipts_build.py --week <workspace>/weeks/<date>.json
```

It headless-screenshots every shot-list URL, styles each into the yap editor's locked
white-card look (rounded card, source pill, <=972px wide), parses suggested overlay
timings from the beat map, and writes a `receipts_manifest.json` in the editor's
overlays shape. Pages that block headless browsers (paywalls, storefronts, cookie
walls) get flagged `needs_manual`: capture those by hand (or with a browser agent) into
the `manual/` folder and rerun; the styling pass keeps every card uniform either way.
Verify every card by eye before burning. Screenshot hygiene: crop to headline plus the
outlet's logo, clean browser, zoom until the money number reads at phone size.
`tiktok-yap-editor` burns the cards in its locked placement band and its
`pip_coverage.py` enforces that every claim got its receipt.

## The text-hook layer (the vacuum test)

**The one hard gate: a cold scroller with zero context, sound off, one fixation, must
instantly get WHAT this is about and want to stay.** Concrete claim, plain words.
"Apple stopped selling iPhones" passes. "The trap is polite." fails: it needs the
video to explain it. Plain beats clever, on screen exactly as everywhere else. This
was learned the hard way: a "make the text a different channel from the voice" rule
produced clever riddles that meant nothing in a vacuum, and the creator killed them
on sight.

**Duplicating the spoken hook is fine and often right.** Dual-track: the text overlay
carries the hook for sound-off viewers while the voice carries it for sound-on. Same
claim, compressed to ~6-8 words. Never force a difference; never write a riddle to
avoid an overlap.

**Ship 2 `text_hook_alts` per episode**: variants of the SAME claim at different
angles (a number-forward cut, a question cut), each passing the vacuum test on its
own. They feed hook testing (several burned variants on one locked cut). Batch check:
no two episodes share a first word.

Machine gate: `python3 hook_lint.py --week <workspace>/weeks/<date>.json` checks only
what a machine can (length, banned words, batch rhymes, alts present). The vacuum
test is human: read each hook to someone who hasn't seen the episode; if they ask
"what does that mean?", rewrite.

## Gates (in order)

1. **Source gate.** Every number, date and name carries a source URL in `sources`
   before filming. VERIFY each fact while researching: confirm it, adjust it, or cut
   the line. Never soften an unverifiable number into "many" or "huge".
2. **Two-question gate** (the skill's master filter) on every episode.
3. **Ownership on the verdict.** The closing POV must be a line only this creator
   would say, through their configured lens. If anyone could say it, re-cut or kill.
4. **Punch up or sideways.** Giants and funded companies take the jab; small
   independents get admiration, never mockery.
5. **Clarity outranks compression.** A zero-prior-knowledge viewer follows every line;
   max one named source per script, glossed in plain words.
6. **Batch check.** Print the episode opening lines in a column; if two rhyme,
   rewrite one.

## Field contract (hard)

`text_hook` = the ~6 words burned on screen. `visual_hook` = what fills frame one
(for the show: the headline receipt). `spoken_hook` = the first words spoken. The
`script` field starts AFTER the spoken hook; never repeat the hook inside it (the
dashboard renders hooks above the script, so a repeat displays twice). A separate
human filming pack may show the full read top to bottom.

## Weekly flow (show mode)

1. Sweep the week's news across the configured beats, multiple angles (mainstream
   tech press, niche trade press, aggregator front pages, wildcard hunting in any
   industry). Coverage breadth with real URLs is the virality proof.
2. Pick `news_picks` news episodes + `wildcards` wildcards. Diversity check: never a
   whole week from one industry. No repeat company inside 8 weeks.
3. Verify every fact that will be spoken and collect the receipt URLs in the same pass.
4. Write on the skeleton, in the creator's configured voice. Each episode carries its
   shot list and (if `linkedin_twins`) a written twin.
5. Gate, persist to `weeks/<date>.json` (`script_class: "research"`,
   `post_type: "receipt-react"`), rebuild the dashboard, run `receipts_build.py`.

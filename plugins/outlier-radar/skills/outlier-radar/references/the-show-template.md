# Show mode: the weekly teardown franchise (template)

_A recurring weekly SHOW where the creator breaks down how a SUBJECT from this week's
news in THEIR industry actually does the thing their niche cares about, through their
own lens. The subject does not have to be a company: a person, a team, a restaurant, a
film, a game, an athlete, a dish, a place. A fitness creator's show might be "How
[Athlete] Actually Trains"; a food creator's "How [Dish] Actually Gets Made"; a film
creator's "How [Movie] Actually Got Made". One subject per episode, receipts on screen
for every claim, one copyable takeaway per episode. **Show mode is optional**, and the
show's name is THE CREATOR'S OWN, discovered in the journey below: never a prefilled
default, never borrowed from another creator's show._

## Why a show

A recognisable franchise compounds where one-off scripts don't: same skeleton, same
spoken devices, fresh subject every episode. Viewers learn the shape, search engines
and answer engines learn the phrase ("how does [subject] [their verb]"), and every
episode advertises the series.

## The config block (written by the first-run interview)

```json
"show": {
  "enabled": false,
  "name": "",
  "turn_line": "",
  "takeaway_lines": [],
  "subject_type": "",
  "lens": "",
  "episodes_per_week": 5,
  "news_picks": 3,
  "wildcards": 2,
  "beats": [],
  "wildcard_taste": "",
  "receipts_strict": true
}
```

Every empty field above is written by the journey. Never prefill a name, a turn line,
or takeaway lines: the creator picks their own exact wording and it locks.

## The journey (run once, inside first-run discovery; use AskUserQuestion at each step)

Show mode is an OPTION. Offer it; a "not now" skips it entirely and the config keeps
`"enabled": false` (it can be run again later with "set up my show").

1. **Do you want a show?** Explain in two sentences why a recurring franchise
   compounds where one-off scripts don't. If no, stop here.
2. **What TYPE of show?** Derived from their niche, offer subject types with concrete
   examples IN THEIR WORLD: companies, people, products, places, events, works
   (films/games/books), teams. "In your niche, whose story would you tear down every
   week?" This sets `subject_type`.
3. **The lens.** "When you look at a [their subject type] in your world, what's the
   question you can't help asking?" Their answer, in their words, is the verdict
   engine. Sharpen it WITH them until it is one line.
4. **The name, theirs.** Generate 3-5 show-name candidates FROM their lens and niche
   vocabulary (never from another creator's show), plus matching turn-line candidates
   (the question spoken at the same beat every episode). They pick or rewrite; the
   exact wording locks. If nothing lands, keep exploring: the name is the franchise,
   do not settle it for them.
5. **The takeaway beat.** Propose 2-3 takeaway phrasings in their voice (the line that
   opens the copyable-lesson beat). They approve the exact wordings; rotation if more
   than one; never improvised on camera.
6. **The beats.** Which corners of THEIR industry should the weekly news sweep cover?
   Default to their niche's trade press and communities, not tech or marketing news.
7. **Cadence + wildcard taste.** Episodes per week, news/wildcard split (default 3+2),
   and what jaw-drop stories they personally love (steers the wildcards).

Close the journey by writing the config, then BUILD AND OPEN THE DASHBOARD so they
see where everything will land (the bundled example week renders until their first
real week exists).

## The fixed skeleton (the recognisable shape)

| Beat | Time | Job |
|---|---|---|
| 1. The news open | 0-4s | Headline screenshot ON SCREEN in frame one. One varied jab about what happened. Never the same syntax two episodes running. |
| 2. The turn | 4-8s | The creator's own turn line from config, exact wording every time. Title card lands on the same beat. |
| 3. The assumption | 8-15s | What everyone thinks the answer is, stated as if true. Then crack it. |
| 4. The receipts walk | 15-45s | 2-3 moves maximum, but/therefore chained, escalating. Every number, brand and claim gets its artifact on screen within a second of being spoken. |
| 5. The takeaway | 45-55s | One mechanism the viewer can copy, in plain words. Opens with the creator's approved takeaway line(s) from config; if a rotating family, never the same one twice in a row. |
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
4. **Punch up or sideways.** Giants and well-funded subjects take the jab; small
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
   whole week from one corner of the niche. No repeat subject inside 8 weeks.
3. Verify every fact that will be spoken and collect the receipt URLs in the same pass.
4. Write on the skeleton, in the creator's configured voice. Each episode carries its
   shot list and (if `linkedin_twins`) a written twin, plus a `visual` block on the
   twin: image | gif | slideshow picked by fit + an image-model prompt carrying the
   creator's brand block from the config (palette, single accent, editorial-minimal,
   no logos, no AI-slop tropes).
5. Gate, persist to `weeks/<date>.json` (`script_class: "research"`,
   `post_type: "receipt-react"`), rebuild the dashboard, run `receipts_build.py`.

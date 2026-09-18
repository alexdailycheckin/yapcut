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
   vocabulary (never from another creator's show). They pick or rewrite; the exact wording
   locks. If nothing lands, keep exploring: the name is the franchise, do not settle it for
   them.
5. **A spoken turn line, only if one fits every episode.** Offer it as optional and say what
   it costs: a phrase forced onto an episode it does not fit spends the opening line on a
   promise the episode never keeps. Ask them to name an episode their candidate phrase would
   NOT survive. If one comes to mind easily, leave `turn_line` empty and let the shape and a
   burned mark carry the franchise. Leave `takeaway_lines` empty by default: the lesson lands
   as a consequence of the story, and a line announcing it is the least story-like move
   available.
6. **The beats.** Which corners of THEIR industry should the weekly news sweep cover?
   Default to their niche's trade press and communities, not tech or marketing news.
7. **Cadence + wildcard taste.** Episodes per week, news/wildcard split (default 3+2),
   and what jaw-drop stories they personally love (steers the wildcards).

Close the journey by writing the config, then BUILD AND OPEN THE DASHBOARD so they
see where everything will land (the bundled example week renders until their first
real week exists).

## The shape (five moves, functions fixed, wording free)

The show is recognisable by what each move DOES, never by a sentence it says. A spoken
catchphrase is optional and usually a liability, because an episode that cannot carry the
phrase spends its opening line on a promise it never keeps. That puts the franchise load on
the shape.

The unit is hook, retain, reward. These five moves are that unit with the retain half written
down, because the retain half is the half that goes missing.

| # | Move | Time | What it has to DO | Status |
|---|---|---|---|---|
| 1 | The receipt | 0-4s | The headline, number or artifact ON SCREEN in frame one, spoken flat. Prove the click before making any argument. | FIXED |
| 2 | The belief | 4-12s | Say what the viewer already believes about this, in their words, as if it were true. | FIXED as a function |
| 3 | The break | 12-45s | The receipts that make the belief untenable. 2 to 4 moves, but/therefore chained, escalating. Every number, brand and claim gets its artifact on screen within a second of being spoken. | FREE |
| 4 | The mechanism | 45-55s | Why it happened, named, arriving as the consequence of move 3 in the same breath. One thing the viewer can carry. | FIXED as a function |
| 5 | The verdict | 55-65s | The creator's POV through their lens, one line, money word last. Hard stop on the payoff. No CTA by default. | FIXED |

FREE means the order, count and wording are the writer's call, and an episode that gets from
the belief to the verdict in a different order should run that way. FIXED as a function means
the move happens every episode and its wording is never the same twice.

### Move 2 is the load-bearing one

Muller's misconception research is the best-evidenced structure available: clear expository
video made students more confident without making them more correct, and presenting the common
misconception FIRST nearly doubled post-test scores. The grammar is in
`the-language-layer.md` part 5: state the wrong belief in the viewer's own words, as if true,
then crack it.

It is general, which is the point. A turn line phrased as one question ("how does this company
actually sell?") only fits episodes about that question. A belief exists in every episode:
about a price rise, a traffic collapse, a measurement claim, the creator's own mistake. There
is always something the viewer walked in holding.

Three ways move 2 fails:

- **A question instead of a statement.** A question hands the viewer no belief to lose.
- **A strawman.** The belief has to be one the viewer recognises as theirs. A belief nobody
  holds breaks nothing.
- **An announcement.** "Here is what everyone gets wrong about this" announces a belief
  instead of stating one. State it flat, as if you agree, and let move 3 do the work.

### The order test

A belief stated after the receipts is a summary of them. The same belief stated before them
turns the identical receipts into a demolition. The wording barely changes and the effect
changes completely, because curiosity fires on a gap and a gap opened after the information
has landed is not a gap. Episodes that read as stat piles almost always have the belief
written somewhere near the end.

### The list test

Read the five moves aloud with the connectors spoken. Every beat joins the next with "but" or
"therefore". Any "and then" is a rewrite order, not a style note (Parker and Stone). A run of
true facts joined by "and then" is a list, and lists bore.

### Move 4 carries no announcement line

The lesson arrives as a consequence of the story, in the same breath. An opening line that
says a lesson is coming ("here is what you can learn from this") is the least story-like move
available: it tells the viewer to start taking notes at the exact moment the story should be
paying off. If `show.takeaway_lines` is empty in config, that is deliberate and correct.

### Move 5 is planned before the episode is written

Peak-end: the audience judges the whole video by its emotional peak and its last line. Hoyos
plans the last line before filming, after measuring a single trailing second cost her 20 to 25
points of retention. Write move 5 and move 1 first, then fill the middle.

## Series memory: callback, promise, follow-up (added 2026-09-09)

A stranger becomes a follower when the episode implies a next one, and a follower becomes
an advocate when they are named in it. Two lines ride inside the skeleton above:

- **Callback** (inside beat 1 or 2, one sentence): last week's episode or a commenter, by
  name. "Last week you told me X was the outlier. You were right, and here is the receipt."
- **Promise** (inside beat 6, one sentence): what next week pays off, including any
  comment-vote ask. "Next week: the company you voted for in the comments."

Every promise is written into the week file as `promised[] {text, made_in, due_week,
paid_in}` and `radar_gate.py` warns on a due promise that is neither paid nor retracted.
A `follow-up` episode type is exempt from the no-repeat rule, one per fortnight, because a
return audience expects the sequel. The comment-vote format (the audience names next week's
subject) is the cheapest audience-participation lever the show has; run it as soon as a
week has comments to choose from.

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

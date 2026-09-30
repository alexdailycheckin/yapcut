# Receipts

One doctrine for both plugins. The Radar verifies and captures; the editor burns. A claim that
cannot be sourced gets cut, never softened.

## The law

Every spoken brand, statistic, date and quote gets a receipt: a source URL in the week file
before filming, a screenshot or a built card on screen while it is spoken. Every figure on a
built card is VERBATIM from the source named in its pill. Reformatting a number is fine;
sourcing one from the script alone is not. An absence claim (a sentence asserting that
something did not happen) can never be receipted and `spoken_lint.py` flags it.

`source_check.py` opens every source URL and proves the words are on the page, reads the
page's own publication date, and fails on two things: a `published` declaration the page
contradicts, and a script asserting freshness ("this week", "just launched", "of the year")
whose newest dated source is more than 45 days old. Age alone never fails: a wildcard tears
down an old subject on purpose. Two dates make a comparison; check both before drawing one.

## Capturing (reject, never repair)

`capture_gate.py` turns a `shot_list` URL into a receipt or refuses and says why. Chrome over
CDP (`cdp.py`, stdlib only) removes consent and promo overlays, reads the DOM, and clips to
the headline's own box. Named refusals: `consent_wall`, `bot_challenge`, `not_found`,
`paywall`, `promo_modal`, `headline_mismatch` (slug versus headline, which catches soft 404s
and homepage redirects that return 200), `flat_capture`, `dark_capture`.

```bash
python3 capture_gate.py --week weeks/<date>.json --out show/receipts/<date>
python3 capture_gate.py --url https://example.com/story --out /tmp/one
```

Never repair a bad capture. Cropping above a cookie modal and undimming the wash
manufactures plausible cards from pages that never rendered (why: CHANGELOG 3.2). A refusal
is not a dead beat. The ladder:

1. The overlay remover usually turns a walled page into a clean capture with no swap.
2. Swap to a capturable source (`receipt-sources.md`).
3. Typeset the headline the gate returned: `evidence_card.py quote --headline "..." --domain x`.
4. For a number or a comparison beat, a built card beats a screenshot on a phone:
   `evidence_card.py stat | bars | chips | timeline`.

Verify cards by eye before burning. The gate proves a page rendered, not that the headline
is the one the beat needs.

## Burning (the editor)

The receipt hierarchy: a brand or product mention gets the official logo on a white rounded
chip (`logo_fetch.py --page "<Wikipedia title>" --box 213x150`); a story or event gets the
real headline card (outlet visible, real screenshot only); a statistic gets a counter or the
headline that contains it. `evidence_card.py` writes brand-typeset transparent PNGs at the
locked width so each drops into an `_overlays.json` pip entry.

Placement is locked, at 1080x1920 (ruled 2026-07-26; the old "below the caption line,
y 1440 to 1650" text was stale until 2026-09-30):

- **The receipt band is above the head, y 180 to 440**, centred, under the platform's top
  chrome (y 0 to 180). The creator frames low and films with headroom for it. Logos, headline
  cards and counters all go here.
- **The hook window is the one exception.** From 0.00 to about 5s the hook holds the top
  (centred near y 430). A receipt on screen then, usually an episode's frame-one headline,
  sits under the caption line at y 1424, about 620px wide, so it ends above the platform's
  bottom chrome (y 1580). Every later receipt goes back to the band.
- A list card that builds item by item may sit under the caption when the head fills the top.
- Never over the face. Text always wins: an overlay that touches the hook or the caption line
  moves (`burn_pips.py` does this). Keep receipts clear of the burned CTA block and of source
  lower-thirds: sequence, never stack. One insert per claim, 2 to 4 seconds, on screen while
  the claim is spoken, a whoosh on entry.

`burn_pips.py` places a pip entry that carries no `y` by these rules. A counter's `y` defaults
to 1150 in `build_ass.py`, just above the caption line; give a counter `"y": 255` to put it in
the band (the block spans y-75 to y+130).

`pip_coverage.py` scans the cut transcript for claim moments and checks each against the
overlays JSON; `yapfull.sh` runs it on the finished file, build-fatal when brand-config sets
`pip_strict: true`, which a scripted channel should.

## Ownership is a receipt too

Every research or educational item declares `proof {kind: own | reach | public, ref}`
(`week-schema.md`). A public-sourced teardown is reproducible by any account with the same
URLs. The creator's own number or conversation is not. `check_fidelity.py` prints the batch
split so a week that is all `public` is visible before it ships.

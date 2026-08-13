# Post-type library (the shape decides before the words do)

_Added 2026-07-10 after Alex's note that scripts weren't bundled into proven post
types. The rule: SUBSTANCE CHOOSES THE SHAPE, then the script is written INTO that
shape's beat map. Talking-head is the fallback, not the default, and it must be
justified (if an artifact on screen would beat the face, use the artifact). Every
script carries a `post_type` field, and `directions` must be the beat map of that
type with rough timestamps, not generic staging notes._

## PRODUCTION CEILING (Alex's standing constraint, 2026-07-11)

**The shot is always a talking head.** Phone, face to camera, one sitting. Alex has
no time for production: no whiteboards, no props, no costumes, no sets, no actors,
no b-roll days, no screen-recording sessions on camera. Every post type below is an
EDIT-LAYER grammar: types differ in what the EDITOR burns onto talking-head footage
(PiP artifacts, progressive diagram overlays, counters, cards, stamps, score,
lower-thirds), never in what Alex films. Concretely:
- **receipt-react / countdown / storytime / teardown / meta-ab:** talking head +
  PiPs and stamps. Already compliant.
- **whiteboard-build:** Alex draws NOTHING. The editor builds the diagram as a
  progressive overlay while he talks.
- **screen-record-walkthrough:** talking head + screen-capture PiPs prepared at
  edit time (Claude captures the screens, Alex never records his screen on camera).
- **skit-pov (office lane):** ONE MAN, SAME SEAT. Characters are energy shifts and
  jump cuts with edit-layer lower-thirds. Multi-actor scenes get rewritten as
  first-person storyteller retellings ("let me tell you what happened at the QBR").
- **day-in-life-vo:** SUSPENDED (requires a b-roll day). Only revive if Alex asks.
- A prop is allowed only if it is within arm's reach at filming time, and the
  script must never depend on it (the PiP fallback is the default).
`directions` must always read as: what Alex does with his face and voice + what the
EDIT LAYER burns. If a direction requires Alex to stand up, it is wrong.

## Type-fit rule (run this before writing a word)

- Data / study / benchmark / canon collision -> **receipt-react**
- Framework / model / two-things-compared -> **whiteboard-build**
- Rules / mistakes / benchmarks in a set -> **countdown-listicle**
- Company story / autopsy / case study -> **storytime-receipts**
- A system or workflow Alex actually runs -> **screen-record-walkthrough**
- Pure hot take where the energy is the point -> **talking-head-rant** (justify it)
- Recognition humour / characters -> **skit-pov** (office lane default)
- A day or process better shown than said -> **day-in-life-vo** (Mode B, see script-anatomy)
- A bad post / bad copy / bad advice as the artifact -> **teardown-react**
- The post tests itself across formats -> **meta-ab** (sparingly, it dulls with reuse)

## Batch rules (QA-gated)

- A weekly 10 must span at least 4 distinct post types.
- Max 3 talking-head-rant per batch.
- Every educational script uses a SHOW type (receipt-react, whiteboard-build,
  countdown-listicle, screen-record-walkthrough, storytime-receipts). A lecture to
  camera is not a teach.
- Show-type hard rule: never SPEAK a stat, name, or step without SHOWING it on
  screen at that moment. If the script says "92 percent", the frame says 92%.

## The types

### receipt-react
The artifact (chart, screenshot, headline, dashboard) is the co-star, on screen
from frame one; Alex reacts to it, points at it, circles it. His editor's PiP
evidence inserts carry this.
- **Beat map:** 0-2s artifact full-screen + one-line shock read of it. 2-8s what
  you're looking at, source NAMED on screen. 8-20s the two or three details that
  matter, each circled or zoomed as its own beat. 20-30s the reframe (what this
  actually means for you). 30-40s the do-this, as an on-screen checklist card
  ("screenshot this" = save-bait). Button to camera, artifact gone.
- **Retention driver:** the artifact is a visual promise; every circle/zoom is a
  mini-payoff; the checklist card farms saves.
- **Fits:** canon collisions, platform studies, benchmark data, Proof-style stats.
- **QA:** artifact visible in frame one; source named on screen; no spoken number
  without its visible twin; do-this rendered as a card.

### whiteboard-build
A diagram draws itself (napkin, whiteboard, or editor overlay) while Alex talks.
The lo-fi high-concept mechanic: crayon production, big idea.
- **Beat map:** 0-2s FLASH the finished diagram ("this is why your content dies")
  then wipe it. Build piece by piece, one element per beat, each element = one
  spoken line. The AH-HA is the final arrow/word drawn. Button over the completed
  drawing.
- **Retention driver:** an incomplete drawing is an open loop; the brain stays to
  see it finished. The 0-2s flash-forward is the promise.
- **Fits:** loops vs funnels, two-schools map, four fits, any model.
- **QA:** flash-forward at 0s; diagram completes on screen; no element drawn
  without its line, no line without its element.

### countdown-listicle
Numbered items with an on-screen counter. The counter is a progress bar.
- **Beat map:** hook promises the payoff at #1 ("the last one is the one your CFO
  will hate"). Items run ascending value, each = claim + one visible proof + one
  line of why. Before #1, a re-hook beat ("this last one is why I made this
  video"). #1 over-delivers. Button.
- **Retention driver:** progress + held-back best item.
- **Fits:** mistakes, rules, benchmark sets, "things I'd never do".
- **QA:** counter on screen; ascending order; re-hook before #1; each item has a
  visible proof, not just a claim.

### storytime-receipts
The SBH engine generalised: a story told through dated artifacts.
- **Beat map:** contrast-line cold open. The height (how big it was, shown). THE
  SCENE: one room, one meeting, named people, a number on the table (this beat is
  mandatory; facts without a scene is a Wikipedia read). The unraveling, date
  stamps as mini-cliffhangers. The autopsy line (one sentence). The transfer to
  the viewer.
- **Retention driver:** scene-level specificity + date stamps as open loops.
- **Fits:** SBH / Won on Distribution, case studies, "I watched this happen".
- **QA:** at least one scene with people deciding something; every date/number
  stamped on screen; admiration tone (punch up or sideways).

### screen-record-walkthrough
The actual screen doing the actual thing, Alex PiP. The hours-saved mechanic
(fastest-rising short-form format of the period).
- **Beat map:** 0-2s the RESULT cold open ("this took four minutes"). Then the
  3-5 steps compressed, each step visibly happening on screen. One catch/nuance
  beat (credibility). Button with the artifact of the result.
- **Retention driver:** watching the thing actually work; time-compression jumps.
- **Fits:** the loop machine, the radar itself, newsletter/blog pipeline, any
  "here's my actual system" teach.
- **QA:** result shown before the steps; every spoken step visible on screen; no
  hypothetical demos, only the real thing.

### talking-head-rant
Face and energy carry it. LEGAL ONLY when no artifact would beat the face
(a genuinely hot take, a confession, a dare). Requires: punch-in or cut every
1-2 sentences, an escalation ladder (each beat raises the stakes), one quotable
line per ~10 seconds, and a button that is NOT a tidy aphorism (see button rules
in script-anatomy).
- **QA:** justify in `borrows` why an artifact would not beat the face; escalation
  present; quotable line engineered.

### skit-pov
Office-lane default: characters, title cards, played straight. Beat map lives with
the borrowed office mechanic (see mechanic-library office table). QA: the bit
lands without sound (title card + visual carry it), insider-specific, no winking.

### teardown-react
A real post, ad, or copy line on screen; Alex reads it, names the smell, rewrites
it live. Runs the Angle Machine six-beat teardown arc.
- **Beat map:** the artifact + verdict cold open ("this post cost someone a
  pipeline"). Read the offending line. Name the smell (category-as-angle,
  for-everyone, naked number, lazy benefit). The three extraction questions,
  fast. The rewrite appears on screen. Before/after side by side. Button.
- **Fits:** copy/messaging content, bad-advice corrections.
- **QA:** real artifact (anonymise if punching down risk); rewrite shown, not
  just described; the flip line lands ("the angle isn't X, it's Y").

### meta-ab
The post is a referendum on itself (video vs document, hook A vs hook B), pinned
comment sends viewers to check the twin. High novelty, dulls fast: max one per
batch, never two weeks running.

### day-in-life-vo
Already systematised: see the Mode B section in script-anatomy.md. Micro-loop
beats, contradiction hook, deadpan VO.

## Growing this file

When an outlier is autopsied (flag protocol) note WHICH post type it was, not just
its hook mechanic. A mechanic is the idea-shape; the post type is the screen-shape.
Both get logged: mechanic to mechanic-library.md, type here (add a new type only
when an outlier proves a shape this file doesn't cover).

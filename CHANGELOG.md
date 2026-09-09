# Changelog

Release notes for [YapCut](README.md), newest first.

## What's new in 3.6.0 (outlier-radar)

**The gate now grades whether the week got made, not only how it reads.**

Every gate in the runner checked craft: hook length, verbless runs, the antithesis epigram,
the numeral law, whether a figure carries a source URL. None of them checked whether the
research behind the week happened. So a week with zero outliers, zero episodes and zero ammo
passed with a clean table, as long as its sentences were tidy.

That gap has a predictable shape. Step 1 of the weekly routine, the early-signal sweep, is the
expensive step, so it is the one a hurried run drops. What comes out instead is a diary: posts
about the creator's own posting habits and analytics, which read perfectly well and teach their
audience nothing. On 2026-09-09 a run did exactly this and went green.

- **New `completeness` gate in `radar_gate.py`.** FAILs a week that shipped items in any lane
  with an empty `inspiration[]`, and names the sweep in the failure. Warns on outliers missing a
  link or a `metric_confidence`, an empty `ammo[]`, a missing `experiment` block, and video
  slots configured in `quantity` but left unfilled.
- Skippable as `--skip complete` when you know the week has no sweep and have said so in
  `sweep_note`.
- The bundled example week passes it unchanged.

## What's new in 3.5.0 (outlier-radar) and 3.1.0 (tiktok-yap-editor)

**The audit release.** A 13-lens audit of the repo and its live install on 2026-09-09 found that
the engine optimised the one stage that was never the constraint: 157 scripts written, 22
posted, every video row a placeholder, the loop run once. This release changes what the engine
optimises for.

**Outlier Radar 3.5.0**
- **Audience first.** Discovery asks who should recognise the creator and for what before it
  asks about niche (`audience` in the config), and runs a proof-extraction interview instead of
  collecting adjectives about the voice. The corpus is harvested from where the creator already
  talks, with a `register:` header per capture, before any batch is written.
- **Filming slots, not a script bar.** `quantity` in the config replaces "about 10 per lane";
  the spare budget goes to variations of the last measured winner. The secondary lane starts off.
- **A gate that gates.** `check_fidelity.py` had no exit call in 713 lines. Every gate now
  returns 0, 1 or 2; `radar_gate.py` runs the five in one command and stamps the week; the
  schema is versioned and validated (`references/week-schema.md`); cadence distribution rules
  are warnings by default and `--strict-cadence` restores them; the ownership split (`proof.kind`)
  is printed for every batch.
- **The loop closes on disk.** `performance/tracking.jsonl` (filmed, posted), `people.jsonl` (who
  answered), `learned.json` (weights past n=4, read by the selector), `last-report.md`, a
  pre-registered `experiment` per week, TikTok Studio and people pastes in `ingest_feed.py`,
  and video rows that carry watch-through. The dashboard seeds from tracking and renders an
  Ammo tab, reply blocks, proof chips, the week's question and the show's promises.
- **Distribution is shipped doctrine** (`references/distribution.md`): the daily block with
  `ammo[]` and `held[]`, the people ledger, callback and promise, day-0, tag guardrails.
- **One resolver** (`yapcut_home.py`), no skill-folder fallback: from the wrong directory the
  scripts used to grade the bundled example inside the plugin cache and exit 0.
- **A law.md overlay.** The playbook reads `<workspace>/law.md` after itself and a workspace
  `references/<name>.md` over its own, so a creator's rulings ride on top instead of forking.
- **LinkedIn craft moved in** from a private skill (save-mechanics, format-library, the
  spec-driven `carousel.py`, Shape 5 in linkedin-visuals). The public engine no longer cites
  private files. The `dashboard/` split (template, CSS, JS) makes the 3.4.1 class of bug lintable.
- **SKILL.md 545 to about 260 lines** with a routing table; the receipts law and trend
  creation moved to references shared by both plugins.

**TikTok Yap Editor 3.1.0**
- **One gate ladder** (`scripts/gates.sh`) for Mode A and Mode B, one exit contract, every
  result recorded; Mode B previously ran none of the eight gates.
- **Frame zero.** The first hook line is static at 0.00 (the typewriter used to show one letter
  and a cursor to the muted feed); a frame-zero gate enforces it. A hook word gate (9 words),
  `hook_variant.sh` for A/B hooks, `YAP_PLATFORM` for per-platform re-composes.
- **The edit record.** `finalize.sh` writes `<name>.edit.json` with the Radar id, hook, gates and
  platform, and no longer deletes the working directory by default. `log_perf.py --edits` joins
  it to the outcome.
- **`retention_check.py --keeps`** discards the cutter's own joins, which were 69 to 86 percent
  of the "visual events" on shipped files.
- **`scripts/yaplib/`**: one brand resolver (workspace, never the skill root), one font finder,
  one media wrapper; `library.py` ships with `reconcile`. `requirements.txt` and a synthetic
  fixture (`tests/`) drive the pipeline end to end in seconds.
- SKILL.md 865 to about 330 lines; Part 1 (editorial) unchanged.

**Repo**
- `release.sh` is the one release command; the pre-commit gate gained `--history` (scans every
  commit, not the staged diff) and a doc-to-code link check; README install route 2 is gone.

## What's new in 3.4.6

`voice_brief.py` stopped printing its own section headings into the corpus statistics (the
brief's headings were being counted as the creator's sentences). No changelog entry shipped
with it at the time; recorded here 2026-09-09.

## What's new in 3.4.5

**The tracked doctrine no longer names a creator.** 101 references to one person by name
had accumulated across 17 skill files: decisions attributed as "X's directive, 2026-08-11",
production constraints written as what one person does with their face, a lint that failed
on "phrases X has already rejected". All of it now reads as the creator, and the two knobs
that genuinely belong to a person, the subject lane and the target mix, already read from
`radar-config.json`, which is gitignored. The code was config-driven the whole time. The
prose was not.

**This mattered because of how the repo is wired, which is worth stating plainly.** This
tree is simultaneously the public repo and the single source for a live install, so the
plugin copy and the working copy cannot drift. The cost of that design is that there is no
private tree to write personal notes into. `.gitignore` fences the data correctly, the
config, the weeks, the dashboard, the performance log. Prose has no such fence, so every
Alex-shaped comment written while fixing a bug published on the next release.

**The gate now enforces it.** A staged plugin diff that names the creator is refused, with
a message pointing at `radar-config.json`. Deliberate attribution is spelled differently
and passes untouched: the owner and author fields, the byline, alexmuresan.com, the Reach
partner pill. "Alex Hormozi" is excused by name, because he is a cited author rather than
the creator, and a substitution that did not know the difference would have rewritten three
citations in `video-scripting-as-a-science.md`.

## What's new in 3.4.4

**Private material is out of the public repo, and the gate that missed it is wider.**
Four things had reached this repo that should never have: a private vault file cited by
bare name in two places, a named customer's revenue metrics sitting next to that
customer's name, the employer's commercial strategy given as the reason for a design
decision, and one absolute path into a private folder. The path was the only one the
pre-commit gate caught, because the gate only knew about machine paths. It now also
refuses vault filenames, the employer named as an actor or owner rather than as the
partner pill, and a list of named customers.

**The reasoning survived the scrub, which is the test that mattered.** Every passage
that cited something private was making a real argument, so each was rewritten to make
the same argument from the creator's own configuration instead of from one creator's
private files. The worked example that named a customer now describes the shape of its
stats and says to name a customer only where the figures are already public and the
customer has agreed.

## What's new in 3.4.3

**The show's shape stopped reading as a checklist.** SKILL.md called the six beats in
`references/the-show-template.md` a fixed skeleton, so an episode that filled all six
could satisfy every gate and surprise nobody. Two parts are fixed now: the receipt sits
in frame one, and the verdict comes through the creator's own lens. Those two are what
an audience returns for. The middle exists to get from one to the other, so a story that
arrives in a different order, or cracks two assumptions, or has no clean steal line,
should run that way.

**The asset step knows more than one shape.** It recognised exactly one before: three or
more headed units becomes a document post. Everything else shipped as plain text, or
shipped with a card invented that afternoon and never written down. On 2026-09-07 four
single-image cards got built in a day, none of them a carousel, all four worth repeating,
and their builders lived in a session scratchpad that garbage collects.
`references/linkedin-visuals.md` is now Stage 0 of the asset step: meme, borrowed quote,
customer sighting, category map, carousel, asked cheapest first, and answering "text
only" when nothing on the list has an input on disk. `linkedin-selector.md` points at it.

**What that file stores is reasoning, not layout.** Each shape carries what it is for,
what it requires on the table before it can be built at all, the one move that makes it
work, and the way it fails. Those transfer between builds. Type sizes do not, so the
worked examples record one solution each with real hexes and paths and are labelled as
the instance rather than the pattern.

## What's new in 3.4.2

**The source gate finally looks at the date.** `source_check.py` proved every claim
string was on its page and never once asked when the page was written, so a batch
shipped describing a February 2025 campaign as "the most copied campaign of the year",
and, worse, ran a head-to-head between 2 LinkedIn experiments 18 months apart that
straddled the March 2026 feed-ranker replacement. 32 verified claims produced total
confidence in a stale one. The gate now reads each page's own machine-readable
publication date, prints the age of every receipt, and fails on 2 things: a declared
`published` date the page contradicts from a trustworthy field, and any script
asserting freshness whose newest dated source is over 45 days old.

**Age by itself is not a defect, and the gate is built to keep it that way.** A
wildcard tears down an old subject on purpose. Only claiming recency you do not have
fails. Sources are tiered too: a date from article-level structured data can fail a
declaration, while a bare `<time>` tag or a date in the URL path can only raise an
unconfirmed warning. That tier exists because the first run of this gate read a
related-posts sidebar on buffer.com and called a correct declaration a mismatch.

**The freshness vocabulary is deliberately narrow.** Bare "just" and bare "now" are
ordinary adverbs and matching them flagged every script in the batch. First-person
time references were dropped for the same reason: "a post I wrote 9 days ago" claims
nothing about a source. "this week" and "this month" are kept despite the same risk,
because a false positive costs 1 reworded hook and a miss costs a batch asserting a
dead story is live.

## What's new in 3.4.1

**The dashboard survives a number where it expected a word.** One numeric field in
an episode's `shot_list` used to take down the entire card render. `esc()` assumed
its argument was a string, so `"beat": 4` threw `(s || "").replace is not a
function` inside `render()`, and because the header, tabs and brief are static HTML
the page still looked healthy while every card and every button in it was gone. It
reported as "the ignore button doesn't work", which it could not, since no card had
been drawn to carry a button. Fixed at `esc()` rather than at the one field: the
same line already coerced `s.n`, and patching field by field is what left the
landmine in place.

**The shot list stops hiding its own instructions.** The table read only `shoot`,
while `capture_gate.py` accepts `what` or `shoot`. A shot list written for the
capture pipeline rendered an empty "Shoot this" column. The dashboard reads either
name now, so the two tools agree.

**Tracking admits when the browser will not let it save.** The theme calls were
always wrapped; the two the whole UI depends on were not. Where `localStorage`
throws, and Safari on a `file://` origin does exactly that, the unguarded write
killed `setT()` before it reached `render()`, so a click changed nothing on screen.
Both calls are guarded now. A failed write no longer stops the UI updating, and it
says once that marks will not survive a reload instead of failing quietly.

## What's new in 3.2.2

**The lockup is balanced.** The wordmark now stands at 78% of the dog's height,
close enough to read as equal without swallowing the mark, and the two sit on one
shared centre line. Sizes were chosen from rendered comparisons at the real header
size rather than from the numbers, since the dog is a tall thin subject and its
optical weight is lower than its bounding box implies.

## What's new in 3.2.1

**The masthead gets out of the way.** It was eating a quarter of the viewport on
a laptop; it is now 125px instead of 215px. The wordmark sits smaller against the
dog so the mark leads, the byline is flush to the lockup's left edge, and the
accent bloom behind the header is gone. The page grain stays.

## What's new in 3.2

**YapCut has a face, and the dashboard wears it.** The mark is a yapping Yorkie
next to a red foil balloon wordmark. The kit now ships two files: `logo.png`, the
full lockup for the masthead, and `logo-mark.png`, the dog alone for the sticky
bar and the browser tab. Both are inlined as data URIs, so the dashboard stays a
single self-contained file. Drop either name into your workspace to run your own
art; with no logo file at all the original rings mark still renders.

**The surface is branded, not just the header.** A fine generated grain sits over
the whole page so flat panels read as paper instead of screen, and one soft accent
bloom sits behind the masthead so the logo has its own light. Both derive from
your configured accent, so they follow your palette rather than ours.

## What's new in 3.1.2

**The mark doubles again, 160px.** The smiley is the header's hero now, circular
lettering fully readable. The sticky topbar grows with it; that is the point.

## What's new in 3.1.1

**The face is legible now.** The header mark doubles from 38px to 80px; at 38px the
smiley's circular lettering was an unreadable smudge.

## What's new in 3.1

**Outlier Radar has a face.** The acid smiley: a radar sweep for an eye, a waveform
drip for a mouth. It ships as `logo.svg` next to the build script and renders as the
dashboard's header mark on every install, same standing as the wordmark. Drop your own
`logo.svg` in the workspace to replace it; with no logo file anywhere, the original
rings mark still renders.

## What's new in 3.0.1

**The Reach partner pill is locked.** It was a config default in 3.0.0; it is now part of
the tool. Outlier Radar is built by alexmuresan.com in partnership with Reach, and every
install renders that credit, mark, link and tagline included. No config key touches it.
The source stays open, so a fork can do what forks do, but the config will not do it for
you. The example config lost its dead partner knobs; `byline` remains yours to keep or
clear.

## What's new in 3.0

**The QA and measurement release.** Until now the kit could research, write, select and
render, but it could not grade its own output or learn from what shipped. Both halves of
that loop now ship, ported from the author's live install, where every piece below ran for
weeks before landing here.

**Outlier Radar**

- **`check_fidelity.py`, the machine QA gate.** Voice fingerprint on testimony scripts
  (does the script move like the creator talks), and a LinkedIn pass over the `linkedin[]`
  lane plus every embedded twin: every number written as a numeral, every figure backed by
  a source URL, duplicate ids caught (tracking is keyed on id, so a duplicate silently
  overwrites one post's numbers with the other's), and `qa` limited to its two legal
  values. `passed` means shippable today; `pending-approval` means clean and waiting on
  your yes. The old `pre-qa` limbo state is gone: it rendered identically to "nothing ever
  read this", which is how posts sat unreviewed for weeks.
- **`log_perf.py`, the ledger.** `--paste` logs a week of video views in one paste,
  `--linkedin` logs twin impressions, `--followers` tracks the follower delta, `--due`
  lists what was measured too early, `--report` reads back what works by mechanic, shape
  and job. Append-only jsonl; anything younger than 48h is stored but never ranked,
  because early numbers measure age, not quality.
- **`ingest_feed.py`.** Paste the whole analytics table, get clean performance rows. Dry
  by default, `--commit` writes. One prompt per post is how a performance folder stays
  empty for ten weeks.
- **`visual_lint.py`, the feed-asset floor.** Measures a render against the feed's own
  background before you post it: a cream card on LinkedIn's cream page reads as no image
  at all (the case that created this gate measured 4.9% edge delta against a 25% floor).
- **`hook_lint.py` v4.** Now also gates closing lines, including the banned two-sentence
  antithesis closer, because the same closing mold on two adjacent posts reads as a
  template even when the posts are good.
- **`select_linkedin.py` current generation.** Twin cap with banked posts (a post that
  loses its slot carries to a future week instead of dying), a posting calendar with
  urgency-ordered slots, and per-post `post_day`/`post_slot`/`post_why` the dashboard
  renders as a publishing plan. Your subject lane and weekly mix now live in
  `radar-config.json` (`selector.lane`, `selector.target_mix`) instead of being anyone's
  hardcode.
- **Dashboard.** Three QA states rendered honestly (QA passed / Awaiting approval /
  Pre-QA as a visible bug flag), the posting calendar, banked-post section, accent
  derivatives computed from your brand accent instead of shipping the author's palette,
  `brand.fonts.google_import` honored, and the partner pill now carries an optional
  tagline (`partner_tagline` in the config clears or replaces it).
- **References.** The LinkedIn selector doctrine is current, and three craft files ship:
  `post-types.md` (pick the screen shape from substance before writing a word),
  `video-scripting-as-a-science.md`, and `shorts-craft-2026.md`.

**TikTok Yap Editor**

- **`burn_pips.py`.** Receipt PiPs (logos, headline screenshots) burned onto the finished
  clip with the hard text-collision rule: a PiP may never sit on the hook or the caption
  line, offenders are auto-fitted or shrunk, text always wins. Wired into `yapfull.sh`
  post-compose, so `pip` entries in the overlays JSON never silently drop.
- **`reanchor_overlays.py`.** Re-anchor hand-placed receipts across a re-cut by
  spoken-word index instead of re-timing them by hand.
- **Two-pass loudness in `compose_ass.sh`.** Single-pass loudnorm under-shoots on short
  clips with a loud transient (a 17s clip with a gong measured -17.6 LUFS against the -14
  target, thin in the feed). Pass 1 measures, pass 2 applies a clamped linear gain with a
  limiter guarding the ceiling. The 48kHz sample-rate pin stays.
- **`build_ass.py` subheading fix.** In the minimal hook style, context lines after the
  big statement are drawn smaller and are now MEASURED at that size too; measuring them
  full-size wrapped one-line subheadings and silently broke the intended look.
- **Cut stage defaults.** `--auto-floor` (measure each take's noise floor and lift the
  silence gate above it, so a take with loud room tone still gets cut) and `--head-trim`
  now on by default via `yapfull.sh`, and `HOOK_SECS` is honored end to end.

## What's new in 2.6

**Outlier Radar picks the LinkedIn post's own shape, and tells you what order to publish in.**
Only relevant if you turned LinkedIn twins on.

- **A twin no longer inherits the video's shape.** Each primary-lane script gets a written
  LinkedIn version, and it used to copy the video's `post_type`. That gave you a week of
  identical posts, and five posts of one shape read as one post published five times. The
  new `select_linkedin.py` picks the FEED shape from the substance instead, because the two
  surfaces do not reward the same thing: short-form rewards watch-through on a hook, the
  feed rewards dwell time, saves and early comment velocity.
- **It reports the week, not just each post.** Job mix against a portfolio of 2 reach, 2
  authority and 1 relatability, because follower growth is reach to non-followers times
  conversion to follow, and each job serves a different half. Drop the reach leg and the
  week only reaches people who already follow you. Drop the authority leg and strangers
  arrive with no reason to stay.
- **Length is now a character rule with a real dead zone.** Two shapes work: under about 300
  characters, which wins on replies rather than dwell, or 1,300 to 1,900, which is the reach
  band. Roughly 600 to 1,000 characters buys neither and the tool flags it. Length is a
  ceiling, never a target.
- **It points you at the carousel pipeline that already shipped.** Document posts report
  around 6.60% engagement against 2.00% for text-only, so if a post is already a sequence
  of headed units the shape decision beats every other lever. When the substance is a
  sequence argument written as prose, the tool says so and tells you the three steps.
- **Publishing order follows urgency, not quality.** A news peg decays, so the order is by
  how fast an item loses value rather than how old it is: a 7-day peg expiring tomorrow goes
  before a fresher one with room. A great post whose peg died is worth less than a good post
  published while it is alive. Evergreen items sort last and act as the buffer that absorbs
  a slipped week.
- **It asks instead of guessing.** Whether a claim is arguable, whether a list is really an
  ordering argument, whether a story carries real failure: these are declared on the twin,
  never inferred. A regex cannot detect contrarianism, and a tool that pretends to is worse
  than one that asks. Undeclared items are flagged, not silently assumed.

The scoring weights are priors from published studies, not findings, and the reference says
so plainly: the platform never exposes saves or dwell to authors, so those weights stay
priors and impressions are the proxy. Reasoning, sourcing and limits in
`references/linkedin-selector.md`.

## What's new in 2.5.1

- **An interrupted onboarding resumes instead of stranding you.** The discovery gate used
  to be "does `radar-config.json` exist", but the config is written at step 1, so a first
  run that ended early (session closed, context ran out) left a config behind that made
  every later run skip discovery and jump to the weekly routine. You got scripts but no
  cadence and no chance to answer the questions you never reached. The gate now reads
  `schedule.enabled`, which is only true once the interview has actually been through it,
  and resumes from the first unanswered question. Established users from before cadence
  existed are detected by a real batch in `weeks/` and are asked the cadence question only,
  never re-interviewed.
- **Install says `/reload-skills`, not "restart Claude Code"**, and hands you the literal
  sentence that starts onboarding (`run outlier radar`), because loading a skill does not
  start it and the difference read as a broken install.

## What's new in 2.5

- **Onboarding now finishes the job.** It used to end on the config with the bundled
  sample week still on screen, which read as a broken install. The first run now also
  writes your first real batch, creates an actual recurring weekly run at a day and time
  you pick, and opens the dashboard on **your** scripts.
- **The dashboard is finally yours.** The `brand` block in `radar-config.json` (colours
  and fonts) was being written at onboarding and then ignored by the dashboard builder,
  so every install rendered in the same default theme no matter what you answered. It now
  themes properly, with neutral defaults when you skip the question.
- **Receipts: reject, never repair (`capture_gate.py` + `cdp.py`).** The old capture path
  cropped above cookie modals and undimmed the wash, so it produced plausible-looking
  cards from pages that never rendered: one 7-video batch shipped 21 junk receipts
  (10 cookie walls, a 404 page, a bot challenge, a discount popup, nav lists in place of
  headlines). The new gate drives Chrome over CDP with no extra dependencies, removes
  consent overlays before judging, verdicts from page TEXT rather than pixels, and clips
  the screenshot to the headline's own bounding box so "cropped the wrong region" stops
  being possible. On the same 48 URLs: 39 pass / 9 reject, against 9 usable of 34 before.
  `receipts_build.py` and `cards_from_raws.py` are deprecated but still bundled.
- **Six receipt card types (`evidence_card.py`).** When a page refuses to be captured,
  or when the beat is a number rather than a story, build the card instead: `capture`,
  `quote`, `stat`, `bars`, `timeline`, `chips`. Brand-typeset, transparent PNG at the
  locked receipt width. Every figure must be verbatim from the source in its pill.

## What's new in 2.4

- **Three new ship gates, wired into `yapfull.sh` (a batch of 12 shipped with
  defects a human pass missed; these make that class impossible):**
  - **Dead-air gate** (`gap_check.py`, fatal): transcribes the finished cut
    punct-separate and fails any surviving inter-word gap >= 0.8s. Silence
    detection reads room tone as sound and the caption transcript glues pause
    time into word tokens; both said "clean" while a 1.3s hole shipped.
  - **Caption-garble gate** (`caption_qa.py`, fatal on scripted runs): diffs
    every burned caption word against the verbatim script (numbers fold across
    notations, "fifteen dollars" == "$15"). Whisper had shipped "ARK" for Arc,
    "Radio" for Rdio, "clod" for Claude, "chatgbt", and "Ferguson" for
    "first and". Garbles go in `_corrections.json`, ad-libs in `_capqa_ok.json`.
  - **Receipts gate** (`pip_coverage.py`): every spoken brand/stat wants a PiP
    evidence insert or counter on screen while it is said; report by default,
    fatal with brand-config `"pip_strict": true`. retention_check now also runs
    automatically post-compose, with the real hook-end read from the .ass.
- **96kHz export bug fixed**: loudnorm resamples internally; compose now pins
  the export back to 48kHz.
- **Mode B push-in no longer shakes**: zoompan renders on a 2x supersampled
  frame, so the 12% push steps sub-pixel. Push defaults to off; spend it only
  on shots that would otherwise sit dead.
- Docs: receipts rule ("every named brand/stat gets its receipt on screen"),
  scripted-run contract (`<out>_script.txt`), per-run output subfolders,
  Mode B finishing rules (picture == VO length, day-flow chronology),
  footage-library path via `YAP_LIBRARY`.

## What's new in 2.3.3

- **Noisy-take protocol** (SKILL.md 6b): a loud room-tone bed (fan/AC) is
  diagnosed by measuring real gap windows (astats' "noise floor" is misleading)
  and fixed with a gentle `afftdn` pass on the cut intermediate + a
  `YAP_FROM_CUT` rebuild, keeping the noisy copy for one-command re-tuning.

## What's new in 2.3.2

- **The repetition gate now listens to the audio, not just the transcript.**
  Whisper transcribing a whole video sometimes collapses a repeated line into
  one ("then read the post history... then read the post history" came back as
  a single sentence), which made the defect invisible to any transcript-based
  check. New `scripts/restart_scan.py` re-transcribes the cut in overlapping
  30s windows (short-context whisper stays literal) and flags repeats on the
  video timeline. `yapfull.sh` runs BOTH detectors; either HIGH fails the build.
- **Artifact guard.** A "repeat" whose whole span is under 150ms is whisper
  token-splitting, not speech, and no longer flags.
- **HIGH flags are auto-verified before they can fail a build.** Two
  independent paths: reproduce in a tight re-transcription, or show the
  double-take envelope dip (attempt, pause, attempt) inside the span. True
  restarts pass at least one (some never reproduce in ANY transcript and are
  confirmed by envelope alone); token-splitting artifacts fail both and are
  demoted to review.

## What's new in 2.3.1

- **The build gates itself.** `yapfull.sh` now refuses to finish a video with a
  known defect: a stutter/restart in the cut's own transcript fails the build
  before captions (STUTTER GATE), and a splice hole at any join fails it after
  compose (SEAM GATE). QA is in the build path, not a checklist after it.
- **Smarter restart detection.** `stutter_check.py` matches fumbles whisper
  hears differently on each side (consonant-skeleton fuzzy matching), and its
  confidence is evidence-based: 3+ word echoes gate the build, 2-word echoes
  are flagged for the human line audit (they are usually deliberate rhetoric).
  It also catches **distant line re-reads** (miss a line, read it again later):
  a 6+ word echo within 20s fails the build; short topic-phrase echoes and
  older callbacks are flagged for review instead of blocking.
- **Caption-only rebuilds.** `YAP_FROM_CUT=1` skips the cut stage and reuses
  the existing cut: fix a caption word without re-cutting, or rebuild when the
  raw footage is gone.
- **Splice-hole repair.** New `scripts/patch_hole.py` fills an audio dropout at
  a join with adjacent room tone, video untouched: for when the source is gone
  and the cut is all you have.
- **The pipeline cleans up after itself.** Segment scratch is deleted after
  every successful concat (a 13-video batch used to leave gigabytes behind).

## What's new in 2.3

- **Perfect cuts.** The cutter stopped machine-gunning: a cut must earn its visual
  jump. Only pauses >= 0.55s become cuts (0.3-0.5s pauses are speech cadence), no
  segment shorter than 0.45s ever ships (short bursts bridge into a neighbour), a
  cut must remove at least 0.25s to exist, and pads are decay-aware (0.12/0.10) so
  word edges never get shaved. On a real 13-video batch the old defaults made 57%
  of joins micro-gap cuts and left 4-frame flash segments; v2.3 removes only real
  dead air.
- **Click-proof pause detection.** Pauses are found on a median-smoothed RMS
  envelope instead of an instantaneous level gate: a single mouth click used to
  split a 1.5s pause into undetectable chunks, shipping a 2-second on-screen gap.
- **No more splice blips.** Segment audio is PCM with 4ms edge fades and gets one
  continuous AAC encode; per-segment AAC + concat stream-copy inserted a ~20-40ms
  audible hole at every join. New `seam_qa.py` probes every join in the finished
  video and fails the build if a splice hole survives.
- **Cut-point transparency.** `yapcut.py` writes `keeps_<out>.json` (the exact
  final cut points) so QA can audit seams instead of eyeballing.
- **Boundary ground-truthing rule.** Story-cut boundaries are placed from a ±5s
  window re-transcription, never from full-file word timings (whisper DTW drifts
  up to ~2s mid-file and can swallow words at a splice).
- **Minimal typewriter hook.** `build_ass.py --hook-style minimal` renders the
  no-outline, soft-shadow hook with a size hierarchy inline, so the typewriter
  reveal works with it; set `"hook_style": "minimal"` in brand-config.

## What's new in 2.2

- **Retention gates in the editor.** New `retention_check.py` runs on every finished cut and
  gates the build like the stutter checker: it fails if nothing changes on screen in the
  re-hook window (~2-3.5s) and prints every static stretch over ~5s with the exact timestamp
  to fix. Plus a documented visual-density playbook: text pops, count-ups, and PiP "evidence
  inserts" (real screenshots of the company/article a claim names, receipts + pattern
  interrupt in one).
- **The virality-psychology lens** (`references/virality-psychology.md`): why things get
  watched, held, shared, and copied, ending in a 5-question scoring checklist. Every script
  now carries a `psych` field naming the principles it fires; QA fails anything generic.
- **The two-question gate.** Every script must be entertaining INSIDE your niche (insider
  material, not anyone-with-a-pulse funny) or teach something usable. Neither = killed and
  replaced, no matter how good the mechanic.
- **Early-signal trend detection.** The weekly sweep now has a hard 14-day freshness gate and
  bans peaked-roundup sources; every digest opens with "3 rising signals" presented as shells
  with your transferred version. Plus a mid-week **hot drop** trigger for same-day takes.
- **Trend creation.** Named recurring formats per lane and a coined-terms pipeline
  (`references/coined-terms-template.md`): name the problem your audience feels, plant the
  exact term weekly, own the vocabulary.
- **Feedback without the spreadsheet.** The zero-admin default is the outlier flag (tell it
  when a video pops, it autopsies the winner and writes variations); the 2.1 performance
  export stays as the opt-in data mode, and it never nags.
- **Mode B + SFX scripts now actually ship.** `brollcut.py`, `vo_guide.py`, `storyfull.sh`,
  `gen_sfx.py`, and `sfxmix.py` were documented but missing from the plugin; they are now
  bundled, including a fix for SFX mixes without a music bed.

## What's new in 2.1

- **Your data now lives in a workspace outside the skill folder** (default `~/outlier-radar/`):
  config, weekly script batches, dashboard, carousels, performance exports. Plugin updates and
  reinstalls never touch it. Override with `OUTLIER_RADAR_HOME` or `--dir`.
- **The performance loop.** A new "Export performance" button on the dashboard saves what you
  filmed, posted, and the views you got; the next weekly run reads it and biases the batch
  toward the mechanics and facets that actually worked. The engine now compounds.
- **Verified research only.** Every outlier and inspiration item must be a real post at a real
  URL, and every metric carries a `verified` / `reported` / `estimated` confidence tag. If it
  can't be sourced, it gets dropped, not guessed.
- **Bundled hook library.** The 15 hook pattern families ship with the skill
  (`references/hook-library.md`), so `text_hook` writing has its source material on any install.
- **Example week included.** A fresh install renders a sample dashboard immediately; it
  disappears as soon as your first real week exists.
- **Carousel builder is fully yours.** Name, colours, and fonts come from the `brand` block in
  `radar-config.json` (neutral defaults without one), and Chrome/Chromium is auto-detected on
  macOS, Linux, and Windows.
- **Day-in-the-life beats render on the dashboard** as a film-this table (role, VO line, b-roll,
  duration) so Mode B scripts are usable straight off the card.

## What's new in 2.0

- **Redesigned dashboard** (dark by default, with a light/dark toggle): Inter + Geist
  Mono, pill tabs with live count badges, and a clean card layout. Lane labels and an
  optional "in partnership with X" credit are config-driven via `radar-config.json`.
- **Bundled Outlier Radar + dashboard** with the editor (this used to be the editor alone).
- **Discovery-driven and creator-agnostic** research: any niche, not one person's.
- **Dashboard read laid out like a script:** HOOK (bold) / SCRIPT (one sentence per line) /
  CTA (optional).
- **CTA is optional by default.** Watch-through is the metric a short-form algorithm rewards,
  and a "follow for more" tacked on after the payoff is exactly where people drop, so the
  default is to end on the payoff.
- **On-screen hook can never be cut off.** The caption engine measures the real rendered
  width with your font and auto-wraps + auto-shrinks the hook to a title-safe size.
- **Automatic stutter/restart catching.** A detector flags repeated words and restarted
  clauses from the transcript so they never ship, and gates the build.
- **Long clips are mined end to end** in Mode B: every distinct action in a long take is
  treated as its own usable shot.

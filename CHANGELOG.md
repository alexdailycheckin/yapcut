# Changelog

Release notes for [YapCut](README.md), newest first.

## What's new in 3.11.1 (outlier-radar)

**`build_dashboard.py --strict` judges the newest week, not history.** The first strict build
in a mature workspace refused on 17 weeks that predate gate stamps, so the flag could never be
used where it mattered. It now refuses only when the newest shown week has no current passing
stamp, and warns about the rest.

**The accent floor in `visual_lint.py` is opt-in.** It counted warm red and orange pixels by a
fixed rule, so a cover rendered in a creator's current palette failed with 0.0% while looking
right. It now runs only against an accent the asset declares (`visual.accent` next to
`visual.path`; `radar_gate.py` passes it per render as `--accent`). No declaration, no accent
floor. The four legibility floors (luminance, contrast, edge against the feed, flat share)
always run, because they measure whether the asset survives the page rather than a taste.

**`build_pack.py` polish.** Shot beats that already carry a number are not numbered twice, and a
source label that already ends in its date does not get the date appended again.


## What's new in 3.11.0 (outlier-radar)

**Fewer gates, and the ones that stay guard the record rather than the writer.** After fourteen
weeks of answering every rejected batch with a new check, the engine carried close to ten
thousand lines of gate code and the creator's verdict on a batch had not moved: a writer
learns a floor, so a batch cleared every cadence distribution and still read as prose. The
distribution rules (sentence stdev, the long-run share, the p90 tail, the marker rate,
first-person presence, the opening clash) are OFF by default in `check_fidelity.py`,
`spoken_lint.py` and `radar_gate.py`. `--cadence` turns them back on as warnings and
`--strict-cadence` makes them fail. The categorical checks stay: schema, ids, sources, the
belief and its order, the word ceiling, rejected phrases, the epigram, a candour marker on an
empty clause.

**The brief opens with what the creator said yes to.** `voice_brief.py` now prints the last
three approved scripts first: anything with a `filmed`, `posted` or `approved` event in
`performance/tracking.jsonl`, or marked `qa: passed`. For fourteen weeks the brief listed
rejections and no approvals, so a writer learned what to avoid and nothing about what to do.
Filmed counts as approved.

**One item, one subject.** A `research` item whose `company` is set must name it in the
title, and its embedded twin must mention it, or the item fails. A secondary-lane item whose
title or hook names a primary episode's company fails: one story, one lane. Both were learned
from a week where two episodes were swapped in place, kept their ids, and shipped a new
script over an old twin, POV beat and subject. The playbook now says it plainly: a subject
that changes gets a new id.

**The filming pack is rendered, not typed.** `build_pack.py --week weeks/<date>.json` writes
`show/<date>-filming-pack.md` from the week file, full read, shots, sources and LinkedIn text.
`radar_gate.py` gains a `pack` gate: a pack older than its week file, or naming an episode no
item carries, fails. The routine builds the dashboard with `--strict`, so a failed stamp never
reaches the page looking green.

**Smaller cuts.** `hook_lint` no longer warns on missing `text_hook_alts`. `completeness` warns
instead of failing on an empty `inspiration[]` and no longer asks for an `experiment` block.
`ammo[]` accepts `round` as the fact key. A post or twin whose `proof.kind` is `own` carries
the creator's own figures and needs no URL for them. `select_linkedin.py` gets a real argument
parser and `--dry-run`; before this any unknown flag, `--help` included, ran the selector and
rewrote the latest week file. The word-ceiling gate keeps its fail and drops the "no room
left" warning band, which invited trimming to the line.

**The playbook is a third shorter and opens with the three jobs:** understand the creator from
the onboarding, learn them more every week from what they film, post and kill, and write ideas
good enough that they want to film them. The measurement loop is a log until the creator says
a post was incredible; then it gets an autopsy. Before adding a rule, delete one.


## What's new in 3.10.4 (outlier-radar)

**The length ceiling is a gate now, because as prose it rotted.** The show doctrine has
carried a spoken-word ceiling since 2026-08-19 and nothing in this engine had ever counted a
word. The 2026-09-20 batch shipped episodes at 242, 228 and 202 words against a stated 189,
which is 70 to 83 seconds against a 65-second format. A rule with no gate is a suggestion,
and this one had been one for a month.

`check_fidelity.py` now fails a `research` item over the ceiling and warns inside the last
3% of it, and the failure says to cut by deletion, since a word budget is satisfied by
removing words rather than by writing different ones. The numbers live in
`radar-config.json` under `show.word_ceiling` and `show.words_per_second`, because they come
from a measured delivery rate rather than a universal truth; without a config they default
to 189 and 2.9.


## What's new in 3.10.3 (outlier-radar)

**A candour marker on an empty clause now fails the spoken gate.** The creator flagged
"crawling is free, and honestly it's always been good for you" as a machine tell, and
the marker is not what is wrong with it. His own to-camera speech runs candour markers at
about 16 per 1000 words and the show doctrine asks for them. The defect is placement: the
clause after the marker held no number, no name and no object, so the adverb was buying
warmth the sentence never earned and telling the listener how to feel instead of giving them
anything.

`sincerity_tag` fires only when all three are true: a candour marker is present, its clause
is a copula plus an evaluative adjective, and the clause carries no digit and no proper noun.
Checked against his real lines, it leaves them alone: "they're just honestly tired of these
bullshit tools" passes on the real claim, "it didn't go great because Product Hunt's an
asshole" passes on the proper noun, "Honestly, 37% of them reprice" passes on the number.

**This one is a doctrine backfire and it is worth naming.** `the-show.md` set a marker RATE
on 2026-09-18 with no rule about where the marker lands. A rate with no placement rule is a
quota, and a quota gets filled with empty clauses. The doctrine now carries the placement
rule next to the number: a marker rides a clause that carries a fact, or it does not go in.


## What's new in 3.10.2 (outlier-radar)

**A stated emotion has to carry its cause, and the fix is never to cut the emotion.** A script
ended on "It just annoyed me" and the creator's note was that the line only works if it says
why: "because it's that smart". The instinct on a bare reaction is to delete it, because a
stated feeling looks like filler next to a fact. That instinct is backwards. What is missing
is the cause, not the feeling, and the version with both lands harder than the flat version
would have.

`the-language-layer.md` now carries the rule next to "Name the feeling before the fact",
which was the closest existing guidance and only covered labelling the VIEWER's feeling, never
the creator's own.

Also recorded, as a workspace-level rejection rather than shipped doctrine because it is a
phrasing and not a principle: the lesson-announcement family. "because it's the actual lesson
here" is the same move as the three takeaway openers retired in 3.4.x, wearing different
words. The tell is that the sentence after it already IS the lesson, so the clause only adds
a label.

## What's new in 3.10.1 (outlier-radar)

**The blind read was measuring form, not voice, and scoring 16 out of 16 for it.** The spoken
lane sampled `corpus-work-spoken.txt`, which in a mature workspace is sales calls. So every real
passage on the sheet was a fragment of somebody being interrupted, complete with false starts and
dangling clauses, and the generated side was a finished script. A judge separating those two is
separating a meeting transcript from a script. It can do that perfectly, forever, at any writing
quality, and the engine was reporting the result as a verdict on the writing.

The spoken lane now prefers `corpus-monologue-spoken.txt` when the workspace has one (3.10.0),
because a script is a monologue. The sheet also prints both sides' form and subject, and raises a
CONFOUND banner when they differ:

    real side:      corpus-monologue-spoken.txt  (form: monologue, subject: ...)
    generated side: the week's scripts  (form: monologue, subject: on-subject)

Two confounds are named explicitly. A dialogue corpus against a script is separable on form. A
personal-register monologue corpus against on-subject scripts is separable on topic. Both produce
a high score that means nothing, and a workspace with no monologue view is told so before the
judge ever runs.

**What this exposes is a supply problem, not a scoring problem.** The clean test needs the
creator speaking a monologue about their own subject, and most workspaces have neither: calls
give the subject with the wrong form, personal video gives the form with the wrong subject.
Roughly twenty minutes of the creator talking to a camera about their actual subject, filed
`register: work` and `form: monologue`, is the whole fix, and that one file serves as both the
target corpus and the blind-read comparison.

## What's new in 3.10.0 (outlier-radar)

**Form: a script is a monologue, and the brief now knows the difference.** `targets.json` is
derived from the work-spoken register, which in a mature workspace means sales calls and
conversation extracts. That is the creator TALKING TO SOMEBODY. A show script is the creator
alone with a camera, and measurement says those are two different speakers:

    monologue to camera   3,561w   cut-off 0.0/1k   um-uh  7.3   like 11.8
    dialogue on calls     9,733w   cut-off 10.0/1k  um-uh 18.1   like 27.4

So every brief has been serving conversation marker rates to somebody writing a monologue,
roughly a factor of two off, and the error was invisible because the rates were correctly
measured, just measured on the wrong speaker.

A source file can now carry `form: monologue` or `form: dialogue` alongside its register
header. `segment_corpus.py` builds `corpus-monologue-spoken.txt`, a derived VIEW pooling every
spoken monologue whatever its register, on the principle that subject does not transfer across
registers but delivery physics does: a personal-register video is admissible evidence for how
somebody sounds and inadmissible as a passage to imitate. The view is rebuilt from sources
every run and never merged, because it is a projection rather than a place anything is filed.

`derive_voice_targets.py` reads it into a new `delivery` block: marker rates, doubled words,
um and uh, and cut-off words. `voice_brief.py` prints those as the target and demotes the
conversation rates to a labelled contrast.

**Cut-off words are now measured and banned.** `be-`, `yo-`, `i-`. They run 10 per 1000 words
in conversation and 0.0 across 3,561 words to camera, so they are the sound of being
interrupted rather than a feature of anybody's delivery, and a script carrying one orders the
creator to perform a stutter they do not have. This was the tell that lost a blind read 20 out
of 20: every real passage on the sheet came from a call.

The default form is `dialogue`, deliberately. `capture/` looks like one voice because it holds
the creator's turns only, but a capture is an extract from a call, so defaulting that directory
to monologue would pour conversation into the one view that exists to keep it out. A file is a
monologue when it says so.

A workspace with no monologue source gets no `delivery` block and is told so loudly by both
scripts, rather than silently falling back to the rates that are wrong.

## What's new in 3.2.1 (tiktok-yap-editor)

**A source lower-third is one line, at y=1498.** 3.2.0 allowed two, and two collided with the
caption: build_ass's own meta sidecar puts the caption band at 1220-1420, and TikTok's caption
and username block starts around y=1520, so the usable gap is about 70px. One `fs42` line is
~52px of ink and fits; two need the block bottom at 1544, inside TikTok's chrome. A two-line
source had also stopped being an attribution and become a sentence, which is the thing this
change exists to prevent. Over-length text is truncated with a printed warning, so the fix
stays "write a shorter attribution".

## What's new in 3.2.0 (tiktok-yap-editor)

**The source lower-third is readable on a phone and stays out of TikTok's chrome.** It used to
be one `fs34` Space Mono run pinned at y=1500. Measured on a burned frame, Space Mono at that
size runs about 19.2px per glyph, so a 50-character attribution was ~960px wide and crossed
x=900, where TikTok's action rail sits; y=1500 is also inside the band TikTok's own caption and
username block can cover. So a source line now sizes up to `fs42`, wraps at 34 columns to a
maximum of two lines, and the block finishes at y=1430. An over-long line is truncated with a
printed warning rather than silently shrunk, because the fix is a shorter attribution, not
smaller type.

Audited against a real eight-episode batch first: 28 of 37 source lines were too wide, and
several named nothing at all, which is the tell that they were written to fill a retention gap
rather than to attribute a claim.

## What's new in 3.9.6 (outlier-radar)

**`--strict` now requires the bucket to rebuild.** 3.9.5 shipped it global, and within minutes
it dropped 19,970 hand-filed words of banter and personal corpus while the intent was to clean
one bucket. Turning guard 2 off is correct after a quarantine and catastrophic anywhere else,
so the scope is mandatory: `--strict work-typed`, a comma-separated list, or `all` said out
loud. Every bucket not named keeps guard 2. Run with no argument and it prints what it would
destroy instead of destroying it.

## What's new in 3.9.5 (outlier-radar)

**`segment_corpus.py --strict` rebuilds from source files alone.** Guard 2 keeps any line in
an existing `corpus-*.txt` that no source file reproduces, so a hand-filed line is never
silently lost. The cost surfaced twice on 2026-09-18: removing a source file does not remove
its words, because deleting the source turns its lines from derived into orphaned and guard 2
then preserves them forever. An editorial marker survived every rebuild that way, and then
three quarantined files kept 449 words in the corpus after being pulled. Removing a source is
a deliberate act and it now removes the text. Guard 2 stays the default; `--strict` is the
switch to throw after quarantining anything.

**Why this matters more than it looks.** The corpus is not data the engine reports on, it is
the specification the engine writes against, and `voice_brief.py` prints it verbatim into
every script prompt. A word of unknown authorship in there is indistinguishable from the
creator's own voice at the point where it does damage. The 2026-07-26 audit in this workspace
already found 71 of 71 teleprompter reads were the creator reading the engine's scripts, so
measuring them measured the engine; the same trap reopened through a different door.

## What's new in 3.9.4 (outlier-radar)

**The blind test put the creator's own writing on the generated side.** A week file holds what
the engine drafted and also what the creator rewrote by hand: `add_post.py` and the dashboard
editor both write human text into the same arrays. `turing_check.py` treated every item in the
file as engine output. On 2026-09-18 `li-20260917-1` went onto a sheet labelled generated, the
creator read it and correctly said "that's mine", and it was scored as a MISS against him. Its
own `selector_note` said he wrote it. The test was grading him wrong on his own prose, which
makes its verdict worthless in the direction that matters most.

Authorship is data the file already carries, so the sheet reads it. An explicit
`authored_by: creator` excludes an item, and for everything already on disk the free-text
`selector_note` is matched for the phrases that record hand-authorship. Excluded ids are
printed when the sheet is built, so the exclusion is visible rather than silent, and a lane
with no engine-written text left says exactly that instead of building a sheet from nothing.

**Two scoring defects in a row is the pattern worth naming.** 3.9.3 fixed a corpus annotation
that reached a sheet; this fixes a provenance error that reached a score. The blind read is the
only instrument in this engine whose output is a verdict rather than a warning, so a defect in
it costs more than a defect anywhere else. Score against the sheet that was actually read,
check the key's own source attribution, and never re-run `--answers` to score a sheet answered
by hand: that regenerates the sheet first.

## What's new in 3.9.3 (outlier-radar)

**An editorial note reached a blind-read sheet.** `segment_corpus.py` strips a bracketed note
that owns its own line, but not one appended to the end of a line, and guard 2 deliberately
preserves corpus text that no source file reproduces. So a `<- NOT CAPTURED` marker baked in
by an older build survived every rebuild afterwards. On 2026-09-18 it landed inside a passage
of the creator's OWN writing on a blind-read sheet, which made that passage unreadable and
cost a data point in the one test that decides whether the voice work is finished. Trailing
annotations are now stripped too, and inline brackets that are real copy, such as a template
placeholder, are left alone.

## What's new in 3.9.2 (outlier-radar)

**The order test failed correctly placed beliefs.** It measured the belief's position against
every numbered sentence in the hook AND the script. Move 1 is the receipt and it is supposed
to carry a number, so an episode whose hook held two figures put the median at sentence 2 and
a belief sitting at the top of the body failed. Caught on the 2026-09-13 rewrite, twice. The
test now runs inside the script alone, which is where the receipts walk lives and the only
place an order exists to check.

**A belief spoken only in the hook is legal.** The receipt and the belief can share the
opening breath, and there is nothing to order in that case.

**A two-sentence belief now says so.** The field is matched sentence by sentence, so a belief
written as two sentences could never match and reported "not a paraphrase", which is not what
was wrong with it. The message names both causes.

## What's new in 3.9.1 (outlier-radar)

**The voice profile called itself provisional forever.** `derive_voice_targets.py` wrote a
fixed "derived from a THIN corpus, treat every number as directional until the on-target
corpus passes ~4000 words" note whatever the corpus actually held, so a profile measured from
10,000 words of speech still told every reader to discount it. The note is now computed: below
the 4,000-word floor it says how far short the corpus falls and that the fix is speech rather
than arithmetic, and above it says how many sentences and words the numbers rest on. The
`_register` note stopped hardcoding one sample's median and filler rate, which had gone stale
the first time the corpus grew, and states the register rule instead.

## What's new in 3.9.0 (outlier-radar)

**A week of verified facts is not an episode.** The 2026-09-07 batch shipped eight scripts
that passed every gate in this engine and read as a pile of true statistics, and the creator
rejected the whole batch after filming it. The cause traces to 3.4.3, which loosened the show
from six fixed beats to two so that nobody would fill six boxes mechanically. That was the
right problem to fix. The cost was that the beat naming what the viewer already believes
became part of the optional middle, and it went.

**The belief was written. It was in the wrong place.** Four of the five episodes contained the
sentence, placed last: "that was a reasonable test in 2025", "HubSpot did nothing wrong".
Stated after the receipts, a belief is a summary of them. Stated before them, the identical
receipts become a demolition. Curiosity fires on a gap, so a gap opened after the information
has landed is not a gap. Moving one sentence up fixes an episode without rewriting a word of
it, which is why this is a structure defect and not a copy defect.

**The show now runs five moves:** the receipt in frame one, THE BELIEF, the break, the
mechanism, the verdict. Three are fixed and the break is free in order, count and wording, so
3.4.3's point survives. The belief is fixed as a FUNCTION and never as a sentence, so no
spoken catchphrase returns: a phrase forced onto an episode it does not fit spends the opening
line on a promise the episode never keeps. The shape carries the franchise instead. The
first-run interview stops offering a turn line and a takeaway line as defaults, and asks
instead for an episode the candidate phrase would not survive.

**It is a gate, not a paragraph.** This tree has already run the experiment on prose: the
2026-08-28 rewrite rules lived in a filming-pack header rather than in a file that executes,
and the next run could not see them. So `research` items now require a `belief` field, copied
verbatim out of `spoken_hook` or `script`, and `check_fidelity.py` locates that sentence and
fails a week whose belief sits after half the numbers. Verbatim matching is load-bearing: the
first version of the check scored the field against the script by content-word overlap and
passed both bad 2026-09-07 episodes, because a belief's words appear all over an episode about
that subject. The regression test runs it both ways.

**`references/the-language-layer.md` ships.** The spoken-word spec, companion to
`video-scripting-as-a-science.md`, which has shipped since 3.0.0. It sets how every line
sounds: money word last, source attributed before the claim, no mid-sentence clauses, "you"
outnumbering "I", and the spoken filler KEPT, because a written-copy standard cuts filler on
sight and in speech that filler is the texture of a person thinking in real time. Nothing
referenced it until now, which is how a 17KB spec goes unused for two months.

The dashboard marks the belief in place inside the read, because where it sits is the thing
worth seeing.

## What's new in 3.8.4 (outlier-radar)

**The dashboard showed a post body it could not change.** The week file holds what the
selector wrote. What actually gets posted is edited right up to the moment it ships, and
the page rendered `body` read-only, so the tracked text drifted from the published text
and the ledger measured a post nobody sent. Every LinkedIn card now has an Edit button.
The edited body joins the tracked record beside status and link, so it survives a reload,
overrides the embedded text everywhere the page reads it, and carries a marker until it
reaches disk.

**Export gained Save week file.** The page is a file:// document with no server, so the
edits are rebuilt into the week JSON and handed to the filesystem: written in place
through showSaveFilePicker on Chromium, downloaded to drop over `weeks/<week>.json`
everywhere else. Either route means the next `build_dashboard.py` inherits the creator's
text rather than reverting it. Revert to week file undoes an edit without hunting for the
original.

## What's new in 3.8.3 (outlier-radar)

**A post the sweep did not commission had no way into the week.** Anything built outside the
weekly run, a deck from a one-off question or a reaction to something that landed on a
Wednesday, could only reach `linkedin[]` by hand. A `linkedin[]` item carries 25 fields and
the dashboard is keyed on `id`, so a near-miss does not error: the card renders without
tracking, or drops out of the lane silently. `add_post.py` is the one supported door. It
appends a schema-valid item, records in `selector_note` that a human put it there, and
refuses a duplicate id.

**Built assets were invisible from the page that decides what to post.** The dashboard is
where the creator picks the week's posts, and the deck those posts ship with lived in a
folder they had to go hunting for. Week files carried a path anyway: a bare `carousel`
string on some items, `visual.path` on others, hand-written over about a month and read by
nothing. Posts now render an Assets block with a `file://` link and a copyable path, from
the canonical `assets` field and from both of those older shapes. Relative paths resolve
against the workspace root, which `build_dashboard.py` now passes to the page.

## What's new in 3.8.2 (outlier-radar)

**A drawn initial reads as a placeholder beside a brand that owns a mark.** `carousel.py` built
the `brand_header` chip by taking the first letter of the label and setting it in a rounded
square. That was right while the kit shipped neutral and wrong the moment a deck carried real
artwork, because the card then advertised a logo the brand does not use. `brand_header` now
also accepts `{"logo": path, "height": N, "y": N}` and pastes the artwork centred at the top.
A string still draws the old chip, so no existing spec moves. A reversed lockup needs a dark
band behind it and the script does not check for one, because the band colour is the spec's
call, not the renderer's.

**The footer baseline was hardcoded at 128px from the bottom of the card.** On a framed card
that left the byline avatar 5px off the frame line, which reads as a crop rather than as a
margin, and no spec could reach it. It is now `footer_baseline`, defaulting to 128 so every
deck already shipped renders identically.

## What's new in 3.8.1 (outlier-radar)

**A tracking row the engine cannot read is worse than a missing one.** `tracking.jsonl` is
written by `log_perf.py` and keyed on `event` (filmed, posted, ignored). Write it by hand with
some other key and nothing errors: the report still prints its counts, all zeros, which reads
as "nothing shipped" rather than "this file is in the wrong shape". That is exactly what
happened to one week's batch, hand-written with a `state` key. Eighteen rows went unread, two
posted posts showed as queued, and the miss survived a full weekly run because the only signal
was eighteen identical warnings nobody reads to the bottom of.

Both readers now name it instead:

- `log_perf.py --report` counts the rows it could not read, says they are invisible to the
  report and to the dashboard, lists the keys they actually carry, and prints the three
  commands that write the file properly.
- `build_dashboard.py` collapses the per-row wall into one warning with the count, the first
  few line numbers and the same key list, and says what the consequence is: that work renders
  as queued on the page.

Neither guesses. A `state` key is not silently mapped onto `event`, because a reader that
repairs a broken writer hides the broken writer.

## What's new in 3.8.0 (outlier-radar)

**The renderer can draw.** It knew four shapes: a headline, a paragraph, a stat row and the
byline avatar. That is why every deck read as text on a background no matter how good the
background got. Added: `panel()`, `bar_chart()` and an `icon()` set, drawn from the design
tokens rather than pasted in as assets, and driven by figures already parsed out of the
script, so nothing new has to be written for them to fire.

**Two parser bugs that were silently flattening data pages:**

- `split_sentences` could not split before a DIGIT. The lookahead accepted an uppercase
  letter, a quote or a currency symbol, so "48% run hybrid. 35% have a consumption component.
  18% charge on outcomes." parsed as ONE sentence. A creator with a numeral law writes
  sentences opening with numbers constantly, so this flattened exactly the pages that most
  needed splitting.
- `NUM_RE` dropped the percent sign. Its unit group was followed by `\b`, and no word boundary
  exists between "%" and a space, so every percentage in the deck parsed as a bare number.
  That also made percentages look unit-less, and therefore comparable to bare counts.

**A chart has to earn the axis.** Same unit is not the same as comparable: in one script "67%"
is a price rise, "37%" is a plan to reprice, and "48 / 35 / 18%" are shares of one pie. Bars
now require an EXPLICIT shared unit and CONSECUTIVE sentences, because a writer listing
comparable quantities puts them next to each other. A chart that puts unrelated figures on one
axis does not just look wrong, it asserts something false, and more confidently than the prose
did.

## What's new in 3.7.2 (outlier-radar)

**The stat table now actually fires, and its labels read.** 3.7.1 shipped `stat_rows()` and it
never once triggered. Three separate faults, each found only by rendering a real deck:

- It bailed on any sentence carrying two figures, and a real data page is full of them
  ("It runs a $70 million revenue rate with about 650 employees"), so nothing ever qualified.
- The decision was made per 2-sentence chunk, after grouping. A data run is a property of the
  argument, so it is now found across the whole body BEFORE chunking.
- The run gate allowed at most one non-numeric line. The first real data page had two
  interjections and failed by exactly one. It is a ratio now.

Then the labels themselves were wrong, in the same way the cover headline was wrong before
3.6.4: built by cutting the figure out of the sentence, which left "The company is months old"
and "Roughly of revenue per employee". A stat row reads "20 / months old", so the label is the
UNIT PHRASE after the figure. Trailing function words are trimmed, a label opening with a
conjunction is rejected as prose, a comma ends the label, and a figure that appears twice
renders one row.

## What's new in 3.7.1 (outlier-radar)

**A data page now renders as a table instead of five equal sentences.** `stat_rows()` detects a
chunk where most sentences carry exactly one liftable figure and lays it out as label/value
rows. Before this, "20 months old / $70 million revenue rate / 650 employees / roughly
$108,000 per employee" shipped as prose and made the reader do the arithmetic the card exists
to do for them. On a data page the layout IS the argument.

**Three fixes that had shipped on every deck ever built:**

- **Blank kickers on interior slides.** The cover, the lesson and the close all had one and the
  middle had none, so the header flickered on and off as you swiped.
- **"Reframe:" on the lesson card.** The prefix stripper only matched ALL CAPS, so any
  sentence-case field label went straight to print.
- **"Your move. Save this. Then go use it this week."** The stock CTA the creator's own gates
  ban, hard-coded as the default close on any item without a `cta`. The close now ends on the
  last line of the script, which is the payoff the deck was built to arrive at.

**The dashboard shows LinkedIn formatting instead of hiding it.** 3.7.0 converted markers on
copy, but the preview still rendered the raw body, so bold and arrows were invisible until you
pasted. Both preview surfaces now run through `linkedinText()`.

## What's new in 3.7.0 (outlier-radar)

**Copy now hands LinkedIn text it can actually use.** LinkedIn strips every kind of rich
formatting on paste, so a "copy post" that returns plain text loses whatever structure the
draft had. `linkedinText()` converts markers at copy time: `**bold**` and `*italic*` become
Unicode mathematical alphanumerics, and a leading `- ` becomes the arrow bullet.

Conversion happens on COPY, never in storage. The stored body has to stay real text, because
check_fidelity, spoken_lint and hook_lint all read it, and a body full of Mathematical
Sans-Serif Bold defeats every one of them.

**Use the bold sparingly, and never on a number or the central claim.** Unicode bold is not
text: screen readers announce it as gibberish or skip it, and parsers handle it badly. For a
creator whose subject is AI search visibility that is an own goal, because the sentence you
most want quoted is the one you just made unreadable to the thing quoting it.

**A second carousel skin.** A workspace holding `assets/reach-system/` gets a dark skin: near
black ground, a real `feTurbulence` fractal-noise grain, a soft bloom that alternates sides,
serif display, jewel accent. Opt-in by the presence of those files rather than a config flag,
because the skin cannot render without them and a flag that silently produces an unstyled deck
is worse than no flag. `carousel.skin: "paper"` forces the light one back.

## What's new in 3.6.7 (outlier-radar)

**The posting calendar printed the format instead of the post.** A solo LinkedIn post carries
no `title`, and `calendarBlock` fell through to `x.type`, so the week rendered as a column of
"text", "single-image", "text". A format label never answers "which post is this".

- New `postName()` falls through title, then `text_hook`, then the first line of the body,
  truncated. It only says "Post" when the item is genuinely empty.

## What's new in 3.6.6 (outlier-radar)

**Finishing the cover.** Inverting it in 3.6.5 cleared luminance, edge and flatness but left
2 of 5 checks failing across every deck: RMS contrast 38 to 44 against a 55 floor, accent 0 to
2% against a 4% floor. Two causes, both structural rather than stylistic.

- **Cover type is now 150px, and the stat 210px**, up from the interior body size of 84px. On
  a 1080px frame, 84px is a body size, so there was almost no bright mass to vary against the
  dark ground. The scroll-stop rule is that the subject occupies 40 to 70% of the frame, and
  on a text cover the type IS the subject.
- **A full-width accent block** on the cover supplies the colour mass. Sized to clear the
  floor even on a deck with no stat to blow up.

Measured after: all 4 decks pass all 5 checks, RMS contrast 61 to 70, accent 9 to 14%.

## What's new in 3.6.5 (outlier-radar)

**Every carousel this renderer has ever produced failed the feed floor on its cover, and
nothing caught it.** Measured 2026-09-10 across 4 freshly built decks: mean luminance 242
against a 200 ceiling, near-flat frame 94 to 97% against a 55% ceiling, accent coverage under
1% against a 4% floor, RMS contrast 36 to 46 against a 55 floor. Five checks out of five,
every deck.

Two failures stacked to hide it. `visual_lint` was handed the PDF the renderer emits, could
not decode it, and raised `PIL.UnidentifiedImageError` instead of failing the asset, so the
cover was never graded. And a cream card with black type looks correct in isolation, which is
how it survived every human review.

The creator's own numbers agreed the whole time: his carousels ran a 581 median impressions
against 880 for text over 19 posts. The format was never the problem. The cover was.

- **Slide 1 now inverts:** ink field, paper type, accent on the stat and the swipe cue.
  Interior slides stay light, because they are read after the swipe rather than scrolled past.

## What's new in 3.6.4 (outlier-radar)

**The carousel cover cut numbers out of the middle of sentences.** The cover lifted the first
number it found into the big accent slot and rebuilt the headline from the two halves either
side of it. When the number sat mid-sentence, the headline shipped with a hole in it:

- "Two AI studies disagree by 39 points." rendered as **"Two AI studies disagree by points"**
- "Wonderful sells engineers. The market paid $5 billion." rendered as **"Wonderful sells
  engineers. The market paid"**

Both reached PDF on 2026-09-10 before a human read a cover.

- The number is now lifted only when the hook LEADS with it, which is the only position where
  removing it leaves a clause that still parses. Any other position renders the hook whole.

## What's new in 3.6.3 (outlier-radar)

**The carousel byline never used the author block.** `radar-config.json` has carried
`carousel.brand_author` with `{name, org, photo}` since 2026-08-14. `build_carousels.py` read
none of it and rendered a platform glyph plus a bare name, so every deck was visually
interchangeable with any other deck built from the same template.

- The byline now renders the configured photo as a circular avatar, with the name and the org
  stacked beside it. The photo is inlined as a data URI so the deck stays self-contained, the
  same rule the LinkedIn mark already followed.
- No `brand_author.photo` configured falls back to the platform mark and prints why, rather
  than silently shipping a bare name.

## What's new in 3.6.2 (outlier-radar)

**The same blind spot, the other half of English.** 3.6.1 taught `has_verb()` third-person
present after a PERSONAL pronoun. Indefinite pronouns were still missing, so "One counts visits
to the platforms. The other counts the clicks those platforms send back out." scored as a
verbless run at HIGH severity inside a day of shipping the first fix.

- `has_verb()` now covers one, another, other, nobody, somebody, someone, everyone, anyone,
  each, both, all, most, none, everything, nothing, something.
- Re-verified against the fragment set: 3 false positives cleared, every genuine verbless
  fragment still fails.

## What's new in 3.6.1 (outlier-radar)

**`spoken_lint` could not see the present tense.** `has_verb()` tested a closed verb list,
contractions, and `-ing` / `-ed` endings. Third-person singular present matched none of those,
so "It opens a browser, fills in the forms, sends the emails and checks out" scored as a
`verbless_list` at HIGH severity despite carrying 4 finite verbs.

That is the expensive kind of lint bug. A missed detection costs one warning. A false FAIL
costs a correct sentence, because the writer rewrites a good line to satisfy a gate that was
wrong, and the batch gets worse while the table goes green.

- `has_verb()` now also accepts a subject pronoun followed by a word ending in `-s`.
- Verified against the 11 known fragment cases: exactly one changed, the false positive.
  Every genuine verbless fragment ("30 mins, no deck.", "Short one, promise.", "Bigger
  budget, smaller team, same target.") still fails.

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

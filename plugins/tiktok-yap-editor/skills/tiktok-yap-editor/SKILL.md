---
name: tiktok-yap-editor
description: "Turn raw phone clips into finished, captioned vertical video for TikTok, Reels, Shorts and LinkedIn. Use for make a tiktok from these clips, caption this, tighten this yap, turn this footage into a post, add subtitles, day in the life edit, script my voiceover and cut my day clips, add SFX or music, or a dropped folder of .MOV or .mp4 clips. Mode A cuts a talking head to the words said; Mode B locks picture to a scripted voiceover. Not for AI-generated video or static images."
---

# TikTok Yap Editor

Turn raw phone clips into a finished vertical short. Bias toward shipping a clean, tight,
captioned clip that serves the channel, not technical perfection.

Two parts. **Part 1 is the editorial judgment** (which take, what story, what goes on screen,
where to stop) and it is where the video is won or lost. **Part 2 is the pipeline**, which is
deterministic, gated, and lives in bundled scripts. Read Part 1 before you cut anything. When
a pipeline step and an editorial rule pull against each other, Part 1 wins, because a gate
that passes on an illegible video has measured the wrong thing.

## Two modes (pick one before you start)

- **Mode A: talking-head yap.** The creator yaps to camera; audio leads, picture follows.
  Transcribe, build a premise-first story, cut the footage to the words actually said
  (`yapfull.sh`).
- **Mode B: VO-to-picture storytelling.** Loose b-roll with no usable on-camera speech;
  picture leads, voice follows. Script the voiceover beat by beat, lock picture to it
  (`brollcut.py`), burn a record-to-picture guide (`vo_guide.py`), then lay the VO in and
  finish (`storyfull.sh`, which runs the same gates as Mode A).

Pick the mode from what the footage is. Short form targets 25 to 40 seconds; long form 60 to
90, with a mid-point re-hook past 90. Per-platform bands live in the brand config.

## First run: brand discovery (once per creator)

Look for `brand-config.json` in the workspace (`$YAPCUT_HOME`, else the folder holding
`radar-config.json`, else `~/outlier-radar/`), then in the footage's `.yap_build/`. Never in
the skill folder. If missing, interview with `AskUserQuestion` and write the workspace file
from `brand-config.example.json`:

1. **Niche** (one line) and **pillars** (2 to 4).
2. **Caption font and case**, **accent**, **base** and **ink** colours.
3. **Handle** and **contact lines** for the CTA block; **CTA style** (off by default: end on
   the payoff; a spoken outro clip only when the reason to follow can land before attention dies).
4. **Platforms**: which of TikTok, Reels, Shorts, LinkedIn they post to. Each has a length band
   and a hook animation (LinkedIn: static first frame, since it autoplays muted). The example
   config carries defaults.
5. **Series**: the franchise name (the cover kicker), the question template, a mark file if
   they have one, the pillars. Recognition is the same name and mark repeated until the
   audience spots the show in a grid.
6. **Reference accounts** to study.

The fonts must be installed (`preflight.py` checks). The brand is data, never hardcoded.

# Part 1: Editorial. This decides whether the video is good.

The pipeline in Part 2 is deterministic and it will happily produce a technically
clean video nobody watches. This part is the judgment no script can make. It
binds both modes.

**The law: nothing goes on screen that a stranger cannot decode in one second.**
Every rule below is that law pointed at a different surface. A cutaway that needs
explaining fails it. A hook that wraps to four lines fails it. A logo burned over
the caption fails it. Cleverness the viewer cannot see is noise.

**Precedence, when two rules pull against each other:**

1. **Legibility.** A weak cutaway is worse than staying on the face.
2. **Story.** A beat that breaks the premise comes out, even when it is the best
   take you have.
3. **Retention.** Density serves the story. The story does not get rearranged to
   feed a gate.
4. **Polish.**

A retention gate demanding a visual event at 14s does not license a cutaway that
fails the one-second test. Use a punch-in and move on.

## Premise first, always

The creator supplies the takeaway in one sentence. You build the storyline. If
they have not given you one, ask before you cut anything, because a story built
backwards from a transcript is just a list of things they said in the order they
said them.

Inventory every usable fragment with its source and timestamp. Tag each one with
a role: HOOK, STAKES, ESCALATION, TURN, EVIDENCE, BUTTON, CUT. (Mode B uses its
own shorter role set, see B1.) Pick a shape (confession to cost to reframe;
contrarian to proof to implication; before and after; problem to insight to
payoff; list with a turn). Write the ordered line sequence before you touch the
footage.

Lead with the sharpest line even when it sits ninety seconds into the take.

Then test it. Does line one open a loop? Is the sharpest line first? Is there an
escalation and a turn? Does the button pay the loop? Is it one idea? Present the
beat sheet and get a yes.

## The shape

1. Cold open on the sharpest, most honest fragment. Never "hey guys".
2. A burned on-screen hook, around six words, for the majority watching muted.
3. A visual interrupt in frame zero.
4. Three to five loose points.
5. One closing line, then a hard stop or a loop.

Short-form runs 25 to 40 seconds. Long-form runs 60 to 90, and past 90 it needs a
mid-point reset (a new sub-hook line) or it sags. Tag each video to a pillar.

**The spoken CTA is off by default.** Watch-through is the metric the algorithm
reads, and a "follow for more" tacked on after the payoff is the exact frame
where people leave. It costs around nine seconds. Spend them only when the reason
to follow is strong enough to land before attention dies. End on the button.

## The line audit is editorial, not QA

After the cut, read the line sequence back as a story. Two things kill it and
neither one trips a gate. Reordering creates contradictions the original take
never had. Restart-heavy phone takes double their phrases, and while
`stutter_check.py` catches the literal repeats, you catch the ones that use
different words to say the same thing twice.

Do this every time, including when it sounds fine.

## Cutaways earn their place or stay off

Match the LINE to what the clip actually shows, never to a metaphor that needs
outside knowledge. Three legal matches, strongest first:

1. **Literal.** The clip shows the thing the line says.
2. **Speaker-action.** The creator is visibly doing what the line describes.
3. **Neutral motion.** Register-matched movement under a purely conceptual line,
   and only when the retention gate demands an event there and no literal shot
   exists.

If the connection needs explaining, it fails, however clever it is. When nothing
passes, stay on the face and use a punch-in, a text pop, or an evidence insert.

Register gates it too. Holiday footage under a work argument reads as a vlog,
unless the take itself was filmed in that context and the line is about
lifestyle, reward, or people.

## Density and receipts

One event per beat, not per word. In order of preference: a real cut, then a PiP
evidence insert, then a number count-up, then a source lower-third, then a
caption emphasis pop, then a punch-in. SFX hits land on those events and never
between them. Under-season it. Sound is seasoning, not the dish.

**Every spoken brand, stat or quote gets an on-screen receipt.** The mechanics,
the receipt hierarchy and the `pip_coverage.py` gate live in Part 2. The
editorial half is simpler: assign the receipt to the claim while you write the
story, not after the cut. A script that names a claim with no capturable receipt
gets rewritten now, not discovered at compose.

Real footage and real screenshots only. No AI-generated visuals anywhere.

## The words

Two rules carry most of it.

**Speak so that someone with zero prior knowledge follows it.** One gloss and one
metaphor per video, maximum. Video has no scroll-back, so a viewer who loses the
thread does not recover it. A gloss that explains jargon with more jargon is not
a gloss.

**Write it the way you would say it out loud.** Read every line aloud before it
reaches the clauses file. If you would not say it to someone's face, it does not
get said to camera.

Never use em dashes or en dashes, on screen or anywhere else. Commas and colons.

## Before it ships

- Did the creator give you the takeaway, and did they approve the beat sheet?
- Does the sharpest line open the video?
- Would a stranger connect every cutaway to its line in one second?
- Does every spoken claim have a receipt on screen while it is spoken?
- Does it end on the button?
- Is there anything on screen you would have to explain?

---

# Part 2: The pipeline

## Folder convention (non-negotiable)

Working files go under `<footage>/.yap_build/`. Finals land in a per-run subfolder named after
the footage folder (`output/<footage-folder-name>/<name>.mp4`) with a cover beside them, and
`finalize.sh` writes `<name>.edit.json` there: the decision record (clauses, hook, gates,
platform, radar id) that joins the cut to the post. It no longer deletes the working
directory by default; `--wipe` does.

## The sequence is locked

One video walks every step before it is done, sequentially, never a batch ahead of the gates.
`yapfull.sh` (Mode A) and `storyfull.sh` (Mode B) both source `scripts/gates.sh`, which runs
every gate and records each result in `<workdir>/<out>_gates.json`. Exit codes: 0 pass, 1
warning (printed, the build continues), 2 fail (the build stops and the gate names its fix and
its override variable). Never set an override to turn a red gate green; each one exists
because of a shipped defect (why: `references/gotchas.md`, CHANGELOG).

| Step | You write | You run | A red gate means | Details |
|---|---|---|---|---|
| 0. Preflight | | `preflight.py` (once: `setup_fonts.sh`) | apply the printed fix hint | `requirements.txt` |
| 1. Survey | | probe every clip; never pre-judge takes by length | | |
| 2. Transcribe | | `transcribe.sh <clip> <out>` per clip; read all transcripts together | | |
| 2b. Restart-heavy takes | `keep_whole` rows via `mkclauses.py` | `segmenter.py <clip>` for silence-accurate runs | | gotchas.md, "Clause boundaries": use run boundaries verbatim, never auto-fit them |
| 2c. Stutters | `<out>_stutter_ok.json` for deliberate repeats | `stutter_check.py --words`, `restart_scan.py --video` | listen; cut it via the clause plan or record its key. A MEDIUM is a decision, not a note | `references/speech-and-repetition.md` |
| 2d. Footage library | `records.json` (kind, tags, moments, `reads_as`) | `library.py prep`, `upsert`; after finalize `mark-used`, `reconcile --roots` | | `library.py --help`; data in `<home>/footage-library/` |
| 3. Storyline | the beat sheet, with the receipt and the cutaway per line, approved by the creator | | | Part 1 |
| 4. Clause plan | `clauses.json` with boundaries taken from a window re-transcription, never a full-file transcript | `transcribe.sh` on a trimmed window | | gotchas.md, "Boundary placement" |
| 5. Cut | | `yapcut.py` (flags fixed in yapfull.sh; `--grade` rides inside the segment pass) | black frames are a canary; `seam_qa.py` is the fatal check | "Why yapcut", CHANGELOG 2.3 |
| 6. Gates | `<out>_script.txt` (scripted runs), `<out>_corrections.json`, `<out>_capqa_ok.json`, `<out>_overlays.json` | inside `yapfull.sh`: hook words, stutter and restart, dead air, caption, seam, receipts, retention (with `--keeps`, so pause cuts do not count as events), drift, frame zero | the gate prints the fix and its `YAP_*` override; a scripted run with a garbled caption fixes it in corrections and reruns with `YAP_FROM_CUT=1` | `gates.sh` header |
| 7. Captions, hook, CTA | the hook (9 words or fewer, first line static at frame zero) and the spark word | `yapfull.sh <workdir> <clauses> <out> "<hook|line two>" "<spark>"` | hook too long: cut words, never shrink type | `hook_styles.py` for a designed hook |
| 8. Compose, receipts, cover | `<out>_overlays.json` pip entries; cover title and kicker (from `series`) | `compose_ass.sh`, `burn_pips.py` (inside yapfull), `cover.py --video <caption-free cut> --contact-sheet`, then `--frame N --title` | loudness is measured and printed; check the line | `references/receipts.md`, 8c below |
| 8b. Variants and platforms | a second hook | `hook_variant.sh <workdir> <clauses> <out> "<hook B>" "<spark B>"`; `YAP_PLATFORM=linkedin yapfull.sh ...` re-composes from the cut | outside the platform's length band: a warning | brand config `platforms` |
| 9. Finalize | the Radar item id, pillar, episode | `finalize.sh <final> <footage_dir> <name> --radar-id <id>` (or `--standalone`) | refuses without an id: the edit record is the point | Contract in the script header |
| 10. Measure | | the Radar's `log_perf.py --edits <output dir>`, `--posted <id> <url>` | | outlier-radar SKILL.md |

### Notes that survive from the incident history

- **Boundaries.** Whisper word times drift up to about 2 seconds mid-file. A boundary placed on
  drifted times once swallowed the words "Don't write" while keeping the flubbed take it was
  meant to remove. Re-transcribe a 5-second window around every intended cut.
- **Noisy takes.** If the dead-air gate fails on a cut that should be tight, the cutter never
  saw the pause: room tone sits above the silence gate. Measure the floor, denoise the cut
  intermediate (`afftdn`), rebuild with `YAP_FROM_CUT=1`. Never hand-wave it (6b in gotchas.md).
- **Loudness** is measured, corrected and verified in three passes with no round-number cap on
  the gain; the safety rail is on the input (below -45 LUFS there is no speech to lift).
- **The hook can never be cut off** (build_ass auto-fits), and that is exactly why the word
  gate exists: the fitter removed the constraint that forced the craft decision, and
  twelve-word three-line hooks reported success.
- **Frame zero.** The muted feed judges the first frame. The first hook line is static from
  0.00; only a second line types in. The frame-zero gate fails a build whose first frame
  carries a cursor and one letter.

### 8c. Cover

Candidates from the caption-free cut, never the delivered file (a frame from the final bakes
a caption word into the thumbnail). Eye contact and expression; real frames only. The default
`clean` style sets bone type onto the dark t-shirt under the chin inside the centre 1080x1080
(Instagram's grid crop), sentence case, left aligned, one accent rule; placement is measured
per frame. The kicker comes from the brand config's `series.name` and the mark is drawn only
when `series.mark_png` exists. For a show episode the title is the franchise question, not the
claim hook.

## Mode B: VO-to-picture storytelling

The inverse of Mode A. Same brand config, captions, SFX, cover, finalize, and since 2026-09-09
the same gates.

1. **Survey and script** (Part 1 binds). Probe the clips, get the takeaway, write the beat-by-beat
   VO: one short spoken line per beat with a role (HOOK, CONTEXT, BEAT, TURN, BUTTON) and a
   target duration; hook beat 1.5 to 2.5 seconds, later beats 3 to 4. **Mine long clips end to
   end**: every new action inside a long take is a separate usable shot with its own in and
   out. Persist the contact sheet to the footage library; `moments` carries the timecoded
   per-action shots.
2. **beats.json**: one clip per beat matched on what it literally shows (`reads_as`), the VO
   line and its match written together. `push: true` only where a shot would otherwise sit dead.
3. **Lock the picture**: `brollcut.py --beats beats.json --workdir .yap_build --out .yap_build/picture.mp4`
   writes `picture.timeline.json`.
4. **The guide**: `vo_guide.py --picture ... --timeline ... --out guide.mp4`. The creator plays
   it and reads the lines aloud in time, one voice memo, starting on "1".
5. **Finish**: `storyfull.sh <workdir> <picture.mp4> <vo.m4a|-> <out.mp4> "<hook|line two>"
   "<spark>" [sfx.json] [brand-config] [corrections] [vo_offset]`. Picture length equals VO
   length; chronology reads as day flow; read the full VO aloud once to catch three beats
   starting "so I".

## SFX and music (optional, both modes)

`gen_sfx.py` builds a CC0 pack once (`assets/sfx/`, generated, never shipped). An `sfx.json`
names a bed (`duck: true` sidechains it under the voice) and hits placed from the timeline: a
whoosh on each cut, an impact on the hook word, a riser into a turn, a ding on a stat. Under-mix
it. Mode B passes it to `storyfull.sh`; Mode A runs `sfxmix.py` on the finished clip.

## Retention pass (gates, on the finished file)

Four gates, automated where a machine can see them. **Frame zero** (gate): the full first hook
line at 0.00, mid-action framing. **Re-hook** (gate): something changes on screen between about
2 and 3.5 seconds. **Pattern-interrupt budget** (gate): no stretch over 5 seconds (6 past 60s)
without a visual event, counted after discarding the cutter's own joins. **Loop or button**
(eyeball): the last line hard-stops on the payoff or connects back to the first. A flagged
static stretch is not a licence for a cutaway that fails the one-second test: use a punch-in.
Which lever, and how much, is Part 1, "Density and receipts".

## Receipts

The law, the hierarchy (logo chip, headline card, counter), the placement band (receipt ink
above y=1650, below the caption line, never over the face) and `pip_coverage.py` live in
`references/receipts.md`, shared with the Radar. `evidence_card.py` (`capture`, `quote`, `stat`,
`bars`, `chips`, `timeline`) writes the cards; `logo_fetch.py` fetches and chips a logo. Every
figure on a card is verbatim from the source in its pill.

## Decisions to ask (and proven defaults)

| Decision | Default |
|---|---|
| Which take | The two longest are usually the takes; ask if ambiguous. Never skip short clips. |
| Takeaway | The creator supplies it. If missing, ASK before cutting. |
| Story shape | You build it premise-first, present the beat sheet, get a yes. |
| Caption preset | brand config (minimal, scale-only highlight). |
| Hook | One line if it fits (9 words or fewer), else two with `|`. Second hook as a variant when the platforms differ. |
| Platform | TikTok by default; `YAP_PLATFORM=linkedin` for the ICP lane. |
| Crop alternation | On (masks jump-cut stutter). Off only if the creator dislikes any framing change. |

## When it misbehaves

`references/gotchas.md` (threshold tuning per noise floor, clipped quiet words, seam
hallucinations, the no-libass constraint, voice-picture drift) and
`references/speech-and-repetition.md` (which repeats to cut and which to keep). Read before
improvising.

## Why yapcut

The old flow concatenated auto-editor output and dropped a one-frame black flash at every
jump cut. `yapcut.py` does everything in one clean CFR pass, cuts only at pauses of 0.55s or
more, bridges segments under 0.45s, requires a cut to remove 0.25s to exist, finds edges by
walking the energy envelope out to a measured margin, and paces frames against the cumulative
audio clock so lips never slide off the voice. Zero dead space means zero DEAD space: real
pauses, restarts and stutters go; speech cadence stays.

## Hard rules

Editorial hard rules (no AI-generated visuals, no dashes, receipts on every claim) are Part 1.
Operational: run the batch sequentially in one process and never build ahead of the gates.

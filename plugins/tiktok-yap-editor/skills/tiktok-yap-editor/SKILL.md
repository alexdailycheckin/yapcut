---
name: tiktok-yap-editor
description: Turn raw phone clips into finished, post-ready vertical TikTok/Reels/Shorts videos. Two modes. Mode A (talking-head yap): transcript-first story edit, zero-dead-air jump-cut tightening, word-by-word burned captions in the creator's brand, a burned text hook, an optional spoken-outro CTA, loudness for the feed, QA. Mode B (VO-to-picture storytelling / day-in-the-life): the creator films loose b-roll clips of their day, the skill scripts the voiceover beat by beat, locks the PICTURE to that script at attention-tuned clip lengths, and burns a record-to-picture guide so the creator records the VO later in sync, then lays it in and captions it. Both modes can add an optional SFX + ducked music-bed layer and support 25-40s short-form or 60-90s long-form. Use whenever someone wants to edit, caption, cut, or finish a talking-head/yapping/selfie video OR a scripted-voiceover storytelling/day-in-the-life montage from b-roll, even without the word "edit" (e.g. "make a tiktok from these clips", "caption this", "tighten this yap", "turn this footage into a post", "add subtitles", "script my voiceover and cut my day clips", "day in the life edit", "add SFX/music to my video", or a dropped folder of .MOV/.mp4 clips). Creator-agnostic: on first run it interviews the creator for their brand (niche, fonts, colours, handle, contact, CTA) and saves a brand-config.json. Do NOT use for AI-generated video, static social images, or branded corporate assets.
---

# TikTok Yap Editor

Turn raw phone clips into a finished vertical short. The pipeline is
deterministic (bundled scripts); the editorial judgment (which take, what story,
where to stop) stays with you and the creator. Bias toward shipping a clean,
tight, captioned clip that serves the channel, not technical perfection.

## Two modes (pick one before you start)
- **Mode A: talking-head yap.** The creator yaps to camera; **audio leads,
  picture follows**. Transcribe, build a premise-first story, cut the footage to
  the words actually said. This is the original flow (`yapcut.py` + `yapfull.sh`),
  documented under "The pipeline" below.
- **Mode B: VO-to-picture storytelling / day-in-the-life.** The creator films
  loose b-roll of their day with NO usable on-camera speech; **picture leads,
  voice follows**. You SCRIPT the voiceover beat by beat, lock the picture to that
  script at attention-tuned clip lengths (`brollcut.py`), burn a record-to-picture
  guide (`vo_guide.py`) the creator reads VO against later, then lay the VO in,
  caption, and finish (`storyfull.sh`). Documented under "Mode B" below.
Both modes share the brand-config, the caption/hook engine, the SFX layer, and
the cover/finalize steps. **Pick the mode from what the footage is**: people
talking to camera = A; silent/ambient day-clips + "script my voiceover" = B.

**Length.** Short-form target stays 25-40s (Mode A's default). Mode B / long-form
targets **60-90s**: keep the hook in the first ~2s, cut fast (1.5-2.5s clips) for
the first 4-5 beats, then let later beats breathe (3-4s) under a music bed. Past
~90s, add a clear mid-point reset (a new sub-hook line) or it sags.

## First run: brand discovery (do this once per creator)

Before editing for a new creator, check for a `brand-config.json` (look in
`<footage>/.yap_build/`, then the skill root). **If it is missing, interview the
creator** with `AskUserQuestion` and write the config. Ask about:

1. **Niche / positioning** (one line; drives hook + story framing) and **content
   pillars** (2-4).
2. **Caption font** (default `Montserrat Black` ALL CAPS; or a brand display font
   like `Bricolage Grotesque ExtraBold` in sentence case) and **case**.
3. **Accent colour** (a single spark/highlight hex, e.g. `#FF5A2A`, or none) plus
   **base** (caption fill, usually white) and **ink** (stroke, usually near-black).
4. **Handle** to burn at the CTA (e.g. `YOURNAME.COM`) and any **contact lines**
   under it (email, site).
5. **CTA style** (optional, off by default for retention): if the creator wants
   one, a reusable **spoken-outro clip** (record one "hey I'm X, follow for…"
   and reuse it, set `cta_clip`) or just the burned handle/contact block. Leave
   `cta_clip` empty to end on the button; only add the spoken CTA when the
   creator specifically wants it and retention can carry the extra seconds.
6. **Reference accounts** to study/tag.

Write the answers to `<footage>/.yap_build/brand-config.json` using
`brand-config.example.json` as the schema. `scripts/yapfull.sh` reads it, so the
brand is data, not hardcoded. (The font choice must be installed, see Preflight.)

## Two non-negotiables (every run, never skip)

1. **Premise first (storyline step).** Never go transcript -> clauses. Build the
   story around a one-sentence takeaway. **The creator supplies the takeaway; you
   build the storyline.** If they haven't, ASK before cutting.
2. **Line audit (after the cut).** Read the actual cut line sequence and audit for
   (a) timeline/logical contradictions from reordering, and (b) repetition that
   isn't worth repeating (restart-heavy phone takes constantly double phrases).
   Fix before captioning. Every time, even when it "sounds fine".

## The locked short-form format

1. **Cold open**: the sharpest, most honest fragment first. No "hey guys".
2. **On-screen hook**: ~6 words, high contrast, clear of platform UI. Burned for
   the muted majority. **The hook can never be cut off: `build_ass.py` measures
   the real rendered width with the actual font and auto-wraps + auto-shrinks
   it to a title-safe width (≤90% of 1080px, ≤3 lines) on every run.** You no
   longer hand-break long hooks; pass the whole line and it fits itself. You
   may still force a break with `|` (`--hook "line one|line two"`) for a
   deliberate two-line look, and it will still be width-checked.
3. **Visual interrupt** in frame zero.
4. **3-5 loose points**, free-flow.
5. **Land on one closing line** (button), hard stop or loop. **A spoken CTA is
   OPTIONAL and off by default.** Watch-through is the metric: a "follow for
   more" tacked on after the payoff is the exact spot people drop, which drags
   the retention curve the algorithm reads. End on the button. Only append the
   CTA when it genuinely earns its seconds (a strong reason to follow that lands
   before attention dies), never as a reflex.

Target 25-40s. If a spoken-outro CTA is used it adds ~9s, so only spend that
when retention can carry it. Tag each video to a pillar.

**Never use em/en dashes** in any on-screen text or message. Commas/colons.

## Folder convention (non-negotiable)

Working files go under `<footage>/.yap_build/` (dot-prefixed, wiped at the end).
The deliverable folder holds ONLY the finished video (+ its cover). `finalize.sh`
promotes the final and clears the working dir.

## The pipeline

**The sequence is locked.** One video walks all of it before it is "done";
a file in the deliverable folder means every gate below passed. Never build a
batch ahead of the gates: builds that sprint ahead of QA are how defects reach
the creator.

1. survey + word-transcribe the raw
2. restart map on the raw (2c): flagged spans become planned cuts
3. premise -> storyline -> clause plan (4)
4. ground-truth every boundary with a window re-transcription (4, boundary rule)
5. cut (5) -> GATE: black frames (yapfull)
6. transcribe the cut -> GATE: stutter_check on the cut (yapfull, build-fatal)
7. line audit (read the cut as a story; adjudicate MEDIUM stutter flags)
8. captions + hook + corrections -> compose -> GATE: seam_qa (yapfull, build-fatal)
9. retention check + cover
10. creator watches -> finalize (promote + wipe workdir)

### 0. Preflight
```bash
bash scripts/setup_fonts.sh        # one-time: libass ffmpeg + Montserrat/Anton + Bricolage/Space Mono
python3 scripts/preflight.py       # asserts ffmpeg+libass, whisper-cli + model, Pillow, fonts
```
`auto-editor` is NOT required (the old flow used it; `yapcut.py` replaced it,
see "Why yapcut").

### 1. Survey the footage
List clips; probe duration/resolution/rotation. **Do NOT pre-judge takes by
length** (a key beat can live in a short clip). iPhone 4K is often landscape with
`rotation:90` (really portrait); ffmpeg auto-rotates.

### 2. Transcribe every clip
```bash
bash scripts/transcribe.sh "IMG_XXXX.MOV" .yap_build/transcripts/IMG_XXXX
```
Read all transcripts together. Transcript-first is the whole method.

### 2b. Segment restart-heavy takes (the reliability tool)
Phone takes have many restarts ("Brand used to be X. Brand used to be X traffic…").
**Whisper word-times DRIFT** and will make surgical clause boundaries miss the
duplicate. Instead list silence-accurate runs with per-run text and pick the clean
pass:
```bash
python3 scripts/segmenter.py "IMG_XXXX.MOV"      # idx  start-end  text
```
Use these exact run boundaries as `keep_whole` clauses.

### 2c. Catch stutters + restarts (automatic, never skip)
Phone takes double phrases ("now use AI, now use AI, now use AI…"), repeat a
word ("the the"), or restart a clause. These used to be caught by hand, clip by
clip, and slipped through. Now run the detector on each clip's word JSON:
```bash
python3 scripts/stutter_check.py --words .yap_build/transcripts/IMG_XXXX.json
```
It catches adjacent restarts AND distant line re-reads (you miss a line and
read it again seconds later): a 6+ word echo within 20s gates the build; short
topic-phrase echoes and older callbacks are flagged MEDIUM for the line audit
(your subject noun phrase recurs legitimately, and a deliberate hook callback
at the button should not die at a gate). It prints every hit with timestamps,
keeps the cleanest (usually last) delivery, and emits both **video cut-ranges** (subtract these from the
clause in/out you write in step 4) and a **caption drop-list**. Exit code 2 =
stutters found, so it gates the build. Pass `--emit-corrections
<out>_corrections.json` to write the caption `drop` indices straight into the
file step 7 reads. This is the automated half of the step-2 line audit; you
still eyeball it, but nothing ships with an uncaught repeat.

### 3. Build the storyline (premise first)
Get the takeaway (one sentence) from the creator. Inventory usable fragments with
source+timestamp, tag each a role (HOOK / STAKES / ESCALATION / TURN / EVIDENCE /
BUTTON / CUT), pick a story shape (confession->cost->reframe; contrarian->proof->
implication; before/after; problem->insight->payoff; list-with-a-turn), and write
the full ordered line sequence BEFORE cutting. Lead with the sharpest line even if
it sits late. Story-test: does line one open a loop? sharpest line first?
escalation + turn? button pays the loop? one idea? Present the beat sheet, get a
yes.

### 4. Write clauses.json (ordered source + in/out)
```json
[
  {"src":"/abs/IMG_1.MOV","start":3.64,"end":6.58,"label":"hook","keep_whole":true},
  {"src":"/abs/IMG_1.MOV","start":34.8,"end":37.0,"label":"stat","keep_whole":true,"gain_db":12},
  {"src":"/abs/cta-alex.mp4","start":0.0,"end":9.5,"label":"cta"}
]
```
- `keep_whole`: keep the span as-is, no internal silence processing (use for the
  silence-accurate runs from segmenter, and for fragile quiet words).
- `gain_db`: boost a quietly-spoken fragment so it survives + is audible.
- `protect_tail`: keep a quiet final word (no tight trim). Omit on button/CTA
  joins so they cut tight (tail-protection there causes a big pre/post-CTA pause).
- Append the shared `cta_clip` as the final clause for a spoken-outro CTA.

**Boundary placement rule (hard lesson):** NEVER take clause in/out times from
a full-file word transcript: whisper DTW times drift up to ~2s mid-file, and a
boundary placed on drifted times can swallow kept words while keeping the
flubbed take it was meant to remove. Before writing any story-cut boundary
(restart removal, take selection, CTA trim), re-transcribe a ±5s window around
the intended cut (`transcribe.sh` on a trimmed wav is seconds of work): window
timings are accurate. Put the boundary in the pause between the anchor words,
then read the joined sentence back after cutting (the line audit) to confirm
nothing was swallowed or doubled.

### 5. Cut (single pass)
```bash
python3 scripts/yapcut.py --clauses clauses.json --workdir .yap_build --out .yap_build/full.mp4
```
One clean CFR 30fps encode: clause selection + dead-air removal + tight tails +
alternating static crop (anti-stutter). Pause detection is a median-smoothed
RMS envelope, immune to the mouth clicks that split a real 1.5s pause into
sub-threshold chunks an instantaneous level gate cannot see. Flags: `--silence-db -42` (quiet indoor;
raise toward -19 for noisy/outdoor), `--padr 0.12` / `--padl 0.10` (decay-aware:
silencedetect fires while word tails are still audible, tighter pads shave word
edges), `--min-gap 0.55` (only pauses this long become cuts; 0.3-0.5s pauses
are cadence, cutting them machine-guns the edit), `--min-seg 0.45` (no
flash-frame segments; shorter runs get bridged, never across >0.75s of pause),
`--min-cut 0.25` (a cut must remove at least this much to earn its visual
jump), `--d 0.10`. It writes `keeps_<out>.json` (the final cut points) for
the QA seam audit. Do NOT snap cuts to whisper word timings: DTW tokens tile
the whole timeline (spans absorb pauses), so word-snapping degenerates into
padding every cut with dead air.

### 6. QA gate (automate it, don't eyeball randomly)
```bash
ffmpeg -i full.mp4 -vf "blackdetect=d=0.02:pic_th=0.95" -an -f null -   # zero black flashes
python3 scripts/seam_qa.py --keeps .yap_build/keeps_full.json --video full.mp4  # no splice holes/blips at joins
bash scripts/transcribe.sh full.mp4 .yap_build/w --words                # re-read line sequence (5b audit)
python3 scripts/stutter_check.py --words .yap_build/w.json               # re-run on the CUT: must come back clean
python3 scripts/retention_check.py --video full.mp4                     # retention gates (see Retention pass)
```
Plus a seam contact-sheet (frames at each cut) to scan for any leftover look-down,
and confirm loudness ~-14 after compose. The **line audit** lives here: fix
restart doublings (the stutter_check re-run on the cut must come back clean, or
tighten the offending clause), clipped word tails (widen that clause boundary),
dangling fragments.

### 7. Captions + hook + CTA, in the brand (one driver)
```bash
bash scripts/yapfull.sh .yap_build clauses.json output/clip.mp4 "HOOK|LINE2" "sparkword"
```
`yapfull.sh` runs steps 5-8 reading `brand-config.json`: word-by-word captions in
the brand font/case (active word scales, no neon), an accent spark on the hook
word, and the handle + contact block at the CTA tail. For caption fixes write a
`<out>_corrections.json` (`{"fix":{"5":"Google"},"drop":[31]}`) keyed by the
build word index (it skips empty tokens).

### 8. Compose
`compose_ass.sh` (called by yapfull) burns the `.ass`, normalizes to -14 LUFS, and
does the clean CFR re-encode.

### 8c. Cover (post-ready thumbnail)
```bash
python3 scripts/cover.py --video final.mp4 --contact-sheet --out .yap_build/cov   # candidates
python3 scripts/cover.py --image <frame.png> --title "HOOK|LINE2" --out output/clip.jpg
```
Pick eye-contact + expressive. Covers come from REAL frames only (no AI).

### 9. Finalize (after sign-off)
```bash
bash scripts/finalize.sh final.mp4 "/path/to/footage" clean-name
```

## Why yapcut (replaced cut.py + auto-editor)
auto-editor outputs a variable timebase; concatenating + re-encoding it dropped a
1-frame **black flash at every jump cut**. `yapcut.py` does everything in one
clean CFR pass. It also fixes the two things creators always flag:
- **Dead air / look-down**: tight trailing pad cuts the frame where they glance at
  the script.
- **Jump-cut "stutter"** (a cut landing on a near-identical pose reads as "I said
  it twice", even with clean audio): alternating static crop (1.00/1.06, hard cut,
  NO animation) changes framing at every cut so the pose-match is masked.

**Perfect-cuts rules (v2, learned from a real 13-video batch):** the old
defaults over-cut. Cutting a 0.3-0.5s breath saves ~0.2-0.4s but costs a
pose-jump + zoom toggle; a batch audit showed 57% of joins were such micro-gap
cuts, plus 4-frame flash segments. v2 therefore: cuts only at pauses >= 0.55s,
no segment < 0.45s (bridged into a neighbour instead), cuts must remove
>= 0.25s to exist, decay-aware pads (0.12/0.10, energy-verified to clip
nothing audible at -42dB boundaries), and envelope-based pause detection (an
instantaneous gate lets a single mouth click hide a 2-second gap; the median
envelope does not). Audio is spliced from PCM segments with 4ms edge fades and
encoded to AAC once at the end: per-segment AAC + concat stream-copy inserted
a ~20-40ms audible hole at every join. Zero dead space still means
zero DEAD space: real pauses (>= 0.55s), restarts and stutters are cut hard;
speech cadence is not.


## Mode B: VO-to-picture storytelling / day-in-the-life
The inverse of Mode A. The creator hands you loose b-roll (walking, working,
coffee, screen, street) with no usable on-camera speech. You build the video by
**locking picture to a script**, then the creator records the voiceover to a
guide. Same brand-config, captions, SFX, cover.

### B1. Survey + script the voiceover (premise first, same rule)
Probe the clips (duration, what's in frame). Get the takeaway from the creator,
then **YOU write the beat-by-beat VO script**: one short spoken line per beat,
each with a role (HOOK / CONTEXT / BEAT / TURN / BUTTON) and a target on-screen
duration. Hook beat short (1.5-2.5s), later beats breathe (3-4s). Premise first:
the hook line opens a loop, the button pays it. Present the beat sheet, get a yes.

**Mine long clips end to end, one file is many shots.** In day-in-the-life
footage the creator lets the camera roll and does several things in one long
take. Watch the WHOLE clip (a timecoded contact sheet across its full length,
not a single thumbnail), and **whenever a NEW ACTION starts inside the clip,
treat it as an intentional, separate usable shot** with its own in/out, not a
throwaway. A 4-minute cooking clip is not "one chopping shot", it is chopping +
plating + stepping back + tasting, each a candidate beat. Assume the new action
was filmed on purpose. Never judge a long clip by its first few seconds or
grab only one shot from it, walk its entire duration and pull every distinct
moment into the shot pool before matching beats.

### B2. Assign a clip to each beat + write beats.json
Match each scripted beat to its best visual (the one whose action illustrates the
line), pick an in-point, and set the play length from the beat's target duration.
```json
[
  {"src":"/abs/IMG_1.MOV","start":2.0,"target_dur":2.2,"role":"hook","text":"VO line you read","push":true},
  {"src":"/abs/IMG_2.MOV","start":11.0,"end":14.0,"role":"beat","text":"next line"},
  {"src":"/abs/IMG_3.MOV","start":0.0,"target_dur":3.0,"role":"button","text":"closing line"}
]
```
- `target_dur` (or `end`) = how long the clip plays = the pacing lever.
- `push:true` = slow 12% push-in for life on a near-static shot (skip on clips
  that already move).
- `text` = the exact VO line for that beat (drives the guide + sync).

### B3. Lock the picture + emit the timeline
```bash
python3 scripts/brollcut.py --beats beats.json --workdir .yap_build --out .yap_build/picture.mp4
```
Builds the silent (natural-audio-bed) vertical timeline and writes
`.yap_build/picture.timeline.json` (per-beat assembled times) that drives the
guide, captions, and SFX.

### B4. Burn the record-to-picture guide -> creator records VO
```bash
python3 scripts/vo_guide.py --picture .yap_build/picture.mp4 \
  --timeline .yap_build/picture.timeline.json --out guide.mp4 --font "Bricolage Grotesque"
```
`guide.mp4` = a 3s countdown then the picture with each beat's VO line burned
over its clip. **Send it to the creator: they play it and read the lines aloud
in time, recording a single voice memo.** Because the picture is locked, the take
lands in sync. Tell them to start reading on "1".

### B5. Finish (lay VO in, caption, brand, SFX, compose)
```bash
bash scripts/storyfull.sh .yap_build .yap_build/picture.mp4 vo.m4a output/clip.mp4 \
  "HOOK|LINE2" "sparkword" sfx.json
# vo = "-" to skip an external VO and keep the clips' own audio.
# trailing arg = vo_offset seconds if the recording has leading silence.
```
`storyfull.sh` lays the VO over the picture (ducking each clip's natural sound
under it), transcribes the VO for word-by-word brand captions, adds the hook +
handle/contact block, mixes the SFX/music layer, and composes to -14 LUFS. Then
do the cover (8c) and finalize (9) exactly as Mode A.

## SFX + music layer (optional, both modes)
A generated, royalty-free pack (no downloads, no licensing) lives at
`assets/sfx/`. Build it once:
```bash
python3 scripts/gen_sfx.py            # whoosh, swish, impact, riser, ding, click, bed_calm, bed_drive
```
Layer it with a `sfx.json` (Mode B: pass it to `storyfull.sh`; Mode A: run
`sfxmix.py` on the finished clip):
```json
{
  "music": {"file": "bed_calm", "gain_db": -22, "duck": true},
  "hits": [
    {"sfx":"whoosh","at":0.0,"gain_db":-8},
    {"sfx":"impact","at":1.6,"gain_db":-5},
    {"sfx":"swish","at":5.0,"gain_db":-10},
    {"sfx":"ding","at":11.2,"gain_db":-12}
  ]
}
```
```bash
python3 scripts/sfxmix.py --in output/clip.mp4 --sfx sfx.json --out output/clip_sfx.mp4
```
- **music.duck:true** sidechain-ducks the bed whenever the voice talks (keeps the
  VO clear). `file` resolves a pack name OR an absolute path (drop in your own
  music/SFX). Beds are subtle ambient pads, fine to BYO a licensed track instead.
- **Place hits from the timeline**: a `whoosh`/`swish` on each cut (use the
  `t_start` of each beat from `picture.timeline.json`), an `impact` on the hook
  word landing, a `riser` into a turn, a `ding` on a stat/list beat.
- **Taste**: under-mix it. SFX is seasoning, not the dish. One whoosh per real
  cut, not per caption word. Final loudness still lands ~-14 (alimiter guards
  clipping when hits stack on the voice).
- Generated tones are CC0; this does NOT break the "no AI-generated assets" rule,
  which is about VISUALS (covers, b-roll, hero frames stay real footage only).

## Retention pass (gates, every video, both modes)

The editor optimises the retention curve, not just a clean cut. Watch-through is
the metric. Four gates, run on the FINISHED cut (after captions/overlays, before
finalize), all enforced by `retention_check.py` plus two eyeball checks:

```bash
python3 scripts/retention_check.py --video output/clip.mp4 \
  --overlays .yap_build/<slug>_overlays.json --hook-end 5.2
ffmpeg -i output/clip.mp4 -frames:v 1 .yap_build/frame0.png   # first-frame audit
```

1. **First-frame gate (eyeball frame0.png).** At 0.0s there must be motion or
   mid-action framing (never settling in), the text hook readable in one
   fixation, and something that differs from a generic talking head. If frame
   zero could be any video in the feed, re-pick the hook clip in-point.
2. **Re-hook gate (scripted).** Something must CHANGE on screen between ~2s and
   ~3.5s: a cut, punch-in, text pop, or overlay landing with a raised stake.
   The tool fails the build if the frame sits still through the window.
3. **Pattern-interrupt budget (scripted).** No stretch longer than ~5s (short
   form) or ~6s (60s+, pass `--max-gap 6`) without a visual event. The tool
   prints every static stretch with a timestamp: fix each one by aiming an
   overlay, counter, PiP evidence insert, or punch-in AT that timestamp, then
   re-run. The longest static stretch is where people leave.
4. **Loop-or-button ending (eyeball).** The last line either hard-stops on the
   payoff or connects back to the first line so rewatches register. Never let
   the energy trail off after the payoff.

**Density levers, in order of preference:** a real cut > a PiP evidence insert >
a number count-up > a source lower-third > a caption emphasis pop > a punch-in.
Under-season: one event per beat, not per word. SFX hits should land ON these
events (same timestamps), not between them.

### Evidence inserts (PiP: show the company / article / chart)
When the script names a company, an article, a chart, or a number, SHOW it.
Real screenshots only (no AI, per Hard rules): screenshot the actual headline,
pricing page, chart, or post; save to `.yap_build/evidence/`. Burn as
picture-in-picture for 2-4s, placed in the upper-middle third, clear of the
hook window and the caption line:
```bash
ffmpeg -i cut.mp4 -i .yap_build/evidence/shot.png -filter_complex \
  "[1]scale=880:-1,pad=iw+16:ih+16:8:8:color=white[e];\
   [0][e]overlay=(W-w)/2:260:enable='between(t,12.4,15.6)'" \
  -c:a copy out.mp4
```
Rules: one insert per claim, on screen only while the claim is spoken, add a
`whoosh` SFX hit on entry. Log each insert in the overlays JSON (`{"type":"pip",
"start":12.4,"end":15.6}`) so retention_check counts it. An evidence insert does
two jobs at once: pattern interrupt + receipts (credibility), so aim them first
at the static stretches the tool flags, and always on the biggest claim.

## Motion layers (typewriter hook, source tags, number count-ups)
Driven by `build_ass.py` + `brand-config.json`, applied by `yapfull.sh`:
- **Typewriter hook**: set `"hook_anim": "typewriter"` in brand-config (Alex = on). The
  hook reveals character-by-character with a cursor, then holds with the accent spark on
  the spark word. `"none"` = the old fade.
- **Source lower-thirds + number count-ups**: per clip, drop a
  `<workdir>/<out-slug>_overlays.json` (yapfull auto-applies it):
  `[{"type":"source","text":"Source: Forrester, 2026","start":8.0,"end":12.0},
    {"type":"counter","value":"23X","label":"vs everyone else","start":11.6,"end":14.2,"y":420}]`
  Counter ticks 0->value in the accent then holds the exact `value` string (handles 23X,
  $1B, 89%). Use for the data/educational videos. The accent colour comes from
  `accent_hex` even when captions are scale-only.
All real/typeset, no AI-generated assets.

## On-screen hook styles (native / minimal / branded)
Two ways to burn the hook. The **inline ASS hook** (`build_ass.py --hook`, auto-fit so
it never clips) is the default, fast path. For a designed, typography-driven hook, use
`hook_styles.py`, which renders a transparent 1080x1920 PNG you overlay on the cut for
the hook window (~0.15-5s). Three styles, all auto-shrink so nothing ever clips:
```bash
python3 scripts/hook_styles.py --style branded \
  --setup "SETUP LINE|OPTIONAL SECOND" --payoff "the tension underneath" \
  [--eyebrow POV] --brand brand-config.json --out .yap_build/hook.png
# then burn it for the hook window:
ffmpeg -i cut.mp4 -i .yap_build/hook.png -filter_complex \
  "[0][1]overlay=0:0:enable='between(t,0.15,5.2)'" -c:a copy out.mp4
```
- **native** = looks typed in TikTok: SF NS Rounded Heavy, white + dark outline, balanced.
- **minimal** = tight brand sans (`caption_font`), big statement + smaller context line,
  no outline, subtle shadow only.
- **branded** = the house style: SETUP big in a condensed display face (Anton) in the
  brand `accent_hex`, uppercase, up to 2 lines; PAYOFF in an italic serif (Hoefler Text
  Italic), white, ALWAYS one line. NO outline, NO shadow (font-classification contrast is
  the point). Colours/fonts come from `brand-config.json`. Rules: the payoff never wraps
  or clips; emphasis spans a phrase, not one word before a period.

## Decisions to ask (and proven defaults)
| Decision | Default |
|---|---|
| Which take | Two longest are usually the takes; ask if ambiguous. Never skip short clips. |
| Takeaway/premise | Creator supplies it. If missing, ASK. |
| Story shape/order/cuts | You build it premise-first, present the beat sheet, get a yes. |
| Caption preset | brand-config (minimal scale-only highlight; bold/Anton only for YouTube repurposes). |
| Hook length | One line if it fits, else two (`a|b`). |
| Crop alternation | On (masks jump-cut stutter). Turn off only if the creator dislikes any framing change. |

## When it misbehaves
`references/gotchas.md` (threshold tuning per noise floor, clipped quiet word,
transcriber seam hallucinations, no-libass constraint, black-video fix) and
`references/speech-and-repetition.md` (which repeats to cut vs keep). Read before
improvising.

## Hard rules
- **No AI-generated assets** (covers, b-roll, hero frames). Covers from real
  frames; visual variety from the creator's own footage only.
- Run the batch **sequentially** in one process (the cutters are parallel-safe via
  per-output scratch, but races still risk surprises).
- No em/en dashes anywhere on screen or in messages.

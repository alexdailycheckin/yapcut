---
name: tiktok-yap-editor
description: Turn raw talking-head phone clips into finished, post-ready vertical TikTok/Reels/Shorts "yapping" videos: transcript-first story edit, zero-dead-air jump-cut tightening, word-by-word burned captions in the creator's brand, a burned text hook, an optional spoken-outro CTA with a contact block, loudness for the feed, and a QA pass. Use whenever someone wants to edit, caption, cut, or finish a talking-head / yapping / selfie-monologue video, even without the word "edit" (e.g. "make a tiktok from these clips", "caption this", "tighten this yap", "turn this footage into a post", "add subtitles to my talking head", or a dropped folder of .MOV/.mp4 selfie clips). Creator-agnostic: on first run it interviews the creator for their brand (niche, fonts, colours, handle, contact, CTA) and saves a brand-config.json. Do NOT use for AI-generated video, static social images, or branded corporate assets.
---

# TikTok Yap Editor

Turn raw talking-head phone clips into a finished vertical short. The pipeline is
deterministic (bundled scripts); the editorial judgment (which take, what story,
where to stop) stays with you and the creator. Bias toward shipping a clean,
tight, captioned clip that serves the channel, not technical perfection.

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
5. **CTA style**: a reusable **spoken-outro clip** (best: record one "hey I'm X,
   follow for…" and reuse it on every video, set `cta_clip`) or just the burned
   handle/contact block.
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
   the muted majority. **If it doesn't fit one line, break it into two**
   (`--hook "line one|line two"`). This is a rule, not an option.
3. **Visual interrupt** in frame zero.
4. **3-5 loose points**, free-flow.
5. **Land on one closing line** (button), hard stop or loop. Then the CTA.

Target 25-40s (the spoken-outro CTA adds ~9s). Tag each video to a pillar.

**Never use em/en dashes** in any on-screen text or message. Commas/colons.

## Folder convention (non-negotiable)

Working files go under `<footage>/.yap_build/` (dot-prefixed, wiped at the end).
The deliverable folder holds ONLY the finished video (+ its cover). `finalize.sh`
promotes the final and clears the working dir.

## The pipeline

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

### 5. Cut (single pass)
```bash
python3 scripts/yapcut.py --clauses clauses.json --workdir .yap_build --out .yap_build/full.mp4
```
One clean CFR 30fps encode: clause selection + dead-air removal + tight tails +
alternating static crop (anti-stutter). Flags: `--silence-db -42` (quiet indoor;
raise toward -19 for noisy/outdoor), `--padr 0.04` (tight trailing = removes the
look-down-at-script frame), `--min-gap 0.28`, `--d 0.10`.

### 6. QA gate (automate it, don't eyeball randomly)
```bash
ffmpeg -i full.mp4 -vf "blackdetect=d=0.02:pic_th=0.95" -an -f null -   # zero black flashes
bash scripts/transcribe.sh full.mp4 .yap_build/w --words                # re-read line sequence (5b audit)
```
Plus a seam contact-sheet (frames at each cut) to scan for any leftover look-down,
and confirm loudness ~-14 after compose. The **line audit** lives here: fix
restart doublings, clipped word tails (widen that clause boundary), dangling
fragments.

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

---
_Created by Alex Mureșan (https://alexmuresan.com). Creative Commons Attribution-NonCommercial 4.0 (CC BY-NC 4.0) — keep the NOTICE with any copy or derivative; commercial use: alex@alexmuresan.com._

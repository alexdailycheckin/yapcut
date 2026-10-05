# Technical gotchas and tuning notes

Read this when something misbehaves or when tuning for unusual footage. These
are failures that actually happened and cost real time; each fix is proven.

## ffmpeg in this environment

- **libass: now installed, was the original constraint.** The default Homebrew
  `ffmpeg` bottle ships WITHOUT the text/subtitle filters (`ass`, `subtitles`,
  `drawtext` all fail "No such filter"). This machine now runs `ffmpeg-full`
  (force-linked), which HAS them, so the preferred caption path is generated
  `.ass` (`build_ass.py` then `compose_ass.sh`). The Pillow + `overlay` path
  (`caption_frames.py` then `compose.sh`) remains as a fallback for builds
  without libass, and for anything ASS cannot draw (custom emoji/sticker PNGs,
  image B-roll cards). Verify the build: `ffmpeg -filters | grep -E "ass|overlay"`.
  If a later `brew upgrade` relinks the minimal ffmpeg and the `ass` filter
  disappears, re-run `brew link --overwrite --force ffmpeg-full` (or
  `bash scripts/setup_fonts.sh`). preflight.py asserts the filter.
- **`-nostdin` always.** Inside a `while read` loop, ffmpeg reads from the
  loop's stdin and devours the remaining lines, corrupting every iteration after
  the first. Symptom: later loop iterations get garbled args like `../4.00.MOV`.
  Every ffmpeg call in the scripts uses `-nostdin`.
- **Black video after concat.** `ffmpeg -f concat -c copy` can produce a file
  that plays black in QuickTime (audio fine, or black until you scrub) because
  the copied streams have slightly irregular timestamps and a non-integer avg
  fps. The fix is the final re-encode in `compose.sh` (`-r 30`,
  `-video_track_timescale 30000`). The cut from `cut.py` is intermediate only.
- **Voice/picture drift that GROWS with every cut (the worst one).** TWO
  independent causes; fixing only the first one shipped desynced batches twice
  (measured +0.30s to +0.77s of lag by the end of a clip):
  1. *Timestamp gaps*: the concat demuxer + `-c copy` leaves a small PTS gap at
     every segment join; the VIDEO accumulates them while yapcut's single
     continuous PCM->AAC audio has none. Fixed by RENUMBERING every frame onto a
     gapless grid by index: `-vf "setpts=N/(30*TB)"` before the ass burn (in
     `compose_ass.sh`) and in `yapcut.py`'s final mux (never `-c:v copy` there).
  2. *Per-segment frame-count excess*: the per-segment `fps=30` encode emits
     `floor(dur*30)+1` frames = **+0.5 frame per cut on average**, while the
     PCM audio is cut sample-exact. These are REAL extra frames, so no amount
     of PTS renumbering removes them; renumbering actually produces a perfectly
     clean PTS grid on a still-drifting file. Fixed in `yapcut.py` by pacing
     every segment's frame count against the CUMULATIVE audio clock
     (`nfr = round(t_audio*30) - f_video`, `tpad` clone headroom +
     `-frames:v nfr`), which bounds total drift at half a frame forever.
  Two supporting rules baked into `yapcut.py`: video and audio are cut to
  SEPARATE per-segment files and concatenated separately (in a muxed concat
  the demuxer offsets each next segment by one stream's duration, CLIPPING
  audio whenever the paced video ran shorter than its audio), and segment
  windows use `-ss/-to`, never input `-t` (input `-t` measures from the packet
  where reading starts and shaves ~5-10ms of audio per segment).
  Diagnose with STREAM DURATIONS, not the PTS profile: `ffprobe ... stream=
  codec_type,duration`; video minus audio beyond ~2 frames means drift, and
  the per-segment excess shows as (video - audio) ≈ 0.5 frames x segment count.
  Both `yapcut.py` and `yapfull.sh` carry a fatal DRIFT GATE so a regression
  can never reach a post.
- **Rescuing an already-shipped drifting file** (raw/plan gone): the excess
  accumulates roughly linearly across joins, so a uniform video retime onto
  the audio length corrects it to within a frame everywhere:
  `-vf "setpts=PTS*(AUDIO_DUR/VIDEO_DUR)" -r 30 -vsync cfr -t AUDIO_DUR
  -c:a copy`. Burned captions drift WITH the picture, so the retime re-locks
  them to the voice too. This is a rescue, not the pipeline: when the clause
  plan survives, re-cut.
- **Never re-cut an already-cut file ("double cut").** Feeding a re-assembled
  cut (content re-muxed via concat-copy, hence VFR) back into `yapcut` for a
  second dead-air pass stacks a second set of join gaps on top. If a shipped
  edit needs tightening, edit the clause plan and re-cut ONCE from the
  original raw. Re-cutting a cut only compounds drift.

## Whisper

- **Word END-times are unreliable** for cutting. Whisper stamps words nearly
  back-to-back and the end of a quiet word drifts. Cut on `silencedetect` energy
  instead. Use whisper word times only for caption sync, and then with `-dtw`.
- **`-dtw small.en`** (token-level DTW alignment) gives noticeably more accurate
  per-word timing. Use it for captions; without it captions lead/lag the speech
  and feel "off".
- **Transcriber hallucinations at jump-cut seams.** When two clips butt
  together, whisper sometimes invents filler ("And again...") at the seam. It is
  not in the audio. Sanity-check by confirming the word exists in a source clip;
  if not, drop it via the corrections file.

## Pause trimming is content-dependent

- The silence threshold depends entirely on the recording's noise floor. **Quiet
  indoor**: pauses may sit around -30 to -40 dB, use `--silence-db -30`.
  **Outdoor / noisy ambient** (birds, wind, traffic): the floor is high, pauses
  sit around -19 to -25 dB, use `--silence-db -19` (the default). If trimming
  does nothing, the threshold is too low (too negative); raise it toward -16. If
  it eats real words, lower it.
- **Quiet words overlap pause energy.** A softly spoken word (a fading "from"
  at the end of a line, a quiet "If" before a loud one) sits under the speech
  gate, so the gate alone calls it silence. Since 3.7.3 `yapcut.py` walks every
  boundary out from the gate crossing until the sound falls below -55 dB
  (`cut.edge.word_db`), so a soft word next to a pause stays in the cut.
  `protect_tail` still keeps a clause's last tail up to the clause end, and a
  clause with no detected speech is kept whole. A word quieter than -55 dB, or
  one parted from its line by more than ~90 ms of silence, can still be cut:
  give it its own narrow clause in `clauses.json`.
- **Diagnosing a specific word.** When unsure where a word actually is, scan RMS
  in small windows rather than trusting whisper:
  ```bash
  for t in $(seq 4.0 0.15 6.0); do
    echo -n "$t "; ffmpeg -nostdin -ss $t -t 0.15 -i audio/clip.wav \
      -af volumedetect -f null - 2>&1 | grep mean_volume
  done
  ```
  Speech is typically ~-24 dB, pauses ~-35 dB, quiet words land in between.

## Gated mics make the seam gate cry wolf

`seam_qa.py` calls anything under -65dB beside a join a splice dropout, reasoning
that room tone never reaches digital silence. With a noise gate, a shotgun mic or
a very quiet room, that assumption is false: the gap between two words genuinely
is silence, so a clean edit fails most of its joins. Measured on one such batch:
every flagged join carried 0-100ms of sub-65dB and a largest sample step of a few
hundred, against a file-wide 99.9th percentile of 6400-7700. No clicks, nothing
audible.

Do not tune the cut to satisfy it, and do not switch it off blind. Tighter pads
make it worse (fewer frames of speech either side of the gap, same gap), and
re-cutting to avoid it costs word endings. Instead:

```bash
python3 scripts/seam_evidence.py output/clip.mp4 .yap_build/keeps_full_clip.json
```

That reports the longest sub-threshold run and the worst step against the file's
own dynamics, and exits non-zero if any join looks like a genuine defect. Only
when it passes, re-run with `YAP_ALLOW_SEAM=1`. A run over ~150ms or a step well
above the file's 99.9th percentile is a real hole: fix the cut, do not override.

## Clause boundaries: take the segmenter's, do not "improve" them

Learned the expensive way on a seven-episode batch. The seam gate was failing, so
a helper was written to nudge every clause edge onto the nearest speech energy.
It cleared the gate and quietly ate the end of a line in five of the seven
videos: "a media company that sells a drink" became "...that sells", "they give
you fifty free" became "fifty fr-", "credit card" became "credit", and one
episode lost a dozen word endings ("the boring half" -> "the boring", "since
roughly forever" -> "since roughly 4S"). Every one of them passed the gates,
because no gate checks that the words are still there. They were caught only by
reading the cut transcript out as prose.

The recipe that works:

1. Take boundaries from `segmenter.py` **verbatim**. They are silence-accurate;
   that is the whole point of the tool.
2. Set `protect_tail` on clauses whose last word is quiet or sentence-final,
   which is most of them. It costs nothing and stops the tail trim biting.
3. Move a boundary by hand ONLY to dodge a false start, and only after a window
   re-transcription of that exact span shows where the good take begins.
4. Never auto-fit boundaries in bulk. Silence detection cannot tell a quiet
   final consonant from a pause, so a batch nudge trades a visible gate failure
   for an invisible content failure.
5. After any recut, re-read the whole cut as a line sequence. A clipped word is
   almost always visible as a mangled transcript ("They lost the" -> "Last the",
   "Neither of those" -> "Either of those").

If the seam gate is what pushed you toward fitting in the first place, measure it
with `seam_evidence.py` instead: on a gated mic those failures are usually the
gate being wrong, not the cut.

## Repeat detectors fire on deliberate parallelism

`stutter_check.py` and `restart_scan.py` both flag a repeated phrase, and good
writing repeats phrases on purpose. Real examples that failed the gate:

- A hook built on a mirrored clause: "X said no more discs, Y said no more pizzas."
- A concession that reuses the noun: "Neither of those is a business, and this is a business."
- A callback that repeats the key term: "...were never the moat. The moat is the distribution."

Verify against the audio with a window transcription, then pass
`YAP_ALLOW_STUTTER=1`. Also note `restart_scan.py` re-transcribes short windows
and sometimes hallucinates a doubled function word ("It it", "took took") that
is not in the audio at all: check before cutting anything, because deleting a
"duplicate" that does not exist removes a real word.

## The transcript merges a short restart; short windows do not

A restart whose first pass trails off and whose second pass follows within a
fraction of a second reads as ONE phrase in the whole-cut transcript, in
`restart_scan.py`'s 30s and 6s windows, and in the segmenter. On 2026-09-30 a take
said "It's the same bet we made. It's the same bet we made at <company>" with 0.22s
between the passes, and all three passed it. `xwin_scan.py`, the third detector in
the repetition gate, transcribes the cut in 1.1s and 1.6s windows (0.45s hop) and
flags the same trigram, or a bigram carrying a content word, in two windows that do
not overlap and start within 3s. It is MEDIUM only when the cut's own transcript
says those words exactly once across that span: two separate pieces of audio said
them, the transcript merged them. Everything else is LOW and printed without failing:
the transcript says it twice too (the script's own repeated noun, "the work ... the
work"), the transcript never says it (a mis-decode), or it carries a number or a
letter (short windows decode "28th, 2027" as "28th, 20th, 20th"). Clear a MEDIUM like
any other: cut the first pass in the clause plan, or listen and add its printed key
to `<out>_stutter_ok.json`. A fresh scan costs about 1s of whisper per window
(about 4 minutes on a 55s cut); the decodes are cached in `xwin_<out>.json`, so a
`YAP_FROM_CUT=1` rebuild reuses them.

## Caption corrections are position-keyed, so a recut invalidates them

`<out>_corrections.json` maps a WORD INDEX to a replacement. Change anything
about the cut and every index after the change shifts. Symptom: the corrected and
original words both render, stacked in the same spot, e.g. a burned caption
reading "and posted 109.4 190.4" after `protect_tail` lengthened one clause by a
few frames. Worse, a drop lands on a real word: on 2026-09-30 a drop computed for a
stray "-" token deleted "software" after a re-transcription.

Name the word each entry expects, and a stale entry is skipped with a warning
instead of applied:

```json
{"fix":  {"12": {"from": "chat", "to": "ChatGPT"}},
 "drop": {"13": {"from": "-"}}}
```

The legacy forms (`"fix": {"12": "ChatGPT"}`, `"drop": [13]`) still apply blind.
The warning says where the expected word sits now when it is within six words.
`stutter_check.py --emit-corrections` writes the named form. Still re-derive the
indices from the fresh `w_<slug>.json` after a rebuild; the check stops the damage,
it does not move the entry for you.

## Captions

- **Stable phrase + moving highlight** is the smooth default. A line that
  accumulates words and then clears reads "erratic" because the box grows and
  resets. `caption_frames.py` shows the whole phrase and only moves the yellow
  highlight.
- **Place lower-third, clear of the face.** `--cap-y 1300` sits over the chest in
  a typical selfie-framed vertical. Faces usually fill the upper-center, so
  centered captions cover them.
- **Hook overlay collides with the face** when the subject fills the top of the
  frame. There is no perfect spot; raise `--hook-y`, shorten the line, or accept
  it for the 2.5s it shows. Differentiate hook colour from the active-word colour
  so they do not read as the same element.
- **The minimal hook is for small print only.** `hook_style: minimal` draws every
  line after the first at 55% (`rules.json` `hook.styles.minimal.sub_frac`). When a
  later line carries the claim ("ChatGPT ads:|$1 billion in|under 200 days") that
  is fine print; a 2026-09-30 batch put the claim on line two in all four hooks and
  ran on `outline`. `build_ass.py` now switches a minimal hook to outline whenever a
  later line has more characters than line 1, and prints why. Minimal also has no
  stroke, so white type vanishes on a bright sky or a pale wall: use outline outdoors.
- **The hook fitter shrinks before it wraps.** Each `|` line stays on one line and
  the whole hook shrinks toward the 54px floor (`hook.min_size`); only a line that
  cannot fit at the floor wraps. Wrapping first broke "Reasons to follow|or unfollow
  me" into "Reasons to / follow / or unfollow me". The cost: an over-long line now
  renders small instead of on two lines ("bought a spreadsheet", 20 characters, sets
  the hook at 88px). Break lines yourself at about 16 characters.

## Reframing

- iPhone clips are often 4K landscape (3840x2160) with `rotation: 90` metadata,
  i.e. actually portrait. Modern ffmpeg auto-rotates on decode, so
  `scale=...:force_original_aspect_ratio=increase,crop=1080:1920` yields correct
  vertical framing with no manual rotate. Confirm orientation by extracting one
  frame and looking at it before assuming.

## Quick QA frame check

Pull frames and eyeball framing, caption position, and hook placement:
```bash
for t in 1 5 12 20 26; do
  ffmpeg -nostdin -y -ss $t -i final.mp4 -frames:v 1 /tmp/qa_$t.png \
    -hide_banner -loglevel error
done
```

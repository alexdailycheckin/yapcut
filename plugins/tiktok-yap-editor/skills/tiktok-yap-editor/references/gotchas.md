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
- **Quiet words overlap pause energy.** A softly-spoken word (a trailing
  "period", a fading "time") can measure quieter than the ambient pauses around
  it, so any energy threshold will mistake it for silence and clip it. Two
  defenses, both in `cut.py`: the last speech run of every clause is force-
  extended to the clause end, and clauses with no detected speech are kept
  whole. If a specific quiet word still gets clipped, give it its own narrow
  clause in `clauses.json`.
- **Diagnosing a specific word.** When unsure where a word actually is, scan RMS
  in small windows rather than trusting whisper:
  ```bash
  for t in $(seq 4.0 0.15 6.0); do
    echo -n "$t "; ffmpeg -nostdin -ss $t -t 0.15 -i audio/clip.wav \
      -af volumedetect -f null - 2>&1 | grep mean_volume
  done
  ```
  Speech is typically ~-24 dB, pauses ~-35 dB, quiet words land in between.

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

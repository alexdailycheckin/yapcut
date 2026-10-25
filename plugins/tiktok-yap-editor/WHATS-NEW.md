# What's new in the YapCut editor

The first session after an update shows the entries you have not seen yet, once, and checks
what your machine still needs for them (`hooks/whats_new.py`, run by the plugin's session-start
hook). Newest first. Each entry says what changed and what you have to do to get it.

## 3.8.2: faster pause checks

**What's new.** The step that double-checks every pause before cutting it now listens to longer
stretches of audio at once and reuses them, so a talking-head cut with lots of pauses finishes in
about half the time it took in 3.8.1.

**What you need to do.** Nothing.

## 3.8.1: pauses under wind get cut

**What's new.** Filming outside used to leave long pauses in the cut when the wind was as loud
as your voice, and someone had to split the clips by hand. The editor now finds those pauses
from what you said, checks each one twice before cutting it, and cuts them. The pause check now
sees them too, with the same double check, so a cut that still has one stops there instead
of passing.

**What you need to do.** Nothing. Re-cut a windy video to get it.

## 3.8.0: faster batches, fewer false alarms

**What's new.** Three changes aimed at the hours a batch used to take:

- The script settles its own repeats. When your script says "they poke at it" twice, the
  repetition checks no longer stop the build for it, and a deliberate repeat you listened to can
  be cleared with a reason instead of switching the whole check off.
- Captions take the script's spelling, case and punctuation for every word you said from it,
  so "fineman" comes out Feynman before the caption check runs. Words you ad-libbed still come to
  you for a yes.
- A batch runs as one queue (`yapbatch.py`): each video is cut, checked and rendered in turn, a
  video that fails a check is set aside with the reason while the rest carry on, and
  `batch_status.txt` shows where everything is with an ETA. The slowest check now reuses its work
  across re-cuts of the same takes, so a re-cut costs about two minutes of it instead of 13 to 22.

**What you need to do.** Nothing. Your next batch uses all three.

## 3.7.13: one word at a time

**What's new.** A packaged video can show its captions one word at a time, each word on screen
exactly while you say it.

**What you need to do.** Nothing for your current videos. Add `ep.cap_words = 1` to a spec to get
single-word captions.

## 3.7.12: the music ducks under your voice again

**What's new.** HeyGen moved the script that lowers the music under your voice into its media-use
skill. The editor now finds it there, so the music bed drops under your voice again instead of
playing at one flat level.

**What you need to do.** If your music has been playing flat, install the skill once:
`npx skills add heygen-com/hyperframes -s media-use -g -a claude-code`, then rebuild the video.

## 3.7.11: HDR clips look the way your phone shows them

**What's new.** 3.7.10 converted HDR clips too bright: faces came out flat and pinkish. The
conversion now matches the way your iPhone and Mac show the same clip on a normal screen, within
a few levels of brightness, with the same cut points as before.

**What you need to do.** Nothing. Re-cut any HDR video you made with 3.7.10.

## 3.7.10: HDR iPhone clips work as they are

**What's new.** Clips your iPhone shot in HDR (10-bit, HLG) used to go into the cut still marked
HDR, and the HyperFrames render then filled the disk with raw frames. The editor now converts
them to normal SDR color inside the cut, at the brightness your SDR clips have, with the same cut
points. SDR clips are cut exactly as before.

**What you need to do.** Nothing, as long as `preflight.py` shows the zscale and tonemap filters
as OK. If it does not, install the full ffmpeg build it names.

## 3.7.9: tighter pauses

**What's new.** The editor now cuts every pause of half a second or more (it was 0.55), and a
short phrase only joins its neighbour across half a second of quiet (it was 0.75), so talking
head cuts feel faster with no change to how words are kept.

**What you need to do.** Nothing. To keep the old pace on one video, pass `--min-gap 0.55
--bridge-max 0.75` to `yapcut.py`.

## 3.7.8: a carved music bed is kept between builds

**What's new.** If you grade your footage with `hyperframes media-treatment --apply` before you
carve the music bed, the editor reported the carve as failed and kept no copy of it, so every
rebuild carved the bed again. The carve was in your video all along. Now the carved bed is found
and kept, and later builds reuse it.

**To get it.** Nothing to do. The next carve is saved, and the builds after it reuse it.

## 3.7.7: captions land on each word, and a missing script stops the build

**What's new.** Caption words were never timed by the alignment the editor asked for, so fast
words bunched up and a whole group appeared at once. Words are now timed one by one and checked
against your voice. The editor uses whisper's large model when you have it, which hears names
and word endings better. A scripted video with no `<out>_script.txt` now fails the caption gate
instead of skipping it.

**To get it.** For the large model (1.6 GB), run
`curl -L -o ~/.whisper-models/ggml-large-v3-turbo.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin`.
Without it the editor keeps using small.en, with the new timing. Save the script you read as
`<out>_script.txt` next to the build before the gates run. For a take with no script, set
`YAP_UNSCRIPTED=1`. A video cut before this update keeps its old word times until you
re-transcribe it, which means running yapfull without `YAP_FROM_CUT=1`.

## 3.7.6: captions stop doubling up between groups

**What's new.** In a HyperFrames package, two caption groups used to sit on top of each other
for one frame at most handovers. Now one group leaves as the next one shows.

**To get it.** Rebuild and re-render a package to pick it up. A video already rendered keeps
the doubled frames.

## 3.7.5: quiet sentence endings stay in the cut

**What's new.** The cutter keeps a sentence that trails off, like a fading "stopped tomorrow" or
a soft "do it." just after the line before it, without splitting the clause by hand.
`protect_tail` now works on a clause that runs to the end of the take: it used to trim the last
word anyway. Cuts come out a little longer.

**To get it.** Nothing to do. A video already cut keeps its old cut until you run yapfull on it
again. If you rerun an old plan, check its last clause: `protect_tail` now keeps everything to
the clause end, the silence after the last word included, so drop the flag unless that word is
very quiet. The Anima app still cuts the old way until it updates.

## 3.7.4: the rulebook drops a setting nothing reads

**What's new.** `rules.json` loses `cut.edge.tail_extra_s`, the limit the cutter used before
3.7.3. The Anima phone app now keeps soft words the way the Mac has since 3.7.3, so neither
editor reads the setting any more. Your cuts do not change.

**To get it.** Nothing to do on the Mac. If you use the Anima app, update it: a build from before
this change keeps the rules it already has and stops picking up new ones.

## 3.7.3: soft words stay in the cut

**What's new.** The cutter keeps a softly spoken word next to a pause, like a quiet "If" before
a line or a fading "from" at the end of one, instead of cutting it as silence. Cuts come out a
fraction of a second longer.

**To get it.** Nothing to do. A video already cut keeps its old cut until you run yapfull on it
again.

## 3.7.2: logo chips show the real logo

**What's new.** `logo_fetch.py --page` reads the logo the Wikipedia article itself shows, so a
chip no longer comes out as Wikipedia's gold category icon or a company's old logo.

**To get it.** Nothing to do. If a chip from an earlier batch shows a gold coin, fetch it again.

## 3.7.1: the chart grows with the list

**What's new.** The two-sided chart opens one row at a time as you say it, instead of starting as
a tall empty card, and its type is bigger. A number on the first line of a hook now shows its
real value at frame zero.

**To get it.** Nothing to do.

## 3.7.0: a two-sided chart for "if you want, you need" videos

**What's new.** `ep.pairs(("If you want", "You need"), rows, t0, t1)` in a HyperFrames spec
draws a two-column chart above your head. Each row appears as you say it: the left side on "if
you want", the right side on "you need", the newest one in your accent colour.

**To get it.** Nothing to do. Use it in the spec of any video built from paired lines.

## 3.6.0: your take stays whole, brand objects, time stamps

**What's new.**

- **The opinion slot.** When a script ends in your own take, the editor keeps it whole (only
  restarts and dead air come out), labels it "My take" on screen, and the caption check stops
  flagging your own words as garbles.
- **Your icon kit.** Put brand objects in `<workspace>/assets/icons/` with a `library.json` and
  `ep.icon("check", ...)` pops one in on the line that names it.
- **Day-in-the-life and break clips.** `scripts/clip_clock.py` reads when each clip was filmed,
  and `ep.stamp("07:40", ...)` puts the time on screen, hour by hour.
- **Explainers** get a long-form recipe: 90 to 180 seconds, a numbered badge per step.

**To get it.** Nothing to install. The icon kit is yours to make; without one, `ep.icon` says so.

## 3.5.1: you hear about updates now

**What's new.** The first session after an update tells you what changed and what your machine
still needs to use it, once. Nothing else changed.

**To get it.** Nothing. To read the list again, ask Claude "what's new in yapcut", or run
`python3 hooks/whats_new.py --all` inside the plugin folder.

## 3.5.0: HyperFrames packaging

**What's new.** A finished cut can now be packaged as a designed video. Receipt cards build
while you say the line: headlines, counters that count up to the number you say, flows, quotes
underlined as you say them, charts. The hook is on screen at frame zero, captions pop word by
word, the camera pushes in slowly on your key lines, every on-screen event gets its own sound,
and a music bed ducks under your voice. It uses your colours, font and contact lines from
`brand-config.json`. The cut itself does not change.

**To get it.**
1. Node 22 or newer (`node --version`; on a Mac, `brew install node`). Rendering runs through
   `npx hyperframes`, which is free, open source and needs no account.
2. The sounds need a free HeyGen account. Install their CLI with
   `curl -fsSL https://static.heygen.ai/cli/install.sh | bash`, sign in with
   `heygen auth login`, then ask Claude to fetch the YapCut sound library. With no account, ask
   for the offline library instead: it works, and it sounds thinner.
3. Optional: `npx skills add heygen-com/hyperframes`, so the music ducks under your voice.
   Without it the music plays at a steady low volume.
4. After a yapcut run, ask Claude to "package <video> in HyperFrames". It plans the cards from
   your transcript, shows you a frame of every card, and renders when you say go.

Nothing you have already made changes, and plain yapcut runs work as before.

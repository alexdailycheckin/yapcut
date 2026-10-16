# What's new in the YapCut editor

The first session after an update shows the entries you have not seen yet, once, and checks
what your machine still needs for them (`hooks/whats_new.py`, run by the plugin's session-start
hook). Newest first. Each entry says what changed and what you have to do to get it.

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

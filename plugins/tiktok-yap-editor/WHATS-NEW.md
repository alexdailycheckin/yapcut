# What's new in the YapCut editor

The first session after an update shows the entries you have not seen yet, once, and checks
what your machine still needs for them (`hooks/whats_new.py`, run by the plugin's session-start
hook). Newest first. Each entry says what changed and what you have to do to get it.

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

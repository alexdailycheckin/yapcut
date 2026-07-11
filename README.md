# YapCut by alexmuresan.com

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)

**A two-part short-form content engine for Claude Code.** It takes you from "I don't know
what to post" all the way to a finished vertical video, and it is **creator-agnostic**: on
first use each part interviews you about your niche and brand, then works to yours.

1. **Outlier Radar** researches your niche every week. It finds short-form videos that went
   viral (specifically, ones that beat their own creator's baseline by 5x or more, so you
   are copying a proven *mechanic*, not chasing follower counts), extracts the hook and
   format that made them work, pours in fresh substance from *your* subject, and writes ~10
   ready-to-film scripts per lane to a self-contained tracked dashboard.
2. **TikTok Yap Editor** turns your raw phone clips into a finished, captioned, feed-ready
   vertical video, either a talking-head cut or a day-in-the-life storytelling montage.

Pick a script on the dashboard, shoot it, drop the clips on the editor. That is the loop.

## What you get, end to end

- **Discovery, once.** Both parts walk you through setup the first time (your niche, the
  accounts you want to track, your voice, your brand fonts/colours/handle) and save a config,
  so everything after is in your world, not a template's.
- **Weekly research on tap.** Say "run outlier radar" and it does the scan, the mechanic
  extraction, and the writing, then rebuilds your dashboard.
- **Two content lanes**, which you can rename:
  - **Industry** (your primary lane): teach real, concrete value in your niche.
  - **Viral videos** (your secondary lane): lighter reach plays that borrow a proven viral
    mechanic to travel beyond your niche. Optional, but this is where growth comes from.
- **A tracked dashboard** (`dashboard.html`): every script is a card with a bold **HOOK**,
  the **SCRIPT** laid out one sentence per line like a teleprompter, and an optional **CTA**.
  Mark things Filmed / Posted, log views, ignore what you won't use. Your tracking lives in
  the browser, so regenerating each week never wipes it.
- **Two editor modes:**
  - **Mode A, talking-head:** transcript-first cut, zero dead air, word-by-word captions in
    your brand, and a burned on-screen hook.
  - **Mode B, day-in-the-life:** you film loose b-roll, it scripts the voiceover beat by beat,
    locks the picture to it, and burns a record-to-picture guide so you record the VO in sync.

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

## Install (Claude Code plugin, recommended)

```
/plugin marketplace add alexdailycheckin/yapcut
/plugin install outlier-radar
/plugin install tiktok-yap-editor
```

## Install (manual copy)

```
git clone https://github.com/alexdailycheckin/yapcut.git
cp -R yapcut/plugins/outlier-radar/skills/outlier-radar        ~/.claude/skills/
cp -R yapcut/plugins/tiktok-yap-editor/skills/tiktok-yap-editor ~/.claude/skills/
```

## One-time editor setup (for the video side)

```
bash ~/.claude/skills/tiktok-yap-editor/scripts/setup_fonts.sh   # libass ffmpeg + fonts
python3 ~/.claude/skills/tiktok-yap-editor/scripts/preflight.py  # should print ALL GOOD
```

## Use

- **Ideas:** in Claude Code say "run outlier radar". First time, it interviews you and creates
  your workspace (default `~/outlier-radar/`) with `radar-config.json` inside; after that it
  researches and writes your weekly scripts, then opens the dashboard. Fill `positioning.md`,
  `methods.md` (your own how-to knowledge, so educational scripts teach a real step), and
  optionally `leaders-to-study.md` and `watch-accounts.md` in the workspace from the provided
  templates.
- **Close the loop:** after posting, log views on the dashboard and click "Export performance",
  saving the file into `<workspace>/performance/`. The next weekly run reads it and doubles down
  on what worked.
- **Edit:** drop a folder of `.MOV`/`.mp4` clips and say "make a tiktok from these" (Mode A) or
  "script my voiceover and cut my day clips" (Mode B). First run asks the brand questions and
  saves `brand-config.json`.

## Requirements (editor)

- macOS with Homebrew, Python 3, `ffmpeg`/`ffprobe` with libass (the setup script installs it),
  `whisper-cli` (whisper.cpp) + a ggml model. Outlier Radar itself just needs Claude Code with
  web access.

## What's inside

- `plugins/outlier-radar/skills/outlier-radar/` — the research playbook (`SKILL.md`),
  `build_dashboard.py`, `build_carousels.py`, `references/` (templates you fill + the hook
  library + the mechanic library), `radar-config.example.json`, and a bundled example week.
- `plugins/tiktok-yap-editor/skills/tiktok-yap-editor/` — the editor playbook + deterministic
  scripts (`yapcut.py`, `stutter_check.py`, `build_ass.py`, `brollcut.py`, `vo_guide.py`, and
  the drivers), `brand-config.example.json`.

Your filled-in config, weekly batches, dashboard, and exports live in your workspace (default
`~/outlier-radar/`), outside the repo and the plugin folder; only templates and the example
week ship.

## Author

Created by **Alex Mureșan** — [alexmuresan.com](https://alexmuresan.com). If this is useful, a
credit and a link back are appreciated.

## License

Licensed under **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**
(full text in [LICENSE](LICENSE); attribution in [NOTICE](NOTICE)).

- **Free to use, modify, and share for noncommercial purposes** — personal projects, learning,
  research, hobby use, nonprofits, schools.
- **You must give credit.** Any copy, fork, or derivative has to credit
  "Alex Mureșan (https://alexmuresan.com)" and keep the notice.
- **No commercial use under this license.** Selling it, building a paid product or service on
  it, or running it inside a for-profit company's operations needs a separate commercial
  license. Contact **alex@alexmuresan.com**.

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

## What's new in 2.0

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

- **Ideas:** in Claude Code say "run outlier radar". First time, it interviews you and saves
  `radar-config.json`; after that it researches and writes your weekly scripts, then opens the
  dashboard. Fill `positioning.md`, `methods.md` (your own how-to knowledge, so educational
  scripts teach a real step), and optionally `leaders-to-study.md` and `watch-accounts.md` from
  the provided templates.
- **Edit:** drop a folder of `.MOV`/`.mp4` clips and say "make a tiktok from these" (Mode A) or
  "script my voiceover and cut my day clips" (Mode B). First run asks the brand questions and
  saves `brand-config.json`.

## Requirements (editor)

- macOS with Homebrew, Python 3, `ffmpeg`/`ffprobe` with libass (the setup script installs it),
  `whisper-cli` (whisper.cpp) + a ggml model. Outlier Radar itself just needs Claude Code with
  web access.

## What's inside

- `plugins/outlier-radar/skills/outlier-radar/` — the research playbook (`SKILL.md`),
  `build_dashboard.py`, `references/` (templates you fill), `radar-config.example.json`.
- `plugins/tiktok-yap-editor/skills/tiktok-yap-editor/` — the editor playbook + deterministic
  scripts (`yapcut.py`, `stutter_check.py`, `build_ass.py`, `brollcut.py`, `vo_guide.py`, and
  the drivers), `brand-config.example.json`.

Your filled-in config and generated weeks/dashboard stay local (see `.gitignore`); only the
templates ship.

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

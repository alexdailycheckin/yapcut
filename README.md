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

## Install it on your own computer

You need [Claude Code](https://claude.com/claude-code). Two routes.

**Route 1, the plugin marketplace.** Type these three commands inside Claude Code:

```
/plugin marketplace add alexdailycheckin/yapcut
/plugin install outlier-radar
/plugin install tiktok-yap-editor
```

**Route 2, from git, with Claude doing the setup.** Copy the prompt below, paste it into
Claude Code, and it clones the repo, installs both skills, pulls the video dependencies,
and verifies the install before telling you it is done.

```text
Install YapCut (Alex Mureșan's short-form content engine) from git into my Claude Code
setup, then verify it actually runs. Do the work, don't just print instructions.

1. Clone and copy the two skills to user level so they load in every project:
   git clone https://github.com/alexdailycheckin/yapcut.git ~/yapcut
   mkdir -p ~/.claude/skills
   cp -R ~/yapcut/plugins/outlier-radar/skills/outlier-radar ~/.claude/skills/
   cp -R ~/yapcut/plugins/tiktok-yap-editor/skills/tiktok-yap-editor ~/.claude/skills/

2. Install the video editor dependencies (macOS + Homebrew required):
   bash ~/.claude/skills/tiktok-yap-editor/scripts/setup_fonts.sh
   brew install whisper-cpp
   mkdir -p ~/.whisper-models
   curl -L -o ~/.whisper-models/ggml-small.en.bin https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin
   pip3 install Pillow fonttools

   setup_fonts.sh installs a libass-enabled ffmpeg (ffmpeg-full) plus the caption fonts
   (Montserrat Black/ExtraBold, Anton, Bricolage Grotesque ExtraBold, Space Mono). It is
   idempotent. If a later `brew upgrade` relinks the minimal ffmpeg and captions break,
   re-run: brew link --overwrite --force ffmpeg-full

3. Verify before you tell me anything is done:
   python3 ~/.claude/skills/tiktok-yap-editor/scripts/preflight.py
   It must print ALL GOOD. Every failed check prints its own fix hint. Apply the hints and
   re-run until it is green. If something cannot be fixed, say exactly which check failed
   and what still works without it.

4. Load the new skills without killing the session: tell me to run /reload-skills myself
   (you cannot run slash commands for me). Confirm both outlier-radar and tiktok-yap-editor
   are loaded before moving on.

5. Then report the preflight output, what got installed, and end your message with the
   exact sentence I should type next, on its own line, which is:

   run outlier radar

   That is what starts onboarding. Reloading the skills only makes them available, it does
   not begin anything, so nothing happens until I say it. First run interviews me about my
   niche, creates the workspace at ~/outlier-radar/, asks which day and time I want the
   weekly run, writes the first real batch, and opens the dashboard on my own scripts.

   Also tell me the editor entry point: drop a folder of .MOV/.mp4 clips and say either
   "make a tiktok from these" (Mode A, talking head) or "script my voiceover and cut my day
   clips" (Mode B, day in the life). First run asks brand questions, saves brand-config.json.

Notes:
- If onboarding gets interrupted before it finishes, say "run outlier radar" again and it
  resumes from the first unanswered question rather than starting over.
- Outlier Radar itself needs nothing but Claude Code with web access. Everything in step 2
  is for the editor only, so if I only want the research engine, stop after step 1.
- My data (config, weekly batches, dashboard, exports) lives in ~/outlier-radar/, outside
  the skill folder, so reinstalls never touch it. Override with OUTLIER_RADAR_HOME or --dir.
- License is CC BY-NC 4.0: free to use, modify and share for noncommercial purposes, must
  credit "Alex Mureșan (https://alexmuresan.com)". Commercial use needs a separate license
  via alex@alexmuresan.com.
```

Either route, the research side works anywhere Claude Code runs. **The editor side is
macOS + Homebrew**: the font setup script targets `~/Library/Fonts` and preflight looks for
a macOS system font, so on Linux or Windows you get Outlier Radar and the editor will not
pass preflight. Step-by-step detail is in [Install details](#install-details) below.

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
- **A LinkedIn layer, if you want it** (optional, `linkedin_twins` in your config): every
  primary-lane script also gets a written LinkedIn post. `select_linkedin.py` then picks each
  one's shape from its substance, checks the week has a working mix rather than five of the
  same thing, flags the posts that should be carousels, and tells you what order to publish
  in so the perishable ones go first.

## Use

- **Ideas:** in Claude Code say "run outlier radar". First time, it interviews you, creates
  your workspace (default `~/outlier-radar/`) with `radar-config.json` inside, asks which day
  and time you want the weekly run, then **writes your first real batch, sets up the recurring
  run, and opens the dashboard on it** before it finishes. After that it fires on your schedule,
  or say "run outlier radar" any time. Fill `positioning.md`,
  `methods.md` (your own how-to knowledge, so educational scripts teach a real step), and
  optionally `leaders-to-study.md` and `watch-accounts.md` in the workspace from the provided
  templates.
- **LinkedIn (optional):** before you publish the week's LinkedIn posts, run
  `python3 select_linkedin.py`. It prints each post's shape and score, the week's verdict (job
  mix, character bands, carousel opportunities) and a dated publishing order with the reason
  for each slot. Declare `news_peg_days`, `evergreen`, `arguable`, `executable`,
  `ordering_claim` and `friction_story` on a twin and it stops guessing.
- **Close the loop:** after posting, log views on the dashboard and click "Export performance",
  saving the file into `<workspace>/performance/`. The next weekly run reads it and doubles down
  on what worked.
- **Edit:** drop a folder of `.MOV`/`.mp4` clips and say "make a tiktok from these" (Mode A) or
  "script my voiceover and cut my day clips" (Mode B). First run asks the brand questions and
  saves `brand-config.json`.

## Install details

<a id="install-details"></a>
The paste-in prompt at the top does all of this for you. Here it is by hand.

**1. Copy the skills** (or use the `/plugin` route at the top, which keeps them updated
with the marketplace):

```
git clone https://github.com/alexdailycheckin/yapcut.git
cp -R yapcut/plugins/outlier-radar/skills/outlier-radar        ~/.claude/skills/
cp -R yapcut/plugins/tiktok-yap-editor/skills/tiktok-yap-editor ~/.claude/skills/
```

Then run `/reload-skills` in Claude Code so both are picked up without restarting the
session (`/reload-plugins` if you took the marketplace route instead). Outlier Radar is
ready at this point: say **`run outlier radar`** to start onboarding. Loading a skill does
not start it, so nothing happens until you say that.

**2. One-time editor setup** (video side only):

```
bash ~/.claude/skills/tiktok-yap-editor/scripts/setup_fonts.sh   # libass ffmpeg + fonts
brew install whisper-cpp                                          # transcription
mkdir -p ~/.whisper-models && curl -L -o ~/.whisper-models/ggml-small.en.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin
pip3 install Pillow fonttools
```

**3. Verify.** This must print `ALL GOOD`; each failed check prints its own fix:

```
python3 ~/.claude/skills/tiktok-yap-editor/scripts/preflight.py
```

## Requirements (editor)

- macOS with Homebrew, Python 3, `ffmpeg`/`ffprobe` with libass (the setup script installs it),
  `whisper-cli` (whisper.cpp) + a ggml model. Outlier Radar itself just needs Claude Code with
  web access.

## What's inside

- `plugins/outlier-radar/skills/outlier-radar/`: the research playbook (`SKILL.md`),
  `build_dashboard.py`, `build_carousels.py`, `select_linkedin.py` (the LinkedIn shape and
  order picker), `references/` (templates you fill + the hook library + the mechanic library
  + `linkedin-selector.md`), `radar-config.example.json`, and a bundled example week.
- `plugins/tiktok-yap-editor/skills/tiktok-yap-editor/`: the editor playbook + deterministic
  scripts (`yapcut.py`, `stutter_check.py`, `build_ass.py`, `brollcut.py`, `vo_guide.py`, and
  the drivers), `brand-config.example.json`.

Your filled-in config, weekly batches, dashboard, and exports live in your workspace (default
`~/outlier-radar/`), outside the repo and the plugin folder; only templates and the example
week ship.

## What's new in 2.6

**Outlier Radar now picks each LinkedIn post's own shape and tells you what order to publish
in.** A twin used to copy the video's `post_type`, which gave you a week of identical posts.
`select_linkedin.py` picks the FEED shape from the substance instead, reports the week's job
mix and character bands, flags posts that should be carousels, and orders the week by how
fast each item loses value rather than by how good it is.

Full notes for this and every earlier release: **[CHANGELOG.md](CHANGELOG.md)**.

## Author

Created by **Alex Mureșan** ([alexmuresan.com](https://alexmuresan.com)). If this is useful, a
credit and a link back are appreciated.

## License

Licensed under **Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)**
(full text in [LICENSE](LICENSE); attribution in [NOTICE](NOTICE)).

- **Free to use, modify, and share for noncommercial purposes**: personal projects, learning,
  research, hobby use, nonprofits, schools.
- **You must give credit.** Any copy, fork, or derivative has to credit
  "Alex Mureșan (https://alexmuresan.com)" and keep the notice.
- **No commercial use under this license.** Selling it, building a paid product or service on
  it, or running it inside a for-profit company's operations needs a separate commercial
  license. Contact **alex@alexmuresan.com**.

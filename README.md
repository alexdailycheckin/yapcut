# TikTok Yap Editor

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)

A standalone Claude Code skill that turns raw talking-head phone clips into finished,
post-ready vertical TikTok / Reels / Shorts: transcript-first story cut, zero-dead-air
jump-cut tightening, word-by-word burned captions in **your** brand, a burned text hook,
an optional spoken-outro CTA with a contact block, feed loudness, and a QA pass.

It is **brand-agnostic**: the first time you use it, it interviews you about your brand
(niche, fonts, colours, handle, contact, CTA) and saves a `brand-config.json`, then every
edit is styled in your brand. No AI-generated assets, covers come from real frames.

This repo contains nothing but this one skill and works end to end on its own.

## Install (Claude Code plugin, recommended)

```
/plugin marketplace add alexdailycheckin/alex-gtm-yap-editor
/plugin install tiktok-yap-editor
```

## Install (manual copy)

```
git clone https://github.com/alexdailycheckin/alex-gtm-yap-editor.git
cp -R alex-gtm-yap-editor/plugins/tiktok-yap-editor/skills/tiktok-yap-editor ~/.claude/skills/
```

## One-time environment setup

```
bash ~/.claude/skills/tiktok-yap-editor/scripts/setup_fonts.sh   # libass ffmpeg + fonts
python3 ~/.claude/skills/tiktok-yap-editor/scripts/preflight.py  # should print ALL GOOD
```
If preflight says a whisper model is missing, it prints the exact `curl` to download one
(`small.en` is the right balance).

## Use

In Claude Code, drop a folder of `.MOV`/`.mp4` selfie clips and say something like
"make a tiktok from these clips" or "tighten this yap". On first run it asks the brand
questions and saves your `brand-config.json`; after that it just edits in your brand.

## Requirements

- macOS with Homebrew (the setup script uses `brew`)
- Python 3, `ffmpeg`/`ffprobe` with libass (installed by the setup script)
- `whisper-cli` (whisper.cpp) + a ggml model
- Internet on first setup (fonts download from fontsource)

## What's inside

- `plugins/tiktok-yap-editor/skills/tiktok-yap-editor/SKILL.md` — the playbook
- `.../scripts/` — the deterministic tools (`yapcut.py` single-pass cutter, `segmenter.py`,
  `yapfull.sh` driver, captions, compose, cover, finalize, font setup)
- `.../references/` — tuning notes
- `.../brand-config.example.json` — the config schema (or let the first-run interview write it)

## Author

Created by **Alex Mureșan** — [alexmuresan.com](https://alexmuresan.com). Go-to-market
distribution. If this is useful, a credit and a link back are appreciated.

## License

Licensed under **Creative Commons Attribution-NonCommercial 4.0 International
(CC BY-NC 4.0)** (full text in [LICENSE](LICENSE); attribution in [NOTICE](NOTICE)).

In plain English:

- **Free to use, modify, and share for noncommercial purposes** — personal projects,
  learning, research, hobby use, nonprofits, schools.
- **You must give credit.** Any copy, fork, or derivative has to credit
  "Alex Mureșan (https://alexmuresan.com)" and keep the notice. That is the attribution
  requirement, not optional.
- **No commercial use under this license.** Selling it, building a paid product or service
  on it, or running it inside a for-profit company's operations needs a separate commercial
  license. Contact **alex@alexmuresan.com**.

This keeps it open for people to use and learn from while reserving the commercial rights.
A license does not stop a determined copier, but it makes credit a legal obligation that
legitimate users and companies honor.

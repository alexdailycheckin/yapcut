# YapCut by alexmuresan.com

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)

**A measured-first short-form content engine for Claude Code.** Its job is to make you the
person your audience thinks of for one subject, and it is judged on what gets posted and
answered, never on how many scripts it writes. Creator-agnostic: on first use it interviews you
about who should recognise you and for what, what only you can say, and how you actually talk,
then works to that.

1. **Outlier Radar** researches your niche every week: it finds short-form videos that beat
   their own creator's baseline by 5x or more (a proven *mechanic*, not a follower count),
   extracts the hook and format, pours in substance from *your* subject and *your* proof, and
   writes scripts and LinkedIn posts to the filming slots you actually have, on a tracked
   dashboard. Each week starts by reading last week's numbers.
2. **Lead Magnet Report** turns one category's measured data into a comment-gated document
   post: the finding free in the feed, the raw sheet behind a comment.
3. **TikTok Yap Editor** turns your raw phone clips into a finished, captioned, gated vertical
   video, talking-head or day-in-the-life, with an edit record that joins the cut to the post.

Pick a script, shoot it, drop the clips on the editor, paste your numbers back. That is the loop.

## Install (Claude Code)

```
/plugin marketplace add alexdailycheckin/yapcut
/plugin install outlier-radar@yapcut
/plugin install tiktok-yap-editor@yapcut
```

Then say **`run outlier radar`** to start onboarding. Loading a skill does not start it. There
is one install route on purpose: a copy under `~/.claude/skills/` shadows any plugin install
silently and never updates, so this README no longer offers it.

**Or paste this into Claude Code** and let it do the setup and verify it:

```text
Install YapCut (Alex Mureșan's short-form content engine) into my Claude Code setup and
verify it runs. Do the work, don't just print instructions.

1. Add the marketplace and install both plugins:
   /plugin marketplace add alexdailycheckin/yapcut
   /plugin install outlier-radar@yapcut
   /plugin install tiktok-yap-editor@yapcut
   Find the installed editor's path in ~/.claude/plugins/installed_plugins.json.

2. Install the editor's dependencies (macOS + Homebrew): run its scripts/setup_fonts.sh,
   then: brew install whisper-cpp; mkdir -p ~/.whisper-models; download
   https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.en.bin into it;
   pip3 install -r <repo>/requirements.txt (Pillow).

3. Verify: python3 <editor>/scripts/preflight.py must print ALL GOOD. Apply its fix hints and
   re-run until green. If something cannot be fixed, say which check failed and what still
   works without it.

4. Tell me to run /reload-plugins myself, then end with the exact sentence I type next:

   run outlier radar

   First run interviews me (who should recognise me and for what, what only I can say, where
   I already talk unscripted), creates the workspace at ~/outlier-radar/, writes the first
   real batch to my filming slots, sets up the weekly run, and opens the dashboard.
```

The research side works anywhere Claude Code runs. **The editor is macOS + Homebrew** (fonts,
libass ffmpeg, whisper.cpp); on Linux or Windows you get Outlier Radar and the editor will not
pass preflight.

## What you get, honestly, by day 7

- **A workspace** (`~/outlier-radar/`) that is yours: `radar-config.json` with your audience,
  proof, quantity and voice settings, `positioning.md`, `methods.md`, `leaders-to-study.md`,
  your voice corpus, your weeks, your performance ledger. Plugin updates never touch it.
- **One batch written to your filming slots** (default 3 video slots plus 2 spares and 5
  LinkedIn slots for a new creator), each script gated by machine (`radar_gate.py`: schema,
  voice, hooks, sources, visuals) before you see it, on a dashboard with an Ammo tab for your
  daily comments, a proof chip on every card, and this week's one measured question.
- **A weekly rhythm** that starts by pasting your analytics table (five minutes) and reads the
  result before writing anything. Skip the paste and the digest says so and the batch ships.
- **Not yet, by design:** your voice will be thin until you have harvested 20 to 30 minutes of
  yourself talking unscripted (calls, voice notes, a podcast); `methods.md` holds the plays
  only you can supply; the secondary "viral" lane is off for the first four weeks.

## What it needs from you in week one

| Ask | Time | Why |
|---|---|---|
| One sentence: who should recognise you, and for what | 2 min | every gate, the selector and the north star read it |
| Five things you have done a competitor cannot claim, three plays you run, ten lines you would never say | 20 min | the un-copyable material; adjectives about your voice produce pastiche |
| Transcripts of you talking unscripted (or a 20 to 30 minute phone recording) | 0 to 30 min | the voice is measured, never described |
| How many videos you will actually film this week | 1 min | scripts you do not film teach the loop nothing |
| Paste your analytics table once a week | 5 min | the loop |

## Use

- **Ideas:** "run outlier radar". Weekly by schedule or on demand. "hot drop" for a same-day
  post when something breaks in your niche.
- **Numbers:** paste the LinkedIn activity table or the TikTok Studio table when asked;
  `ingest_feed.py` turns it into rows, `log_perf.py --report` reads it back and writes
  `performance/last-report.md`.
- **LinkedIn:** `select_linkedin.py` picks each post's shape, job and posting day from its
  substance and from what your own numbers have learned.
- **Distribution:** the daily block (comments with receipts, connection requests, the reply
  block), day-0 posts, the people ledger, callback and promise: `references/distribution.md`.
- **Edit:** drop a folder of clips and say "make a tiktok from these" (Mode A) or "script my
  voiceover and cut my day clips" (Mode B). `finalize.sh` writes the edit record that joins
  the cut to the post.

## What's inside

- `plugins/outlier-radar/skills/outlier-radar/`: the playbook (`SKILL.md`, about 260 lines
  with a routing table), the gate runner and gates, the ledger scripts, `build_dashboard.py`
  plus `dashboard/`, `carousel.py`, `references/` (schema, receipts, distribution, hooks,
  LinkedIn craft, the show template), `radar-config.example.json`, a bundled example week.
- `plugins/outlier-radar/skills/lead-magnet-report/`: the report builder, the request ledger,
  the measurement law.
- `plugins/tiktok-yap-editor/skills/tiktok-yap-editor/`: the editor playbook, the gate ladder
  (`scripts/gates.sh`), `scripts/yaplib/`, the drivers, `brand-config.example.json`.
- `tests/`: a synthetic fixture that drives the editor end to end and the radar gates on the
  example week. `release.sh` is the one release command.

## What's new in 3.6.0

**The audit release.** The engine used to optimise the one stage that was never the
constraint: 157 scripts written, 22 posted, the loop run once. 3.5.0 asks who your audience is
before it asks your niche, writes to filming slots instead of a script bar, ships a gate that
actually gates, closes the loop on disk (tracking, a people ledger, learned weights, one
measured question a week), and ships the distribution doctrine. Full notes for this and every
earlier release: **[CHANGELOG.md](CHANGELOG.md)**.

## Author

Created by **Alex Mureșan** ([alexmuresan.com](https://alexmuresan.com)). If this is useful, a
credit and a link back are appreciated.

## License

**Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0)** (full text in
[LICENSE](LICENSE); attribution in [NOTICE](NOTICE)). Free to use, modify and share for
noncommercial purposes with credit to "Alex Mureșan (https://alexmuresan.com)". Commercial use,
including running it inside a for-profit company's operations, needs a separate license:
**alex@alexmuresan.com**.

---
name: outlier-radar
description: "Weekly viral-outlier research and ideation engine for any creator or brand. First use interviews you about your niche and saves a config to a local workspace. Each week it finds short-form videos that beat their own creator's baseline 5x+, extracts the transferable hook and format mechanic, and writes ~10 ready-to-film scripts per lane in your voice to a tracked dashboard. Use when the user says 'run outlier radar', 'find viral videos to copy', 'what should I post this week', 'weekly content ideas', or wants short-form video ideas for their niche."
---

# Outlier Radar

Finds short-form videos that beat their own creator's baseline by a wide margin (the
signal that a HOOK and FORMAT worked, independent of audience size), then re-skins that
proven mechanic with substance from YOUR niche. The topic is yours. The skeleton is
borrowed from something that already went viral. Output is a weekly batch of filmable
scripts on a tracked dashboard, handed off to the `tiktok-yap-editor` skill to cut.

This skill is **creator-agnostic**. It does not assume a niche, a brand, or a voice; it
learns yours once and then works to it.

## The workspace (where everything you own lives)

All mutable data lives in a **workspace directory outside the skill folder**, so plugin
updates and reinstalls never touch it. Default: `~/outlier-radar/`.

Both Python scripts and this playbook resolve the workspace in this order:
1. `--dir <path>` passed to a script
2. the `OUTLIER_RADAR_HOME` environment variable
3. the current directory, if it contains `radar-config.json`
4. `~/outlier-radar/`, if it contains `radar-config.json`
5. legacy fallback: the skill folder itself (old installs kept data next to the scripts)

The workspace holds: `radar-config.json`, `positioning.md`, `methods.md`,
`leaders-to-study.md`, `watch-accounts.md`, `mechanic-library.md` (your growing copy),
`weeks/`, `performance/`, `carousels/`, `blog-queue/`, and the generated `dashboard.html`.
The skill folder stays read-only: the playbook, the scripts, the templates in
`references/`, and a bundled example week.

## First run: discovery (do this once)

Resolve the workspace (order above). **If no `radar-config.json` exists anywhere,
interview the user** with `AskUserQuestion`, then create the workspace and write the
config there (schema in `radar-config.example.json`). Ask:

1. **Workspace location.** Where to keep their data (default `~/outlier-radar/`).
   Create it, plus `weeks/` and `performance/` inside it.
2. **Who + where.** Name and site/handle.
3. **Your niche** (one line: the subject you want to be known for) and **2-4 facets**
   (sub-angles to rotate and test across the weeks, so we learn what resonates).
4. **Voice** (how the scripts should sound: blunt, warm, contrarian, funny, etc.).
5. **Do they want to track specific accounts** for inspiration, or research the niche
   openly, or both? (Fills `watch-accounts.md` from `references/watch-accounts-template.md`.)
6. **Channels** (do they post on LinkedIn too? decides `linkedin_twins`. Do they want the
   filmed scripts turned into blog posts? decides `blog_pipeline`.)
7. **Lane labels.** Confirm the two lane names (defaults: primary "Industry", secondary
   "Viral videos") or rename to fit their world.
8. **Brand basics** (optional, used by the carousel builder): display name, an accent
   colour, fonts. Fills the `brand` block in the config; skip to use neutral defaults.

Then copy `references/mechanic-library.md` into the workspace (that copy is the one that
grows), and help them fill three working files **in the workspace** from the templates:
- `positioning.md` (from `references/positioning-template.md`) - the lens every
  primary-lane script passes through, plus what they sell and their funnel phase.
- `methods.md` (from `references/methods-template.md`) - their own how-to knowledge base, so
  educational scripts can hand the viewer a concrete do-this, not just a reframe.
- `leaders-to-study.md` (from `references/leaders-to-study-template.md`) - the roster in their
  niche to study weekly (optional, mainly for the LinkedIn scan).

## The two lanes
- **Primary lane (default "Industry"):** your core niche. Teach real, concrete value:
  educational and insight-led. An educational script that only names a problem has failed;
  it must hand over one step the viewer can run this week, sourced from `methods.md`.
- **Secondary lane (default "Viral videos"):** reach plays adjacent to your niche. Borrow a
  proven viral mechanic and ride a broader or lighter angle to go viral. Less educational,
  more entertainment/relatable/shock. Optional but powerful for growth.

Lean into **repeatable formats as recurring series** (they compound): pick 1-2 series the
creator can run weekly with fresh substance.

## Weekly routine
0. **Read the scoreboard first.** If `performance/performance-*.json` exists in the
   workspace, read the newest one. In one or two lines, name what WON (mechanics, facets,
   value types with the most views and the highest posted rate) and what flopped. Bias this
   week's batch toward the winners, retire anything that flopped twice, and consider
   promoting a winner into a named recurring series. If no export exists yet, remind the
   user once: the dashboard's **Export performance** button feeds this step; without it
   every week starts from zero.
1. **Scour for outliers (any industry).** Web-research ~12 short-form videos from roughly the
   last 2 months that massively overperformed (5x+ the creator's normal, or huge views on a
   small/mid account). Demand MECHANIC variety, not topic variety. Include a few
   contrarian/controversial ones (they travel). If `watch-accounts.md` is filled, prioritise
   those creators.
   **Verification rules (non-negotiable):** every outlier must be a real post you actually
   found at a real URL. Never invent a creator, a video, a metric, or a link. Tag every
   metric with `metric_confidence`: `"verified"` (you fetched the post or a primary source),
   `"reported"` (a credible article or aggregator states it), or `"estimated"` (inferred;
   say from what). If you cannot source a candidate, DROP it rather than guess. Fewer real
   outliers beat twelve with one fake: one invented link poisons trust in the whole board.
2. **Scour for substance in the niche.** In parallel, gather the freshest real material to pour
   into those shells: trending data, hot takes, coined terms, "everyone is wrong about X"
   angles from the last 3-4 weeks in the creator's subject.
3. **Extract the mechanic.** For each viral video capture the exact HOOK (first line / first
   3s), the STRUCTURE (2-4 beats), and WHY IT WENT VIRAL (the single transferable mechanic).
   Grow the workspace copy of `mechanic-library.md`.
4. **Marry mechanic + premise.** Each script = one proven mechanic applied to one current
   premise/data point from the niche, in the creator's voice.
5. **Write ~10 primary-lane scripts and ~10 secondary-lane scripts** in the labelled anatomy.
   Read `references/script-anatomy.md` and follow it exactly. Secondary-lane scripts must
   borrow the hook + structure from a REAL viral video (put the URL in `sources`).
6. **QA GATE.** Run the checklist in `references/script-anatomy.md` on every script. The one
   thing that fails is no payoff (a hot take with nothing under it). **A CTA is OPTIONAL:**
   default is to end on the payoff/button, because watch-through is the metric and a CTA that
   runs past the payoff makes people drop. Mark each `qa:"passed"` or `"pre-qa"`.
7. **Persist + hand off.** Write the run to `<workspace>/weeks/<YYYY-MM-DD>.json`, rebuild the
   dashboard, then route picked scripts to `tiktok-yap-editor` to cut (see Handoff).

## Script anatomy (summary; full spec in references/script-anatomy.md)
Each script is written in labelled parts: `title`, `borrows`, `carries`, `text_hook`
(~6-word on-screen overlay, NOT spoken; pick a family from `references/hook-library.md`),
`visual_hook` (what to show), `spoken_hook` (the opening 1-2 lines said, the dashboard
renders this BOLD as the HOOK section), `script` (verbatim spoken body), `directions`
(NOT spoken), `value` (the payoff + its type), `cta` (OPTIONAL ending). Never mash spoken
words and stage directions together. The dashboard renders the read as **HOOK (bold) /
SCRIPT / CTA (optional)**, one sentence per line.

Additional per-item fields the dashboard uses (set them all):
- `id`: STABLE, format `<lane letter>-<week>-<n>`, e.g. `d-2026-06-23-9` (d = primary
  lane, o = secondary). Browser-side tracking is keyed by id, so never renumber or reuse
  an id once a week has shipped.
- `intent`: `"educational"` or `"storytelling"` (primary lane; drives the stats bar).
- `facet`: which config facet the script tests (also the carousel cover kicker).
- `sources`: array of `{label, url}`, shown on the card as "check before posting".
- `format` + `beats[]`: only for day-in-the-life VO scripts (see script-anatomy.md);
  the dashboard renders `beats[]` as a film-this table.
- `qa`: `"passed"` or `"pre-qa"`.

## Persist to the dashboard (every run)
Write `<workspace>/weeks/<YYYY-MM-DD>.json` then run `python3 build_dashboard.py`
(from the skill folder; it finds the workspace, or pass `--dir <workspace>`). It writes
`<workspace>/dashboard.html`; open it directly. Week schema:
`{ week, positioning, distribution[], office[], linkedin[], inspiration[] }`. The two script
arrays keep the historical keys `distribution` (your PRIMARY / "Industry" lane) and `office`
(your SECONDARY / "Viral videos" lane); the tab LABELS come from `radar-config.json`
(`primary_lane.label` / `secondary_lane.label`), so users only ever see their own names.
`linkedin[]` holds the leaders-scan posts (the legacy key `gtm_linkedin` is still read).
Primary-lane items may carry an embedded `linkedin` twin `{id,type,hook_arch,body,qa,source}`
when `linkedin_twins` is on. `inspiration[]` items:
`{creator, platform, metric, metric_confidence, mechanic, link}`. Tracking (filmed / posted
/ views / ignore) lives in the browser's localStorage keyed by item id, so new weeks never
wipe past logs. Dashboard tabs: **[primary] (to film)**, **[secondary] (to film)**, **Filmed
& metrics**, **LinkedIn posts**, **Viral inspiration**.

A bundled example week ships with the skill and renders automatically until the first real
week exists, so a fresh install can open the dashboard and see the product immediately.

## The performance loop (how the engine compounds)
The dashboard's **Export performance** button writes `performance-<week>.json` with every
tracked item (status, views, link, notes, plus its mechanic, facet, intent, and value type)
across all weeks. Tell the user to save it into `<workspace>/performance/`. Step 0 of the
weekly routine reads the newest export and biases the next batch toward what actually
worked. If several runs go by with no performance file, nudge once per run, gently: the
loop is the whole point.

## Handoff to the editor (tiktok-yap-editor)
For any script the user picks, route to the `tiktok-yap-editor` skill to cut the video. That
skill has TWO modes; pick by what the footage is:
- **Mode A: talking-head yap.** The creator talks to camera. Transcript-first cut, zero
  dead-air, burned brand captions, the burned `text_hook`, optional spoken-outro CTA. This is
  the default for most scripts.
- **Mode B: VO-to-picture storytelling / day-in-the-life.** The creator films loose b-roll
  and records a voiceover to a guide. A storytelling script written as a `day-in-life-vo`
  format (a `beats[]` array of `{role, text, b_roll, target_dur}`) routes here: the beats
  become the picture-lock + a record-to-picture guide. Write at least one storytelling script
  per week in this format when it suits the idea.

## Optional layers (gated by radar-config.json)
- **LinkedIn twins** (`linkedin_twins: true`): each primary-lane script gets a written LinkedIn
  version of the same core idea, embedded as `item.linkedin`. LinkedIn is the authority lane:
  lean educational and expertise-forward, one job per post, a specific-claim hook, one CTA.
- **Leaders scan** (gated by `leaders-to-study.md` existing and filled in the workspace):
  each run, study what is working from the leaders in that roster, capture hook + structure +
  why-it-worked with citations, and turn the sharpest mechanics into that week's scripts.
  Results go in the week's `linkedin[]` array. See `references/leaders-to-study-template.md`.
- **Blog pipeline** (`blog_pipeline: true`): the dashboard's "Export week for blog" button saves
  everything marked Filmed/Posted so a downstream routine can turn films into articles. Wire
  this to your own site build; it is off by default.
- **Carousels:** flag any script "Carousel" on the dashboard, click "Export carousel queue",
  save the file into `<workspace>/carousels/`, then run `python3 build_carousels.py`. Branding
  (name, accent colour, fonts) comes from the `brand` block in `radar-config.json`.

## Quantity bar
At least ~10 scripts per lane per run. Give the creator volume to choose from, not a curated 3.

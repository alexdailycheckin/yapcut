---
name: outlier-radar
description: "Weekly viral-outlier research + ideation engine for any creator or brand. On first use it interviews you about your niche (or the accounts you want to track) and saves a radar-config.json. Each week it scours the web for short-form videos that massively overperformed their creator's own baseline (5x+ outliers, across any industry), extracts the transferable HOOK + FORMAT mechanic, gathers fresh substance in YOUR niche, and marries the two into ready-to-film scripts in your voice, written to a self-contained dashboard. Two lanes: your primary niche lane (default 'Industry', teach real value) and a secondary reach lane (default 'Viral videos', borrow a viral mechanic to go viral). Pairs with the tiktok-yap-editor skill to actually cut the videos. Use when the user says 'run outlier radar', 'find viral videos to copy', 'give me video ideas for my niche', 'what should I post this week', 'weekly content ideas', or wants viral short-form ideas tailored to their subject."
---

# Outlier Radar

Finds short-form videos that beat their own creator's baseline by a wide margin (the
signal that a HOOK and FORMAT worked, independent of audience size), then re-skins that
proven mechanic with substance from YOUR niche. The topic is yours. The skeleton is
borrowed from something that already went viral. Output is a weekly batch of filmable
scripts on a tracked dashboard, handed off to the `tiktok-yap-editor` skill to cut.

This skill is **creator-agnostic**. It does not assume a niche, a brand, or a voice; it
learns yours once and then works to it.

## First run: discovery (do this once)
Before generating anything, check for `radar-config.json` (skill root). **If it is
missing, interview the user** with `AskUserQuestion`, then write the config
(schema in `radar-config.example.json`). Ask:

1. **Who + where.** Name and site/handle.
2. **Your niche** (one line: the subject you want to be known for) and **2-4 facets**
   (sub-angles to rotate and test across the weeks, so we learn what resonates).
3. **Voice** (how the scripts should sound: blunt, warm, contrarian, funny, etc.).
4. **Do they want to track specific accounts** for inspiration, or research the niche
   openly, or both? (Fills `watch-accounts.md` from `references/watch-accounts-template.md`.)
5. **Channels** (do they post on LinkedIn too? decides `linkedin_twins`. Do they want the
   filmed scripts turned into blog posts? decides `blog_pipeline`.)
6. **Lane labels.** Confirm the two lane names (defaults: primary "Industry", secondary
   "Viral videos") or rename to fit their world.

Then help them fill three working files from the templates (keep the templates; copy to
the unsuffixed name and fill):
- `references/positioning.md` (from `positioning-template.md`) - the lens every primary-lane
  script passes through, plus what they sell and their funnel phase.
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
1. **Scour for outliers (any industry).** Web-research ~12 short-form videos from roughly the
   last 2 months that massively overperformed (5x+ the creator's normal, or huge views on a
   small/mid account). Demand MECHANIC variety, not topic variety. Include a few
   contrarial/controversial ones (they travel). If `watch-accounts.md` is filled, prioritise
   those creators.
2. **Scour for substance in the niche.** In parallel, gather the freshest real material to pour
   into those shells: trending data, hot takes, coined terms, "everyone is wrong about X"
   angles from the last 3-4 weeks in the creator's subject.
3. **Extract the mechanic.** For each viral video capture the exact HOOK (first line / first
   3s), the STRUCTURE (2-4 beats), and WHY IT WENT VIRAL (the single transferable mechanic).
   Grow `references/mechanic-library.md`.
4. **Marry mechanic + premise.** Each script = one proven mechanic applied to one current
   premise/data point from the niche, in the creator's voice.
5. **Write ~10 primary-lane scripts and ~10 secondary-lane scripts** in the labelled anatomy.
   Read `references/script-anatomy.md` and follow it exactly. Secondary-lane scripts must
   borrow the hook + structure from a REAL viral video (put the URL in `sources`).
6. **QA GATE.** Run the checklist in `references/script-anatomy.md` on every script. The one
   thing that fails is no payoff (a hot take with nothing under it). **A CTA is OPTIONAL:**
   default is to end on the payoff/button, because watch-through is the metric and a CTA that
   runs past the payoff makes people drop. Mark each `qa:"passed"` or `"pre-qa"`.
7. **Persist + hand off.** Write the run to `weeks/<YYYY-MM-DD>.json`, rebuild the dashboard,
   then route picked scripts to `tiktok-yap-editor` to cut (see Handoff).

## Script anatomy (summary; full spec in references/script-anatomy.md)
Each script is written in labelled parts: `title`, `borrows`, `carries`, `text_hook`
(~6-word on-screen overlay, NOT spoken), `visual_hook` (what to show), `spoken_hook` (the
opening 1-2 lines said, the dashboard renders this BOLD as the HOOK section), `script`
(verbatim spoken body), `directions` (NOT spoken), `value` (the payoff + its type), `cta`
(OPTIONAL ending). Never mash spoken words and stage directions together. The dashboard
renders the read as **HOOK (bold) / SCRIPT / CTA (optional)**, one sentence per line.

## Persist to the dashboard (every run)
Write `weeks/<YYYY-MM-DD>.json` then run `python3 build_dashboard.py` to regenerate
`dashboard.html` (open it directly). Week schema:
`{ week, positioning, distribution[], office[], linkedin[], inspiration[] }`. The two script
arrays keep the historical keys `distribution` (your PRIMARY / "Industry" lane) and `office`
(your SECONDARY / "Viral videos" lane); the tab LABELS come from `radar-config.json`
(`primary_lane.label` / `secondary_lane.label`), so users only ever see their own names.
Each script item needs a STABLE `id` and the labelled-anatomy fields. Primary-lane items may
carry an embedded `linkedin` twin `{id,type,hook_arch,body,qa,source}` when `linkedin_twins`
is on. `inspiration[]`: `{creator,platform,metric,mechanic,link}`. Tracking (filmed / posted
/ views / ignore) lives in the browser's localStorage keyed by item id, so new weeks never
wipe past logs. Dashboard tabs: **[primary] (to film)**, **[secondary] (to film)**, **Filmed
& metrics**, **LinkedIn posts**, **Viral inspiration**.

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
- **Leaders scan** (`leaders_file` filled): each run, study what is working from the leaders in
  `leaders-to-study.md`, capture hook + structure + why-it-worked with citations, and turn the
  sharpest mechanics into that week's scripts. See `references/leaders-to-study-template.md`.
- **Blog pipeline** (`blog_pipeline: true`): the dashboard's "Export week for blog" button saves
  everything marked Filmed/Posted so a downstream routine can turn films into articles. Wire
  this to your own site build; it is off by default.

## Quantity bar
At least ~10 scripts per lane per run. Give the creator volume to choose from, not a curated 3.

## Dormant fallback: account watchlist mode
`fetch.py` + `watch-accounts.md` can flag outliers from a fixed creator watchlist via a
scraper (e.g. Apify) when you have API credit. Until then, the web-research routine above is
the engine.

---
name: outlier-radar
description: "Weekly viral-outlier research and ideation engine for any creator or brand. First use interviews you about your niche and saves a config to a local workspace. Each week it detects RISING formats early (14-day freshness gate, no peaked-roundup mechanics), extracts the transferable hook/format mechanic, scores every idea through a virality-psychology lens, and writes ~10 ready-to-film scripts per lane in your voice to a tracked dashboard. Every script must pass the two-question gate (niche-insider entertaining OR teaches something usable). Also runs a trend-CREATION lane: named recurring formats plus a coined-terms pipeline. Use when the user says 'run outlier radar', 'find viral videos to copy', 'what should I post this week', 'weekly content ideas', 'what trends are rising', 'hot drop', or wants short-form video ideas for their niche."
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

**The secondary lane must still be INSIDER to the creator's world.** The gate below applies
to both lanes: a joke that anyone with a pulse finds equally funny builds audience but not
authority. Insider humour travels anyway, because people share what signals their job or
identity, and it compounds the creator's authority instead of sitting beside it.

## The two-question gate (the master filter, above everything else)
Every script ships only if the answer is YES to at least one of these. Run it BEFORE the
QA checklist; a script that answers yes to neither is DEAD (killed and replaced, not
pre-qa), no matter how proven the mechanic or how good the psych score.
1. **Is this entertaining IN the creator's niche?** Insider material: something only
   people in the niche would know, get, or find funny. The test is exclusivity: if
   everyone finds it equally entertaining, it is not a gate-1 pass; if a niche insider
   wouldn't grin, nod, or feel seen, it fails too.
2. **Does it teach something useful someone can use?** A concrete takeaway the viewer can
   actually run (sourced from the workspace `methods.md`), not just a reframe of their problem.
Both at once is the sweet spot. One clean yes ships.

## Weekly routine
0. **Feedback, two modes (zero-admin default).** The default loop is the **outlier flag**:
   the creator will KNOW when a video clearly pops (an outlier is unmissable), and says so.
   That flag triggers the deep work: autopsy the winner (hook, mechanic, which psychology
   principles fired, per `references/virality-psychology.md`), mark its mechanic PROVEN in
   the workspace `mechanic-library.md`, write 3-4 variations attacking the same belief
   through different doors into the next batch, and consider promoting it into a named
   recurring series. Never require scheduled metric logging. OPT-IN mode: if the creator
   uses the dashboard's **Export performance** button and a `performance/performance-*.json`
   exists in the workspace, read the newest one silently and bias the batch toward what won;
   if none exists, do not nag.
1. **Early-signal sweep (predict by detecting early).** Nobody predicts trends, they detect
   them before saturation. Web-research ~12 short-form videos/formats/mechanics that are
   RISING RIGHT NOW, with a hard **freshness gate: the mechanic must have started rising in
   the last ~14 days**. BAN "best viral videos of the month" roundups as a source: anything
   already in a roundup has peaked and is wallpaper (habituation, see
   `references/virality-psychology.md`). Sources that run ahead of roundups: TikTok Creative
   Center trending (public, no login), Google Trends breakout queries, rising Reddit threads,
   platform-change news, breakout small accounts. For each candidate also capture: when it
   started rising, and the evidence it is rising not peaked (small accounts overperforming
   with it, "new format?" comments, no brand accounts on it yet). The call per candidate is
   binary: **ride it in the first wave, or skip it**. Demand MECHANIC variety, and include a
   few contrarian/controversial ones (high-arousal, they travel). If `watch-accounts.md` is
   filled, prioritise those creators. **Signals are SHELLS, never topics**: never pitch "how
   to post" or "how to go viral" as the SUBJECT of a script unless that literally is the
   creator's niche; present every signal WITH the transferred version ("the shell: X. Your
   version: Y about Z").
   **Verification rules (non-negotiable):** every outlier must be a real post you actually
   found at a real URL. Never invent a creator, a video, a metric, or a link. Tag every
   metric with `metric_confidence`: `"verified"` (you fetched the post or a primary source),
   `"reported"` (a credible article or aggregator states it), or `"estimated"` (inferred;
   say from what). If you cannot source a candidate, DROP it rather than guess. Fewer real
   outliers beat twelve with one fake: one invented link poisons trust in the whole board.
2. **Scour for teachable substance (be first to teach it).** In parallel, gather the freshest
   real material the creator can TEACH before anyone else: new studies, fresh platform
   changes, new data, hot takes, "everyone is wrong about X" angles from the last 2-3 weeks
   in the creator's subject. Priority order: (a) things nobody has explained simply yet
   (first-mover teach), (b) things everyone is getting wrong (correction teach), (c)
   evergreen how-to with a fresh number. Every substance item arrives with its do-this step
   attached (pull from the workspace `methods.md`), not just the headline.
3. **Extract the mechanic, then name its psychology.** For each rising video capture the
   exact HOOK (first line / first 3s), the STRUCTURE (2-4 beats), and WHY it works, named as
   principles from `references/virality-psychology.md` (which attention trigger, which open
   loop, which sharing lever). This is what makes prediction possible: a mechanic whose
   psychology you can name transfers to a new topic; one you can only describe ("it's
   funny") does not. Grow the workspace copy of `mechanic-library.md`, tagging each entry
   with its principles.
4. **Marry mechanic + premise.** Each script = one proven mechanic applied to one current
   premise/data point from the niche, in the creator's voice. **Then run every hook through
   `references/hook-psychology.md` (the six psychological hook styles: Crystal Ball, Insider,
   Lab Rat, Expert, Mirror, Sledgehammer).** Every `text_hook`/`spoken_hook` must fire at
   least one of the six; stack two where natural; spread the styles across the batch so one
   doesn't dominate. Tag each item with a `hook_styles` array.
5. **Write ~10 primary-lane scripts and ~10 secondary-lane scripts** in the labelled anatomy.
   Read `references/script-anatomy.md` and follow it exactly. Secondary-lane scripts must
   borrow the hook + structure from a REAL viral video (put the URL in `sources`).
6. **QA GATE.** FIRST run the two-question gate (top of this file) on every script: neither
   yes = the script dies here, silently, and is replaced. Then run the checklist in
   `references/script-anatomy.md`. The one thing that always fails is no payoff (a hot take
   with nothing under it). **Fail any script whose `psych` field is empty or generic** (it
   must name real principles from `references/virality-psychology.md`; "it's relatable" is
   not a mechanism). **A CTA is OPTIONAL:** default is to end on the payoff/button, because
   watch-through is the metric and a CTA that runs past the payoff makes people drop. Mark
   each `qa:"passed"` or `"pre-qa"`.
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
- `psych`: 1-3 principle names from `references/virality-psychology.md` + one line on why
  this will work, written by answering the 5-question scoring checklist at the end of that
  file; the "argued about" answer doubles as the pinned-comment plan.
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

## The performance loop (opt-in; the outlier flag is the default)
The zero-admin default is the **outlier flag** (step 0): the creator tells you when a video
pops, and that triggers the autopsy + variations. For creators who WANT data, the
dashboard's **Export performance** button writes `performance-<week>.json` with every
tracked item (status, views, link, notes, plus its mechanic, facet, intent, and value type)
across all weeks; saved into `<workspace>/performance/`, step 0 reads the newest export
silently and biases the next batch toward what actually worked. Mention the button once
during discovery, then never nag about it: unsustainable tracking is worse than none.

## Trend creation (the first-mover lane, every run)
Riding trends is defence; creating them is the lean. A trend is a template other people can
perform: it needs a copyable skeleton, low effort + high identity fit, and a NAME (the full
theory is section 5 of `references/virality-psychology.md`). Two pipelines, both live in
every weekly run:
1. **Named formats.** Each lane keeps 1-2 named recurring series with a fixed skeleton and
   a signature line. If a lane has none, propose ONE candidate per run (skeleton + signature
   line + episode 1 script) until the creator locks one. A format graduates to "trend" when
   a stranger makes their own episode.
2. **Coined terms.** Copy `references/coined-terms-template.md` into the workspace as
   `coined-terms.md` (the ledger). Keep 1-2 candidate terms in play at any time: each names
   a problem or dynamic the audience already FEELS but has no word for (label the feeling,
   own the feeling). Rules: every mention uses the EXACT same term (repetition is the
   planting); the term gets its own definition beat in at least one script per week while in
   play ("I call this X: it's when..."); publish the term's page on the creator's site early
   (AI engines cite the coiner). A term graduates when someone else uses it unprompted;
   retire candidates with no pickup after ~4 weeks.
Open every weekly digest with a **"3 rising signals"** block: the sharpest early-detection
calls from step 1, each as a one-line prediction with its transferred version. Being on
record early is the credibility play even when a call misses.

## Hot drop (mid-week trigger, outside the weekly cadence)
The weekly cadence cannot catch waves. When something breaks in the creator's niche and they
say "hot drop" or ask for a take, write ONE same-day script: normal anatomy, freshness above
polish, first credible take beats best take. The test for whether a story qualifies: will
everyone in the niche be talking about this in 3 days? If yes, ship today; if it is already
everywhere, skip (peaked).

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

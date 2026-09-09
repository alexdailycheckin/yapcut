---
name: outlier-radar
description: "Weekly viral-outlier research and script engine for a creator or brand, measured-first. Use for run outlier radar, run the show, what should I post this week, weekly content ideas, hot drop, or short-form video and LinkedIn ideas for a niche. First run interviews the creator (audience, proof, voice corpus) into a local workspace; each week it reads last week's numbers, finds rising mechanics, writes to filming slots and gates the batch. Not for cutting footage or gated reports."
---

# Outlier Radar

Finds short-form videos that beat their own creator's baseline (the signal that a HOOK and a
FORMAT worked, independent of audience size), then re-skins the proven mechanic with
substance only this creator can supply. Output is a weekly batch of filmable scripts and
LinkedIn posts on a tracked dashboard, handed to `tiktok-yap-editor` to cut. The unit of work
is posts published and measured, never scripts written: a relevant creator is one a specific
audience recognises, returns to and answers, and this engine is judged on that.

Creator-agnostic. It learns the creator once (who they want to be recognised by, what only
they can say, how they actually talk) and works to that.

## Routing

| You are | Read or run |
|---|---|
| onboarding a new creator | First run, below |
| running the week | Weekly routine, below; `references/week-schema.md` for the file it writes |
| writing hooks | `references/hook-psychology.md` (six triggers), `references/hook-library.md` (15 families) |
| writing a script | `references/script-anatomy.md`; the voice stack, below |
| writing the show | `references/the-show-template.md` |
| writing or shaping LinkedIn | `references/save-mechanics.md`, `references/format-library.md`, `references/linkedin-selector.md`, `references/linkedin-visuals.md` (five visual shapes) |
| verifying and capturing receipts | `references/receipts.md`, `references/receipt-sources.md` |
| naming why a mechanic works | `references/virality-psychology.md`, `references/mechanic-library.md` |
| the first-mover lane, coined terms | `references/trend-creation.md` |
| what happens after the post is written | `references/distribution.md` |
| craft references on shorts | `references/shorts-craft-2026.md`, `references/video-scripting-as-a-science.md`, `references/post-types.md` |
| a gate is red | the gate's own output names the rule; `check_fidelity.py --help` and `radar_gate.py --help` |

## The workspace

All mutable data lives in a workspace OUTSIDE the skill folder. Every script resolves it the
same way (`yapcut_home.py`): `--dir <path>`, then `$YAPCUT_HOME` (or the older
`$OUTLIER_RADAR_HOME`), then the current directory if it holds `radar-config.json`, then
`~/outlier-radar/` if it does. Nothing else: with no workspace the scripts exit 2 and name the
places they looked. There is no fallback to the skill folder.

Layout: `radar-config.json`, `positioning.md`, `methods.md`, `leaders-to-study.md`,
`watch-accounts.md`, `mechanic-library.md`, `coined-terms.md` (one of each, at the root, and
these are the files the engine reads), `weeks/`, `performance/`, `voice-corpus/`, `capture/`,
`carousels/`, `show/`, and the generated `dashboard.html`.

**The overlay.** If `<workspace>/law.md` exists, read it after this playbook; where the two
conflict, `law.md` wins. A real file at `<workspace>/references/<name>.md` shadows this skill's
`references/<name>.md`. That is how a creator's own rulings ride on top of the shipped
playbook without forking it.

## First run: discovery (once)

Resolve the workspace. The config is written at step 1, so its presence proves nothing about
whether onboarding finished; `schedule.enabled: true` is the signal. Config present and
enabled: skip to the Weekly routine. Config present, not enabled, real weeks exist: ask only
the cadence and quantity questions. Config present, no real weeks: resume from the first
unanswered question, never restart. Interview with `AskUserQuestion`, one question per
message where the answer shapes the next.

1. **Workspace location** (default `~/outlier-radar/`). Create it with `weeks/`, `performance/`,
   `voice-corpus/`, `capture/`.
2. **Who should recognise you, and for what.** One sentence for the role and situation of the
   people they want to be known by; the one sentence those people should say about them; the
   one surface they will show up on every week. Writes `audience` in the config. This comes
   before niche because relevance is a relation between the creator and a specific group,
   and every gate, the selector and the north star read this block.
3. **Name, site or handle.**
4. **Niche** (one line, the subject) and **2 to 4 facets** to rotate.
5. **Proof extraction.** Five things you have done that a competitor cannot claim (number and
   date each). Five beliefs your niche gets wrong and the moment you were proven right. Three
   processes you run, each with the kill threshold. Ten lines you would never say. The
   answers land in files the engine reads: the proof bank in `positioning.md`, the plays in
   `methods.md` (shape in `references/methods-template.md`), the lines in
   `voice-corpus/rejections.json` (from `rejections.example.json`). An interview that collects
   adjectives about the voice produces pastiche; this one collects material.
6. **The corpus.** Where do you already talk unscripted: sales or customer calls (harvest the
   transcripts), podcasts, voice notes, meeting recordings. Transcripts go in `capture/` with
   a `register: work` header for on-subject speech. Only if nothing exists: 20 to 30 minutes
   into a phone on 4 or 5 subjects in the niche, not read, not rehearsed. Then
   `python3 segment_corpus.py` and `python3 derive_voice_targets.py`. **No batch is written
   without a corpus** except with `--allow-unvalidated` on the gate, said out loud.
7. **Roster.** Generate ten leaders in the niche from audience and niche; the creator strikes
   and adds. Writes `leaders-to-study.md` (`references/leaders-to-study-template.md`) and,
   for creators to watch, `watch-accounts.md`.
8. **Channels.** LinkedIn too (`linkedin_twins`)? Blog (`blog_pipeline`)?
9. **Lanes.** Confirm the two lane names. The secondary lane starts OFF
   (`secondary_lane.enabled: false`, `enable_after_weeks: 4`): a viral-lane hit fills the
   follower count with people who came for the bit, and a stranger's first win should be in
   the lane they want to be known for.
10. **Brand basics** (optional, for the carousel and the dashboard).
11. **Show mode** (optional): the journey in `references/the-show-template.md`.
12. **Cadence and quantity.** Which day and time the weekly run fires (`schedule`), and how
    many filming slots the creator can actually cover (`quantity`: default 3 video slots, 2
    spares, 5 LinkedIn slots for the first four weeks; raise once 8 items are marked Posted).

Then: run the first week to `quantity` (never end on the bundled example), create the
recurring run with the host's scheduler (or say plainly that none exists and leave
`schedule.enabled: true` as the record), and finish with the dashboard open on their week:
`python3 build_dashboard.py --dir <workspace> --open`. Copy `references/mechanic-library.md`
and `references/coined-terms-template.md` into the workspace as the copies that grow.

## The two lanes, and how many scripts

- **Primary lane** (default "Industry"): the subject they want to be known for. An
  educational script hands over one step the viewer can run this week, sourced from
  `methods.md`, and declares where it stands: `proof.kind` is `own`, `reach` (the creator's
  company data) or `public`. A batch that is all `public` is reproducible by anyone and the
  gate says so.
- **Secondary lane** (default "Viral videos"): reach plays adjacent to the niche that borrow
  a proven mechanic. Still insider to the creator's world: a joke that anyone finds equally
  funny builds audience but not authority.

**Quantity is `quantity` in the config, never a fixed bar.** Write the confirmed filming
slots plus spares, then spend any remaining budget on 3 to 4 variations of the last measured
winner. Unfilmed scripts carry zero information back into the loop, and recognition compounds
on repetition of a series, not on inventory.

## The two-question gate (the master filter)

Every script ships only if the answer is YES to at least one: (1) is this entertaining IN the
creator's niche, insider material a niche insider would grin at or feel seen by; (2) does it
teach something the viewer can run, sourced from `methods.md`. Both is the sweet spot. A
script with neither is dead and replaced. For research-class scripts the creator may rule
it AND; when they do, the gate FLAGS in the item's `note` and never rewrites the copy.

## Weekly routine

0. **MEASURE (blocking, five minutes).** Measured-first is the default; the outlier flag is an
   addition. The creator pastes their platform's analytics table once a week:
   `python3 ingest_feed.py` (LinkedIn activity feed), `--tiktok` (TikTok Studio content table),
   dry by default, `--commit` writes. Commenters and new connections go into the people ledger
   with `ingest_feed.py --people --kind comment_by --post <id>`. Filmed and posted state:
   `log_perf.py --filmed <id>`, `--posted <id> <url>`, or `--import <export.json>` from the
   dashboard. Then `python3 log_perf.py --report`: it opens with the relevance line (returning
   versus new engagers, audience share), answers this week's question, and writes
   `performance/last-report.md`. Skip a week and the digest opens with "nothing posted,
   nothing measured" and the batch still ships. Pre-register ONE two-arm question for the
   coming week in the week file's `experiment` block; passive bucketing across six dimensions
   learns nothing at five posts a week.
1. **Early-signal sweep.** Web-research about a dozen formats and mechanics RISING RIGHT NOW,
   with a hard 14-day freshness gate; roundups are banned as a source because anything in one
   has peaked. Sources that run ahead: TikTok Creative Center, Google Trends breakouts, rising
   Reddit threads, platform-change news, breakout small accounts, the `watch-accounts.md`
   roster. Per candidate the call is binary: ride the first wave or skip. Signals are shells,
   never topics. Every outlier is a real post at a real URL with `metric_confidence`
   (`verified`, `reported`, `estimated`); drop what you cannot source. The receipts law and
   the date law are in `references/receipts.md`.
2. **Substance.** The freshest material the creator can teach before anyone else: new
   studies, platform changes, "everyone is wrong about X", each arriving with its do-this step
   from `methods.md` and its `proof.kind`.
3. **Mechanic, then psychology.** Per rising video: the exact hook, the 2 to 4 beat structure,
   and WHY, named from `references/virality-psychology.md`. Grow the workspace
   `mechanic-library.md`.
4. **Marry mechanic and premise.** One proven mechanic, one current premise, the creator's
   voice. Every hook fires at least one of the six triggers in `references/hook-psychology.md`;
   tag `hook_styles`.
5. **Write to quantity** in the anatomy of `references/script-anatomy.md`, AFTER the voice
   stack below. Secondary-lane scripts borrow hook and structure from a real viral video
   (URL in `sources`).
6. **GATE.** One command: `python3 radar_gate.py --week weeks/<date>.json`. It runs
   `check_fidelity.py` (schema, fidelity, cadence, LinkedIn laws, ownership split),
   `hook_lint.py`, `spoken_lint.py`, `source_check.py` and `visual_lint.py` on any renders,
   prints one table, exits 2 on any fail, and stamps `weeks/<date>.gate.json`. Exit codes
   everywhere: 0 pass, 1 warnings, 2 fail. Cadence distribution rules warn by default
   (`--strict-cadence` fails them); categorical rules fail. Then the human half: the
   two-question gate, the checklist in `references/script-anatomy.md`, a `psych` field that
   names real principles, and a CTA that is OPTIONAL (end on the payoff). `qa` is exactly
   `passed` or `pending-approval`.
7. **PUBLISH.** What happens after the writing, `references/distribution.md`: the week's
   `ammo[]` (10 to 15 receipt-bearing rounds from the sweep, on the dashboard's Ammo tab),
   `held[]` receipts and a `reply_stance` on every LinkedIn post for the reply block, the
   day-0 post for a live peg with `post_day_locked`, the callback and promise lines in the
   show (tracked in `promised[]`), the tag pass with its guardrails. When `linkedin_twins`
   is on, `python3 select_linkedin.py` assigns each post its feed shape, job and posting
   day, and reads `performance/learned.json` when it exists.
8. **PERSIST.** Write `weeks/<date>.json` (`references/week-schema.md`, `schema_version: 2`),
   run the gate, then `python3 build_dashboard.py --dir <workspace> --open`. The dashboard is
   the product surface: open it every run and say where it lives.

## The voice stack: show the voice, never describe it (before any spoken script)

A model given a description of a voice produces an imitation of the description, which is the
generic confident-operator register creators reject on sight (why: CHANGELOG 3.4.0). So
grounding is mechanical:

    python3 segment_corpus.py          # only when the corpus changed; routes by register header
    python3 derive_voice_targets.py    # only when the corpus changed; reads on-subject speech only
    python3 voice_brief.py --week <date>

Four rules. Write against the verbatim passages `voice_brief.py` prints; the passages are the
specification. Register is not optional: on-subject speech, casual speech and anything TYPED
are three voices, and only on-subject speech feeds the targets. Never feed teleprompter reads
of scripts this engine wrote back into the corpus; that measures the model. The rejection
ledger (`voice-corpus/rejections.json`) is the only thing that accumulates taste: when the
creator kills a line, append it in the same session with their reason, tagged with the
creator's name in `attribution`, and never add one on a session's own judgement.
`turing_check.py --week <date>` shuffles matched windows of corpus and script for a blind
read, the honest test of whether a batch sounds like the person.

The supply of speech caps everything downstream. Thirty-five sentences cannot ground a voice;
a corpus grows by harvesting calls, not by recalibrating floors.

## The performance loop

Written into the loop, not opt-in: step 0 above. `log_perf.py` is the ledger
(`performance/performance.jsonl`, append-only, latest measured per id wins, nothing under 48
hours old is ranked); `tracking.jsonl` holds filmed and posted state; `people.jsonl` holds who
answered; `--weights-out` writes `performance/learned.json` for any dimension past n=4, which
`select_linkedin.py` multiplies into its priors and prints as prior versus learned. Video rows
carry `full_watch_pct`, `avg_watch_s`, `follows` and the source split when the paste has them,
and the report ranks video by full-watch percentage when present, because a hook problem and
a distribution problem look identical in views. The outlier flag still works: when the
creator says a post popped, autopsy it, mark the mechanic PROVEN, brief 3 to 4 variations.

## Show mode

When `show.enabled` is true the primary lane becomes THE SHOW under the creator's own name
and lens: `episodes_per_week` teardowns from the week's news in their industry, on the shape
in `references/the-show-template.md`. Two parts are fixed (the receipt in frame one, the
verdict through the creator's lens); the middle exists to get from one to the other. Every
spoken fact verified with a URL or cut; every claim a screenshot receipt captured with
`capture_gate.py`; a callback to last week and a promise for next week. The secondary lane and
the trend sweep continue as garnish.

## Hot drop, the day-0 pass

When something breaks in the niche mid-week and the creator asks, or when the sweep finds a
peg under a day old: one same-day text post in the reach band (or under 300 characters), the
ammo rounds for that story, `post_day_locked: true`, no video. Freshness over polish; skip if
it is already everywhere. The filmed episode lands day 2 or 3 referencing it.

## Handoff to the editor

Route picked scripts to `tiktok-yap-editor`. Mode A (talking head) is the default; a
`day-in-life-vo` script with `beats[]` routes to Mode B. Write `post_copy` on the item
(caption, description, `search_query` verbatim, pinned comment) so the editor's finalize
step ships the video with its words. The editor writes an edit record carrying the item id, so
`log_perf.py --edits <output dir>` joins the cut to the outcome.

## Optional layers (config-gated)

- **LinkedIn twins** (`linkedin_twins`): each primary item gets a written twin embedded as
  `item.linkedin`; `select_linkedin.py` picks the shape and the order (`references/linkedin-selector.md`);
  every twin ships a visual chosen from `references/linkedin-visuals.md`.
- **Leaders scan** (a filled `leaders-to-study.md`): study what is working from the roster,
  results in `gtm_linkedin[]`.
- **Blog pipeline** (`blog_pipeline`): text-first. A posted LinkedIn text plus its sources is
  an article draft; the export reads posted posts and twins, not filmed videos.
- **Carousels**: doctrine in `references/linkedin-visuals.md` Shape 5; `carousel.py <spec>`
  renders a spec, `build_carousels.py` derives a deck from a script.
- **Lead magnet**: the sibling skill `lead-magnet-report` turns one category's measured data
  into a comment-gated document post. Mention it once to a LinkedIn creator, then get on
  with the week.

## Hard rules

No invented creators, videos, metrics or links. No em or en dashes anywhere. No third-party
LinkedIn automation. A claim that cannot be sourced is cut, never softened. Tracked doctrine
names no creator; creator specifics live in the workspace.

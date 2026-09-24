---
name: outlier-radar
description: "Weekly script and post engine for a creator or brand. Use for run outlier radar, run the show, what should I post this week, weekly content ideas, hot drop, or short-form video and LinkedIn ideas for a niche. First run interviews the creator (audience, proof, voice corpus) into a local workspace; each week it reads what the creator approved and killed, sweeps the niche, writes to filming slots and hands the batch over. Not for cutting footage or gated reports."
---

# Outlier Radar

Three jobs, in this order. Understand the creator from the onboarding. Learn them more every week, from what they film, post and kill. Find and write script and post ideas good enough that they want to film them. Everything in this folder serves those three, and a rule that does not is a candidate for deletion, because a gate is a substitute for taste and the creator's approved scripts are the taste.

The output is a weekly batch of filmable scripts and LinkedIn posts on a dashboard, handed to `tiktok-yap-editor` to cut. The creator decides what gets filmed and what ships. This engine never posts.

## Routing

| You are | Read or run |
|---|---|
| onboarding a new creator | First run, below |
| running the week | Weekly routine, below; `references/week-schema.md` for the file it writes |
| writing hooks | `references/hook-psychology.md`, `references/hook-library.md` |
| writing a script | `references/script-anatomy.md`, `references/the-language-layer.md`; the voice stack, below |
| writing the show | `references/the-show-template.md` |
| writing or shaping LinkedIn | `references/save-mechanics.md`, `references/format-library.md`, `references/linkedin-selector.md`, `references/linkedin-visuals.md` |
| verifying and capturing receipts | `references/receipts.md`, `references/receipt-sources.md` |
| naming why a mechanic works | `references/virality-psychology.md`, `references/mechanic-library.md` |
| the first-mover lane, coined terms | `references/trend-creation.md` |
| what happens after the post is written | `references/distribution.md` |
| a gate is red | the gate's own output names the rule; `radar_gate.py --help` |

## The workspace

All mutable data lives in a workspace OUTSIDE the skill folder. Every script resolves it the same way (`yapcut_home.py`): `--dir <path>`, then `$YAPCUT_HOME`, then the current directory if it holds `radar-config.json`, then `~/outlier-radar/` if it does. With no workspace the scripts exit 2 and name the places they looked.

Layout: `radar-config.json`, `positioning.md`, `methods.md`, `leaders-to-study.md`, `watch-accounts.md`, `mechanic-library.md`, `coined-terms.md` (one of each at the root; these are the files the engine reads), `observations.md`, `weeks/`, `performance/`, `voice-corpus/`, `capture/`, `carousels/`, `show/`, and the generated `dashboard.html`.

**The overlay.** If `<workspace>/law.md` exists, read it after this playbook; where the two conflict, `law.md` wins. A real file at `<workspace>/references/<name>.md` shadows this skill's `references/<name>.md`.

## How the engine learns the creator

Nothing said in a chat reaches the next run. Four files do, and every yes or no the creator gives lands in one of them the same session:

- **A line they killed:** `voice-corpus/rejections.json`, with their reason, tagged with their name in `attribution`. Never add one on a session's own judgement. `spoken_lint.py` fails every entry.
- **A script they filmed, posted or approved:** `performance/tracking.jsonl` (`log_perf.py --filmed <id>`, `--posted <id> <url>`), or `qa: passed` on the item. `voice_brief.py` prints the last three of these FIRST. Filmed counts as approved; a person does not read a script to camera they dislike.
- **A thing that happened in a room:** one line in `observations.md`, no format, read before the news every week. The test for what belongs there is whether anybody else could have written it.
- **A ruling on direction:** `law.md`.

A brief that shows only what the creator rejects teaches a writer what to avoid and nothing about what to do. The approved scripts are the positive half, and they outrank any description of the voice.

## First run: discovery (once)

Resolve the workspace. `schedule.enabled: true` in the config is the signal onboarding finished; a config alone proves nothing. Config present and enabled: skip to the Weekly routine. Config present, real weeks exist, not enabled: ask only cadence and quantity. Config present, no weeks: resume from the first unanswered question. Interview with `AskUserQuestion`, one question per message where the answer shapes the next.

1. **Workspace location** (default `~/outlier-radar/`). Create `weeks/`, `performance/`, `voice-corpus/`, `capture/`, and an empty `observations.md`.
2. **Who should recognise you, and for what.** One sentence for the role and situation of the people they want to be known by; the sentence those people should say about them; the surface they show up on every week. Writes `audience` in the config. Relevance is a relation between the creator and a specific group, so this comes before niche.
3. **Name, site or handle.**
4. **Niche** (one line) and **2 to 4 facets** to rotate.
5. **Proof extraction.** Five things they have done that a competitor cannot claim, with a number and a date each. Five beliefs the niche gets wrong and the moment they were proven right. Three processes they run, each with its kill threshold. Ten lines they would never say. Answers land in `positioning.md`, `methods.md` (`references/methods-template.md`) and `voice-corpus/rejections.json` (from `rejections.example.json`). An interview that collects adjectives about a voice produces pastiche; this one collects material.
6. **The corpus.** Where they already talk unscripted: sales or customer calls, podcasts, voice notes, their own videos. Transcripts go in `capture/` with a `register: work` header for on-subject speech and `form: monologue` for anything said alone to a camera. If nothing exists: 20 to 30 minutes into a phone on 4 or 5 subjects in the niche, unscripted. Then `python3 segment_corpus.py` and `python3 derive_voice_targets.py`. No batch is written without a corpus except with `--allow-unvalidated` on the gate, said out loud.
7. **Roster.** Ten leaders in the niche from audience and niche; the creator strikes and adds. Writes `leaders-to-study.md` and `watch-accounts.md`.
8. **Channels.** LinkedIn too (`linkedin_twins`)? Blog (`blog_pipeline`)?
9. **Lanes.** Confirm the two lane names. The secondary lane starts OFF (`secondary_lane.enabled: false`, `enable_after_weeks: 4`): a stranger's first win should be in the lane the creator wants to be known for.
10. **Brand basics** (optional, for the carousel and the dashboard).
11. **Show mode** (optional): `references/the-show-template.md`.
12. **Cadence and quantity.** The day and time the weekly run fires (`schedule`), and how many filming slots the creator can cover (`quantity`: default 3 video slots, 2 spares, 5 LinkedIn slots; raise once 8 items are marked Posted).

Then run the first week to `quantity`, create the recurring run with the host's scheduler (or say plainly that none exists), and finish with the dashboard open: `python3 build_dashboard.py --dir <workspace> --open`. Copy `references/mechanic-library.md` and `references/coined-terms-template.md` into the workspace as the copies that grow.

## The two lanes, and how many scripts

- **Primary lane** (default "Industry"): the subject they want to be known for. An educational script hands over one step the viewer can run this week, from `methods.md`, and declares `proof.kind`: `own`, `reach` (the creator's company data) or `public`.
- **Secondary lane** (default "Viral videos"): reach plays adjacent to the niche that borrow a proven mechanic, still insider to the creator's world.

**Quantity is `quantity` in the config, never a fixed bar.** Unfilmed scripts carry nothing back into the loop, and recognition compounds on repetition of a series, not on inventory. When the previous batch sits unfilmed or unposted, say so at the top of the report; the creator decides whether to write on top of it.

**The two-question gate.** Every script ships only if at least one is YES: is this entertaining IN the creator's niche, insider material an insider would grin at or feel seen by; does it teach something the viewer can run. Both is the sweet spot. The creator may rule it AND for research class; then the gate FLAGS in the item's `note` and never rewrites.

## Weekly routine

0. **Log, if numbers arrived.** When the creator pastes their analytics table: `python3 ingest_feed.py` (dry by default, `--commit` writes), `log_perf.py --posted <id> <url>` for anything that shipped, `--report` if they ask. Never blocking, never a reason to stop. Nothing here decides what gets written: until the creator says a post was incredible, the ledger is a log, not an arbiter. When they do say it, autopsy that post, mark its mechanic PROVEN in `mechanic-library.md`, and brief variations.
1. **Read the creator first.** `observations.md` (and say how old its newest line is), `law.md`, `voice-corpus/rejections.json`, and `python3 voice_brief.py --week <date>`, which opens with the last three approved scripts. Material that only the creator could have written outranks anything the sweep finds.
2. **Sweep the niche.** News from the last 14 days where a named subject DID something on a date. Four or five roster accounts from `watch-accounts.md`, each post against that account's own median; 3x or more is an outlier worth banking in `inspiration[]` with `{creator, platform, metric, metric_confidence, mechanic, link}`. Roundups are banned as a source. Log every swept account in `watch-accounts.md`, including the ones with nothing.
3. **Write to quantity.** The approved scripts are the model for taste, the corpus passages for voice, `references/the-language-layer.md` for the sentences, `references/script-anatomy.md` for the parts, the five moves (Show mode, below) for the shape. Every fact carries a source URL and a `must_contain` string on the source, so `source_check.py` can prove it. Secondary-lane scripts borrow hook and structure from a real post (URL in `sources`). Every item gets a real title.
4. **Gate.** `python3 radar_gate.py --week weeks/<date>.json`. It runs the structural checks and stamps `weeks/<date>.gate.json`: schema, ids, sources, the belief present and placed before the receipts, the word ceiling, one item one subject, one story one lane, rejected phrases, the epigram, a candour marker on an empty clause, the pack current. Cadence distributions are OFF; `--cadence` turns them on and `--strict-cadence` fails them, the creator's call. Fix what it names. Never satisfy a gate by faking its input. Then the human half: the two-question gate and the vacuum test on every text hook.
5. **Persist and hand over.** `weeks/<date>.json` (`references/week-schema.md`), then `python3 build_pack.py --week weeks/<date>.json`, then `python3 build_dashboard.py --dir <workspace> --strict --open`. `--strict` refuses to build on a failed stamp, so a red week never reaches the page looking green. The report to the creator is one screen: each idea, one line on why it is theirs, and what the gate said. Then stop; filming and posting are the creator's.

**A subject that changes gets a new id.** Ids are never reused and never rewritten in place. Kill the item to the rolled briefs, mint the next number, write the new one from empty. The swap that keeps an id keeps the old twin, POV beat and subject underneath a new script, and `check_fidelity.py` fails it.

## The voice stack: show the voice, never describe it

A model given a description of a voice produces an imitation of the description, the generic confident-operator register creators reject on sight. So grounding is mechanical, in this order:

    python3 segment_corpus.py          # when the corpus changed; routes by register and form header
    python3 derive_voice_targets.py    # when the corpus changed; on-subject speech only
    python3 voice_brief.py --week <date>

The brief prints the approved scripts, then verbatim corpus passages, then the rejections. Write against the scripts and the passages; they are the specification. A script is a monologue, so the brief's DELIVERY block (measured on `form: monologue` sources) is the target and the conversation rates are contrast. Never write a cut-off word (`be-`, `yo-`): it is the sound of being interrupted, not a feature of anyone's delivery. Never feed teleprompter reads of this engine's own scripts back into the corpus. The supply of speech caps everything downstream, and a corpus grows by harvesting the creator's own calls and videos, not by recalibrating floors.

`references/the-language-layer.md` sets the sentences: money word last, source attributed before the claim, no mid-sentence clauses, "you" outnumbering "I", contractions always, the spoken filler kept at the monologue rate and attached to a fact. `turing_check.py --week <date>` builds a blind read when the creator wants one; it is only honest against a corpus of them speaking a monologue on their own subject.

## Show mode

When `show.enabled` is true the primary lane becomes THE SHOW under the creator's own name: `episodes_per_week` teardowns of subjects that did something this week, on five moves (`references/the-show-template.md`).

| # | Move | What it does |
|---|---|---|
| 1 | The receipt | The number or artifact on screen in frame one, spoken flat |
| 2 | The belief | What the viewer already believes about this, in their words, as if it were true |
| 3 | The break | The receipts that make the belief untenable, but/therefore chained |
| 4 | The mechanism | Why it happened, arriving as the consequence of move 3, never announced |
| 5 | The verdict | The creator's POV in one line, money word last, hard stop |

**The order test.** A belief stated after the receipts is a summary of them; the same belief stated before them turns the identical receipts into a demolition. `belief` is a required field on research items, copied verbatim from the script, and the gate fails a belief that sits after half the numbers. If the sentence naming what the viewer believes does not exist, the episode has no argument and goes back.

**The subject.** An episode is a named subject that did something, on a date, and the viewer has already seen the headline. A study, a survey, the discipline itself, or the creator's own week is material for the secondary lane or a post, not an episode. A spoken franchise catchphrase is usually wrong: forced onto an episode it does not fit, it spends the opening line on a promise the episode never keeps. The shape carries the franchise. Every spoken fact verified with a URL or cut; a callback to last week and a promise for next week, tracked in `promised[]`.

## Hot drop, the day-0 pass

When something breaks in the niche mid-week and the creator asks, or the sweep finds a peg under a day old: one same-day text post in the reach band, `post_day_locked: true`, no video. Freshness over polish; skip if it is already everywhere.

## Handoff to the editor

Route picked scripts to `tiktok-yap-editor`. Mode A (talking head) is the default; a `day-in-life-vo` script with `beats[]` routes to Mode B. On a phone: with `mobile.sync_dir` set, `build_dashboard.py` copies the newest week and `brand-config.json` into that folder, the Anima app films and cuts from it with the editor's own `rules.json`, and its cuts and edit records land in `<sync_dir>/output/<week>/` for `log_perf.py --edits`. Write `post_copy` on the item (caption, description, `search_query` verbatim, pinned comment) so the editor's finalize step ships the video with its words. The editor writes an edit record carrying the item id; `log_perf.py --edits <output dir>` joins the cut to the outcome.

## Optional layers (config-gated)

- **LinkedIn twins** (`linkedin_twins`): a primary item may carry a written twin as `item.linkedin`. A twin is a candidate, not an entitlement: `select_linkedin.py --dry-run` proposes shape, job and day under the cap in `selector.target_mix`, and the writer decides what to keep. Every twin ships a visual chosen from `references/linkedin-visuals.md`.
- **Leaders scan** (a filled `leaders-to-study.md`): results in `gtm_linkedin[]`.
- **Blog pipeline** (`blog_pipeline`): a posted LinkedIn text plus its sources is an article draft.
- **Carousels**: `references/linkedin-visuals.md` Shape 5; `carousel.py <spec>` renders, `build_carousels.py` derives a deck from a script.
- **Lead magnet**: the sibling skill `lead-magnet-report`.

## Hard rules

No invented creators, videos, metrics, memories or links. No em or en dashes anywhere. No third-party LinkedIn automation. A claim that cannot be sourced is cut, never softened. Tracked doctrine names no creator; creator specifics live in the workspace. Before adding a rule here, delete one.

# Week file schema (version 2)

One file per run at `<workspace>/weeks/<YYYY-MM-DD>.json`. `check_fidelity.py` validates it
(`--schema-only` runs just this pass) and `radar_gate.py` stamps it. Everything the
dashboard, the selector and the performance loop read is defined here and nowhere else.
Fields marked WARN are reported when missing or unknown and never fail a batch, because real
week files carry history; fields marked FAIL stop the batch.

## Top level

| key | type | rule |
|---|---|---|
| `schema_version` | int | 2. WARN when missing (a version-1 file). |
| `week` | string | the run date, `YYYY-MM-DD`, or that plus a suffix for a deliberate rewrite (`2026-08-17 v2`). FAIL if two files carry the same value. |
| `positioning` | string | one paragraph, the lens this batch was written through. |
| `supersedes` | string | optional: the `week` value this file replaces. The dashboard hides the superseded week unless `--all`. |
| `distribution[]` | items | the PRIMARY lane (the tab label comes from config). |
| `office[]` | items | the SECONDARY lane. |
| `linkedin[]` | posts | LinkedIn-only posts. |
| `gtm_linkedin[]` | posts | the leaders-scan posts (legacy key, still read). |
| `inspiration[]` | `{creator, platform, metric, metric_confidence, mechanic, link}` | the outliers found. |
| `experiment` | `{dim, arms: {a: [ids], b: [ids]}, metric, question}` | optional: the one pre-registered two-arm question for the week. `log_perf.py --report` answers it at n=4. One open experiment per lane. |
| `ammo[]` | `[{fact, number, source, lanes[], spent_on}]` | optional: 10 to 15 receipt-bearing rounds for the daily comment block, a by-product of the research sweep. The dashboard renders an Ammo tab. |
| `promised[]` | `[{text, made_in, due_week, paid_in}]` | optional: promises the show made to its audience. `radar_gate.py` warns on a due promise neither paid nor retracted. |
| anything else | | WARN "unknown top-level key". Legacy files carry `method`, `distribution_pass`, `receipts`, `sweep_note` and more; they are not errors. |

## Items (video lanes)

Required: `id`, `title`, `script_class` (`testimony`, `format`, `research`), `text_hook`,
`spoken_hook`, `script`, `value`, `sources[]` (`{label, url, published}`), `qa`, `psych`,
`intent` (`educational` or `storytelling`), `tam` (`wide` or `narrow`).

Also carried: `borrows`, `carries`, `hook_family`, `hook_styles[]` (from
`hook-psychology.md`), `visual_hook`, `directions`, `cta` (optional), `facet`, `post_type`,
`source_origin`, `plug` (`receipt`, `cta`, `pitch`), `note`, `shot_list`, `capture{}`
(testimony only), `search_query`, `stitch_candidate`, `beats[]` (format items: `{t,
on_screen, action}`; day-in-life VO items: `{role, text, b_roll, target_dur}`).

New in version 2:

- `proof` `{kind: own | reach | public, ref}`: whose material the payoff stands on. WARN when
  missing on `research` or `educational` items; `check_fidelity.py` prints the batch split.
  `own` is something no competitor could say; `reach` is the creator's company data; `public`
  is sourced from the open web. A batch that is all `public` is reproducible by anyone.
- `post_copy` `{caption, description, search_query, pinned_comment}`: what ships with the
  video. The editor's finalize step reads it; `search_query` rides verbatim.
- `linkedin`: the embedded twin (a post, below), when `linkedin_twins` is on.

## Posts (`linkedin[]`, `gtm_linkedin[]`, embedded twins)

Required: `id`, `body`, `qa`, `source` or `sources[]`. Carried: `type`, `hook_arch`, `visual`
(`{format, model, aspect, why, prompt}`), `script_class`, `plug`, and the selector's
declarations `news_peg_days`, `evergreen`, `arguable`, `executable`, `ordering_claim`,
`friction_story`, `deadline`. `select_linkedin.py` writes `linkedin_format`, `job`,
`post_day`, `post_slot`, `post_why`, and `twin_cut` or `banked` with a reason;
`post_day_locked: true` pins a day.

New in version 2: `held[]` (`[{fact, source}]`, two or three receipts kept out of the body
for the reply block) and `reply_stance` (one line); `target_person` (required by the
`individual` job); `intel_ref` (required by the `operator` job, points at
`weeks/<date>-intel.md`).

## Ids and qa

Ids are stable and never reused. Preferred shape `^(d|o|li|li-tw)-\d{8}-\d+$`; the legacy
dashed shape (`d-2026-06-23-9`) is WARN. Duplicate id inside a week: FAIL. Duplicate id
across weeks: WARN from `radar_gate.py`. Tracking, the performance ledger and the dashboard
are all keyed on the id, so a duplicate silently overwrites one post's numbers with another's.

`qa` takes exactly two values: `passed` (shippable today) or `pending-approval` (clean,
waiting on the creator). Anything else: FAIL.

## Stamp

`radar_gate.py` writes `weeks/<date>.gate.json` `{week_file, passed_at, engine, results
{gate: rc}, skipped[], ok}`. The dashboard warns on a missing or stale stamp, and refuses with
`--strict`.

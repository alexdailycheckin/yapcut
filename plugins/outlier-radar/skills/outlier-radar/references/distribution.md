# Distribution: what happens after the post is written

Writing was never the constraint. A small account's video is jailed at account level and its
LinkedIn pipe, not its writing, decides who sees the work. So the levers here are account-level
or run on other people's surfaces, and every one is written into the weekly loop so it happens
without being asked. The split is fixed: **the engine drafts and sources, the creator clicks.**
Third-party LinkedIn automation (auto-comments, auto-connects) is banned outright; the ToS
restriction risk on a small account outweighs any throughput gain.

Three of these levers have a schema and a dashboard surface, and they are the ones to run
first. Everything below them is protocol.

## 1. The daily block (ammo, comments, connects, the reply block)

- **5 to 10 receipt-bearing comments per weekday** on the roster of watering holes
  (`watch-accounts.md` and `leaders-to-study.md` in the workspace). Each comment carries ONE
  specific number or counter-take from the week's ammo, 20 to 50 words. No speed SLA:
  collapsed comment ranking rewards the quality of the comment, not the minutes to it. Skip
  a day rather than post filler.
- **10 to 20 connection requests per day** to audience people who engaged on a roster post
  or on the creator's own. The click stays human.
- **The reply block.** Post only when a 45 to 60 minute reply block follows. Each reply
  carries a second receipt or a counter-number, never "thanks". The receipts for it are
  written at drafting time as `held[]` on the post: two or three facts kept OUT of the body
  for exactly this use, plus one `reply_stance` line.
- **The engine's job, every research sweep:** emit `ammo[]` in the week file, 10 to 15 rounds
  of `{fact, number, source, lanes[], spent_on}`. They are a by-product of the receipts the
  sweep already verified, so they cost nothing extra. The dashboard renders an Ammo tab
  with a Spent toggle; the creator opens it with the coffee.
- **Measure:** the people ledger below, plus follower adds and profile views in
  `performance/followers.jsonl` (`log_perf.py --followers <week> <delta> [icp_pct]`).
  Retune the roster at four weeks if profile views do not move.

## 2. The people ledger

Prolific is scripts written. Relevant is who answers. Relevance shows first as a handful of
specific people reacting, long before views move, so the loop keeps a ledger of people rather
than only a ledger of posts: `performance/people.jsonl`, one row per person
(`{name, url, role, company, icp, first_seen, last_seen, touches[]}`), fed by paste:

    python3 ingest_feed.py --people --kind comment_by --post <id>     # paste a post's commenters
    python3 ingest_feed.py --people --kind connect                    # paste new connections

`log_perf.py --report` opens with the relevance line (returning versus new engagers this
week, and the share of engagers who match the audience), above impressions. Three hand
counts per week sit beside it and need no tool: audience comments, inbound conversations,
pipeline touches from content. A scoreboard that cannot tell reach from conversation learns
to post more reach.

## 3. Callback and promise (series memory)

A stranger becomes a follower when the episode implies a next one, and a follower becomes an
advocate when they are named in it. Two lines in every show skeleton: a **callback** (one
sentence naming last week's episode or a commenter) and a **promise** (what next week pays
off, including any comment-vote ask). Promises are tracked in the week file as
`promised[] {text, made_in, due_week, paid_in}`, and `radar_gate.py` warns on a due promise
that is neither paid nor retracted. A follow-up episode type is exempt from the no-repeat
rule, one per fortnight, because a return audience expects the sequel.

## 4. Day-0 (the news-peg SLA)

A weekly batch is structurally late for a news peg: the selector scores a peg at full value
to 3 days and half to 7, then schedules across five weekday slots from a weekly run, printing
the cost of the lateness its own cadence creates. So there are two rhythms. The **day-0
pass** (15 minutes, one story, one text post in the reach band or under 300 characters, the
ammo rounds for that story, no video) fires when a story breaks in the niche; set `post_day`
to that day and `post_day_locked: true` so the weekly selector fills around it. The **weekly
run** keeps evergreen, authority, playbook and the show. "Hot drop" is the creator's word
for the day-0 pass.

## 5. Tag the target (the guardrails are the law)

Tag at most one or two executives of the teardown subject, verified active on LinkedIn in
the last 7 days. Extra tags go in the first comment, never the body. Praise-gate: tag only
when the teardown is one the executive could plausibly reshare, because an unanswered tag
now costs reach and a critical teardown tagged at a prospect is pipeline damage. Measure
tagged versus untagged impressions at n=4, response rate, non-follower reach share.

## 6. Search lane (one episode a week)

Pick the news pick with real TikTok search demand and log the exact query as `search_query`
on the episode. The query rides VERBATIM in the caption and description, always
(`post_copy.search_query`, consumed by the editor's finalize step). It enters the burned hook
only if the hook still clears the gap test with it. Measure the traffic-source split per
video and views still accruing after day 7: the search-lane video is the one row where late
views are the point.

## 7. Stitch protocol

Research flags `stitch_candidate` with the canonical clip URL. The stitch is composed IN
the app from a stitch-enabled original (up to 5 seconds of the clip, then the same seated
talking head as the reply). Never fake it: burning the source clip into an off-app edit is
not a stitch, earns no interest-graph seeding, and creates rights exposure.

## 8. Photo mode

Every carousel also ships as a TikTok photo post, same renders, caption from the episode's
own script. A separate, less crowded lane with its own swipe metric that persists in search.

## 9. Prediction-market receipts

Before a spoken prediction ships, check Polymarket and Kalshi for a live market on the call.
If one exists, its odds are the receipt: screenshot in the shot list, spoken as "the market
says X, here is why I am at Y".

## 10. Counter-take invitation (one a week)

After an episode ships, DM one operator at the covered company and invite the counter-take,
posted from THEIR account. Log who was invited on the week file; the reply is a touch in the
people ledger. Over time this is the relationship channel that turns into companies pitching
their story for coverage, which is the only earned-media flywheel a solo creator can run.

## 11. HN and Reddit seeding

When a teardown's receipts layer survives that register (receipts first, zero marketing
voice, nothing about the creator in the body), the loop drafts the native version alongside
the LinkedIn post. The creator posts it; the engine never does. Monthly at most. Measure
referral spikes and profile visits, never upvotes.

## What to measure, and where

Every lever above names its measure. They all land in `performance/` through
`ingest_feed.py` and `log_perf.py`, and `log_perf.py --report` refuses to rank a dimension
under n=4. One pre-registered question per week (`experiment` in the week file) is how the
loop learns anything at five posts a week; passive bucketing across six dimensions does not.

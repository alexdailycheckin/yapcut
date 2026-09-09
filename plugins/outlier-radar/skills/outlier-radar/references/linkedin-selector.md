# The LinkedIn selector

How the week's substance becomes the right SHAPE and the right MIX on LinkedIn. This is the editorial layer: the objective, the argument for each stage, and the precedence when two rules pull against each other. The mechanics live in `scripts/select_linkedin.py` and are not re-prosed here.

## The problem it fixes

`references/post-types.md` picks the SCREEN shape for video, from substance, before a word is written. The LinkedIn side had no equivalent step, so the twin inherited whatever the video was. In `weeks/2026-08-10.json` that produced five twins all typed `receipt-react`, all doing the same job, none shaped as a carousel. Five posts of one shape read as one post published five times.

Video and text are not the same surface and do not reward the same thing. The FYP rewards watch-through on a hook. The feed rewards dwell, saves and early comment velocity. So the twin needs its own selection pass off the same substance, not a copied field.

**Building that pass did not fix it, and the reason is worth recording.** On 2026-08-11 the creator looked at the same week on the dashboard and found five identical shapes, on a week the selector had already assigned four different ones. Two separate causes, and only the first was the one anybody expected:

1. **The proposal was never written down.** `propose_format()` computed a format for every twin, printed it to stdout, and the write-back persisted `post_day`, `post_slot` and `post_why` only. The dashboard renders the week file, so it kept showing the inherited video type. A selector that reports a shape and does not save it changes nothing about what ships.
2. **The mix was unreachable, not merely unmet.** Twins were gated 1:1 to the video slate, so LinkedIn could only ever ship what the show had commissioned. A five-company show week forced five company posts. No reshaping at publish time can produce a confession that nothing upstream wrote, which is why the relatability leg read 0 of 1 in every week on disk and not just that one.

Cause 2 is the real one, and it is a structural point rather than a bug: **grading a mix at publish time cannot produce a mix.** The old loop picked five companies at step 3 and graded the portfolio at step 1 of the following week. The grade always arrived after the only decision that could have acted on it.

## The objective function

the creator's stated north star is engagement and account growth. Decomposed, follower growth on LinkedIn is:

**reach to non-followers x conversion to follow**

That decomposition is the whole reason a mix exists, and it is worth being precise about because the two halves are served by different posts.

**One refinement, and it is a real disagreement with the raw north star.** Raw follower growth is cheap to buy with broad-appeal content, and buying it makes the funnel worse while the number gets better. Your positioning file is what locks the primary student and the funnel it feeds, and it is the thing to read before accepting the raw number as the goal. If your audience's own words include any version of "followers don't pay bills", optimising raw follower count has you doing the exact thing your positioning mocks.

So the objective is **ICP-weighted growth**: net new followers times the share of them who are growth, marketing or GTM leaders. 200 followers at 20% ICP beats 500 at 2%. LinkedIn's follower demographics expose seniority, function and industry, so this is measurable rather than aspirational, and `log_perf.py --followers` records both numbers.

If the creator would rather optimise raw growth, that is a one-line change to the follower report and a reweighting toward reach formats. It is their call. The default is ICP-weighted because it is the one consistent with the locked positioning.

## Why a mix at all (the answer to "do we need this locked")

Not taste, and not a copied ratio. A portfolio, because each job serves a different term in the objective:

- **Reach posts** (news-jack, reorder, short provocation) generate impressions among non-followers. This is the acquisition leg. Without it the week only reaches people who already follow, and growth is structurally capped no matter how good the writing is.
- **Authority posts** (playbook, teardown) farm saves and dwell. A save reportedly drives about 5x the reach of a like and 2x a comment, so this leg is both the conversion mechanism (proof there is more where that came from) and a reach multiplier in its own right.
- **Relatability posts** (confession) convert lurkers and retain. Low reach, high follow-conversion. An account that only publishes analysis reads as a vendor, and vendors do not get followed.

Target is 2 reach, 2 authority, 1 relatability per 5-post week. Drop the reach leg and there is nobody new to convert. Drop the authority leg and strangers arrive with no reason to stay. Drop relatability and the account reads as a feed of press releases.

**Precedence.** The pillar mix in your own positioning file decides WHAT the week is about. The job mix decides WHAT EACH POST IS FOR. They are orthogonal and the pillar mix wins on subject matter. If the two ever conflict, change the shape of a post, never its pillar.

## The two lanes and the twin cap (2026-08-11)

LinkedIn stopped being downstream of the video slate. Two lanes feed the same five slots:

- **Twins**, on `distribution[]` items, are the written version of a video script.
- **LinkedIn-only posts**, in the week file's `linkedin[]` lane, have no video behind them and exist because the feed needed a shape the show did not commission.

Both compete on the same score with no bonus for having a video attached, and **at most `TWIN_CAP` of the five may be twins** (default 3). The cap is the mechanism, so it is worth being exact about what it buys: without it, a research-heavy week's strongest items are all the same shape, they win every slot on merit, and the week ships one post five times. Mix is allocated before score, so the best reach post cannot take a slot the week owes to relatability.

**A twin is a candidate, not an entitlement.** A twin that loses its slot is marked `twin_cut: true` and drops out of the feed plan. This costs nothing, and the creator made the argument themselves: the script still films, and it still ships on TikTok, Reels, Shorts and YouTube, where reach is the job. LinkedIn is the only surface where the ICP is the job, so it is the only one that has to be curated rather than filled.

**Where the missing shapes come from, and it differs by job.** When the mix is short, the selector names the job and says to commission it into `linkedin[]`, because that gap cannot be closed from the video slate by definition. The source depends on which leg is short, and conflating the two was the mistake on the first pass.

**Playbook is its own leg, targeted at 2 of 5** (the creator's call, 2026-08-11). It used to sit inside `authority` next to teardowns, which meant a week could satisfy the mix with two analyses and ship nothing runnable. The useful leg is now a requirement rather than a preference, because "give people useful things they can actually apply themselves to win" is the point of the account, not a nice-to-have.

**A playbook is sourced from what shipped on the market this week.** Not the show corpus, not the creator's notes. New tools, features, platform changes and dated deadlines the ICP has to act on, turned into moves they can run, with the same receipts gate as a reach post. This is fresh research every week and it is the one leg that requires it. The 2026-08-10 pair came from the Google Ads AI Max auto-upgrade dated 1 September and the agentic-buying shift, both verified against primary reporting the day they were written.

**Relatability is targeted at ZERO, and the reason is honest rather than strategic.** A confession needs a failure that actually happened, and this engine cannot have one. Every attempt to fill the leg mined the creator's own work journal and produced posts they did not want and would not have written, twice. The format stays defined so a confession types correctly on the rare week the creator writes one themselves, and the mix simply stops asking. A leg nothing can supply is not a target, it is a nag. The earlier `relatability_candidates()` prompt survives for that case but no longer fires, since the target is met at zero.

**A dated cutoff goes in `deadline`, never in the peg.** A news peg loses value as it ages, so the sort races the clock downward. A deadline gets more urgent as it approaches and the post is not weaker after it passes, it is wrong. Scored as news, the Google Ads playbook looked half-decayed and drifted down the order. The selector now sorts deadline items on days-until-cutoff and refuses to let one ship past its own date without saying so.

**Never persist a computed value to the key that overrides the computation.** For a few hours on 2026-08-11 the selector wrote its chosen format back to `linkedin_format`, which `propose_format()` reads as a human declaration. Run two therefore treated run one's guess as the creator's instruction, and two pegged playbooks stayed typed as newsjacks through three separate attempts to fix the precedence, because the precedence was never reached. The computed shape now persists to `shape`; `linkedin_format` is the hand override and nothing but a human writes it.

**A runnable playbook outranks its own news peg.** The format tree used to check the peg first, so anything timely became a newsjack. That was harmless while playbook lived inside authority and fatal once it became its own leg. The peg decides WHEN to post, not WHAT the post is, and the test is whether every unit names a move.

**Reach and authority both come off the show's own sweep.** A standing call from the creator, 2026-08-11: authority comes from the same research as reach, not from their notes, because those notes are anecdotal and may not be the best available material. What separates the two is the unit of analysis, not the rigour:

- **Reach** is one company on one news peg, with one unclaimed angle.
- **Authority** is the pattern ACROSS companies, cross-cut from teardowns the show already verified and receipted. It makes no new factual claim, it synthesises. That is also why it enumerates naturally (one unit per pattern, two or three named companies each), why it is evergreen, and why it is the easiest carousel in the file to produce.

The corpus is the point. The show banks five companies a week and had 118 items across 12 weeks by 2026-08-11, so this post type gets stronger every week and never needs a fresh source. An authority slot is never genuinely empty.

**A playbook is a set of MOVES, not a set of patterns.** Alex, 2026-08-11: give people useful things they can actually apply themselves to win. The first authority post cross-cut five patterns across thirteen companies, passed every shape check, and left the reader with nothing to do before Monday. It was a diagnosis wearing a playbook's formatting.

The inversion that fixes it: **the show's companies are the PROOF, not the subject.** Each unit carries four things, in this order:

1. An instruction, leading with the verb. Not "before the next campaign ships, write the follow-ups" but "write the two follow-ups before the next campaign ships". Burying the verb is the tell that a move is really an observation.
2. What it costs, in time or in who has to say yes. An afternoon, a 30 minute meeting, a morning in their changelog.
3. Who already paid for the lesson, named, with the real number.
4. How the reader knows it worked.

`playbook_moves()` checks item 1 mechanically and the verdict flags any F1_playbook whose units do not open with an instruction. It is a heuristic and says so: it can tell whether a move was named, never whether it is a good move. It caught the rewrite at 4 of 5 on its first pass, and the fix made the copy stronger, which is the usual result of leading with the verb.

It also cross-checks the declared `executable` flag. That flag is author-declared and easy to over-claim in good faith, which is exactly what happened on the first pass. When a post declares `executable: true` and reads diagnostic, the selector says so rather than silently trusting the declaration.

**Relatability is the one leg research cannot fill, so the selector ASKS.** A confession needs a failure that actually happened, and only the creator knows whether one did. This is the same class as `arguable` and `friction_story`: declared, never inferred, because a regex that claimed to detect real friction would be worse than the question.

Asked cold the answer is always no, since nobody recalls their own week on demand. So `relatability_candidates()` reads `work-journal/` over the 10 days to the anchor and puts the actual material on screen, ranked seeds before tensions and first person before third, because relatability needs the creator IN the story rather than observing it. Seeds carry the verbatim scene and a `naming` line stating what to abstract, so they are closer to ready than a raw tension.

**An empty relatability week is the expected case, not a failure.** The format library caps confession at once a fortnight, so answering "none" is a legitimate outcome and the slot goes to a second authority post. Shipping 2 reach / 3 authority / 0 relatability beats shipping a manufactured confession, which is the single most punished move on the platform.

`capture/` remains the intended testimony path but it runs dry: every file on it had been consumed by the 2026-07-26 week. The work journal is the live source.

**Relatability was structurally impossible before this, not just neglected.** A confession needs testimony with real failure. The office lane holds the personal-story formats and the schema gives office items no twin, so nothing in the pipeline could reach the feed as a confession. Fixing the cap without opening `linkedin[]` would have left that leg empty forever.

## Stage 1: shape from substance

Same principle as the video type-fit rule, different inputs, because the feed cares about different properties. The tree runs in `select_linkedin.py`; the reasoning is:

- A **fresh news peg** is worth more than anything else in the post, so it takes the shape that exploits it (news-jack teardown), and it decays. Full value at 3 days or less, half at 4 to 7, zero after that, at which point the same analysis has to stand on its own merits as an authority post. The first version of this rule was a flat 48-hour cliff; it was corrected 2026-08-10 when it failed every real item in `weeks/2026-08-10.json`, because the peg decays with saturation in the ICP's feed rather than with the clock, and B2B LinkedIn saturates slower than consumer media. A Friday earnings story posted Monday is on time.
- A **saturated story can still carry an unclaimed angle**, and the two expire on different schedules. Amazon's $3 trillion was the loudest business story of its week, but the $19.8bn advertising line inside it was untouched. Declared as `angle_unclaimed`, scored separately from the peg, and the reason a 7-day-old story still earned the reach slot.
- **Enumerated units** are the strongest signal available, because a post with three or more headed units is carousel-shaped, and format outweighs everything else on this surface.
- An **ordering argument** beats a plain list, so if the claim is about sequence it becomes a reorder rather than a playbook. Conceding the items and attacking the order is much harder to scroll past.
- **Real friction in a testimony piece** becomes a confession. This is the scarcest input in the engine and the one the creator under-supplies.
- **One verified counterintuitive number** with nothing to explain becomes a short post, because padding it to reach the band would destroy the only thing it had.

**What the selector refuses to do.** Three properties need human judgment and are declared, never inferred: whether a claim is genuinely arguable, whether a list is an ordering argument, whether a story carries real failure. A regex cannot detect contrarianism, and a tool that pretends to is worse than one that asks. Undeclared items get flagged and score conservatively.

## Stage 2 and 3: slots and scoring

Allocation fills the five slots against the target mix, then scores candidates within each slot. Weights are in the script, visible with `--weights`, and deliberately not buried.

The one thing worth stating in prose: **the carousel weight is the largest by design.** Document posts run around 6.60% engagement against roughly 2.00% for text-only, so the shape decision dominates every other lever in the file. Tuning a hook on a text post that should have been a carousel is optimising the wrong variable.

And it is executable. linkedin-engine's `references/carousel-cards.md` owns the approved editorial-object style plus the Higgsfield prompt recipe, and its `scripts/carousel.py` renders a set from a JSON spec. Radar's own contribution is upstream of that: the depth cards must come from the source script's beats, which is exactly what a Radar teardown already produces, so the carousel is a second surface for verified work rather than a fresh writing session.

**Length is a constraint, not a score.** The reach band is 1,300 to 1,900 characters, the dead zone is roughly 600 to 1,000, and the hard stop is 2,500. Being in the band earns nothing; being in the dead zone is penalised. Never pad to reach the band. Full derivation in linkedin-engine `references/save-mechanics.md`.

## Posting order: urgency, not score

The week ships in decay order, not quality order. **Urgency is how fast an item loses value, which is not the same as how old it is.** A 7-day peg that expires tomorrow outranks a 5-day peg with three days of room, even though the 5-day story is fresher. The selector sorts on days-until-next-decay-step, breaks ties on score, and puts evergreen items last because they hold their value.

That ordering has a consequence worth stating: **a great post whose peg died is worth less than a good post published while its peg is alive.** So score never overrides urgency. It only decides which of two equally urgent items goes first.

Evergreen wildcards are the buffer. They absorb a slipped week or get bumped for a hot drop without costing anything, which is the real argument for keeping two of them in every five.

**Not every post's asset is a carousel.** Stage 0 of the asset step picks between four
single-image shapes and the document, from the post's own inputs, and answers "text
only" when none of them has an input on disk. See `references/linkedin-visuals.md`.

When the selector flags a LATENT carousel (a sequence argument written as prose), the restructure is a judgment call on live creative, so it reports and stops. The tooling is ready if the call is yes: read `carousel-cards.md`, write a spec, run `carousel.py`.

**The order is total, and the days are written down.** Sort keys are days-until-next-decay-step, then score, then id. The id key exists so the result never depends on the order items happen to sit in the file: same week in, same days out, every run. The selector writes `post_day`, `post_slot` and `post_why` back onto each twin, which is what the dashboard calendar renders. Before 2026-08-10 it printed the days to stdout and wrote nothing, so the schedule died with the terminal buffer and the dashboard had nothing to show.

**What is left to a human is the shape, not the order.** When an item's peg is spent by the day it earned, the tool prices the loss and says so, but it does not reopen the ordering. A news-jack whose peg is dead is the wrong shape for its slot, because the news is no longer the reason to stop scrolling. Either it moves up and the item above it takes the loss instead, or it gets rewritten as an authority post that stands on the analysis alone. That is a rewrite of live creative, which is the same class of call as the LATENT carousel above: the tool prices it and stops. An earlier version of this rule framed that as a SLOT CONFLICT with the ordering unresolved, which was wrong on its own terms, since the sort had already assigned every day four lines earlier.

To pin a day by hand, set `"post_day_locked": true` on the twin. The selector keeps that day and fills the remaining weekday slots around it in urgency order, so an override never leaves a gap or a double booking.

## The convergence loop (what makes this an algorithm rather than a rubric)

The weights ship as **priors from platform research, not from the creator's data**, and they are labelled as such. That is the honest starting position, because as of 2026-08-10 there is nothing to learn from:

- `performance.jsonl` holds 22 rows, every one recorded at 215 views on a single day because the creator reported all videos landing at 200 to 230. Zero variance, so zero signal.
- Those rows are also orphaned: their ids predate the current id scheme and no longer resolve to a week file, so their dimensions all report as unknown.
- The LinkedIn lane was never logged at all, because `load_items()` read only the `distribution` and `office` lanes. Fixed 2026-08-10.

So the sequence is: measure first, converge second. `log_perf.py --report` ranks each dimension only once it clears n=4 and says so explicitly otherwise. At five posts a week, the coarse dimensions (carousel or not, job class) clear that in about a month; the fine ones (hook architecture) take a quarter or more. Update the coarse weights from real numbers first and leave the fine ones on priors until they earn it.

**Two things that cannot be measured, so do not pretend.** LinkedIn does not expose saves or dwell time to authors. Both are central to how the ranking works and neither is observable, so impressions and engagement rate are the proxies, and every save-related weight stays a prior permanently. Say this out loud rather than quietly treating impressions as if it were the objective.

## Honest limits

- Five posts a week is 20 a month. This is directional learning, not experimentation. Do not A/B a hook mold and act on n=3.
- Changing two things at once teaches nothing. When a weight moves, move one.
- Constitution rule 10 governs: failures get diagnosed with data, never answered with new law. If a week underperforms, the response is a number, not another rule in this file.

## Cross-references

- `scripts/select_linkedin.py` the mechanics, weights, and the week verdict
- `scripts/log_perf.py` the loop: `--linkedin` for twins, `--followers` for the north star, `--report` for what has cleared n
- `references/post-types.md` the video-side equivalent, screen shape rather than feed shape
- linkedin-engine `references/save-mechanics.md` the length band, the format lever, the CTA gate, and the sourcing for every figure quoted here
- linkedin-engine `references/format-library.md` FORMAT 1 to 4, the shapes this selector assigns

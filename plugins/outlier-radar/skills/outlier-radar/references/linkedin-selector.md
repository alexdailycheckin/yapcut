# The LinkedIn selector

How a week's substance becomes the right SHAPE and ships in the right ORDER on LinkedIn. This is the reasoning layer; the mechanics live in `select_linkedin.py` and are not repeated here.

Only relevant when `linkedin_twins: true` in radar-config.json.

## The problem it fixes

`references/post-types.md` picks the SCREEN shape for video, from substance, before a word is written. The LinkedIn side had no equivalent step, so the twin inherited whatever the video was. That produces a week of identical shapes, and five posts of one shape read as one post published five times.

Video and text are not the same surface. Short-form video rewards watch-through on a hook. The feed rewards dwell time, saves and early comment velocity. Same substance, different shape, chosen by different rules.

## The objective

Follower growth on LinkedIn decomposes to:

**reach to non-followers x conversion to follow**

That decomposition is the whole reason a mix exists, because the two halves are served by different posts.

**One caution about the north star.** Raw follower growth is cheap to buy with broad-appeal content, and buying it makes your funnel worse while the number improves. If you have a defined customer, weight growth by the share of new followers who actually match it. Two hundred followers at twenty percent on-profile beats five hundred at two percent. The platform's follower demographics expose seniority, function and industry, so this is measurable rather than aspirational.

## Why a mix at all

Not taste, and not a ratio copied off someone else's account. A portfolio, because each job serves a different term in the objective:

- **Reach posts** (newsjack, reorder, short) generate impressions among non-followers. This is the acquisition leg. Without it the week only reaches people who already follow you, and growth is structurally capped no matter how good the writing is.
- **Authority posts** (playbook, teardown) farm saves and dwell. A save reportedly drives about 5x the reach of a like and 2x a comment, so this leg is both the conversion mechanism and a reach multiplier in its own right.
- **Relatability posts** (confession) convert lurkers and retain. Low reach, high follow-conversion. An account that only publishes analysis reads as a vendor, and vendors do not get followed.

Target is 2 reach, 2 authority, 1 relatability per five-post week.

**Precedence.** If you keep a topic or pillar mix, that decides WHAT the week is about and it wins. The job mix decides WHAT EACH POST IS FOR. They are orthogonal. When they pull against each other, change a post's shape, never its topic.

## Shape from substance

The tree runs in `select_linkedin.py`. The reasoning:

- A **live news peg** is worth more than anything else in the post, so it takes the shape that exploits it (newsjack), and it decays. Full value at 3 days or less, half at 4 to 7, zero after. The peg decays with saturation in your audience's feed rather than with the clock, and a B2B feed saturates slower than consumer media, so a Friday earnings story posted Monday is on time. A flat 48-hour window is too tight for this surface.
- A **saturated story can still carry an unclaimed angle**, and the two expire on different schedules. When everyone covered the headline and nobody covered the mechanism, the post still works past the window, but it is now carrying itself on the analysis, so hold it to the authority bar rather than the news-jack one.
- **Enumerated units** are the strongest signal available, because three or more headed units means the post is carousel-shaped, and format outweighs every other lever here.
- An **ordering argument** beats a plain list, so if the claim is about sequence it becomes a reorder rather than a playbook. Conceding the items and attacking the order is much harder to scroll past.
- **Real friction of your own** becomes a confession. Usually the scarcest input in the week.
- **One verified counterintuitive number** with nothing to explain becomes a short post, because padding it to reach the band destroys the only thing it had.

**What the selector refuses to do.** Three properties need judgment and are declared, never inferred: whether a claim is genuinely arguable, whether a list is an ordering argument, whether a story carries real failure. A regex cannot detect contrarianism, and a tool that pretends to is worse than one that asks. Undeclared items are flagged and score conservatively.

## Length

Measure in CHARACTERS. Characters are what the platform counts and what the fold and the 3,000 cap are measured in.

Two viable shapes, and the mechanism is dwell time:

- **Under about 300 characters.** Cannot win on dwell, so it wins on reply volume instead. One idea, a real question or an arguable take, no body.
- **1,300 to 1,900 characters.** The reach band. Long enough to hold a reader the 30 to 60 seconds where distribution peaks, which means structure and payoff have to do the work. Hard stop at 2,500, past which engagement falls off.

**The dead zone is roughly 600 to 1,000 characters.** Too long to read at a glance and reply to, too short to hold anyone for thirty seconds. It buys neither mechanism. Resolve it in one direction: cut to the single sharpest observation plus a question, or take it to 1,300.

**Length is a ceiling, not a target.** A 1,500-character post that gets finished beats a 3,000-character post abandoned halfway, because completion rate is part of the same signal. Never pad to reach the band.

## Format beats length

Worth knowing before spending any effort tuning characters: document posts (native PDF carousels) report around 6.60% average engagement against roughly 2.00% for text-only. That is a 3x gap and no amount of character tuning closes it.

The playbook and the reorder are already carousel-shaped: a sequence of discrete units with a header each. Ship those as documents with the text post as framing, and keep pure text for the shapes that depend on prose, which are the newsjack and the confession.

The pipeline for it already exists in this skill: flag the script "Carousel" on the dashboard, click Export carousel queue, save into `<workspace>/carousels/`, then run `build_carousels.py`. Branding comes from the `brand` block in radar-config.json.

One rule that matters more than the layout: **the cards come from the source script's own beats, never from a fresh writing session.** The teardown does the thinking and the carousel is a second surface for it. Inventing claims at card-design time is how a set ends up carrying facts the script never verified. And card copy is still copy: the verbless noun-phrase fragment ("Zero budget, six million views") fits a layout neatly and is the loudest generated-text tell there is. Cut an idea to fit, never the grammar.

## Posting order: urgency, not score

The week ships in decay order, not quality order. **Urgency is how fast an item loses value, which is not the same as how old it is.** A 7-day peg expiring tomorrow outranks a 5-day peg with three days of room, even though the 5-day story is fresher. The selector sorts on days-until-next-decay-step, breaks ties on score, and puts evergreen items last because they hold their value.

The consequence worth stating: **a great post whose peg died is worth less than a good post published while its peg is alive.** Score never overrides urgency; it only decides which of two equally urgent items goes first.

Evergreen items are the buffer. They absorb a slipped week or get bumped for a hot drop without costing anything, which is the argument for keeping one or two in every five.

When more items expire than there are day-one slots, the selector reports the conflict and stops. Doubling up on day one splits the audience; taking the peg loss republishes the lower scorer as an authority post. That is a judgment about which post matters more this week.

## Sourcing and limits

Every figure quoted here comes from vendor studies and published annual algorithm reports, not from the platform itself. Much of the "optimal length" material online is content-farm copy citing itself, so convergence across sites is not independent confirmation. Treat the direction as reliable and the decimal points as indicative.

Two things cannot be measured, so do not pretend otherwise: the platform does not expose saves or dwell time to authors. Both are central to how ranking works and neither is observable, so impressions and engagement rate are the proxies, and every save-related weight stays a prior permanently.

The weights in `select_linkedin.py` are priors, not findings. Replace them with your own measured results, and only once a dimension has enough posts behind it to mean something. At five posts a week the coarse dimensions (carousel or not, job class) take about a month; the fine ones take a quarter or more. Move one weight at a time, because changing two things at once teaches nothing.

## Cross-references

- `select_linkedin.py` the mechanics, the weights, the week verdict and the posting order
- `references/post-types.md` the video-side equivalent: screen shape rather than feed shape
- `references/hook-library.md` the first-line patterns that open each shape

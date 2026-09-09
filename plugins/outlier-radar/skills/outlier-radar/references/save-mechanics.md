# Save Mechanics

_Moved here from the linkedin-engine skill on 2026-09-09: LinkedIn mechanics are owned by this plugin so the public engine never cites a private one._

The empirical layer under `hook-library.md` and `format-library.md`. Those two files say what to write. This one says what the corpus actually shows about why a post gets kept.

## Provenance and limits (read this before citing anything below)

Source: a teardown of ~35 LinkedIn posts, analysed 2026-08-10. the creator saved them by deliberately selecting the top performers from a set of accounts he follows, so treat the corpus as a curated top-of-distribution sample: roughly the best work of those authors, not a random sample of it.

That makes it a stronger dataset than a generic saves list. What it still is not:

- **Selected on visible signals, not measured ones.** Reactions and comment counts are visible in the feed; impressions and dwell are not. So the corpus is ranked by what looked like it performed.
- **No control group.** The same authors' flops are not in the set, so the file can say what the winners have in common but cannot prove those traits caused the win rather than merely accompanying it.
- **One operator's eye.** The selection reflects the creator's judgment of good, which is a feature for tuning to his voice and a bias everywhere else.

Practical rule: patterns here are strong enough to draft against and to argue for. They are not strong enough to carry a stated performance number. Where this file quotes a percentage, the percentage comes from the platform research in the length section, never from the corpus.

The upgrade: rank the creator's OWN posts by impressions and engagement rate from his activity page, then cross-reference, to see which of these patterns move HIS audience rather than a B2B-founder audience in general.

Skew to keep in mind: roughly ten of the ~35 are Chris Donnelly, with the rest clustered on Elena Verna, Lenny Rachitsky, Michel Lieben, lemlist and Harry Stebbings, and themes concentrated on AI search, outbound, growth teardowns and hiring frameworks. That is the creator's ICP, which is lucky, and it will transfer badly to anything else.

## The save trigger

Across the corpus one thing separates the saved from the merely liked: **the post delivers complete value in the feed.** Nothing saved required leaving the post to get the point. The reader could execute from the post alone.

That is the whole mechanism. A save is a reader saying "I will need this again". Nobody bookmarks a teaser.

Two consequences:

1. **Never split value across the post and a link.** If the real payload is behind a click, the post is an ad and gets a like at best. Put the mechanism in the body and let the link be optional.
2. **This aligns with the algorithm rather than fighting it.** LinkedIn suppresses posts that push traffic off-platform, so the self-contained post wins twice.

Read this next to the fold gate in the `copywriting` skill. The fold gate protects the first two lines. The save trigger protects the last ones: the post has to actually pay.

## The length law

Measure in CHARACTERS, not words. Characters are what LinkedIn counts, what the 3,000 cap is set in, and what the fold is measured in.

The corpus bifurcates hard: posts were either 2 to 4 lines, or a long structured list, with almost nothing in between. Platform research says the same thing but gives the reason and corrects the upper bound.

**The mechanism is dwell time.** LinkedIn ranks on how long people actually stay on a post. The reported curve is steep: posts holding a reader 0 to 3 seconds land around 1.2% engagement, 31 to 60 seconds is where distribution peaks, and 61 seconds and over reports around 15.6%. So length is not a style preference, it is a bid for seconds.

**The reach band is 1,300 to 1,900 characters** (roughly 220 to 320 words). Buffer's analysis of 10,000+ posts puts that range around 47% above shorter posts, and reports posts over 2,500 characters dropping about 35%. That last number matters here: the range I first wrote from the corpus alone, 200 to 500 words, tops out at 3,000 characters and so runs past the falloff. **Corrected ceiling: stop at 1,900, hard stop at 2,500.**

**So the two viable shapes are:**

- **Under about 300 characters.** Too short to win on dwell, so it has to win on comment velocity instead: a real question, a take people argue with, a reaction. One idea, no body.
- **1,300 to 1,900 characters.** Long enough to buy 30 to 60 seconds if it holds, which means structure and payoff do the work. This is the reference post.

**The dead zone is real, and it sits at roughly 600 to 1,000 characters** (the 100 to 150 words the creator asked about). It buys neither mechanism: too long to read at a glance and reply to, too short to hold anyone for thirty seconds. A draft landing there is not slightly suboptimal, it is competing on dwell and losing. Resolve it in one direction: cut to the single sharpest observation plus a question, or do the work and take it to 1,300.

**Length is a ceiling, not a target.** A 1,500-character post that gets finished beats a 3,000-character post abandoned halfway, because completion rate is part of the same signal. Never pad to reach the band. If the material is only worth 400 characters, ship 400 characters as a short post.

## The format lever beats the length lever

Worth knowing before spending any effort tuning characters: format outweighs length by more than length outweighs anything. Van der Blom's 2025 report puts document posts (native PDF carousels) around 6.60% average engagement against roughly 2.00% for text-only. That is a 3x gap, and no amount of character tuning closes it.

The implication for this library is specific. The numbered playbook (FORMAT 1) and the reorder (FORMAT 3) are already carousel-shaped: they are a sequence of discrete units with a header each. Ship those as documents with the text post as the framing, and keep pure text for the formats that depend on prose, which are the news-jack teardown and the confession turn.

**This is now executable, not aspirational.** `references/carousel-cards.md` owns the approved editorial-object style (one deadpan studio object shot per slide, argument set in type underneath, cover card lists the moves and one depth card per move) plus the Higgsfield prompt recipe for the object photos, and `scripts/carousel.py` renders a set from a JSON spec so nothing is hardcoded per project. Read the reference and write a spec; never fork the renderer.

Three rules from that file that this one has to respect rather than restate: the depth cards come from the source script's own beats and never from a fresh writing session, card copy runs the full `copywriting` sentence layer with no short-form exemption, and the verbless noun-phrase fragment ("Zero budget, six million views") is blacklisted on cards precisely because it fits a layout so neatly.

Corroborating the whole premise of this file: one save reportedly drives about 5x the reach of a like and 2x a comment. Saves are not just the high-intent signal, they are the highest-value reach signal on the platform. That is the argument for the self-contained payoff rule above.

Sourcing note: these figures come from vendor studies and the annual Algorithm Insights report, not from LinkedIn. Much of the "optimal length" material online is content-farm copy citing itself, so the convergence across sites is not independent confirmation. Treat the direction as reliable and the decimal points as indicative.

## Line discipline

Consistent across every high-craft post in the corpus:

- One thought per line, blank line between. No dense paragraphs anywhere.
- The hook is its own line, standing alone.
- A glyph rail down the left edge so a skim-reader gets the whole shape in five seconds.
- Each point carries a number, a name, or an example. Never a bare assertion.

On glyphs, a taste call and I will name it as taste: the corpus uses two different systems and only one suits the creator. The typographic set (`↳`, `→`) reads as structure. The emoji set (`✅`, `❌`, `1️⃣`) reads as a lead-gen account. the creator's voice is operator, not vendor, and `hook-library.md` already bans opening on an emoji. Use the typographic set. Skip the emoji set even though it is well represented in the corpus.

## CTA policy

The polished corpus posts close with a three-part stack: a save prompt, a comment-a-keyword lead magnet ("Comment OUTBOUND"), and a repost ask.

**Default: one ask, matched to the post's job.** Not the stack. Three asks split the reader's attention and the post ends up getting none of them.

- **Authority post** (playbook, teardown): no ask, or a bare "Save this". The value is the ask.
- **Reach post** (contrarian, news-jack): a question that invites real disagreement. Disagreement is the comment engine.
- **Relatability post** (confession, moment): an open question that invites the reader's own version.

One soft line, below the value, at the very bottom.

### The comment-keyword magnet: allowed, gated

It is a legitimate play and it stays in the toolkit. It works for a real reason: it manufactures comment velocity, and velocity in the first 30 to 60 minutes is one of the strongest ranking inputs there is. Banning it outright would be giving up a real lever on principle.

Run it when all four hold:

1. **There is a genuine asset behind it.** A template, a sheet, an audit, a teardown, a swipe file. Something the creator would have charged for or spent real hours on. A keyword that delivers a link to a blog post is a bait-and-switch and the audience clocks it immediately.
2. **The post already paid.** The magnet is an upgrade on delivered value, never the reason to read. If removing the magnet leaves a post with nothing in it, the post was an ad.
3. **the creator will actually deliver, every time, by hand or by a reliable process.** An undelivered magnet is worse than no magnet: it burns the exact people who raised their hand.
4. **The post type suits it.** Playbooks and list posts, yes. Never on a confession or a teardown of a named company, where an ask reads as instrumental and retroactively cheapens the post.

Cadence: once or twice a month, not a default close. The cost is real and it is cumulative, not per-post. An account that closes every post with a keyword stops reading as an operator sharing work and starts reading as a funnel, which is the specific thing an authority-first phase is protecting. Spend it on the posts with a real asset behind them and it stays potent.

Never stack it with the other two asks. If the keyword is running, it is the only ask in the post.

## Post jobs

Every post does one of three jobs: authority, reach, relatability. Use it as a drafting question, singular: what is this post for? A post trying to do all three does none.

**Ratios only bind when producing a calendar.** Drafting a one-off post, there is no mix to satisfy: write the post the material wants. The ratio question only arises in the Friday interview, where the output is five posts at once and the week can come out lopsided without anyone noticing.

When a calendar IS being built, the ratio already exists and lives in the creator's positioning file: roughly 3 / 1.5 / 1 / 1 / 1.5 across the five pillars per seven posts. Do not introduce a second competing ratio in jobs terms. Map instead:

- Pillar 1 (Product vs Distribution) and Pillar 4 (In the Arena) carry **authority**.
- Pillar 2 (The Distribution System) and Pillar 3 (The Specifics) carry **authority** or **reach**, depending on whether the post teaches or provokes.
- Pillar 5 (Human OS) carries **relatability**.

Use jobs as the check on a finished calendar: five authority posts in a row is a dry week, and the fix is a pillar swap, not a new ratio.

## The proof bank

The highest-leverage line in the whole teardown is structural: the prolific accounts sustain volume because production is assembly, not invention. Every saved post anchors a claim to something concrete. The bottleneck is not writing, it is having a verified number to hand.

So keep a standing proof bank and draft against it. Seeded from the vault, verified:

- Rush Trampolines: built to $2M ARR and 60+ employees, exited.
- Mondans: 800K+ followers, 2M+ monthly organic engagement.
- Previous AI startup: zero to $600K ARR in five months.
- 4x founder, 2 exits.

Company-side proof: check the company's PUBLIC customer-results page first. Anything already public there is usable without an approval step.

Anything that appears in a teardown but not on a public page or in the creator's own records is unverified. Confirm it before a single figure goes in a post.

Rule: a claim with no entry in the bank and no live source does not go in a post. Cut the claim or cut the post.

## The swipe corpus

Authors worth reading for structure rather than takes, in rough order of density in the saves:

Chris Donnelly (Searchable), Elena Verna, Lenny Rachitsky, Michel Lieben (ColdIQ), lemlist, Harry Stebbings, plus one-offs from Jamie Pagan, Ben Gusberg, Ben Lang, Jose Velez, Eric Lay, Fivos Aresti, Louis Van Wyk, Eduardo Ordax, Sam Hogan.

Use them for skeletons. Do not inherit their CTA behaviour, their emoji rails, or their cadence.

## Cross-references

- `references/format-library.md` FORMAT 2, 3 and 4 are the three structures this teardown surfaced that the library did not already carry
- `references/hook-library.md` for the confession mold, which the corpus surfaced and the library was missing
- `references/3-i-framework.md` for the Industry / ICP / Individual layer, which sits above post job
- `copywriting` skill for the fold gate, the sentence layer, and the AI-tell gates

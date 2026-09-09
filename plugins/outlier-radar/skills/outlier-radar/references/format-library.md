# Format Library

_Moved here from the linkedin-engine skill on 2026-09-09. Hooks are in `hook-library.md` and `hook-psychology.md` in this folder; the LinkedIn-only hook deltas (the 220-character fold) stay in linkedin-engine._

Canonical post STRUCTURES (styles), as distinct from hooks. A hook is the first line. A format is the whole skeleton: how the body is organised, what the reader does inside it, and how it lands.

The core insight this file is built on: **most short-form video styles are LinkedIn formats waiting to be un-filmed.** A video hook ("If I were starting over...") plus a video body structure (numbered list, before/after, day-in-the-life) is already a complete post architecture. Strip the camera, keep the skeleton, add real names and real numbers, and you have a LinkedIn post. The video engine and the LinkedIn engine share one library of structures; this file is the LinkedIn-side translation.

Two parts:
1. **The named formats** (fully specified, ready to draft against).
2. **The video-style translation table** (all 15 hook families from the video hook library, each mapped to its LinkedIn format).

Every format below inherits the house voice: compressed, direct, contrarian, value-dense, no em dashes or en dashes, no consultant-speak. And every format still needs a hook from `references/hook-library.md`. Format is the body; hook is the door.

---

## FORMAT 1: The Starting-Over Playbook

The "if I were building this from zero" post, where the twist is that the writer actually is. A numbered list of moves, each move anchored to a real named operator or tool, closed by a contrarian takeaway that reframes the whole list as thought leadership rather than a brag.

This is the format behind the "$0 AI startup GTM plays" post. It fuses two video hook families (Starting-over / hypothetical + Listicle) and layers the Individual-post mechanic (name a real person, prove you consume their work, give them a reason to comment) onto every item. Nine named operators equals nine distribution nodes. It is a tag-bait engine disguised as a founder's operating plan.

### Why it works

- **The "AND I AM" turn.** The hypothetical hook ("if I were starting over") is familiar and gets scrolled. Adding the parenthetical that you are literally doing it right now converts a thought experiment into a live announcement. Stakes and specificity in three words.
- **Every item is a mini Individual post.** Each numbered play names a real person, makes a specific claim that proves you actually use them, and often adds a personal tie ("I get the homie rate because I post about it"). That is the HubSpot-template mechanic (see `references/individual-post-mechanics.md`) repeated N times in one post. Each named person has a reason to comment, react, or reshare.
- **Numbers per item = credibility.** "44 to 164 winning keywords in six months", "$6m emails/mo", "1,335 simultaneous conversations". Specific > clever, every time.
- **The takeaway launders the brag.** Without it the post is a flex. The takeaway ("the bootstrapper does MORE things at LESS cost", "two things every launch needs") reframes the list as a point of view about how to build. That is what makes it Industry-tier thought leadership, not a vendor post.
- **Soft CTA at the very bottom.** One link, one line of offer, after the value is fully delivered. Never in the hook.

### The skeleton

```
[HOOK] If I were [building X from zero] today - AND I AM - here are the [N]
       [plays / moves / bets] I'd run to [specific outcome]
       (+ the [people / tools] I'd use to do it):

1. [Move, sentence case, verb first.]
   [Named operator or tool] [specific thing they do] [proof/number].
   [One personal tie or reason it's real.]

2. [Move, sentence case, verb first.]
   ...

[repeat for N items, 7-10 is the sweet spot]

[Takeaway, sentence case, on its own line]
[The contrarian compression. What the list actually proves.]

[The non-negotiables: 2-3 things every X needs, no matter what.]

[One direct question to the reader in the same situation.]

· · ·

[Soft CTA: link + one-line offer]
```

### The rules that make it land

- **7-10 items.** Under 7 looks thin for a "playbook". Over 10 stops being scannable.
- **Numbered sentence-case headers, never all caps** (the creator's correction, 2026-08-14: caps read as shouting and paste badly; the old caps rule is unlearned). "1. Agree the denominator." The number is the rail: it lets a skim-reader get the whole plan in five seconds, and the header itself leads with the verb so the move is named before the proof.
- **One named human or tool per item, and the claim must prove consumption.** "Sam Dunning took RB2B from 44 to 164 keywords" proves you know his actual work. "Sam is great at SEO" proves nothing. If you cannot make a specific, defensible claim about the person, cut the item or swap the name.
- **Tagging follows the list-post rule.** Do NOT tag all N in the body. Tag 3-5 strategically (most influential + most likely to engage + most strategically valuable). The rest get plain-text full names. Let the comments tag the rest. See `recipes/list-post.md` Element 4.
- **The takeaway must contradict something.** VC-vs-bootstrapper. Fancy-video-vs-word-of-mouth. If the takeaway just summarises the list, the post degrades into a listicle. The takeaway is where the point of view lives.
- **Cadence: maximum once a month.** Same saturation risk as any list post. The named-operator version is more memorable, so it saturates slightly faster. Once a quarter is healthier.

### Self-critique before delivering

1. Does the hook state a real, current situation (not a pure hypothetical)?
2. Is every named person someone you can defend a specific claim about?
3. Does every item carry at least one number or concrete proof?
4. Are there 3-5 tags in the body, not N?
5. Does the takeaway contradict a consensus belief, rather than summarise the list?
6. Is the CTA a single soft line at the very bottom, below the value?
7. Between 1,300 and 1,900 characters, and under 2,500 at the absolute most? (Corrected 2026-08-10: the old ceiling here was 3,000, which runs past the reported engagement falloff. See `references/save-mechanics.md`.)
8. Has the carousel version been considered? This format is a sequence of headed units, which is exactly the shape document posts reward at roughly 3x text-only engagement. Default to shipping it as a document with the text post as framing. The style and the Higgsfield object-shot recipe are in `references/carousel-cards.md`; render from a spec with `scripts/carousel.py` rather than forking it.

Any "no" gets flagged with a redraft.

---

## FORMAT 2: The News-Jack Teardown

A story already in the news, run through the creator's own framework. The news supplies the attention, the framework supplies the reason to follow. Without the framework it is commentary and dies with the news cycle; without the news it is a teardown that has to earn its own audience from zero.

This is the highest-leverage format in the library for Pillar 1, because the "Should Be Huge" company series is already a teardown engine. Pointing it at a company that is in the news THIS WEEK is a reach multiplier on work the creator is doing anyway.

### Why it works

- **Borrowed distribution.** The reader already cares about the event. The post does not have to manufacture stakes, only interpret them.
- **The number does the hook.** The corpus openers are real figures with a gap inside them: "agreed to acquire Airtable for $1.285B, last valued at $11B". The gap is the whole hook. State two numbers that should not sit next to each other.
- **Framework over opinion.** Anyone can react. The follow comes from the reader seeing a repeatable lens applied, and wanting the lens for their own situation.
- **It self-funnels.** A distribution diagnostic performed in public on a company the reader knows makes the reader wonder what it would find in them. That is the mechanism an authority-first positioning relies on.

### The skeleton

```
[HOOK] [Two real numbers with a gap between them, or the surprising fact.]

[One line of what everyone is saying about it.]

[The turn: that is not the interesting part.]

Here's what actually happened:

[2 to 4 short blocks. Each one a beat of the mechanism, not a beat of the news.
 Facts must be right and checkable.]

[The framework named, generalised off this company:
 the pattern, why it repeats, who it happens to next.]

[One question to the reader that only makes sense if they run a company.]
```

### The rules that make it land

- **The peg decays with saturation in YOUR audience's feed, not with the clock.** Corrected 2026-08-10: a flat 48-hour window was the original rule here and it is wrong for B2B LinkedIn, where a Friday earnings story posted Monday is on time rather than late. Working curve: full value at 3 days or less, half at 4 to 7, zero after. Consumer news reaching a GTM audience decays slower still.
- **A saturated story can carry an unclaimed angle.** These are two different things and only one of them expires. When everyone covered the headline and nobody covered the mechanism, the post still works past the window, but it is now carrying itself on the analysis, so hold it to the authority-post bar rather than the news-jack one.
- **Facts must be right.** A wrong number in a news-jack gets corrected in the comments in public, and the correction outlives the post.
- **Punch up or sideways, never down.** Admiration plus opportunity, per the Pillar 1 tone rule. Diagnosing a company is not dunking on it.
- **The framework has to be portable.** If the analysis only works for this one company, there is no reason to follow. Name the pattern.
- **No pitch.** The reader connecting the diagnostic to themselves is the conversion. Saying it out loud kills it.

### Self-critique before delivering

1. Is there a real number in line one, and is it verified?
2. Would this post still be worth reading in three months with the news stripped out?
3. Is the framework named and generalised, or does the post stop at commentary?
4. Is the tone admiration plus opportunity, with no punching down?
5. Is every fact checkable by a hostile reader?

---

## FORMAT 3: The Reorder

Not "the consensus is wrong" but "the consensus has the SEQUENCE wrong". A stronger and rarer move than the plain contrarian post, because it concedes that the items are right and attacks the order. That is much harder to dismiss and much easier to argue with, which is the point.

Corpus examples: hiring a B2B marketing team in a different order than everyone uses, the dinner where the guest list matters more than the agenda, top-of-funnel before bottom-of-funnel.

### Why it works

- **It cannot be waved away.** The reader agrees with every item on the list, so the only thing to disagree with is the ordering, which forces engagement rather than a scroll.
- **Productive disagreement.** People save it to reconsider their own sequence and comment to defend theirs. Both are high-value actions.
- **It signals real operating experience.** Anyone can list the parts. Only someone who has run it knows what order actually works.

### The skeleton

```
[HOOK] If I [built X / ran Y] tomorrow, I'd [do it in this order].
       Not the order most people use.

1. [Item]
   [One line: why it comes first, and what breaks if it does not.]

2. [Item]
   ...

[3 to 6 items. Fewer than the playbook format, because the argument is
 the order, not the coverage.]

[The reason the usual order is wrong. This is the actual payload.
 One to three lines.]

[The cost of the wrong order, stated concretely.]

[Question: what order did you run, and what did it cost you?]
```

### The rules that make it land

- **3 to 6 items.** The reader must be able to hold the whole sequence in their head to disagree with it.
- **Every position needs a reason, not just a label.** "Content second" is a claim. "Content second because the first hire has no idea yet what the buyer objects to" is an argument.
- **Name the default order explicitly.** If the reader cannot see what is being reordered, there is no tension.
- **State the cost.** A reorder with no consequence is a preference. A reorder that costs six months of runway is a post.
- **Do not hedge the ordering.** "It depends" is the one ending that guarantees no comments.

### Self-critique before delivering

1. Is the conventional order stated plainly enough that the flip is visible?
2. Does every position carry a because, not just a name?
3. Is the cost of the wrong order concrete?
4. Could a smart practitioner disagree with this? If not, you have written consensus with numbers on it.
5. Has the carousel version been considered? A numbered sequence is document-post shaped, and one slide per position makes the ordering argument visually. This is the format that benefits most, because the cover card can list the positions in order and each depth card defends one. Style in `references/carousel-cards.md`, rendered by `scripts/carousel.py`. See also the format lever in `references/save-mechanics.md`.

---

## FORMAT 4: The Confession Turn

Opens like bad news, turns out to be a milestone or a reframe. The corpus version is a two-word admission ("I give up") that resolves into a growth story. This is the relatability format, and it is the one the creator runs least and should run about once a fortnight.

### Why it works

- **The fold does the work honestly.** "I give up" needs no engineering. It is short, it is a real sentence, and nobody scrolls past it.
- **It outperforms on comments specifically.** Advice invites agreement. An admission invites people to bring their own version, which is a much lower bar to clear than having a take.
- **It buys credibility for the tactical posts.** An account that only publishes playbooks reads as a vendor. The confession is what makes the playbooks trustworthy.

### The skeleton

```
[HOOK] [The admission. Short. Reads as bad news. Must be literally true.]

[1 to 3 lines of the real texture. The specific detail, not the summary.]

[The turn: what it actually was.]

[What changed as a result, in one or two lines.]

[The transferable line. What this means for anyone in the same spot.]

[Open question inviting the reader's own version.]
```

### The rules that make it land

- **The admission must be literally true.** A manufactured confession that resolves into a humblebrag is the single most punished move on the platform, and the comments will say so.
- **The turn cannot be the point of the post.** If the whole post exists to reveal the win, it is a flex wearing a costume. The point is the transferable line.
- **Keep the vulnerability proportionate.** Real friction, not trauma. This is a work account.
- **No CTA beyond the question.** An ask on a confession post is the fastest way to make the confession look instrumental.
- **Cadence: once every two weeks at most.** A confessional account stops being credible for the same reason a purely tactical one does.

### Self-critique before delivering

1. Is the opening line literally true as written?
2. Is there a specific detail, or only a summary of a feeling?
3. Is the transferable line doing more work than the reveal?
4. Is there anything in here that reads as engineered? If the turn feels too neat, it is.

---

## The video-style translation table

Every family in the video hook library (`references/hook-library.md`, the 1,000-hooks distillation) is a content structure, not just a first line. Below, each family is translated into the LinkedIn format it becomes. Use this when the raw material is a video-shaped reaction and you want it as a post, or when you want to vary the format across a weekly calendar so five posts do not all read the same.

Each entry: the LinkedIn format name, the skeleton, and a B2B GTM-flavoured example line to calibrate voice.

**1. Transformation / before-after -> The Arc Post**
Show a state change with a hard before and a hard after, then the mechanism between them. Numbers on both ends.
Skeleton: "[Metric/state] before. [Metric/state] after. Here's the one thing that changed it."
Example: "Our demo-to-close was 9%. Six weeks later it was 24%. We changed exactly one thing in the follow-up sequence."

**2. Exact-how / tutorial promise -> The Teardown**
Promise a specific mechanism and actually deliver it in the body. The reader should be able to run it.
Skeleton: "Here's exactly how we [got result], step by step. Steal it."
Example: "Here's exactly how we booked 40 qualified meetings from a 300-name list. The 4 steps, including the two everyone skips."

**3. Time-credibility -> The Earned-Lesson Post**
Lead with the cost (years, hours, reps) then hand over the compressed lesson.
Skeleton: "It took me [long time / N reps] to learn this. Here it is in 30 seconds."
Example: "I've sat in 200 discovery calls this year. The single question that predicts whether a deal closes takes four words."

**4. Targeted call-out ("if you...") -> The Direct-Address Post** (this is the ICP hook family, already core)
Name the exact role and situation, then say the thing they feel but haven't heard said.
Skeleton: "If you're a [role] at a [company shape] and [specific pain], read this."
Example: "If you're the first growth hire at a Series A AI company, you're being asked to prove pipeline before you have a funnel. Here's how to survive the first 90 days."

**5. Starting-over / hypothetical -> The Starting-Over Playbook** (FORMAT 1 above)
The full named-operator playbook. The flagship translation.

**6. Listicle -> The List Post** (already core, see `recipes/list-post.md`)
N things, N people, or N mistakes. Grouped in fives for max comment surface.
Example: "The 5 GTM mistakes I see every AI startup make in month one. I've made four of them."

**7. Contrarian / myth-bust -> The Unpopular-Opinion Post** (Industry core)
State the consensus, break it, replace it with the sharper model.
Skeleton: "Everyone says [X]. That's backwards. Here's why, and what to do instead."
Example: "Everyone says AI SDR tools are working. Less than 4% book a qualified meeting. The problem isn't the AI, it's what we're asking it to do."

**8. Curiosity gap / cliffhanger -> The Open-Loop Post** (use sparingly)
Start mid-thought, don't resolve the tension in line one, pay it off in the body. Only works when the loop is a real situation, never a manufactured "wait for it".
Skeleton: "[Surprising fragment of a real event]. I didn't expect what happened next to change how we sell."
Example: "A prospect ghosted us for three months, then signed in a day. What flipped wasn't anything we did."

**9. Comparison / this-vs-that -> The Split-Screen Post**
Same input, two outcomes, or right-way vs wrong-way. The contrast carries the point.
Skeleton: "Same [thing]. One got [result], one got [other result]. The difference was [X]."
Example: "Two identical cold emails. One got 2% replies, one got 18%. The only difference was the first seven words."

**10. Story / personal -> The Moment Post** (Personal core)
A real moment with a specific detail, tied to a work insight. The particular carries the universal.
Skeleton: "[Time, place, specific detail]. It made me rethink [work thing]."
Example: "2pm on a Tuesday, I closed the laptop mid-launch and felt guilty. That guilt is exactly the founder trap that kills good distribution."

**11. Authority / earned flex -> The Insider-Observation Post** (Industry core)
Claim the vantage point (title, volume, years), then deliver the thing only that vantage point can see.
Skeleton: "As [role] for [N years / N reps], here's what nobody tells you about [thing]."
Example: "As the person who's read every one of our churned-customer exit notes, here's the reason they actually leave. It's never the one in the survey."

**12. Day-in-the-life / POV -> The Behind-the-Scenes Post** (ICP core)
Walk the reader through what actually happens inside a real process or a real day. The insider view is the value.
Skeleton: "Here's what actually happens inside a [company type] when [event]."
Example: "Here's what actually happens inside a Series B when the board asks why inbound dropped 30%: three Slack channels, two blamed teams, and one dashboard nobody trusts."

**13. Interactive / challenge -> The Diagnostic Post**
Give the reader a fast self-test they run in their own head, then tell them what the answer means.
Skeleton: "Answer these [N] questions. If you said yes to [X], you have a [problem]."
Example: "Three questions. If your answer to the second is 'the SDR team', your pipeline problem is actually a positioning problem. Here's the fix."

**14. Warning / stakes -> The Red-Flag Post**
Name the mistake and the cost of making it. Stakes drive the read.
Skeleton: "If you're [situation], do NOT do [action]. Here's what it costs."
Example: "If you're about to launch, do not spend on a $100k brand video first. I've watched three startups do it and burn the runway that should have bought distribution."

**15. Result / proof reveal -> The Receipts Post**
Show the actual artifact, number, or output. Proof over claim.
Skeleton: "This is what [N of thing] actually looks like. Here's what worked and what didn't."
Example: "This is what 90 days of daily LinkedIn posting actually did to our pipeline. The chart, the misses, and the two posts that drove half of it."

### How to use the table

- **Weekly variety.** When building a 5-post calendar, deliberately pull from different rows so the week reads as five formats, not one format five times. A good default week: one Unpopular-Opinion (7), one Behind-the-Scenes (12), one Teardown (2) or Receipts (15), one Direct-Address (4), one Moment (10) or a monthly Starting-Over Playbook / List Post.
- **Repurposing from video.** If the creator captured a reaction as a video-shaped hook, find its family here and it is already halfway to a post. The video body structure IS the post structure.
- **Format is not the hook.** Every row still needs a first line from `references/hook-library.md`. The format organises the body; the hook opens the door.

### Cross-references

- `references/save-mechanics.md` - why a post gets kept: the save trigger, the length law, line discipline, the CTA policy that overrides the corpus, and the proof bank. FORMAT 2, 3 and 4 came out of that teardown.
- `references/hook-library.md` - the first-line patterns that open each format
- `references/individual-post-mechanics.md` - the named-operator mechanic that powers Format 1
- `recipes/list-post.md` - tagging strategy, curation, and follow-up commenting (applies to Format 1 and Listicle)
- `references/3-i-framework.md` - which formats serve Industry / ICP / Individual
- source of the video families: `references/hook-library.md` (this folder)

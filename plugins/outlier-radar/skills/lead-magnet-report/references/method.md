# The measurement law

Every rule here was learned by shipping the wrong version first. Read it before computing
anything you intend to publish.

## Gathering the data without a vendor

You do not need a tool. The manual protocol, which is what the flagship shape was first
built on:

1. **Write the question set.** 80 to 100 questions a real buyer would type, covering the
   whole funnel. Cover discovery ("who does X"), comparison ("A versus B"), informational
   ("how does X work"), and procurement ("what does X cost"). Tag each one so you can slice
   by type later.
2. **Pre-register the roster.** List every brand in the category BEFORE running anything.
   Registering afterwards lets you unconsciously fit the roster to the results.
3. **Run each question on each engine, logged out, fresh session, same day.** Note the
   country you ran from: answers are per-market, and the same question from another country
   returns a different shortlist.
4. **Record per answer**: which brands were named, in what order, and every URL cited.
5. **Repeat daily** for as long as you can afford. Thirty days is a good issue. A single
   day is a snapshot, not a finding, and should be labelled as one.

Cost is your time and, if you automate it, API calls. Nothing else.

## Rule 1: exclude seeded questions

**A question that names a brand in its own text is excluded from every ranking.**

A named brand is not earning its mention. The effect is not marginal: in one measured
category, the two brands named inside questions scored three to five times higher on those
questions than on the questions that named nobody. Four seeded questions out of ninety-six
were enough to hand second, third and fourth place a freebie each.

Two traps:

- **Most tools flag "branded" against the tracked brand only.** A question naming a
  *competitor* is flagged unbranded and is the single biggest gift on the board. Test
  against every brand in the roster, not just your own.
- **Do not seed-check against the extractor's full vocabulary.** Brand extractors emit
  category nouns ("financial advisor"), public programmes, and junk tokens. Seeding on
  those excluded eighteen legitimate questions in one run for containing the category's
  own name. Build the seed roster from **commercial firms with a real domain**, minus a
  reviewable stoplist.

Keep the seeded questions for a separate head-to-head section if you want them. Never in
the ranking.

## Rule 2: publish coverage and share of voice, never a raw mention rate

Most tools expose `rate = mentions / answers`. That exceeds 100% as soon as a brand is
named twice in one answer, and it is not the share of answers a brand appears in. One
measured head-to-head returned 107.3%.

Publish these instead:

| Metric | Definition | Safe to say |
|---|---|---|
| **Coverage** | questions where the brand appears at all, over total questions | "appears in 51 of 94 questions" |
| **Share of voice** | brand mentions as a percentage of all brand mentions | "holds 7.8% of all mentions" |
| **Mentions per answer** | the raw rate, labelled exactly that | "named 1.2 times per answer" |
| **Average position** | mean rank within the answer | "lands at position 4.0" |

Never write "appears in X% of answers" unless you measured it at the answer level.

## Rule 3: classify winners by segment

"Won by someone outside the industry" is only true if the peer set is honest. Use four
buckets, and write the roster by hand:

1. **The peer set.** Direct competitors on the same model.
2. **Adjacent model.** Chasing the same buyer with a different business model. A large
   platform against a specialist tool, or a bank against an independent advisory firm.
3. **Another profession.** Accountants, law firms, insurers, consultancies, software
   vendors winning a question the category thinks is its own.
4. **Public bodies and trade associations.**

Drawing bucket 1 too narrowly is the failure mode. It once put one large institution
inside the peer set and two of its direct rivals outside it, which turned a real finding
into a false one. Sanity check: would a buyer shortlist these together? Then same bucket.

The finding usually lives in the split, not in the leaderboard: **what share of the settled
questions does the peer set actually win?**

## Rule 4: public bodies are a vacancy signal

Keep regulators, government portals and trade associations off the leaderboard. No brand
can take share from a tax authority, so ranking one against a company is a category error,
and the "average position" of a primary source is an artefact of the topic mix.

They earn a separate, clearly labelled block, and they carry the sharpest reading in the
dataset: **where a public body leads a question, no brand has published an answer the
engines would rather quote.** Count how many of the open questions they lead. That number
is the reader's to-do list.

## The concentration split

Bucket every question by how decided it is:

- **Settled**: top brand at 30% or more
- **Contested**: 15% to 30%
- **Open**: under 15%

Two numbers from this reliably surprise readers, and they can be true at once: most
individual questions have a clear winner, while no brand leads the category. That is the
difference between winning an election and winning the country.

## The publishing gate

If your data source holds client accounts, maintain a **hardcoded allow-list** of
publishable subjects and refuse everything absent from it.

Do not derive it from a lookup. Client records routinely have null links to their
workspace, so a lookup clears real clients for publication. In one audit, two active
clients would have passed. Ask the owner for each addition, and record the ruling with a
date.

## Honesty rules that survive contact with a reader

- **State the caveat that hurts.** If the question set was generated from one brand's own
  positioning, it leans toward questions that brand should win, and its score is a ceiling.
  Say so, and lead with the findings that do not depend on it.
- **Never silently truncate.** "4 of 15 shown" costs one line and buys all your credibility.
- **Round consistently.** Two decimals or none, and the same choice down a column.

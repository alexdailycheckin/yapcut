---
name: lead-magnet-report
description: "Turn one category's measured data into a weekly lead magnet: a branded paginated report that posts natively as a LinkedIn document, an Instagram carousel or a PDF. Creator-agnostic. First use interviews you about the category you sell into, the shape of magnet you want, your data source and your brand, then saves a config to a local workspace. The flagship shape is the INDUSTRY ANSWER REPORT: pick a category, measure which brands AI engines actually name when buyers ask, and publish who wins, who wins nothing, and which pages get cited. Other shapes supported: the benchmark report, the teardown pack, the prompt sheet and the open-questions list. Includes the measurement law (seed exclusion, share of voice, concentration split, segment classification), the locked page design, the comment-gate mechanics, and a self-checking build that refuses to ship an overflowing page. Use when the user says 'make a lead magnet', 'weekly lead magnet', 'gated content', 'build a report', 'industry report', 'category report', 'AI visibility report', 'what should I give away', 'grow my newsletter from LinkedIn', 'document post', or wants a repeatable asset that earns comments and DMs rather than clicks."
---

# Lead Magnet Report

A lead magnet fails for one of two reasons: nobody wants it, or wanting it costs them a
click. This skill fixes both. It builds a **finished piece of measured research about the
reader's own category**, laid out as a paginated 4:5 document that posts natively, so the
value lands in the feed and the only thing behind a gate is the raw sheet.

Creator-agnostic. It assumes no industry, no brand, no colour and no data vendor.

## Why this shape and not an ebook

Numbers worth designing around, all current as of 2026:

- **Gated ebooks convert under 1%.** Audits, benchmarks and category data convert 5 to 15%
  and produce better-qualified leads, because the friction *is* the qualification.
- **One external link in a LinkedIn post cuts median reach by roughly 19%**, and the
  link-in-first-comment workaround is now detected and suppressed. A magnet that lives
  behind a link pays a reach tax before anyone sees it.
- **Comment-gated posts hold engagement and lift comment volume** (median 17 comments
  against 11 for a straight sales post), because a comment is the price of the file.
- **Document posts out-engage text posts** and hold dwell far longer, which is why the
  deliverable here is a document and not an image.

So: the document is complete and free in-feed, and the gate sits on the one artefact that
genuinely needs a file, usually the full data sheet. Never gate the finding itself.

## The workspace

All mutable data lives **outside the skill folder**, so plugin updates never touch it.
Resolution order, matching the rest of the plugin:

1. `--dir <path>` passed to a script
2. `LEAD_MAGNET_HOME`, then `OUTLIER_RADAR_HOME`
3. the current directory, if it holds `brand.json` or `radar-config.json`
4. `~/outlier-radar/`

The workspace holds `brand.json`, `magnet-config.json`, `findings.json` per issue under
`issues/<slug>/`, and rendered output under `reports/`. The skill folder stays read-only.

## First run: discovery (once)

Ask these, in this order, and write `magnet-config.json` when you have them. **Ask, do not
assume.** One question per message where the answer shapes the next.

1. **What category do you want to publish about?** Not their own company: the category
   their buyers shop in. The report is about an industry, and the publisher is a guide to
   it, never its subject.
2. **What kind of lead magnet do you want to make?** Offer the shapes below, recommend the
   answer report, and say they can describe something else entirely.

   | Shape | What it is | Best when |
   |---|---|---|
   | **Answer report** (flagship) | which brands AI engines name for the category's buyer questions, who wins nothing, which pages get cited | you can measure prompts across engines |
   | **Benchmark report** | the category's real numbers on a metric buyers argue about | you hold or can gather comparable data |
   | **Teardown pack** | one company's public strategy pulled apart, with the transferable move | you have judgement but no dataset |
   | **Prompt sheet** | the exact question set plus a scoring sheet the reader runs themselves | the gate payload, works best beside another shape |
   | **Open-questions list** | the questions in the category nobody has answered | strongest as a section, viable alone for a niche audience |

3. **Where does the data come from?** Three honest answers: a tool they already pay for,
   a manual run (`references/method.md` has the protocol, no vendor needed), or they have
   no data yet, in which case steer to the teardown pack until they do.
4. **Brand.** Publisher name, org, the one footer line, one accent hex, light or dark, and
   optionally a square avatar and a cover image. Fonts: see the rule below.
5. **The gate.** What the reader comments to get, and what you send. Default: the full data
   sheet by DM.
6. **Cadence and the queue.** Weekly is the default. Ask which categories are queued so
   issue 02 is decided before issue 01 ships.

Then build the example so they see the object before committing:
`python3 build_report.py --dir <workspace> --findings example-findings.json --pdf`

**Do not end onboarding on a config.** End it with a rendered PDF the user has opened.

## Fonts: use your own, and only your own

`brand.json` sets `font_display` and `font_mono`, and the defaults are two neutral Google
Fonts chosen to pair without being anyone's brand: **Newsreader** for display and
**JetBrains Mono** for data. Both are free and redistributable.

**Keep the two roles.** One high-contrast display serif carries every headline and figure;
one mono carries every number, label and eyebrow. That split is what gives the pages their
register, and swapping the mono for a sans collapses it.

If a user has their own licensed brand faces installed, they should set them here and the
document will use them locally. **Never bundle a licensed font file with a report you
distribute, and never inline one into a shared HTML page.** Set the family name and let it
resolve, or pick a Google Font.

## The measurement law

Read `references/method.md` before computing anything. The four rules that matter most,
because each one was learned by getting it wrong first:

1. **Exclude seeded questions.** Any question naming a brand in its own text is excluded
   from every ranking. A named brand is not earning its mention, it is being handed one,
   and the distortion is large: in one measured category the two brands named in questions
   scored three to five times higher on those than on questions naming nobody.
2. **Never publish a mention rate as a share of answers.** Most tools compute mentions
   divided by answers, which exceeds 100% the moment a brand is named twice in one answer.
   Publish **coverage** as "appears in N of M questions" and **share of voice** as a
   percentage of all mentions. Label anything else exactly what it is.
3. **Classify winners by segment, not by in-or-out.** "Someone outside the industry won"
   is only meaningful if the peer set is drawn honestly. Classify every winner into the
   peer set, the adjacent-model competitor, another profession, and public bodies. Getting
   this wrong once turned a real finding into a false one.
4. **Regulators and trade bodies are not competitors.** Keep them off the leaderboard.
   They earn their place as a **vacancy signal**: where a public body leads a question, no
   brand has published an answer the engines prefer.

## Publishing gate: whose data may you publish

If the data comes from a tool holding **client** workspaces, the publishable set must be an
explicit allow-list you maintain by hand.

**Do not derive it from a database lookup.** Client records routinely have missing links,
so a lookup will clear a client for publication. Keep a hardcoded list, refuse anything
absent from it, and ask the owner for each addition. `references/method.md` carries the
pattern.

## Build

```
python3 build_report.py --dir <workspace> --findings issues/<slug>/findings.json --pdf
```

Writes `reports/report.html` (paginated, keyboard and click navigation) and `report.pdf`
at 8 x 10 inches, one page per sheet. Every page is conditional on the findings file, so a
file with no engine split simply has no engine page rather than a page of blanks.

The builder prints `no overflow` or the list of overflowing pages. **A page missing its
byline overflowed.** That check exists because measuring page heights in a browser is
unreliable here: a paginated container query can report a zero-height page and hand you
confident nonsense.

## Design law

`references/design-system.md` is the full spec. The rules you cannot break:

- **4:5 pages.** The tallest ratio the feeds render uncropped.
- **Ranked lists are ranked.** A data list out of rank order reads as an error. The builder
  sorts descending by default; pass `rank: false` only for a genuine sequence.
- **One denominator per list, or say so.** If a list mixes measures, name both in the
  caption or the reader will read them as one scale.
- **Long text pages take a character budget, never a fixed row count.** Question text is
  data and the next category's is longer. Say "N of M shown" so nothing is silently cut.
- **Never leave the bottom third empty.** A page of top-anchored content with dead space
  below reads unfinished. Fill it with data you already hold, or make it a big-number page.
- **The cover is the only page without the inner panel**, and its title must sit clear of
  the subject, not on top of it.

## Image law, if you use a cover

Whatever visual device you own, the rule that transfers: **the image has to make the
argument, not decorate it.** Pick the object from what the data actually says.

And on generated type: current image models set beautiful display type and **cannot spell
reliably.** Measured across four renders of one title: a dropped word from a thirteen-word
headline, a duplicated line, an unrequested underline, and a stray digit inside a
three-word subline. **Set type as an HTML overlay, always.** Let the model supply the
photograph only.

## Distribution

`references/distribution.md` has the full mechanics. In short: post the document natively,
put no link in the post or the first comment, gate the sheet on a comment, deliver by hand
rather than by automation at real volumes, and run one gated post per week at most, because
a feed of gates stops being rewarded.

## Handoff

Pairs with `outlier-radar`, which finds the week's ideas, and with `tiktok-yap-editor`,
which cuts video. This skill owns the written, gated, measured asset.

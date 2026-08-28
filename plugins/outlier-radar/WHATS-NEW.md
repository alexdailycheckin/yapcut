# What is new in Outlier Radar

## 3.3.0: the Lead Magnet Report

**New skill: `lead-magnet-report`.** If LinkedIn is part of your strategy, this is the one
to try next.

It turns one category's measured data into a weekly lead magnet: a branded paginated report
that posts natively as a LinkedIn document, an Instagram carousel or a PDF. The document is
complete and free in the feed, and the only thing behind a gate is the raw data sheet, which
is what keeps it out of the reach penalty that links and link-in-comments now carry.

**Why you might want it.** Gated ebooks convert under 1%. Category data, audits and
benchmarks convert 5 to 15% and qualify better, because the friction is the qualification.
A comment gate also lifts comment volume, which is the signal the feed rewards.

**What it gives you:**

- A first-run interview that asks what category you want to publish about, what shape of
  magnet you want, where the data comes from, and your brand. Five shapes are supported and
  you can describe your own.
- The measurement law, so the numbers survive a sceptical reader: seed exclusion, coverage
  and share of voice instead of raw mention rates, segment classification, and the rule that
  regulators are a vacancy signal rather than a competitor.
- A self-checking build. It prints the pages that overflowed instead of letting you ship a
  cut-off caption.
- A locked page design where only your accent colour and your cover image change between
  issues, so a run of issues reads as a series.

**Fonts are yours.** The defaults are two neutral Google Fonts that pair well, Newsreader
and JetBrains Mono. If you have licensed brand faces installed, set them in `brand.json`
and the document uses them locally. Nothing licensed is ever bundled into a report you
distribute.

**Try it:**

```
python3 build_report.py --dir <your workspace> --findings example-findings.json --pdf
```

That renders the bundled example so you can see the object before you gather any data.

Everything you own still lives in your workspace. This update adds a skill and touches
nothing in `weeks/`, `performance/` or your config.

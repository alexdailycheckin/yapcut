# What's new

## 3.5.0: the audit release

An audit of the repo and its live install on 2026-09-09 found the engine optimising the one
stage that was never the constraint: 157 scripts written, 22 posted, every video row a
placeholder, the feedback loop run once. 3.5.0 changes what it optimises for.

- **Audience first.** Discovery asks who should recognise you and for what before it asks
  about your niche, and runs a proof-extraction interview (what you have done that a
  competitor cannot claim, the plays you run, the lines you would never say) instead of
  collecting adjectives about your voice.
- **Filming slots, not a script bar.** `quantity` in your config replaces "about 10 per lane".
  Unfilmed scripts teach the loop nothing.
- **A gate that gates.** `radar_gate.py` runs every check in one command with one exit
  contract and stamps the week. The schema is versioned (`references/week-schema.md`).
- **The loop closes on disk.** Filmed and posted state, a people ledger (who answered),
  learned weights the selector reads, one pre-registered question a week, watch-through on
  video rows, and a dashboard that seeds from all of it.
- **Distribution shipped.** The daily block with ammo and held receipts, day-0, callback and
  promise, the tag guardrails: `references/distribution.md`, with an Ammo tab on the dashboard.
- **Your rulings ride on top.** `<workspace>/law.md` and `<workspace>/references/<name>.md`
  overlay the shipped playbook instead of forking it.

Everything you own still lives in your workspace. Existing week files keep working (legacy
keys warn, never fail).

## 3.4.0: the Voice Stack

Scripts are now grounded in recordings of YOU talking, not in adjectives describing how you
talk. This is the fix for the most persistent complaint this skill has ever had: "it still
sounds like AI wrote it."

**What broke, so the fix makes sense.** A 64-agent rewrite of one week's episodes, at
serious cost, failed to change the creator's verdict. Every writer had been handed
adjectives about the voice while thousands of words of that creator actually talking sat
unused on disk. A model given a description of a voice imitates the description, which is
the generic confident-operator register everyone recognises and nobody wants.

Worse, the cadence gate was causing the problem it was meant to catch. It required a
sentence mean of 9 to 13 words. The creator's unscripted on-subject speech measured 17.8.
For weeks the machine demanded sentences roughly half his natural length and every batch was
written to satisfy it. The number came from a corpus that was 76% casual off-topic chat,
where he genuinely did run short. Two other things hid it: a `Path.resolve()` in a symlinked
script meant the corpus-derivation mode had never once run, and the old rule "at least one
sentence over 25 words" was satisfied by a 26-word sentence, so homogenised output passed.

**New:**
- `derive_voice_targets.py` measures your speech and writes `voice-corpus/targets.json`: a
  full percentile profile, not a few floors. Summary stats can be satisfied a hundred ways.
- `segment_corpus.py` splits your corpus by register and mode. On-subject speech, casual
  speech, and anything you TYPED are three different voices and pooling them is what went
  wrong. Typed material is excluded from a speech profile automatically.
- `voice_brief.py` emits the writing brief: measured targets plus VERBATIM passages of you
  talking. The playbook now requires running it before any script is written, so grounding
  is mechanical and a scheduled run gets it for free.
- `voice-corpus/rejections.json` (start from `rejections.example.json`) is a ledger of lines
  you have killed. `spoken_lint.py` fails on recurrence. Model weights do not change between
  sessions, so this is the only thing that accumulates your taste.
- `spoken_lint.py` adds `rejected_phrase`, `no_speech_markers`, `tail_flat` and
  `batch_no_runaway`. The last one fails a whole batch with no long sentence anywhere, because
  the runaway sentence is usually the most distinctive thing about how someone talks.
- `check_fidelity.py` reads the measured profile instead of constants, and prints a loud
  banner when there is no profile so you never write a batch against unvalidated defaults
  believing they are grounded.

**Fixed:** `spoken_lint.py --dir` crashed with an argparse error, despite `--dir` being
resolution option 1 in the documented order. `--corpus` never worked at all from a symlinked
install.

**What this asks of you, once.** 20 to 30 minutes of you talking through 4 or 5 subjects in
your niche, unscripted, into a phone. Not read, not rehearsed. Transcripts go in `capture/`
with a `mode:` line. Everything above is capped by that supply, and no amount of compute
substitutes for it. Never feed teleprompter reads of AI-written scripts back in: an audit
found 71 of 71 records were exactly that, so the voice being measured was the AI's own.

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

# What's new

The first session after an update shows the entries you have not seen yet, once, and checks
what your workspace still needs for them (`hooks/whats_new.py`, run by the plugin's
session-start hook). Newest first. Each entry says what changed and what you have to do to get it.

## 3.20.0: the dashboard opens on your scripts

**What's new.** The dashboard has three tabs instead of ten. Film is where it opens: pick a
lane, see how many scripts are left in it, and the scripts are right there. Post shows what is
filmed but not posted yet, your week's calendar, your LinkedIn posts and comment ammo. Results
shows what you filmed and posted each week, and how your posts did. Export lives in one place,
top right. Everything you marked before is still marked.

**To get it.** Rebuild the dashboard (`python3 build_dashboard.py --open`). To change the colour,
set `dashboard.accent` in `radar-config.json`; it uses your brand accent otherwise. Add a photo
as `avatar.png` in your workspace to see it beside the welcome line.

## 3.19.0: a Five days tab

**What's new.** The week can carry five short posts on top of the episodes, one per weekday, each
in its own format: Spicy, Deep Dive, Quick Win, Proof and Fun. They have their own tab on the
dashboard and their own section in the filming pack. A script that ends with an ask ("comment
GUIDE and I'll send it to you") shows it, so you don't forget to say it. On your phone the five
days sit at the end of the viral videos for now.

**To get it.** Set `quantity.days` to 5 in `radar-config.json` if you want the weekly run to write
them. Nothing else to do.

## 3.18.2: every episode starts with the story in one line

**What's new.** Each episode now carries the story in one line: what happened, then what happened,
then why it matters. Your filming pack prints it above the script. The dashboard shows it on the
episode card and at the top of the filming view, so you read the point before the words.

**To get it.** Nothing to do. The next weekly run writes the line first, then the script from it.

## 3.18.1: lines you killed stay out of your LinkedIn posts

**What's new.** A line you've killed (anything in `voice-corpus/rejections.json`) now fails in
the LinkedIn post that rides on an episode, not only in the script. Before this the post was
checked for shape but never against your kills, so a killed line could still go out under your
name.

**To get it.** Nothing to do. The next gate run checks your twins.

## 3.18.0: explainers and moments on your phone

**What's new.** This one is for the Anima app on your iPhone.

- **Explainers have their own section.** Each one shows your step-by-step guide above the
  script, so you learn the thing before you film it.
- **Moments are a checklist.** A day in the life or a Pomodoro break shows the clips to capture
  with their times. Tick each one off as you film it; the ticks stay put.
- **Your take is its own card.** The opinion slot sits after the script's last line as a
  separate card with its ideas, instead of trailing the script as more lines to read.

**To get it.** Update Anima on your iPhone. An older Anima keeps working and shows one card at
the top of the week saying what it can't show until you update. Nothing to change on the Mac.

## 3.17.1: fresh news only, and a first line that hooks

**What's new.**

- **Old news fails.** Every episode carries `news_date`, the day the thing actually happened, and
  the gate fails one older than `show.max_news_age_days` (14 by default). A new interview about an
  old raise is still the old raise.
- **The first line is the contradiction.** Move 1 used to be "the receipt, spoken flat", which
  produced first lines like "X reported on September 29th that...". Now the voice opens on the
  one true fact that sounds wrong, and the receipt card carries the date and the source.

**To get it.** Set `show.max_news_age_days` in `radar-config.json` if you want it tighter (7 is a
good number for a weekly news show). Your next weekly run writes `news_date` on every episode.

## 3.17.0: report first, then your take; explainers and moments

**What's new.**

- **Your opinion has its own slot.** Episodes now end on the reported story, and then on a
  labelled slot for your own take, said off the cuff: `[YOUR NAME'S OPINION, IF ANY]` with two or
  three ideas under it. The ideas are prompts, never lines to read, and you can skip the slot.
  It shows in the filming pack, the dashboard and the phone prompter, and it never counts
  toward the word limit.
- **Explainers.** A slower piece on a new feature or release, explained for someone who has
  never done the job, with your own step-by-step guide underneath so you learn it before you
  film it.
- **Moments.** Day-in-the-life and break clips: a capture list of short moments to film, cut
  later with the clock time on screen.
- **A wider sweep.** List the beats you cover in `radar-config.json` `sweep.beats` and the
  weekly run searches each one, not only the loudest funding news.

**To get it.** Set `quantity.explainers` and `quantity.moments` in `radar-config.json` (try 1
and 3), and `sweep.beats` if you want the wider sweep. The next weekly run writes them. Update
the editor to 3.6.0 too, so it keeps your take whole when it cuts.

## 3.16.0: everything since 3.5, and you hear about updates now

**What's new.** Ten releases went out without a note here. The ones you will notice:

- **Your yeses teach it.** The weekly brief now opens with the last three scripts you filmed,
  posted or approved, so it learns what you want and not only what you killed. The checks on
  the writing are fewer; the ones that stay guard the facts, the sources and the length. (3.11)
- **Every episode states what you believe before the proof.** Five moves: the receipt at frame
  one, your belief, the break, how it works, the verdict. Stated after the facts, a belief reads
  as a summary; stated before, the same facts land as an argument. (3.9)
- **Scripts are written as you talking alone to camera**, not as you on a call, because the two
  sound measurably different. (3.10)
- **One file to film from.** The filming pack is generated from the week: the full read, the
  shots, the sources and the LinkedIn text. (3.11)
- **Carousels draw charts and tables**, have a second look, and LinkedIn text keeps its bold
  and line breaks. (3.7, 3.8)
- **The dashboard** takes a post you made outside the weekly run, and links the files each post
  ships with. (3.8)
- **Your phone.** If you use the Anima app on your iPhone, "connect anima" puts the week's
  scripts on it, over the Wi-Fi or from anywhere with a sync code. (3.13 to 3.15)
- **Receipts sit in the band above your head**, under the platform's top bar; only the one on
  screen during the hook goes under the captions. (3.15.1)
- From now on the first session after an update tells you what changed, once.

**To get it.**
1. Run your week as usual. Your workspace, your weeks and your rulings are untouched.
2. Tell Claude "I filmed <the script>" after you film one. That is what the brief learns from.
3. Record about twenty minutes of yourself talking to a camera about your own subject, and ask
   Claude to add it to your voice corpus as a work monologue. It is the biggest single fix for
   scripts that sound like somebody else wrote them.
4. Optional: if you use Anima on your iPhone, say "connect anima".

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

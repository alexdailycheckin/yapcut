# Script anatomy + QA gate

Every script (both lanes: the primary "Industry" lane and the secondary "Viral videos" lane) is written in labelled parts so it is obvious
on the dashboard what to WRITE on the video, what to SHOW, what to SAY, what to
READ, and what to DO. No more mashing spoken words and stage directions together.
Grounded in the Hook-Body-CTA standard for short-form (hook = on-screen text +
spoken line + visual interrupt; body delivers value + payoff; one clear CTA;
30-45s) and the tiktok-engine rule (start from a real reaction, ~6-word
on-screen hook for mute viewers, no consultant-speak, no em/en dashes).

## The seven parts (these are the JSON fields)

1. **text_hook** - the ~6-word overlay burned on the video for mute scrollers. A hook family from `hook-library.md` (in this references folder), in your voice, and it must fire at least one of the six psychological hook styles in `hook-psychology.md` (Crystal Ball, Insider, Lab Rat, Expert, Mirror, Sledgehammer).
2. **visual_hook** - what you physically show or do in the first 1-2 seconds (a prop, a screen, an action, a pattern interrupt). If it is pure talking head, say so ("straight to camera, high energy").
3. **spoken_hook** - the opening 1-2 lines said out loud (it is usually two short lines, and reading it in two breaths is fine). It is NOT a separate thing to record: on the dashboard the whole read is laid out like a movie script in three labelled sections, **HOOK** (this field, rendered BOLD) then **SCRIPT** then **CTA (optional)**, each one sentence per line. Write the hook to flow straight into the script and never repeat it at the top of `script`. It is for the ear; the `text_hook` (for the eye) can and often should differ.
4. **script** - the VERBATIM words to read out loud: the body that follows the hook section. Must follow tension -> value beats -> payoff. Written to be SPOKEN (contractions, short sentences, rhythm), not read like an essay. Do NOT restate the spoken_hook here; start from the next beat. The dashboard renders it as the **SCRIPT** section, one sentence per line, teleprompter style.
5. **directions** - stage directions: b-roll, cuts, on-screen text cues, props, where to punch in. Clearly NOT spoken. Shown in a separate styled box on the dashboard.
6. **value** - one sentence stating the PAYOFF and its TYPE. Value is not always educational. Prefix with the type so it's explicit on the dashboard:
   - **Educational** - viewer learns or can do something (drives saves, authority)
   - **Insight/reframe** - a new way to see something (the contrarian takes in your niche)
   - **Relatable** - "someone finally said it", feel seen (drives shares, comments)
   - **Entertainment/skit** - a laugh, a bit, a character (drives watch-through, shares)
   - **Shock/novelty/curiosity** - a surprise or "wait, what" (stops the scroll)
   The QA test is NOT "is it educational." It is "does it deliver a clear payoff of SOME type." A skit whose value is "this is just funny and shareable" passes. The failure mode is a script that delivers NOTHING: no laugh, no insight, no feeling, no payoff. That is the only thing that fails on value.

### Value mix (don't make everything educational)
Across a weekly batch, aim for a blend, not all teaching. Rough target:
- **Primary "Industry" lane (10):** ~4 educational/insight, ~3 relatable, ~2 entertainment/skit, ~1 shock/novelty. Authority-leaning, but at least half carries emotion or entertainment so it travels. Never 10 lectures.
- **Secondary "Viral videos" lane (10):** mostly relatable/entertainment-skit (~7), ~2 shock/curiosity, ~1 insight/reframe. This lane wins on "someone finally said it" recognition and the laugh, not lessons. Each one borrows a real viral creator's mechanic.
Pure-educational content gets saved but rarely shared; entertainment and relatability drive the reach. Stack both across the week.
7. **cta** - the ending: one clear action (follow for X / comment a word / save this / "which one are you"). Soft engagement bait + a reason to follow. Shown on the dashboard as the final **CTA (optional)** section of the read; write one when the script wants a spoken close, but it can be dropped for a hard-stop button ending.

Secondary "Viral videos" lane scripts use the same fields as the primary lane: `borrows` names the real viral video's mechanic, `carries` is the angle you pour into it, `sources` holds the real source URL. `value` for this lane = the payoff the viewer gets (a laugh, a "someone finally said it" recognition, a sharp observation), plus the reason to engage.

## Storytelling craft principles (apply across EVERY hook family and format)
The transferable laws behind why outliers travel, distilled from the mechanic
library and crystallised by the @solidheaston teardown. They are NOT
day-in-life-specific: apply them to any storytelling script, talking-head or VO,
in any hook family from `hook-library.md`. When writing a
storytelling slot, run the idea through all six and rewrite the hook until it
passes #1.

1. **The hook is a true TENSION, never a topic or a title.** "Day in the life of a
   founder" or "a thread about my niche" are topics, and topics carry no
   pull. Find the contradiction, taboo, stakes, envy, or surprise inside the topic
   and lead with THAT. Every family gets sharper rephrased as a tension: contrarian
   = "everyone's wrong about X", listicle = "the 3 things that nearly killed us",
   day-in-life = an enviable or judgment-bait state, authority = "I do X and I've
   never done the thing everyone says is mandatory". If the hook could be a
   Wikipedia section heading, it is dead.
2. **Specificity is the retention engine.** One precise concrete detail (a real
   number, name, time, dollar amount) beats any general claim and reads as true.
   Vague = scroll. Specifics buy the next 6 seconds, every beat.
3. **Stack open loops; don't tell one long story.** Anything over ~20s should be a
   chain of small self-contained cliffhangers, each opening the next, not one arc
   with a single payoff at the end. This is what holds watch-time and makes it loop.
4. **Engineer the debate.** Reach comes from comments, and comments come from a line
   people NEED to argue with or correct. Plant at least one defensible, polarising
   beat (see the engineered-tension and deliberate-flaw mechanics).
5. **Ambivalence drives shares.** When a viewer both judges and admires, or loves
   and is unsettled, they DM it to a friend to resolve the feeling. Pure agreement
   gets a like; tension gets a share.
6. **Serialise what works.** "Part N", "my last video", a recurring format or
   persona compounds: each episode recruits viewers for the next. Turn a winning
   one-off into a named series.

The @solidheaston day-in-life below is one fully-worked application of all six; the
same six should shape talking-head yaps, case studies, episodic series, and
secondary "Viral videos" lane scripts too.

## Day-in-the-life VO format (storytelling slot -> tiktok-yap-editor Mode B)
A storytelling script can be written as a **day-in-the-life voiceover** that feeds
the editor's VO-to-picture mode (Mode B): you film loose b-roll of your day, the
voiceover is recorded later to a guide, and the picture is cut to the script. Use
this when the idea is better SHOWN than said to camera (a walk-and-talk insight, a
"here's my actual day doing this", a behind-the-scenes of a real move).

Set `format: "day-in-life-vo"` on the item and keep ALL the normal fields (so the
dashboard still renders it), then add a `beats[]` array that is the real handoff:
- `text_hook`, `visual_hook`, `spoken_hook`, `value`, `cta`: as normal.
- `script`: the full voiceover read end to end (all beat lines in order) so it
  reads naturally and the dashboard shows the whole VO.
- `directions`: the shot list (what b-roll to film for each beat).
- `beats[]`: ordered, each `{role, text, b_roll, target_dur}`:
  - `role`: hook | context | beat | turn | button
  - `text`: the exact VO line for that beat (one short spoken sentence)
  - `b_roll`: what to film/show for it (a real clip from your day)
  - `target_dur`: seconds the clip plays (hook 1.5-2.5s, later beats 3-4s)
Pacing rule: total ~60-90s, hook in the first ~2s, fast cuts up front then let it
breathe. The editor turns `beats[]` into `beats.json` for `brollcut.py`, burns the
record-to-picture guide, then finishes with `storyfull.sh`. Talking-head
storytelling scripts (no `format` field) still route to Mode A as before.

### Taboo day-in-the-life (the @solidheaston engine)
Harvested from @solidheaston "unemployed living in my car" (284k likes, 9.6k
saves, 2.5k shares, 3.3k comments). The most repeatable storytelling shape we have
found, and the default for the `day-in-life-vo` slot when we want reach, not warmth.
Why it travels, and the rules that port to any niche:

- **The hook is an identity CONTRADICTION or taboo, NEVER a job title.**
  "Unemployed living in my car" stops the scroll because it fires judgment and
  curiosity at once. "Day in the life of a founder / marketer / operator" dies: a role carries no
  tension. Build the hook on a true tension about you (a cushy life, no office,
  no boss, paid to be online all day), then let the day pay it off. Pull the wording
  from the curiosity-gap + day-in-life/confession families in `hook-library.md`
  (families 8 and 12, fused).
- **Hyper-specific deadpan narration is the retention engine.** Flat first-person
  VO, one precise mundane detail per beat ("my weight's been stuck at 197 for three
  days"). Specificity reads as true and buys the next 6 seconds. No hype, no music
  swell.
- **It is a stack of ~30 four-second micro-loops, not one story.** Each beat is a
  tiny self-contained cliffhanger. That is the only reason a 3-minute day-in-life
  holds and loops. Write `beats[]` as many short beats, not five long ones.
- **The lifestyle starts the comment war.** A judgment-bait life generates argument
  ("why don't you have a gofundme", "where's your family"); the creator replies and
  stokes it. Polarisation = comments = reach. Engineer one or two beats people will
  argue with.
- **Judge/admire paradox = shares.** Looks like rock bottom, behaves with extreme
  discipline. Viewers look down AND respect, so they DM it to a friend. Your
  version can invert it: looks like doing nothing all day, actually running real work.
- **Franchise it.** "my last video", numbered days. Built-in return viewership.

Format = `day-in-life-vo`, route to tiktok-yap-editor Mode B. The candidate
"day in the life of WHAT" hook frames you are testing live in `weeks/<date>.json`.

## The body must actually deliver (the fix for "saying random shit")
A premise is not a video. After the hook, the body has to:
- pay off the hook's promise immediately (no throat-clearing),
- give ONE specific, usable idea (a number, a step, a reframe they can apply),
- land a payoff line that closes the loop the hook opened.
"Interesting observation, then silence" is the failure mode. Always answer: so what do I DO with this?

## QA checklist (gate BEFORE it goes to the dashboard)
A script is `qa: "passed"` only if every box is true. Otherwise it is `qa: "pre-qa"` and shows as a draft.
- [ ] Hook works in under 2 seconds and opens a curiosity loop
- [ ] Hook fires at least one of the six psychological styles in `hook-psychology.md` (fires none = it's a topic, rewrite)
- [ ] text_hook is <= ~6 words and readable on mute
- [ ] spoken_hook is a real human reaction, not manufactured consultant-speak
- [ ] Body delivers a clear PAYOFF of some type (educational, insight, relatable, entertainment, or shock) - the `value` line is fillable, NOT necessarily educational
- [ ] If it is an educational/insight video: at least one concrete proof (a number, a name, a step). If it is entertainment/relatable/shock: the bit actually lands
- [ ] Clear payoff that closes the loop the hook opened
- [ ] A single CTA at the end, OR a deliberate hard-stop button ending (CTA is optional, never two CTAs)
- [ ] `script` is verbatim speech only; all "do this" lives in `directions`
- [ ] Reads naturally out loud in 30-45 seconds
- [ ] On-brand: your niche lens (or the relatable secondary "Viral videos" lane), premise-first, no em/en dashes

## QA gate in the routine
Generate -> self-run the checklist on each script -> only the ones that pass get `qa:"passed"`. Write everything to the week JSON, then rebuild the dashboard. The dashboard badges each card "QA passed" or "Pre-QA draft" so you never film an unchecked one by accident. If a script cannot pass (usually missing value, or a weak/absent payoff), fix it or mark it pre-qa with a one-line note on what it needs. A missing CTA is fine when the script lands on a strong hard-stop button; only fail it for having no ending at all.

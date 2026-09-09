# Distribution mechanics

The report is the asset. This is how it earns anything.

## Post it natively, as a document

Upload the PDF as a document post. Do not post an image of page one with a link to the
rest. Document posts out-engage text posts and hold dwell time, and the whole point of a
paginated 4:5 report is that the feed renders it.

## Pay no reach tax

- **No external link in the post body.** One link costs roughly 19% of median reach, and
  some trackers put it far higher.
- **No link in the first comment either.** That workaround is detected now and the
  link-carrying comment gets suppressed heavily.
- The post must stand alone. If the reader gets nothing without clicking, the algorithm
  has already decided against you.

## Gate the sheet, not the finding

The document is complete and free. The gate sits on the artefact that genuinely needs a
file: the full data sheet, the question set, the scoring template.

The ask is a comment, and the delivery is a DM. Comment-gated posts hold engagement and
lift comment volume, because a comment is the price of the file and people pay it.

Two rules:

- **Deliver by hand at real volumes.** Comment-to-DM automation breaches most platforms'
  terms unless it runs on official endpoints, and at 20 to 80 comments a manual pass is
  under an hour and the DM becomes a real conversation, which is the actual point.
- **Fulfil the same day.** A promised file that arrives late destroys the credibility the
  report just built.

## One gate a week, maximum

Running gated posts constantly turns the feed into a vending machine and the algorithm
stops rewarding it. One gated post per week, in the slot that already carries your
teaching content. Never on a post aimed at strangers, where the audience is deciding in
one post whether you are a person or a funnel.

## Let the comments choose the queue

The strongest version of the gate is not a download, it is **"comment the category you sell
into"**. Each request becomes a future issue, so the audience sets the editorial calendar
and the lead magnet and the production line become the same act.

Requests land two to three weeks out, because measurement takes run time. That is a
feature: it creates a visible queue instead of instant gratification.

## The request ledger and the DM (added 2026-09-09)

A commenter is a self-identified buyer with a named category, and "fulfil the same day" is
unenforceable without a ledger. Every request goes into `issues/<slug>/requests.jsonl` and
every commenter into the workspace's people ledger:

    python3 requests.py add --issue <slug> --commenter "<name>" --url <profile> --category "<what they asked for>"
    python3 requests.py dm-sent --issue <slug> --commenter "<name>"
    python3 requests.py --due          # requests older than 24 hours with no DM sent

The DM, three lines, by hand, never automated:

> Here is the sheet you asked for: [link or attachment].
> The one line I would look at first for [their category]: [one finding from the report].
> If you want the version for your own category, say which one and it goes in the queue.

The queue is the requests file read in order; the sector plan below only breaks ties.

## Sequence the queue by sector, not by shouting

If the series serves a commercial goal, order the issues to match which sector you are
selling into that month, and alternate so it does not read as one long run about one
industry.

## What to measure

- **Comments**, because that is the gate converting.
- **DMs sent and replies received.** Replies are the real number.
- **Saves**, which is the signal that the document was worth keeping.
- **Follower delta from the ICP**, not total followers.

Do not measure impressions. The report exists to convert the audience you have, not to
find a new one.

## Honest expectations

At a few thousand engaged followers, expect tens of qualified DMs per issue, not hundreds
of leads. The compounding asset is the archive: after several issues you hold a
cross-category dataset nobody else has, and that is the piece with real leverage.

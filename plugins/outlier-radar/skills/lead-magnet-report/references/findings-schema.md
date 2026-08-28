# findings.json: the input contract

`build_report.py` reads one JSON file and composes pages from whatever it holds. **Every
block is optional except `meta`.** Omit a block and its page does not exist, which is what
lets one builder serve any category and any magnet shape.

Inline HTML is allowed in the fields marked **rich** below, so you can wrap a phrase in
`<span class="em">` for the accent italic or `<b>` for emphasis. Everything else is escaped.

```
meta                      REQUIRED
  issue                   "01"
  doc_title               browser tab and gallery name. A short noun phrase, not a sentence
  title_before            cover title, the part before the accented claim
  title_claim             the accented claim, set in italic accent. Keep it under 4 words
  title_after             the part after
  questions               int, optional. Shown in the cover strip
  answers, citations, cited_domains   int, optional

headline.anchor           the big-number page
  label, value, unit
  body                    RICH
  caption

segments                  who wins, as a split
  eyebrow
  headline                RICH
  rows[]                  {name, value}
  extra_label             optional heading for top_outside
  caption

top_outside[]             optional. {name, value} rendered under segments

concentration             the proportional band
  eyebrow
  headline                RICH
  segments[]              {name, short, value}   short is the label inside the band
  ends[]                  optional. {label, body RICH} rendered as two panels
  caption

tables[]                  any number of ranked lists
  eyebrow
  headline                RICH
  anchor                  optional {value, body RICH} big figure beside a lede
  columns[]               optional column headings
  rank                    default true. false preserves your order
  rows[]                  [label, numeric, display]  three items
                          [label, numeric, display, secondary]  four items, two metrics
  caption                 RICH

question_list             the long-text page
  eyebrow
  headline                RICH
  items[]                 {text, meta RICH}
  char_budget             default 480. Total question characters before it stops adding
  max_rows                default 6
  caption

quad                      four panels
  eyebrow
  headline                RICH
  cells[]                 {label, value, primary, note, secondary RICH}
  caption

gate                      the only page that asks for something
  eyebrow, headline RICH, body RICH
  next                    optional. The next issue's subject
  method                  the method note, RICH
```

## brand.json

```
series_name     the franchise name, shown on the cover
byline_name     publisher
byline_org      optional
footer          the one line bottom right. A domain, usually
accent          one hex. The whole palette is derived from it
mode            "dark" or "light"
font_display    a display serif. Default Newsreader
font_mono       a mono. Default JetBrains Mono
avatar          optional path, relative to the workspace
cover_image     optional path, relative to the workspace
```

Give one accent hex and the palette is arithmetic from it, so a rotated colour is the same
document in a different key rather than a redesign. Hand-picked neutrals drift apart across
a series; derived ones cannot.

## char_budget, and why it is not a row count

Question text is data. The next category's questions will be longer or shorter than this
one's. A fixed row count overflows on the long ones and leaves half a page empty on the
short ones. Measured on one issue: five rows of about 120 characters pushed the caption and
byline off the page; 330 characters was too tight and left it half empty at two rows; 480
fits four rows of that length and lets a shorter-question category show six.

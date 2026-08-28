# The page design system

The treatment is fixed so a series reads as a series. Two things change between issues:
**the accent colour and the cover image.** Everything else is template.

## The page

- **4:5**, the tallest ratio the major feeds render without cropping. Print is 8 x 10 inches,
  one page per sheet.
- An **outer frame** in the darkest ground, an **inner panel** one step lighter, a hairline
  border between them. That single step of depth is what stops the pages reading as slides.
- A **left edge rail** in the accent, full height. Use a percentage width, not a container
  query unit: `cqw` widths on absolutely positioned children collapse to zero when a
  paginated container query element prints, even though `cqw` font sizes on the same element
  resolve correctly. That bug cost a full debugging pass.
- A **2 x 2 cell mark** top right. It is the quietest possible structural signature.
- **Print needs `.stage` set to `display: block`.** It is flex on screen, and print sets
  every page to `display: block`, so a flex stage lays all pages side by side on one sheet.

## Type

Two roles, always:

- **One high-contrast display serif** for every headline and every figure.
- **One mono** for every number, label, eyebrow and caption.

Swapping the mono for a sans collapses the register. Set `font-variant-numeric:
tabular-nums` anywhere digits line up.

The accent italic carries the claim inside a headline: `<span class="em">`. One phrase per
headline, never two.

## The cover

- **Full-bleed image** if you have one, type alone if you do not. Both work.
- **A light top wash, not a scrim.** Darkening the middle of the frame to guarantee
  legibility smothers the photograph. Push the darkness to the bottom eighth where the
  caption sits, and let a double text shadow carry the type.
- **The title leads.** No eyebrow above it. The eyebrow sits under the title, small.
- **The title must sit clear of the subject.** A title crossing the subject survives at
  full size and fails at thumbnail size. If the composition has no clear space, change the
  composition rather than adding more scrim.
- The cover is the only page with no inner panel and no cell mark.

## Filling a page

The most common defect is a page anchored at the top with dead space below. It reads
unfinished, and a reader who sees one stops swiping.

Three fixes, in order of preference:

1. **Show data you already hold.** Most sparse pages are sparse because the findings file
   carries more than the page shows. A four-row split becomes a four-row split plus the
   three biggest named winners.
2. **Make it a big-number page.** One figure at 19% of page width, the unit, a short
   paragraph, a caption. Deliberate, not empty.
3. **Deepen the panels.** More padding and one more line of real detail per panel.

Padding alone is not a fix. If a page has nothing more to say, cut the page.

## Lists

- **Ranked descending, always**, unless the order is a genuine sequence. A list out of rank
  order reads as a bug. One issue shipped with 92.35% sitting below 13.69%.
- **One denominator per list, or name both.** If a list mixes a share-of-pages measure with
  a share-of-citations measure, say so in the caption or the reader reads one scale.
- **Two metrics go on one row, not in two lists.** Two four-row lists overflow a page; one
  four-row list carrying both fits and reads better.
- **Grey out the near-zero rows** rather than dropping them. The absence is the finding.

## Long text

Take a **character budget, not a row count**, and print "N of M shown". See
`findings-schema.md` for the measured numbers.

## The two checks that must pass before you ship

1. **Overflow.** Extract the PDF text and confirm the footer line appears on every page.
   The byline is the last element on each page, so a page missing it overflowed. Do not
   measure heights in a browser: a paginated container query element can report a
   zero-height page and give you confident nonsense.
2. **Raw markup.** Search the extracted text for `<span` and `&nbsp;`. Passing HTML into a
   field the builder escapes prints the markup literally, and it is invisible until someone
   reads the page.

Both are one command, and both have caught real defects.

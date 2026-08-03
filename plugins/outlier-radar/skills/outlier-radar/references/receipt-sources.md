# Picking sources that can actually become receipts

Every spoken brand and stat gets an artifact on screen. That means a source is
only useful if it will still be a source once it has been through a headless
browser and a crop. A verified fact behind a bot wall is not a receipt, and the
failure is silent: the capture succeeds, the file is the right size, and the card
you burn into the video is a robot-detection notice.

Check this when you pick sources during research, not at edit time. Swapping a
source after the video is cut means recapturing, recropping and recomposing.

## Known bad for capture

| Source | What you get instead |
|---|---|
| **bloomberg.com** | A block page: "Why did this happen? Please make sure your browser supports JavaScript and cookies", plus a block reference ID. Never renders the article. |
| **support.apple.com** | An interstitial "Security verification in progress" challenge. Do not attempt to pass it. |
| Local news on hard paywalls (e.g. blockclubchicago.org) | Refuses headless user agents outright; no file at all. |
| **tiktok.com** profile pages | Renders inconsistently, often just the shell. Fine as a *mention*, weak as a receipt. |

Bloomberg is the trap worth remembering, because it is so often the best-written
source for a business number. Cite it in `sources[]` if it is what you verified
against, but point the `shot_list` entry at something capturable.

## Reliable substitutes, by claim type

- **A public company's own numbers**: the company newsroom or investor page.
  Apple's newsroom press release renders cleanly and states the figure in prose,
  which crops into a perfect card. Beats any outlet's write-up of it.
- **A market-cap or share-price milestone**: CNBC, 9to5Mac, Forbes. All three
  render headline, dateline and byline.
- **A product or firmware story**: Tom's Hardware, PC Gamer, VentureBeat, the
  vendor's own product page, the GitHub repo, the Hugging Face model card.
- **An advertising or media-business number**: Digiday, Marketing Brew,
  Storyboard18.
- **A historical first**: the original press release. `googlepress.blogspot.com`
  still serves Google's 2000 AdWords announcement, which is a far better artifact
  than a modern article describing it.
- **A private company's operating figures**: the official company profile page.
- **A benchmark or survey median**: the publisher's own results post, cropped to
  the figure.

## Practical rules

1. Prefer a **primary** source. It is usually both more credible and more
   capturable than coverage of it.
2. Point the `shot_list` URL at the **exact page carrying the number**, not the
   section index. A newsroom front page is not a receipt for a quarterly figure;
   the press release is.
3. Give every number-bearing claim a **second capturable source** in `sources[]`,
   so a wall on the first costs a swap rather than a reshoot.
4. When a claim can only be sourced to a walled page, either capture it by hand
   into `manual/` or cut the claim. Do not soften it and keep it unreceipted.
5. Verify each card **by eye** before it is burned. Auto-capture cannot tell a
   headline from a cookie banner, and a card is worse than no card if it shows
   the wrong thing.

## Consent banners and modals

Most sites that do render will render a cookie wall over the content. Two things
make this survivable, both handled by `cards_from_raws.py`:

- Capture with a **short virtual-time budget** (~2.2s). Many consent scripts
  paint after the article does, so a fast screenshot catches the headline clean.
- **Detect the modal and crop above it.** A consent panel is a bright box over a
  dimmed page, which is easy to spot and easy to fence off. Beware the inverse
  error: a plain white article column on a light grey page looks similar, and an
  over-eager check truncates good cards.

The banner is also why "pick the most text-dense region" is a bad heuristic for
finding a headline: consent copy is the densest text on the page.

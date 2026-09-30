# HyperFrames packaging

The finished yapcut cut plays underneath, unchanged. HyperFrames (HeyGen's open-source HTML video
renderer) draws everything on top as a web page and renders it to an MP4: the hook at frame zero,
word captions, receipt cards that build as the line is said, slow camera push-ins, a tagged sound
per on-screen event, and a music bed carved around the voice. `scripts/hfkit/` is the engine. A
video is a short Python spec that anchors every card to a phrase in the cut's own corrected
transcript, so nothing is timed by guessing seconds.

## What a creator has to install

| Piece | Needed for | Account |
|---|---|---|
| Node 22+ and ffmpeg | everything | none |
| `npx hyperframes@0.8.96` | check, snapshot, render (downloads its own Chrome on first run) | none |
| HeyGen's skills, `npx skills add heygen-com/hyperframes` | the carve that ducks the music bed under the voice; Claude's authoring help | none |
| HeyGen CLI, `curl -fsSL https://static.heygen.ai/cli/install.sh \| bash`, then `heygen auth login` | the curated sound library | a free HeyGen account |

Nothing here needs a paid plan. Without the skills, the bed plays flat at 10%. Without the HeyGen
CLI, `sfx_library.py offline` maps every sound tag to the CC0 pack `gen_sfx.py` synthesizes: it
works, it sounds thinner.

**Why the sounds are not in the repo.** The library is 30 picks from HeyGen's sound and music
catalog, chosen by ear from ranked searches. The catalog is HeyGen's, so this plugin ships the
catalog IDs and the query that surfaced each one, and `sfx_library.py fetch` downloads them with
the creator's own account. The audio is never redistributed from here.

## The sequence

1. Cut the video with yapcut as usual. The kit reads `.yap_build/full_<name>.nopunch.mp4` (or
   `full_<name>.mp4`), `w_<name>.json` and `<name>_corrections.json`, and takes the voice from
   the finished MP4 when you pass it (already loudness-normalized).
2. `python3 scripts/hfkit/sfx_library.py fetch` once per machine (or `offline`).
3. Copy `scripts/hfkit/example_spec.py` next to the footage and write the cards. Every figure
   and quote on a card is verbatim from the source in its pill.
4. `python3 my_video.py` builds, carves the bed once, runs `hyperframes check` and snapshots
   every card at the moment before it leaves. **Look at every snapshot.** The checker does not
   see a row that runs past its card; the snapshot does.
5. `python3 my_video.py render`.

The theme comes from `brand-config.json`: `accent_hex`, `ink_hex`, optional `pill_hex` and
`overlay_font` (any Google Fonts family, default Outfit), `handle` plus `contact_lines` for the
contact block over the last 9.7 seconds, and `series.mark_png` for the show mark at frame zero on
show episodes (`show=True`).

## Rules the kit enforces, and the incident behind each

- **Nothing leaves its card.** Flow rows are sized in em and scaled to the room inside the card's
  padding after fonts load; hook lines, stats and titles shrink to their own box. Counters hold
  their widest text while this runs, then reset. Found when a four-node flow ran off both edges
  and `check` passed it.
- **A number needs time at its final value.** Land the count on the spoken number and keep the
  card up at least 0.8s after. A counter that landed 0.2s before its card left read as a flash.
- **SVG lines are drawn in the card's own pixels.** A line in a stretched viewBox with
  `vector-effect: non-scaling-stroke` draws as broken dashes, because the dash is measured in one
  space and painted in the other.
- **Text boxes are taller than their line.** A 150px number at line-height 1.05 overlaps its
  label in the layout check; stats sit at 1.28 and hook lines at 1.14.
- **Push-ins never overlap.** Each one eases back over 0.45s, so the next starts at least 0.5s
  after the last ends; the build refuses otherwise.
- **One image file, one element.** The same file in two `<img>` tags trips
  `duplicate_media_discovery_risk`; the kit gives the second a new name.
- **Sounds by meaning.** Each card type calls its tag (card lands, number counts, number lands,
  line strikes, node lights). Volumes live in the theme; the bed is carved under the voice.
- **The hook is on screen at 0.00.** Line one is static at frame zero; later lines land by
  0.6s; a counting number counts in its own line. A frame-one headline sits under the captions
  while the hook holds the top band.

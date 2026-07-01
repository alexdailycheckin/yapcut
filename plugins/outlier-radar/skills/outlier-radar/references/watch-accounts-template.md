# Watch accounts (optional)

An optional list of accounts and creators to track for inspiration and outlier
detection. The weekly scan reads this file, pulls each creator's recent posts,
and flags any that beat that creator's OWN median by the outlier threshold (the
5x-plus overperformers), so the engine can extract the transferable hook or
format mechanic. Leaving this file empty is fine; the engine will fall back to
open web search. Filling it in makes the weekly scan sharper and faster.

Include two kinds of accounts:
- **Niche**: creators in `{{niche}}` (or as close as short-form gets to it). Pure
  niche content sometimes barely goes viral, so these anchor substance and
  credibility more than raw reach.
- **Adjacent**: proven viral creators in a lighter, adjacent lane whose hook and
  format craft you want to borrow for the `{{secondary_lane.label}}` lane. Watch
  these for mechanic, not subject matter.

Edit freely. Add or remove rows as your watchlist evolves. Keep it short enough
to actually scan each week.

## Template

| Handle              | Platform  | Why watch                                              | Niche / adjacent |
|---------------------|-----------|--------------------------------------------------------|------------------|
| {{niche_creator_1}} | tiktok    | Core-niche creator; anchors real substance and proof   | niche            |
| {{adjacent_1}}      | instagram | Elite hook discipline; borrow the format for reach     | adjacent         |
| {{adjacent_2}}      | youtube   | Retention and story-loop craft worth studying          | adjacent         |

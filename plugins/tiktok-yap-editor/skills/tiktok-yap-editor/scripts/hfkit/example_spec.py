#!/usr/bin/env python3
"""A spec template: copy it next to your footage, rename, replace every phrase with words
from YOUR cut (ep.t / ep.e find them in the corrected transcript and fail loudly when a
phrase is not there), and delete the cards you do not need.

    python3 my_video.py            build, check, snapshot every card
    python3 my_video.py render     then render the MP4

The card vocabulary, one line each (all take t0, t1 = on and off, in the cut's seconds):
    headline(img, src, date, t0, t1, pos="under"|"top")    a captured headline, frame one sits under the captions
    image(img, t0, t1, src, date, wipe_at, width, kicker)  a chart or screenshot, optional left-to-right wipe
    title(text, t0, t1, kicker, slam_at)                   the line that carries the argument, slammed in
    chip(logo, tag, t0, t1)                                one logo with a pill under it
    chips(kicker, items, t0, t1, src, date)                a set: logos or pills, no arrows
    flow(kicker, nodes, t0, t1, sub, sub_at, src, date)    a sequence with arrows; nodes can strike, light, ripple
    counter(value, fmt, count_at, land_at, t0, t1, label)  a number counting up (money, int, mult, pct, rank)
    bars(kicker, bars, t0, t1, limit=...)                  comparison bars, optional stop line ("Excel stops")
    quote(text, emphasis, draw_at, t0, t1, src, date, by)  a verbatim quote, the emphasis underlined as it is said
    grid(kicker, t0, t1, strike_at)                        a spreadsheet, struck through
    fan(kicker, left, sub, t0, t1, fan_at)                 build once, sell many: one node, a field of copies
    network(kicker, center, t0, t1, spread_at, sub)        word of mouth: people around a centre
    converge(kicker, box, inside, mover, t0, t1, move_at)  the thing moves into where the person already is
    route(kicker, source, targets, t0, t1, at)             one source, several targets, the hot one gets the line
    list(title, items, t0, t1, mark="tick"|"cross")        a checklist that builds as it is said
    timeline(kicker, ticks, t0, t1)                        dated steps on a rule
    push(t0, t1, scale)                                    a slow camera push-in on a line that carries the belief
Every figure and quote on a card is verbatim from the source named in its pill.
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
from hfkit.run import from_yap, run  # noqa: E402

FOOTAGE = "/path/to/footage/folder"          # the folder yapcut ran on (it holds .yap_build/)
ep = from_yap("episode-01", FOOTAGE, show=True, final="/path/to/output/episode-01.mp4")
T, E = ep.t, ep.e

ep.hook(["Acme just", "bought a spreadsheet"], spark="spreadsheet")                  # on screen at 0.00
ep.headline("/path/to/headline.png", "example.com", "24 Sep 2026", 0.3, 5.3)          # under the captions during the hook
ep.grid("The whole point of AI at work", T("the whole point"), T("acme sells"), T("stop living"))
ep.push(T("the whole point"), E("in spreadsheets"), 1.05)
ep.counter(7, {"pre": "$", "suf": " billion", "dec": 1}, T("acme sells") + 0.4, E("7 billion"),
           T("acme sells"), T("the next line"), "Annualized revenue run rate", "example.com", "24 Sep 2026", final="$7 billion")

if __name__ == "__main__":
    run(ep, sys.argv[1:], out="/path/to/output/episode-01.hyperframes.mp4")

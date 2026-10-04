"""The card theme every video uses: white cards, pill nodes, one accent, an ink source pill
with an accent arrow chip, captions in the overlay font with an ink stroke.

build() takes the brand tokens and returns the theme dict the kit reads. from_brand() reads the
same tokens out of the editor's brand-config.json, so a creator's videos come out in their own
colours without touching this file:
    accent_hex   the one accent (hot nodes, stats, underline, spark word)
    ink_hex      text, strokes, the source pill
    pill_hex     OPTIONAL node / track colour (default a warm sand)
    overlay_font OPTIONAL Google Fonts family for cards, hook and captions (default Outfit;
                 HyperFrames fetches Google fonts at render time)
    handle, contact_lines   the contact block over the last 9.7 seconds
    series.mark_png         OPTIONAL show mark drawn at frame zero on show episodes
"""
import os

ARROW_SVG = ("url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 20 20'%3E"
             "%3Cpath d='M6 14 L14 6 M8 6 H14 V12' fill='none' stroke='%23FFFFFF' stroke-width='2.4' "
             "stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E\")")

CSS = """
      #root { font-family: "FONT", system-ui, sans-serif; color: INK; }
      #hook { color: #FFFFFF; font-weight: 800; letter-spacing: -0.02em; line-height: 1.14;
              -webkit-text-stroke: 7px INK; paint-order: stroke fill; text-shadow: 0 10px 30px rgba(INKRGB, 0.35); }
      #hl0 { font-size: 100px; } #hl1 { font-size: 118px; } #hl2 { font-size: 84px; }
      .spark { color: RED; }
      .card { background: #FFFFFF; color: INK; border-radius: 30px; padding: 32px 36px; box-shadow: 0 30px 70px rgba(INKRGB, 0.25); }
      .card.under, .card.plain { padding: 22px 24px; } .shot { border-radius: 12px; } .wipe { border-radius: 12px; }
      .kicker { display: flex; align-items: center; gap: 12px; font-weight: 600; font-size: 22px; letter-spacing: 0.14em;
                text-transform: uppercase; color: MUTED; }
      .kicker::before { content: ""; width: 12px; height: 12px; border-radius: 50%; background: RED; flex: 0 0 auto; }
      .kicker.center { display: block; text-align: center; text-wrap: balance; } .kicker.center::before { display: none; }
      .src { display: inline-flex; align-items: center; gap: 12px; background: INK; color: #FFFFFF; border-radius: 999px;
             padding: 8px 8px 8px 22px; font-weight: 600; font-size: 22px; white-space: nowrap; }
      .src::after { content: ""; width: 34px; height: 34px; border-radius: 50%; background: RED ARROW center / 20px no-repeat; flex: 0 0 auto; }
      .date { font-weight: 500; font-size: 22px; color: MUTED; white-space: nowrap; }
      .node { background: SAND; color: INK; border: 0 solid SAND; border-radius: 999px; padding: 0.6em 0.8em; font-weight: 700; font-size: 1em; }
      .node.hot { background: RED; border-color: RED; color: #FFFFFF; }
      .logochip { background: #FFFFFF; border-radius: 18px; padding: 6px; box-shadow: 0 0 0 2px rgba(INKRGB, 0.08); }
      .logochip img { border-radius: 12px; }
      .arrow path { stroke: rgba(INKRGB, 0.5); stroke-width: 4; }
      .sub { text-align: center; margin-top: 18px; font-weight: 500; font-size: 26px; color: MUTED; text-wrap: balance; }
      .ripple { border: 5px solid RED; }
      .strike path { stroke: INK; }
      .title { font-weight: 800; font-size: 84px; line-height: 1.02; letter-spacing: -0.03em; color: RED; }
      .tagpill { display: inline-block; background: INK; color: #FFFFFF; border-radius: 999px; padding: 12px 24px; font-weight: 700; font-size: 24px; white-space: nowrap; }
      .takepill { background: SAND; color: INK; } .takechip { background: RED; color: #FFFFFF; }
      .stamp { background: #FFFFFF; color: INK; box-shadow: 0 24px 60px rgba(INKRGB, 0.25); } .stamplab { color: MUTED; }
      .chipcard img { border-radius: 26px; box-shadow: 0 24px 60px rgba(INKRGB, 0.3); }
      .stat { font-weight: 800; font-size: 150px; line-height: 1.05; letter-spacing: -0.04em; color: RED; margin-bottom: 8px; }
      .whead img { border-radius: 16px; box-shadow: 0 0 0 2px rgba(INKRGB, 0.08); }
      .bname { font-weight: 700; font-size: 30px; }
      .track { background: SAND; }
      .fill.f1 { background: INK; } .fill.f2 { background: RED; }
      .bval { font-weight: 800; font-size: 44px; color: INK; }
      .limline { background: RED; }
      .limlabel { font-weight: 700; font-size: 20px; letter-spacing: 0.1em; text-transform: uppercase; color: RED; padding-bottom: 2px; }
      .q { font-weight: 700; font-size: 50px; line-height: 1.18; letter-spacing: -0.02em; padding: 10px 6px 6px; }
      .ul path { stroke: RED; }
      .by { font-weight: 600; font-size: 20px; letter-spacing: 0.12em; text-transform: uppercase; color: MUTED; }
      .cell { background: SAND; } .cell:nth-child(-n+5) { background: PILLDARK; }
      .dot { background: INK; } .fanrow + .sub { font-size: 36px; font-weight: 700; color: INK; margin-top: 20px; }
      .netlines path { stroke: rgba(INKRGB, 0.35); stroke-width: 4; }
      .person { background: SAND; border: 5px solid INK; }
      .cbox { border: 4px dashed rgba(INKRGB, 0.35); }
      .cboxlabel { background: #FFFFFF; font-weight: 600; font-size: 20px; letter-spacing: 0.14em; text-transform: uppercase; color: MUTED; }
      .slot { border: 3px dashed rgba(INKRGB, 0.3); }
      .rlines path { stroke: rgba(INKRGB, 0.25); stroke-width: 4; } .rlines path.hotline { stroke: RED; stroke-width: 6; }
      .ltitle { font-weight: 800; font-size: 60px; line-height: 1.05; letter-spacing: -0.03em; color: INK; }
      .ltitle.red { color: RED; }
      .litem { font-weight: 700; font-size: 44px; line-height: 1.12; letter-spacing: -0.01em; }
      .lmark.tick rect { fill: INK; } .lmark.cross rect { fill: RED; } .lmark path { stroke: #FFFFFF; }
      .trule { background: INK; }
      .tdot { background: RED; border: 7px solid #FFFFFF; box-shadow: 0 0 0 3px INK; }
      .tlabel { font-weight: 800; font-size: 44px; letter-spacing: -0.02em; }
      .tsub { font-weight: 600; font-size: 24px; color: MUTED; }
      #contact { font-weight: 700; color: #FFFFFF; line-height: 1.25; -webkit-text-stroke: 6px INK; paint-order: stroke fill; }
      #contact .h { font-size: 40px; } #contact .s { font-size: 30px; font-weight: 600; }
      #contact .plus { display: inline-block; background: RED; color: #FFFFFF; -webkit-text-stroke: 0; border-radius: 10px; padding: 0 10px; }
"""

CAP_CSS = """
          #captions-band .capgroup { font-family: "FONT", system-ui, sans-serif; font-weight: 800; font-size: 84px; gap: 0.3em; letter-spacing: -0.01em; }
          #captions-band .cw { color: #FFFFFF; -webkit-text-stroke: 7px INK; paint-order: stroke fill; text-shadow: 0 8px 24px rgba(INKRGB, 0.35); }
"""

SFX_VOLUME = {"sting": 0.2, "counter": 0.1, "money": 0.23, "headline": 0.32, "card_in": 0.26, "card_in_heavy": 0.24,
              "pop": 0.26, "pop_small": 0.3, "slam": 0.3, "tap": 0.45, "message": 0.26, "win": 0.24, "sweep": 0.18,
              "fail": 0.14, "strike": 0.22, "chime_short": 0.22, "tick": 0.26, "riser": 0.16, "thud": 0.24, "whip": 0.2,
              "shutter": 0.25, "notify_double": 0.24, "coins": 0.22}


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def build(accent, ink="#17181B", pill="#EFE3CE", font="Outfit", contact=None, star=None, pill_dark=None, bed_volume=0.1):
    r, g, b = _rgb(ink)
    pd = pill_dark or "#%02X%02X%02X" % tuple(max(0, int(c * 0.93)) for c in _rgb(pill))
    tok = {"ARROW": ARROW_SVG, "INKRGB": f"{r}, {g}, {b}", "INK": ink, "RED": accent, "PILLDARK": pd, "SAND": pill,
           "MUTED": f"rgba({r}, {g}, {b}, 0.72)", "FONT": font}
    css, cap = CSS, CAP_CSS
    for k in ("ARROW", "INKRGB", "INK", "RED", "PILLDARK", "SAND", "MUTED", "FONT"):
        css, cap = css.replace(k, tok[k]), cap.replace(k, tok[k])
    return {"accent": accent, "on_accent": "#FFFFFF", "css": css, "font_faces": "", "cap_css": cap, "bed_volume": bed_volume,
            "sfx_volume": dict(SFX_VOLUME), "star": star, "contact": contact}


def from_brand(cfg):
    """Theme from an editor brand-config dict (yaplib.brand.load())."""
    accent = cfg.get("accent_hex") if cfg.get("accent_hex") not in (None, "", "none") else "#E8232F"
    mark = (cfg.get("series") or {}).get("mark_png") or None
    contact = [cfg["handle"]] + list(cfg.get("contact_lines") or []) if cfg.get("handle") else None
    return build(accent, ink=cfg.get("ink_hex") or "#17181B", pill=cfg.get("pill_hex") or "#EFE3CE",
                 font=cfg.get("overlay_font") or "Outfit", contact=contact,
                 star=mark if mark and os.path.exists(mark) else None)

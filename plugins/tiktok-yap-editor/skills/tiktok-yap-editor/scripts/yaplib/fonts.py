"""Font lookup by FAMILY NAME, not by macOS path.

The audit counted 16 hardcoded font paths across 7 scripts, which is what made
"creator-agnostic" mean "macOS only". hook_styles.py already resolved by family
through a FONT_DIRS scan; that pattern now lives here for everyone, with the
Linux dirs added.

  find_font("Space Mono", "700")            -> /Users/x/Library/Fonts/spacemono-700.ttf
  find_font("Bricolage Grotesque ExtraBold") -> .../BricolageGrotesque-ExtraBold.ttf
  find_font("Nope Sans")                    -> raises FontNotFound naming the dirs
  find_font("Nope Sans", required=False)    -> None
  first_font([("Helvetica", None), ("Arial", None)]) -> first path that exists, or None

Matching is on the normalised file stem (lowercase alphanumerics). An exact
stem == family(+weight) match wins; then a stem containing the family AND the
weight hint (700/bold, 800/extrabold, 900/black...); then any stem containing
the family. Never a fuzzy "stem in target" guess: that is how a request for
"Montserrat Black" could come back with Montserrat[wght].ttf (renders Thin).
"""
import os
import re

FONT_DIRS = [
    os.path.expanduser("~/Library/Fonts"), "/Library/Fonts",
    "/System/Library/Fonts", "/System/Library/Fonts/Supplemental",
    os.path.expanduser("~/.fonts"), os.path.expanduser("~/.local/share/fonts"),
    "/usr/share/fonts", "/usr/local/share/fonts",
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "assets", "fonts"),
]
_EXTS = (".ttf", ".otf", ".ttc")

# weight words that name the same face; a hint in either column matches
WEIGHT_SYNONYMS = {
    "100": ["thin", "100"], "200": ["extralight", "ultralight", "200"],
    "300": ["light", "300"], "400": ["regular", "book", "normal", "400"],
    "500": ["medium", "500"], "600": ["semibold", "demibold", "600"],
    "700": ["bold", "700"], "800": ["extrabold", "ultrabold", "800"],
    "900": ["black", "heavy", "900"],
}


class FontNotFound(RuntimeError):
    pass


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _weight_tokens(hint):
    if not hint:
        return []
    h = norm(hint)
    for key, words in WEIGHT_SYNONYMS.items():
        if h == key or h in words:
            return [norm(w) for w in words]
    return [h]


def _scan(extra_dirs=()):
    """(stem_norm, path) for every font file under the search dirs, with
    variable fonts ([wght]) sorted LAST so a static instance wins ties."""
    seen = set()
    files = []
    for d in list(extra_dirs) + FONT_DIRS:
        if not d or not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if not fn.lower().endswith(_EXTS):
                continue
            p = os.path.join(d, fn)
            if p in seen:
                continue
            seen.add(p)
            files.append((norm(os.path.splitext(fn)[0]), p, "[" in fn))
    files.sort(key=lambda t: t[2])
    return [(s, p) for s, p, _v in files]


def find_font(family, weight_hint=None, required=True, extra_dirs=()):
    """Resolve a family name (+ optional weight) to a font file path."""
    fam = norm(family)
    if not fam:
        if required:
            raise FontNotFound("find_font: empty family name")
        return None
    wtoks = _weight_tokens(weight_hint)
    files = _scan(extra_dirs)
    # 1. exact stem: "spacemono700", "bricolagegrotesqueextrabold", "antonregular"
    exact_targets = [fam + w for w in wtoks] + ([fam] if not wtoks else [])
    for stem, p in files:
        if stem in exact_targets:
            return p
    # 2. family + weight both present in the stem
    if wtoks:
        for stem, p in files:
            if fam in stem and any(w in stem for w in wtoks):
                return p
    # 3. family alone (the family name may itself carry the weight, e.g.
    #    "Montserrat Black" -> montserratblack)
    for stem, p in files:
        if stem == fam or stem.startswith(fam):
            return p
    for stem, p in files:
        if fam in stem:
            return p
    if required:
        looked = [d for d in list(extra_dirs) + FONT_DIRS if os.path.isdir(d)]
        raise FontNotFound(
            f"font not installed: {family!r}"
            + (f" (weight {weight_hint})" if weight_hint else "")
            + "\n  looked in: " + ", ".join(looked)
            + "\n  fix: install the family (bash scripts/setup_fonts.sh installs the defaults), "
              "or change caption_font / label_font in brand-config.json")
    return None


def first_font(candidates, extra_dirs=()):
    """candidates: [(family, weight_hint), ...]. First installed path or None."""
    for fam, w in candidates:
        p = find_font(fam, w, required=False, extra_dirs=extra_dirs)
        if p:
            return p
    return None


def is_installed(family, weight_hint=None):
    return find_font(family, weight_hint, required=False) is not None

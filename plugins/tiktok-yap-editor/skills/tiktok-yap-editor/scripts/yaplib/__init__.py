"""yaplib: the shared helpers every tiktok-yap-editor script imports.

One place for the things the audit (2026-09-09) found copied across the flat
scripts: brand-config resolution (7 copies, 3 default sets), ffprobe duration
(14), whisper word-JSON parsing (8), hex to ASS colour (3), the 1080x1920 canvas
(12 literals), font lookup by hardcoded macOS path (16 in 7 files).

Import pattern for a flat script in scripts/ (works through a symlink, because
realpath locates the SIBLING module, never the workspace):

    sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
    from yaplib import brand, media, words, ass, fonts

Modules:
  home    workspace resolver, byte-identical to outlier-radar/yapcut_home.py
  brand   brand-config resolution + ONE DEFAULTS dict (+ --shell emitter)
  media   ffprobe/ffmpeg helpers, run() that raises with stderr, W/H canvas
  words   whisper word-JSON loaders shared by captions and every gate
  ass     hex to ASS colour, ASS time formatter
  fonts   FONT_DIRS + find_font(family, weight_hint)
"""
__all__ = ["home", "brand", "media", "words", "ass", "fonts"]

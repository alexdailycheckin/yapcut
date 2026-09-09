"""ASS (Advanced SubStation) primitives shared by build_ass.py, cta_block.py and
the gates that parse cap_<out>.ass. Colours in ASS are &HAABBGGRR (alpha first,
then BLUE, GREEN, RED), the reverse of a CSS hex, which is why this lived as
three slightly different copies before."""
import re

# a Hook event "starts at 0.00" when its Start is within this of zero
# (ASS times are centiseconds, so anything under one tick).
T0_TOL = 0.005


def hex_to_ass(h, alpha="00", fallback="FFFFFF"):
    """'#RRGGBB' -> '&H00BBGGRR'. A malformed hex falls back to opaque white
    rather than raising: a wrong colour is visible, a crashed build at 2am is
    not. 'none'/'off'/'' are caller-level decisions, see is_none()."""
    h = (h or "").strip().lstrip("#")
    if len(h) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        h = fallback
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H{alpha}{b}{g}{r}".upper()


def is_none(h):
    """True when a brand colour field means 'no colour' (spark off)."""
    return (h or "").strip().lower() in ("", "none", "off", "false")


def hex_to_rgba(h, a=255, fallback=(255, 90, 42)):
    """'#RRGGBB' -> (r, g, b, a) for Pillow callers (cover, cards, hooks)."""
    h = (h or "").strip().lstrip("#")
    if len(h) != 6 or not re.fullmatch(r"[0-9a-fA-F]{6}", h):
        return (*fallback, a)
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


def cs(t):
    """seconds -> H:MM:SS.cc (centiseconds), the ASS time format."""
    if t < 0:
        t = 0
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def parse_time(s):
    """'H:MM:SS.cc' -> seconds."""
    h, m, sec = s.strip().split(":")
    return int(h) * 3600 + int(m) * 60 + float(sec)


def strip_tags(text):
    """Remove {\\...} override blocks and turn \\N into a space."""
    return re.sub(r"\{[^}]*\}", "", text).replace("\\N", " ").replace("\\n", " ")


def dialogue_events(ass_path, style=None):
    """Yield (start_s, end_s, style, raw_text) for every Dialogue line,
    optionally filtered to one style name (e.g. 'Hook', 'Cap')."""
    with open(ass_path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line.startswith("Dialogue:"):
                continue
            parts = line.split(",", 9)
            if len(parts) < 10:
                continue
            st_name = parts[3].strip()
            if style and st_name != style:
                continue
            yield parse_time(parts[1]), parse_time(parts[2]), st_name, parts[9].rstrip("\n")


def hook_end(ass_path, default=2.5):
    """When the burned hook leaves the screen: the latest End of any Hook event.
    Read from the .ass so the retention gate never counts a phantom default."""
    last = 0.0
    for _st, en, _style, _txt in dialogue_events(ass_path, style="Hook"):
        last = max(last, en)
    return last if last else default


def _norm_shown(s):
    return re.sub(r"\s+", " ", s.replace("{", "(").replace("}", ")")).strip().casefold()


def frame0_check(ass_path, hook):
    """Frame-zero gate. Returns (rc, message): rc 0 when a Hook event that
    starts at 0.00, with NO fade-in, carries the full first hook line; 2 when
    frame zero would show anything less (one typed letter and a cursor, or a
    blank fade-in); None when no hook was given (not applicable)."""
    segs = [s for s in (hook or "").split("|") if s.strip()]
    if not segs:
        return None, "frame0: no hook given, not applicable"
    target = _norm_shown(segs[0])
    seen_any = False
    for st, en, _style, txt in dialogue_events(ass_path, style="Hook"):
        if st > T0_TOL:
            continue
        seen_any = True
        m = re.search(r"\\fad\(\s*(\d+)", txt)
        fade_in = int(m.group(1)) if m else 0
        shown = _norm_shown(strip_tags(txt).replace("\u258c", " "))
        if target in shown:
            if fade_in > 0:
                return 2, (f"frame0 FAIL: the hook at 0.00 fades in over {fade_in}ms, "
                           "so frame zero is blank. Use \\fad(0,...) on the first hook event.")
            return 0, f"frame0 OK: full first hook line on screen from 0.00 to {en:.2f}s"
    if seen_any:
        return 2, ("frame0 FAIL: a Hook event starts at 0.00 but does not carry the full "
                   f"first line ({segs[0]!r}). Frame zero shows a partial hook.")
    return 2, "frame0 FAIL: no Hook event starts at 0.00 (frame zero has no hook)"


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3 and sys.argv[1] == "frame0":
        rc, msg = frame0_check(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
        print(msg)
        sys.exit(3 if rc is None else rc)      # 3 = not applicable (caller records null)
    if len(sys.argv) == 3 and sys.argv[1] == "hook-end":
        print(f"{hook_end(sys.argv[2]):.2f}")
        sys.exit(0)
    sys.exit("usage: ass.py frame0 <cap.ass> \"<hook|line2>\" | ass.py hook-end <cap.ass>")

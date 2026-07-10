#!/usr/bin/env bash
# Full per-clip pipeline: single-pass cut -> QA -> brand captions -> CTA contact
# block -> compose. Reads a brand-config.json so it is creator-agnostic.
#
# Usage:
#   yapfull.sh <workdir> <clauses.json> <out.mp4> "<hook|line2>" "<hookword>" \
#              [brand-config.json] [corrections.json]
#
# Config resolution (first found): arg > <workdir>/brand-config.json >
#   <skill>/brand-config.json > scripts/brand-config.default.json
set -euo pipefail
WD="$1"; CLAUSES="$2"; OUT="$3"; HOOK="$4"; HOOKWORD="${5:-}"; CFG="${6:-}"; CORR="${7:-}"
SCRIPTS="$(cd "$(dirname "$0")" && pwd)"
OUTBASE="$(basename "${OUT%.*}")"

if [ -z "$CFG" ]; then
  if   [ -f "$WD/brand-config.json" ];        then CFG="$WD/brand-config.json"
  elif [ -f "$SCRIPTS/../brand-config.json" ]; then CFG="$SCRIPTS/../brand-config.json"
  else CFG="$SCRIPTS/brand-config.default.json"; fi
fi
[ -n "$CORR" ] || CORR="$WD/${OUTBASE}_corrections.json"
[ -f "$CORR" ] || echo '{}' > "$CORR"

eval "$(python3 - "$CFG" <<'PY'
import json,sys,shlex
c=json.load(open(sys.argv[1]))
g=lambda k,d:c.get(k,d)
print("CFONT=%s"%shlex.quote(g("caption_font","Montserrat Black")))
print("CCASE=%s"%shlex.quote("on" if str(g("caption_case","on")).lower() in("on","caps","upper","true") else "off"))
print("ACCENT=%s"%shlex.quote(g("accent_hex","none")))
print("BASE=%s"%shlex.quote(g("base_hex","#FFFFFF")))
print("INK=%s"%shlex.quote(g("ink_hex","#000000")))
print("HANDLE=%s"%shlex.quote(g("handle","")))
print("HFONT=%s"%shlex.quote(g("label_font", g("caption_font","Montserrat Black"))))
print("CONTACT=%s"%shlex.quote("\n".join(g("contact_lines",[]))))
print("HANIM=%s"%shlex.quote(g("hook_anim","none")))
print("HSTYLE=%s"%shlex.quote(g("hook_style","outline")))
PY
)"
# optional per-clip extra overlays (source tags, number count-ups): <out>_overlays.json
# (always pass --overlays, quoted; empty string when absent so paths with spaces are safe)
OVRFILE="$WD/${OUTBASE}_overlays.json"; [ -f "$OVRFILE" ] || OVRFILE=""

# 1. single-pass cut (clean CFR, dead-air, tight tails, anti-stutter crop-alt)
python3 "$SCRIPTS/yapcut.py" --clauses "$CLAUSES" --workdir "$WD" --out "$WD/full_${OUTBASE}.mp4" \
  --silence-db -42 --padr 0.12 --padl 0.10 --min-gap 0.55 --min-seg 0.45 --d 0.10
echo "--- blackdetect (cut) ---"
ffmpeg -nostdin -i "$WD/full_${OUTBASE}.mp4" -vf "blackdetect=d=0.02:pic_th=0.95" -an -f null - 2>&1 \
  | grep -i black_start || echo "  NO black frames"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$WD/full_${OUTBASE}.mp4")
echo "--- dur: $DUR ---"

# 2. word-timed captions in the brand style
bash "$SCRIPTS/transcribe.sh" "$WD/full_${OUTBASE}.mp4" "$WD/w_${OUTBASE}" --words >/dev/null 2>&1
python3 "$SCRIPTS/build_ass.py" --words "$WD/w_${OUTBASE}.json" --out "$WD/cap_${OUTBASE}.ass" \
  --preset minimal --font "$CFONT" --caps "$CCASE" --accent none --active-scale 112 \
  --hook-y 430 --hook "$HOOK" --hook-anim "$HANIM" --hook-style "$HSTYLE" --hook-spark "$HOOKWORD" \
  --accent-hex "$ACCENT" --overlays "$OVRFILE" --corrections "$CORR" >/dev/null

# 3. brand touches: accent spark on the hook word + contact block at the CTA tail
python3 - "$WD/cap_${OUTBASE}.ass" "$HOOKWORD" "$DUR" "$ACCENT" "$BASE" "$INK" "$HANDLE" "$CONTACT" "$HFONT" <<'PY'
import sys
p,hw,dur,accent,base,ink,handle,contact,hfont=sys.argv[1:10]
dur=float(dur)
def hx(h):  # #RRGGBB -> ASS &H00BBGGRR
    h=h.lstrip("#"); return "&H00%s%s%s"%(h[4:6],h[2:4],h[0:2]) if len(h)==6 else "&H00FFFFFF"
A=hx(accent) if accent.lower() not in("none","off","") else None
B=hx(base); I=hx(ink)
s=open(p).read()
def t(x): return "0:00:%05.2f"%x
if handle:
    hs=max(0.0,dur-9.7)
    lines=[l for l in contact.split("\n") if l.strip()]
    spark=("{\\1c%s&}+ "%A) if A else "+ "
    body=spark+"{\\1c%s&}%s"%(B,handle)
    for l in lines: body+=r"\N{\fs30\1c%s&}%s"%(B,l)
    ev=(r"Dialogue: 2,%s,%s,Cap,,0,0,0,,{\an2\pos(540,1792)\fn %s\3c%s\bord5\shad0\fsp2\fad(150,0)}{\fs38}%s"
        %(t(hs),t(dur),hfont,I,body))
    s=s.rstrip()+"\n"+ev+"\n"
open(p,"w").write(s)
PY

# 4. compose: burn captions, loudnorm -14, clean CFR re-encode
bash "$SCRIPTS/compose_ass.sh" "$WD/full_${OUTBASE}.mp4" "$WD/cap_${OUTBASE}.ass" "$OUT" 2>&1 | grep -E "wrote|I:"
ffmpeg -nostdin -i "$OUT" -vf "blackdetect=d=0.02:pic_th=0.95" -an -f null - 2>&1 \
  | grep -i black_start || echo "  FINAL: NO black frames"
echo "DONE -> $OUT"

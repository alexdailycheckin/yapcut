#!/usr/bin/env bash
# tests/run.sh: the repo's only test harness. Three stages, no creator footage involved.
#
#   tests/run.sh          all stages (the editor stages cut a synthetic clip and scan a
#                         synthetic restart; a few minutes)
#   tests/run.sh --fast   stages 0, 0b, 2 and 3 (rulebooks, editor units, radar gates,
#                         dashboard), a few seconds;
#                         wired into release.sh and usable from the pre-commit hook
#
# Every regression in CHANGELOG.md before 3.5.0 was found by watching a shipped video or a
# broken dashboard, weeks late. This pins the contracts instead: exit codes, the example week
# passing its own gates, the dashboard rendering cards.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RADAR="$ROOT/plugins/outlier-radar/skills/outlier-radar"
FAST=0; [ "${1:-}" = "--fast" ] && FAST=1
fails=0
ok()   { echo "  ok   $1"; }
bad()  { echo "  FAIL $1"; fails=$((fails+1)); }

# Stage 0: the two rulebooks (rules.json in each plugin) are the only home of their numbers,
# and they agree with each other and with the playbook. The phone reads the same files.
echo "[0] rulebooks"
python3 -B "$ROOT/tests/rules_check.py" && ok "rules_check.py" || bad "rules_check.py"

# Stage 0b: editor contracts with no footage, whisper or fonts (the resolver, named caption
# corrections, the hook fitter and style, receipt placement, finalize's build-folder warning).
echo "[0b] editor units"
python3 -B "$ROOT/tests/editor_units.py" >/tmp/yapcut-units.log 2>&1 && ok "editor_units.py" || { bad "editor_units.py"; grep FAIL /tmp/yapcut-units.log; }

# Stage 1: the editor on a synthetic fixture (Mode A, Mode B, a hook variant).
if [ "$FAST" = 0 ]; then
  echo "[1] editor smoke"
  if [ -x "$ROOT/tests/editor_smoke.sh" ]; then
    if "$ROOT/tests/editor_smoke.sh" >/tmp/yapcut-editor-smoke.log 2>&1; then ok "editor_smoke.sh"; else bad "editor_smoke.sh (see /tmp/yapcut-editor-smoke.log)"; tail -20 /tmp/yapcut-editor-smoke.log; fi
  else
    bad "tests/editor_smoke.sh missing"
  fi
  # Stage 1b: the cross-window scan catches a known restart (needs say + whisper; ~60s)
  echo "[1b] cross-window restart scan"
  if bash "$ROOT/tests/xwin_restart.sh" >/tmp/yapcut-xwin.log 2>&1; then ok "xwin_restart.sh"; else bad "xwin_restart.sh (see /tmp/yapcut-xwin.log)"; tail -20 /tmp/yapcut-xwin.log; fi
fi

# Stage 2: the radar gates on the bundled example week, in a throwaway workspace.
echo "[2] radar gates on the example week"
WS="$(mktemp -d /tmp/yapcut-ws.XXXXXX)"
mkdir -p "$WS/weeks" "$WS/performance" "$WS/voice-corpus"
cp "$RADAR/radar-config.example.json" "$WS/radar-config.json"
cp "$RADAR/weeks/0000-00-00-example.json" "$WS/weeks/"
for s in check_fidelity.py hook_lint.py spoken_lint.py; do
  python3 "$RADAR/$s" --help >/dev/null 2>&1 && ok "$s --help" || bad "$s --help"
done
python3 "$RADAR/radar_gate.py" --week "$WS/weeks/0000-00-00-example.json" --dir "$WS" --skip source,visual --allow-unvalidated >/tmp/yapcut-gate.log 2>&1
rc=$?
if [ "$rc" = 0 ]; then ok "radar_gate.py on the example week (rc 0)"; elif [ "$rc" = 1 ]; then ok "radar_gate.py on the example week (rc 1, warnings only)"; else bad "radar_gate.py on the example week rc $rc"; tail -15 /tmp/yapcut-gate.log; fi
[ -f "$WS/weeks/0000-00-00-example.gate.json" ] && ok "gate stamp written" || bad "no gate stamp"
# exit contract: an illegal qa value must be rc 2
python3 - "$WS" <<'PY'
import json, sys, os
ws = sys.argv[1]; p = os.path.join(ws, "weeks", "0000-00-00-example.json"); d = json.load(open(p))
d["distribution"][0]["qa"] = "pre-qa"; json.dump(d, open(os.path.join(ws, "weeks", "0000-00-00-bad.json"), "w"))
PY
python3 "$RADAR/check_fidelity.py" --dir "$WS" --week "$WS/weeks/0000-00-00-bad.json" --schema-only >/dev/null 2>&1
[ $? = 2 ] && ok "illegal qa value exits 2" || bad "illegal qa value did not exit 2"
rm -f "$WS/weeks/0000-00-00-bad.json"
# the order test: a belief written after the receipts must be rc 2, and the same
# belief moved back to move 2 must pass. This is the 2026-09-07 regression.
python3 - "$WS" <<'ORD'
import json, sys, os
ws = sys.argv[1]; d = json.load(open(os.path.join(ws, "weeks", "0000-00-00-example.json")))
it = d["distribution"][0]
b = it["belief"]
it["script"] = it["script"].replace(b + " ", "").rstrip() + " " + b
json.dump(d, open(os.path.join(ws, "weeks", "0000-00-00-late.json"), "w"))
it["belief"] = "You think you will sort your taxes out later in the year."
json.dump(d, open(os.path.join(ws, "weeks", "0000-00-00-para.json"), "w"))
ORD
python3 "$RADAR/check_fidelity.py" --dir "$WS" --week "$WS/weeks/0000-00-00-late.json" --schema-only >/tmp/yapcut-order.log 2>&1
rc=$?
if [ "$rc" = 2 ] && grep -q "ORDER TEST" /tmp/yapcut-order.log; then ok "belief after the receipts exits 2"; else bad "order test did not fire (rc $rc)"; fi
python3 "$RADAR/check_fidelity.py" --dir "$WS" --week "$WS/weeks/0000-00-00-para.json" --schema-only >/dev/null 2>&1
[ $? = 2 ] && ok "paraphrased belief exits 2" || bad "paraphrased belief did not exit 2"
rm -f "$WS/weeks/0000-00-00-late.json" "$WS/weeks/0000-00-00-para.json"
# old news (3.17.1): a story whose news_date sits past show.max_news_age_days must be rc 2,
# and the same story inside the window must pass. A fresh article about an old event is old.
python3 - "$WS" <<'OLD'
import json, sys, os
ws = sys.argv[1]; d = json.load(open(os.path.join(ws, "weeks", "0000-00-00-example.json")))
d["week"] = "2026-01-05"; it = d["distribution"][0]
it["news_date"] = "2025-12-10"; json.dump(d, open(os.path.join(ws, "weeks", "0000-00-00-old.json"), "w"))
it["news_date"] = "2026-01-02"; json.dump(d, open(os.path.join(ws, "weeks", "0000-00-00-fresh.json"), "w"))
OLD
python3 "$RADAR/check_fidelity.py" --dir "$WS" --week "$WS/weeks/0000-00-00-old.json" --schema-only >/tmp/yapcut-old.log 2>&1
rc=$?
if [ "$rc" = 2 ] && grep -q "Old news" /tmp/yapcut-old.log; then ok "old news exits 2"; else bad "old news did not fail (rc $rc)"; fi
python3 "$RADAR/check_fidelity.py" --dir "$WS" --week "$WS/weeks/0000-00-00-fresh.json" --schema-only >/tmp/yapcut-fresh.log 2>&1
grep -q "Old news" /tmp/yapcut-fresh.log && bad "fresh news flagged as old" || ok "fresh news passes the age check"
rm -f "$WS/weeks/0000-00-00-old.json" "$WS/weeks/0000-00-00-fresh.json"
# a rejected line in a LinkedIn twin (3.18.1): the twin's body ships under the creator's name,
# so a phrase they killed must fail there exactly as it fails in a script.
python3 - "$WS" <<'TWIN'
import json, sys, os
ws = sys.argv[1]; d = json.load(open(os.path.join(ws, "weeks", "0000-00-00-example.json")))
json.dump({"rejections": [{"pattern": "zzq twin phrase", "date": "2026-10-05", "why": "test"}]},
          open(os.path.join(ws, "voice-corpus", "rejections.json"), "w"))
tw = d["distribution"][0]["linkedin"]
tw["body"] = tw["body"] + "\n\nzzq twin phrase."
json.dump(d, open(os.path.join(ws, "weeks", "0000-00-00-twin.json"), "w"))
TWIN
python3 "$RADAR/spoken_lint.py" --dir "$WS" --week "$WS/weeks/0000-00-00-twin.json" >/tmp/yapcut-twin.log 2>&1
rc=$?
if [ "$rc" = 2 ] && grep -q "d-example-1-li.body" /tmp/yapcut-twin.log; then ok "a rejected phrase in a twin exits 2"; else bad "twin rejection did not fire (rc $rc)"; tail -8 /tmp/yapcut-twin.log; fi
rm -f "$WS/weeks/0000-00-00-twin.json" "$WS/voice-corpus/rejections.json"
# the story in one line (3.18.2): an episode's story_line prints above its script in the pack,
# so the read starts from what happened and why it matters.
python3 - "$WS" <<'STORY'
import json, sys, os
ws = sys.argv[1]; d = json.load(open(os.path.join(ws, "weeks", "0000-00-00-example.json")))
d["distribution"][0]["story_line"] = "zzq happened, then zzq happened, which matters because zzq."
json.dump(d, open(os.path.join(ws, "weeks", "0000-00-00-story.json"), "w"))
STORY
YAPCUT_HOME="$WS" python3 "$RADAR/build_pack.py" --week "$WS/weeks/0000-00-00-story.json" --out /tmp/yapcut-story-pack.md >/dev/null 2>&1
grep -q "The story in one line:\*\* zzq happened" /tmp/yapcut-story-pack.md && ok "story_line prints above the script in the pack" || bad "story_line missing from the pack"
rm -f "$WS/weeks/0000-00-00-story.json" /tmp/yapcut-story-pack.md
# no workspace: exit 2, never the skill folder
( cd /tmp && env -u YAPCUT_HOME -u OUTLIER_RADAR_HOME -u LEAD_MAGNET_HOME HOME=/tmp/yapcut-nohome python3 "$RADAR/yapcut_home.py" >/dev/null 2>&1 ); [ $? = 2 ] && ok "no workspace exits 2" || bad "no workspace did not exit 2"

# Stage 2b: "connect anima" serves the phone over the local network: nothing without a token,
# a wrong code refused, the right code pairs, and the week, an inbox event and an upload work.
echo "[2b] anima link"
AWS="$(mktemp -d /tmp/yapcut-aws.XXXXXX)"; APORT=$((20000 + RANDOM % 20000))
mkdir -p "$AWS/weeks"
cp "$RADAR/radar-config.example.json" "$AWS/radar-config.json"
cp "$RADAR/weeks/0000-00-00-example.json" "$AWS/weeks/2026-01-05.json"
python3 -B "$RADAR/anima_link.py" --dir "$AWS" --port "$APORT" --code 314159 --no-bonjour --no-sync --minutes 2 --quiet >/tmp/yapcut-link.log 2>&1 &
APID=$!
for _ in 1 2 3 4 5 6 7 8 9 10; do curl -s -o /dev/null "http://127.0.0.1:$APORT/status" && break; sleep 0.5; done
python3 - "$AWS" "$APORT" <<'LINK'
import json, os, sys, urllib.request, urllib.error
ws, port = sys.argv[1], sys.argv[2]
base = f"http://127.0.0.1:{port}"
def call(method, path, body=None, token=None, raw=None):
    data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
    req = urllib.request.Request(base + path, data=data, method=method)
    if token: req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=5) as r: return r.status, r.read()
    except urllib.error.HTTPError as e: return e.code, e.read()
assert call("GET", "/status")[0] == 401, "no token must be refused"
assert call("POST", "/pair", {"code": "000000", "device": "t"})[0] == 403, "a wrong code must be refused"
code, out = call("POST", "/pair", {"code": "314159", "device": "Test iPhone"})
assert code == 200, code
token = json.loads(out)["token"]
code, out = call("GET", "/status", token=token)
assert code == 200 and json.loads(out)["week"] == "2026-01-05.json"
assert call("GET", "/week", token=token)[0] == 200
assert call("POST", "/inbox", {"type": "kill", "reason": "not me"}, token=token)[0] == 200
assert call("PUT", "/output/2026-01-05/cut.mp4", raw=b"x" * 5000, token=token)[0] == 200
assert call("PUT", "/output/.x/cut.mp4", raw=b"x", token=token)[0] == 400
assert len(os.listdir(os.path.join(ws, "mobile", "inbox"))) == 1
assert os.path.getsize(os.path.join(ws, "mobile", "output", "2026-01-05", "cut.mp4")) == 5000
devices = json.load(open(os.path.join(ws, "mobile", "devices.json")))
assert devices and "token" not in devices[0] and len(devices[0]["token_sha256"]) == 64, "store hashes only"
LINK
[ $? = 0 ] && ok "anima_link.py pairs, serves the week, takes events and cuts" || { bad "anima link contract"; tail -5 /tmp/yapcut-link.log; }
kill "$APID" 2>/dev/null; wait "$APID" 2>/dev/null
rm -rf "$AWS"

# Stage 2c: sync from anywhere with a code. The seal matches the shared vector that Anima's
# SyncCode.swift pins, a wrong code or a changed byte never opens, and a push to a relay with
# the real one's rules sends the week, then the status, and nothing again while nothing changed.
echo "[2c] anima sync"
SWS="$(mktemp -d /tmp/yapcut-sws.XXXXXX)"
mkdir -p "$SWS/weeks"
cp "$RADAR/radar-config.example.json" "$SWS/radar-config.json"
cp "$RADAR/weeks/0000-00-00-example.json" "$SWS/weeks/2026-01-05.json"
python3 -B - "$RADAR" "$SWS" <<'SYNC'
import hashlib, http.server, json, os, sys, threading
sys.path.insert(0, sys.argv[1])
import anima_sync as s
from anima_link import Link
ws = sys.argv[2]

assert s.normalize("k7qm 2xdp 9rta") == s.normalize("K7QM-2XDP-9RTA") == "K7QM2XDP9RTA"
assert s.normalize("O1Il") == "0111", "O reads as 0, I and L as 1"
enc, mac, box = s.keys("K7QM-2XDP-9RTA")
assert box == "fa14db30fb23391bc8c9aca10ea7638dd25e7caa5ce953fe55b490f08a3b7746", box
plain = b'{"week":"2026-09-27"}'
blob = s.seal(plain, enc, mac, nonce=bytes(range(16)))
assert blob.hex() == ("415331000102030405060708090a0b0c0d0e0f6feca0a1b58f16346d30e0d4224955e773f820cce865e7"
                      "fadfa81c23f6cac584791c3bb7d9e945aeb117b3d6f9de8f566a2128ff9d"), blob.hex()
assert s.open_sealed(blob, enc, mac) == plain
changed = bytearray(blob); changed[25] ^= 1
for bad, keys in ((bytes(changed), (enc, mac)), (blob, s.keys("0000-0000-0000")[:2]), (b"AS1short", (enc, mac))):
    try:
        s.open_sealed(bad, *keys)
        raise SystemExit("a changed blob or another code must not open")
    except ValueError:
        pass
assert len(s.normalize(s.new_code())) == 12

store = {}
class Relay(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_PUT(self):
        _, _, bx, name = self.path.split("/")
        body = self.rfile.read(int(self.headers["Content-Length"]))
        h = hashlib.sha256(self.headers.get("Authorization", "")[7:].encode()).hexdigest()
        if store.get((bx, "owner"), h) != h:
            self.send_response(403); self.send_header("Content-Length", "0"); self.end_headers(); return
        store[(bx, "owner")] = h
        store[(bx, name)] = body
        self.send_response(200); self.send_header("Content-Length", "0"); self.end_headers()
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Relay)
threading.Thread(target=srv.serve_forever, daemon=True).start()

r = s.load_relay(ws)
r["relay"] = f"http://127.0.0.1:{srv.server_port}"
assert oct(os.stat(s.relay_path(ws)).st_mode & 0o777) == "0o600", "the code is a secret"
sent, err = s.push(ws, r)
assert err is None and "week" in sent and sent[-1] == "status", (sent, err)
enc, mac, box = s.keys(r["code"])
status = json.loads(s.open_sealed(store[(box, "status")], enc, mac))
assert status["week"] == "2026-01-05.json" and status["workspace_id"], status
# the phone gets the week as written (3.18.0): Anima reads explainers and moments in their own lanes
# and shows the opinion slot from the data, so no script carries it; the Mac adds the slot's label,
# and one card at the top that tells an Anima from before 3.18.0 what it cannot show
from anima_link import phone_week
src = json.load(open(os.path.join(ws, "weeks", "2026-01-05.json")))
sent_week = json.loads(s.open_sealed(store[(box, "week")], enc, mac))
assert sent_week == json.loads(phone_week(os.path.join(ws, "weeks", "2026-01-05.json"), ws))
assert sent_week["explainers"] == src["explainers"] and sent_week["moments"] == src["moments"]
card, *rest = sent_week["distribution"]
assert rest == src["distribution"] and sent_week["office"] == src["office"], "every script travels untouched"
assert card.get("anima_notice") == "update" and "qa" not in card, card
assert "1 explainer, 1 moment to film and a slot for your own take after 1 of" in card["script"], card["script"]
assert sent_week["opinion_label"] == "[YOUR OPINION, IF ANY]", sent_week.get("opinion_label")
plain = os.path.join(ws, "plain.json")
json.dump(dict(src, explainers=[], moments=[], **{lane: [{k: v for k, v in i.items() if k != "opinion"} for i in src[lane]]
                                                   for lane in ("distribution", "office")}), open(plain, "w"))
assert phone_week(plain, ws) == open(plain, "rb").read(), "a week with nothing new goes byte for byte"
os.remove(plain)
assert s.push(ws, r) == ([], None), "an unchanged week is not pushed again"
other = dict(r, write_secret="x" * 43, pushed={})
assert "403" in (s.push(ws, other)[1] or ""), "another Mac cannot overwrite the box"

link = Link(ws)
link.sync_code = r["code"]
assert link.status(paired=True)["sync_code"] == r["code"] and "sync_code" not in link.status()
srv.shutdown()
SYNC
[ $? = 0 ] && ok "anima_sync.py seals to the shared vector and pushes a changed week once" || bad "anima sync contract"
rm -rf "$SWS"

# Stage 3: the dashboard builds and renders cards.
echo "[3] dashboard"
python3 "$RADAR/build_dashboard.py" --dir "$WS" >/tmp/yapcut-dash.log 2>&1 && ok "build_dashboard.py" || { bad "build_dashboard.py"; tail -5 /tmp/yapcut-dash.log; }
[ -s "$WS/dashboard.html" ] && ok "dashboard.html written ($(wc -c <"$WS/dashboard.html" | tr -d ' ') bytes)" || bad "dashboard.html missing"
grep -q 'id="weeks-data"' "$WS/dashboard.html" && ok "weeks embedded as JSON" || bad "weeks-data block missing"
node --check "$RADAR/dashboard/app.js" >/dev/null 2>&1 && ok "app.js parses" || bad "app.js does not parse"
python3 -c "import ast,sys; ast.parse(open(sys.argv[1]).read())" "$RADAR/build_dashboard.py" && ok "build_dashboard.py parses" || bad "build_dashboard.py does not parse"
rm -rf "$WS"

echo
[ "$fails" = 0 ] && { echo "ALL GREEN"; exit 0; } || { echo "$fails failure(s)"; exit 2; }

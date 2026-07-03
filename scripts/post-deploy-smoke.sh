#!/usr/bin/env bash
# post-deploy-smoke.sh — verify a live amorae deploy end-to-end.
#
# Two probes:
#   (a) health   — GET the health URL returns 200.
#   (b) ticket   — the v2 valet-ticket single-use property, exercised
#                  SERVER-SIDE using the mounted X-Amorae-Secret and a
#                  crafted test JWT (v2 does not sig-verify JWTs, so a
#                  structurally-valid token for a synthetic test user is
#                  enough to mint a ticket). The shared secret NEVER leaves
#                  the cluster: by default the ticket check runs INSIDE the
#                  amorae container, reading /run/secrets/V2_WEB_SHARED_SECRET.
#
# Usage:
#   ./post-deploy-smoke.sh                 # in-cluster (on a swarm manager)
#   ./post-deploy-smoke.sh --local \       # against staging, pre-launch
#       --health-url https://amorae.rishi.yral.com/healthz \
#       --secret "$V2_WEB_SHARED_SECRET"
# Flags: --local | --base-url <v2> | --health-url <url> | --secret <val>
#        | --secret-file <path> | --service <swarm service name>
#
# NOTE: the ticket-check assertions (200 + user_id on exchange#1, 4xx on
# exchange#2) are the EXPECTED shape from design §4.7 — reconcile against
# Session 6's live single-use result and adjust if the bodies differ.

set -euo pipefail

V2_BASE="${V2_BASE_URL:-https://agent.rishi.yral.com}"
HEALTH_URL="${HEALTH_URL:-https://amorae.ai/health}"
SERVICE="${SMOKE_SERVICE:-amorae_web}"
SECRET="${V2_WEB_SHARED_SECRET:-}"
SECRET_FILE=""
SECRET_FILE_DEFAULT="/run/secrets/V2_WEB_SHARED_SECRET"

while [ $# -gt 0 ]; do
  case "$1" in
    --local)       [ "${HEALTH_URL}" = "https://amorae.ai/health" ] && HEALTH_URL="https://amorae.rishi.yral.com/healthz"; shift ;;
    --base-url)    V2_BASE="$2"; shift 2 ;;
    --health-url)  HEALTH_URL="$2"; shift 2 ;;
    --secret)      SECRET="$2"; shift 2 ;;
    --secret-file) SECRET_FILE="$2"; shift 2 ;;
    --service)     SERVICE="$2"; shift 2 ;;
    *) echo "unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ── (a) health ──────────────────────────────────────────────────────────
echo "[smoke] health → $HEALTH_URL"
code=$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 "$HEALTH_URL" || echo fail)
[ "$code" = "200" ] || { echo "  ✗ FAIL health=$code"; exit 1; }
echo "  ✓ 200"

# ── (b) ticket single-use — python (stdlib only), run wherever the secret is
PYPROG="$(mktemp)"
trap 'rm -f "$PYPROG"' EXIT
cat > "$PYPROG" <<'PY'
import os, base64, hmac, hashlib, json, time, urllib.request, urllib.error

def b64(d): return base64.urlsafe_b64encode(d).rstrip(b"=")

secret = os.environ.get("SMOKE_SECRET") or open("/run/secrets/V2_WEB_SHARED_SECRET").read().strip()
base = os.environ.get("SMOKE_V2_BASE", "https://agent.rishi.yral.com").rstrip("/")
user = os.environ.get("SMOKE_USER", "amorae-smoke-user")

# Structurally-valid JWT for a synthetic test user. v2 decodes with
# verify_signature=False, so the signature is cosmetic; iss must be allowed.
hdr = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
pl = b64(json.dumps({"iss": "https://auth.yral.com", "sub": user,
                     "exp": int(time.time()) + 300}).encode())
sig = b64(hmac.new(b"smoke", hdr + b"." + pl, hashlib.sha256).digest())
jwt = (hdr + b"." + pl + b"." + sig).decode()

def post(path, data, headers):
    req = urllib.request.Request(base + path, data=json.dumps(data).encode(),
                                 headers={"Content-Type": "application/json", **headers},
                                 method="POST")
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

st, body = post("/api/v1/spicy/handoff", {"bot_handle": "tara"},
                {"Authorization": "Bearer " + jwt})
assert st == 200, f"handoff mint expected 200, got {st}: {body[:200]}"
ticket = json.loads(body)["ticket"]
print(f"  ✓ minted ticket ({st})")

st1, b1 = post("/api/v1/spicy/handoff/exchange", {"ticket": ticket},
               {"X-Amorae-Secret": secret})
assert st1 == 200, f"exchange#1 expected 200, got {st1}: {b1[:200]}"
uid = json.loads(b1).get("user_id")
assert uid == user, f"exchange#1 user_id mismatch: {uid!r} != {user!r}"
print(f"  ✓ exchange#1 200, user_id={uid}")

st2, b2 = post("/api/v1/spicy/handoff/exchange", {"ticket": ticket},
               {"X-Amorae-Secret": secret})
assert 400 <= st2 < 500, f"exchange#2 expected 4xx (single-use), got {st2}: {b2[:200]}"
print(f"  ✓ exchange#2 {st2} — single-use enforced")
print("SMOKE TICKET PASS")
PY

echo "[smoke] ticket single-use → $V2_BASE"
# Resolve the secret's home context: run locally if we can read it here,
# else exec inside the amorae container where it's mounted.
[ -z "$SECRET" ] && [ -n "$SECRET_FILE" ] && [ -f "$SECRET_FILE" ] && SECRET="$(cat "$SECRET_FILE")"
[ -z "$SECRET" ] && [ -f "$SECRET_FILE_DEFAULT" ] && SECRET="$(cat "$SECRET_FILE_DEFAULT")"

if [ -n "$SECRET" ]; then
  SMOKE_SECRET="$SECRET" SMOKE_V2_BASE="$V2_BASE" SMOKE_USER="amorae-smoke-$$" \
    python3 "$PYPROG"
else
  CID=$(docker ps -qf "name=$SERVICE" 2>/dev/null | head -1 || true)
  [ -n "$CID" ] || { echo "  ✗ FAIL: no secret available and no '$SERVICE' container found"; exit 1; }
  echo "  (running inside container $CID — secret stays in-cluster)"
  docker exec -e SMOKE_V2_BASE="$V2_BASE" -e SMOKE_USER="amorae-smoke-$$" -i "$CID" \
    python - < "$PYPROG"
fi

echo "[smoke] ALL PASS"

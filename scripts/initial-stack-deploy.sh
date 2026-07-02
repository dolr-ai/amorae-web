#!/usr/bin/env bash
# initial-stack-deploy.sh — FIRST-TIME manual Swarm deploy of amorae.
#
# Run BY SESSION 6 on a swarm manager (leader) as rishi-deploy, ONCE. After
# this, deploy.yml auto-deploys every main merge via `docker service update`.
#
# Usage:
#   ./initial-stack-deploy.sh --check     # preflight only (safe dry-run)
#   IMAGE_TAG=<sha> ./initial-stack-deploy.sh    # preflight + deploy
#
# Env expected (from a chmod-600 .env you `source` first):
#   IMAGE_TAG (required), OPENROUTER_API_KEY, V2_WEB_SHARED_SECRET,
#   SENTRY_DSN, GEO_BLOCKED_COUNTRIES (optional), V2_BASE_URL (optional).
# Optional: AMORAE_DB_DSN — if set, preflight runs a live `SELECT 1` against
#   amorae_db over the overlay to prove reachability before deploying.

set -euo pipefail
STACK="amorae"
SERVICE="amorae_web"
OVERLAY="yral-v2-data-plane"
DB_SECRET="amorae_database_url"
COMPOSE="docker-compose.swarm.yml"

fail() { echo "✗ PREFLIGHT FAIL: $*" >&2; exit 1; }
ok()   { echo "✓ $*"; }

preflight() {
  echo "── amorae preflight ──"
  docker info --format '{{.Swarm.LocalNodeState}}' 2>/dev/null | grep -q active \
    || fail "this host is not an active swarm node"
  docker node ls >/dev/null 2>&1 || fail "not a swarm MANAGER (run on rishi-4/5/6 leader)"
  ok "swarm manager reachable"

  docker network ls --format '{{.Name}}' | grep -qx "$OVERLAY" \
    || fail "overlay '$OVERLAY' not found — cluster bootstrap must create it first"
  ok "overlay '$OVERLAY' exists"

  docker secret ls --format '{{.Name}}' | grep -qx "$DB_SECRET" \
    || fail "docker secret '$DB_SECRET' missing — create it: printf '%s' '<amorae_db DSN>' | docker secret create $DB_SECRET -"
  ok "secret '$DB_SECRET' exists"

  [ -n "${IMAGE_TAG:-}" ] || fail "IMAGE_TAG not set (the git SHA / image tag to run)"
  ok "IMAGE_TAG=$IMAGE_TAG"

  for v in OPENROUTER_API_KEY V2_WEB_SHARED_SECRET; do
    [ -n "${!v:-}" ] || fail "$v not set (source your .env first)"
  done
  ok "required runtime env present (OPENROUTER_API_KEY, V2_WEB_SHARED_SECRET)"

  [ -f "$COMPOSE" ] || fail "$COMPOSE not found — run from the repo root"
  ok "$COMPOSE present"

  # Optional live DB reachability check over the overlay.
  if [ -n "${AMORAE_DB_DSN:-}" ]; then
    echo "── checking amorae_db reachability over $OVERLAY ──"
    if docker run --rm --network "$OVERLAY" -e DSN="$AMORAE_DB_DSN" postgres:16 \
         sh -c 'psql "$DSN" -tAc "select 1" | grep -qx 1'; then
      ok "amorae_db answered SELECT 1"
    else
      fail "amorae_db not reachable / SELECT 1 failed over $OVERLAY"
    fi
  else
    echo "  (AMORAE_DB_DSN not set — skipping live DB check; the post-deploy"
    echo "   /health probe verifies DB connectivity anyway.)"
  fi
  echo "── preflight PASSED ──"
}

preflight

if [ "${1:-}" = "--check" ]; then
  echo "Dry-run complete. Re-run without --check to deploy."
  exit 0
fi

echo "── deploying stack '$STACK' ──"
docker stack deploy -c "$COMPOSE" "$STACK"
echo "── service status ──"
docker service ls | grep "$SERVICE" || true
echo "── tailing logs (Ctrl-C to stop; watch for DB pool + /health OK) ──"
docker service logs -f "$SERVICE"

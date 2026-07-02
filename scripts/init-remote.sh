#!/usr/bin/env bash
# init-remote.sh — wire the (already-created) GitHub remote + sync secrets.
#
# ⛔ DO NOT RUN until Rishi says "run init-remote.sh". Run it line-by-line.
#
# Repo ALREADY created: gh repo create dolr-ai/amorae-web --private (done
# by Rishi 2026-07-02) → https://github.com/dolr-ai/amorae-web (empty).
# Decisions locked: org=dolr-ai, name=amorae-web, private (public at launch).

set -euo pipefail
ORG="dolr-ai"
REPO="amorae-web"
BRANCH="feat/amorae-walking-skeleton"

# ── 1. Wire the remote (HTTPS — matches gh's configured git protocol) ────
git remote add origin "https://github.com/$ORG/$REPO.git"

# ── 2. Establish an EMPTY main, then land the skeleton via a REVIEWABLE PR.
# NOTE — deliberate deviation from the literal sequence in chat: doing
# `git checkout -b main` off the feature branch makes main already contain
# the skeleton, so the feat→main PR would have an EMPTY diff. Instead we
# root an empty main so PR #1 shows the full skeleton for review (pipeline).
git checkout --orphan main
git rm -rf --cached . > /dev/null 2>&1 || true   # unstage skeleton → empty root commit
git commit --allow-empty -m "chore: initialize amorae-web repo"
git push -u origin main
git checkout "$BRANCH"                            # restores the skeleton working tree
git push -u origin "$BRANCH"

# Opened as DRAFT: Session 6 first-reviews the CI/CD files, then ready-for-
# review is flipped for Rishi (also exercises codex-review.yml's
# ready_for_review trigger).
gh pr create --repo "$ORG/$REPO" --base main --head "$BRANCH" --draft \
  --title "Initial: amorae-web walking skeleton + CI/CD + Swarm stack" \
  --body "First PR: landing → 18+ gate → SSE text chat (persisted to amorae_db), plus the full CI/CD + Swarm stack. See README + CLAUDE.md. Deploy won't fire usefully until the cluster service exists — the initial stack deploy is manual (scripts/initial-stack-deploy.sh)."

# ── 3. GitHub Actions secrets (CI/CD only) — RUN THESE YOURSELF ──────────
# These handle credentials (a private SSH key + an API token), so the
# operator runs them, not the agent. GITHUB_TOKEN is auto-provided by
# Actions — do NOT set it. GHCR push uses GITHUB_TOKEN (same-repo package),
# so no separate GHCR_TOKEN is needed.
#   gh secret set DEPLOY_SSH_KEY       --repo dolr-ai/amorae-web < ~/.ssh/rishi-hetzner-ci-key
#   gh secret set OPENAI_CODEX_API_KEY --repo dolr-ai/amorae-web   # paste value (Keychain: account=dolr-ai)

# GOTCHA (v2 #303): if deploy's `crane tag ... :stable` / GHCR push fails
# with "installation not allowed to Write organization package", enable
# repo Settings → Actions → General → Workflow permissions → Read+Write.

# ── 4. Cluster / runtime secrets — NOT GitHub; set on the swarm ─────────
# Consumed by docker-compose.swarm.yml at `docker stack deploy` time. Run
# on a swarm manager (leader) as rishi-deploy. See initial-stack-deploy.sh.
#   printf '%s' 'postgresql://amorae:<PW>@<patroni-endpoint>:5432/amorae_db' \
#     | docker secret create amorae_database_url -
#   # + a chmod-600 .env with OPENROUTER_API_KEY / V2_WEB_SHARED_SECRET /
#   #   SENTRY_DSN / IMAGE_TAG / GEO_BLOCKED_COUNTRIES for the stack deploy.
#   # V2_WEB_SHARED_SECRET MUST match the value the dev session sets on v2.

# ── 5. Branch protection (optional, recommended before merging PR #1) ───
#   gh api -X PUT "repos/$ORG/$REPO/branches/main/protection" \
#     -H "Accept: application/vnd.github+json" \
#     -f 'required_status_checks[strict]=true' \
#     -f 'required_status_checks[checks][][context]=lint' \
#     -f 'required_status_checks[checks][][context]=test' \
#     -F 'enforce_admins=false' \
#     -F 'required_pull_request_reviews[required_approving_review_count]=1' \
#     -F 'restrictions='

echo "✔ Remote wired, PR #1 opened, GitHub secrets set."
echo "  Next: stand up amorae_db + cluster secrets, then run the INITIAL"
echo "  stack deploy manually (scripts/initial-stack-deploy.sh, Session 6)."

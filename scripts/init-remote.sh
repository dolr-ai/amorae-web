#!/usr/bin/env bash
# init-remote.sh — one-time GitHub remote creation + secret sync for amorae-web.
#
# ⛔ DO NOT RUN until Rishi says "create". This is a ready-to-run recipe,
#    not an automatic step. Run it line-by-line, not blindly.
#
# Decisions locked (Rishi 2026-07-02): org = dolr-ai, name = amorae-web.
# Prereqs: `gh auth status` shows dolr-ai access; the ci-key exists at
# ~/.ssh/rishi-hetzner-ci-key; amorae_db exists on Patroni (infra track).

set -euo pipefail
ORG="dolr-ai"
REPO="amorae-web"
BRANCH="feat/amorae-walking-skeleton"

# ── 1. Create the remote ────────────────────────────────────────────────
# Rishi picks --private or --public. Recommend --private for v1 (adult
# brand; go public only when the site is launch-ready). --no-* flags keep
# our local history as the source of truth (no auto-generated README/main).
gh repo create "$ORG/$REPO" --private --disable-wiki

# ── 2. Wire the remote + establish an empty main so the skeleton lands
#       via a REVIEWABLE PR (respects the pipeline — no direct-to-main). ──
git remote add origin "git@github.com:$ORG/$REPO.git"

git switch --orphan main-bootstrap
git commit --allow-empty -m "chore: initial commit"
git push -u origin main-bootstrap:main
git switch "$BRANCH"
git branch -D main-bootstrap

# Push the skeleton branch and open PR #1 (skeleton + CI) into main.
git push -u origin "$BRANCH"
gh pr create --repo "$ORG/$REPO" --base main --head "$BRANCH" \
  --title "amorae: walking skeleton + CI/CD + Swarm stack" \
  --body "First PR: landing → 18+ gate → text chat (amorae_db), plus the full CI/CD + Swarm stack. See README + CLAUDE.md. Deploy will not fire usefully until the cluster service is stood up (initial stack deploy is manual — see below)."

# ── 3. GitHub Actions secrets (CI/CD only) ──────────────────────────────
# GITHUB_TOKEN is auto-provided by Actions — do NOT set it. GHCR push uses
# GITHUB_TOKEN (same-repo package), so no separate GHCR_TOKEN is needed.
gh secret set DEPLOY_SSH_KEY      --repo "$ORG/$REPO" < ~/.ssh/rishi-hetzner-ci-key
gh secret set OPENAI_CODEX_API_KEY --repo "$ORG/$REPO"   # paste value (Keychain: account=dolr-ai)

# GOTCHA (from v2 #303): if deploy's `crane tag ... :stable` or GHCR push
# fails with "installation not allowed to Write organization package",
# enable it in repo Settings → Actions → General → Workflow permissions:
# "Read and write permissions". Also allow the org to accept the repo's
# GHCR package writes.

# ── 4. Cluster / runtime secrets (NOT GitHub — set on the swarm) ────────
# These are consumed by docker-compose.swarm.yml at `docker stack deploy`
# time, not by Actions. Run on a swarm manager (leader) as rishi-deploy.
#
#   # amorae_db DSN as a docker secret (mounted at /run/secrets/database_url):
#   printf '%s' 'postgresql://amorae:<PW>@<patroni-endpoint>:5432/amorae_db' \
#     | docker secret create amorae_database_url -
#
#   # Runtime env for the stack deploy — put in a chmod-600 .env on the
#   # manager, then `set -a; source .env; set +a; docker stack deploy ...`:
#   #   OPENROUTER_API_KEY=...     (same OpenRouter key as v2 user_chat_main_nsfw)
#   #   V2_WEB_SHARED_SECRET=...   (must match the value the dev session sets on v2)
#   #   SENTRY_DSN=...             (sentry.rishi.yral.com project for amorae)
#   #   IMAGE_TAG=<git-sha>        (the built image to run)
#   #   GEO_BLOCKED_COUNTRIES=     (empty = default OPEN)

# ── 5. Branch protection (optional, recommended before merging PR #1) ───
# Require CI to pass before merge; Codex is advisory (never a required check).
#   gh api -X PUT "repos/$ORG/$REPO/branches/main/protection" \
#     -H "Accept: application/vnd.github+json" \
#     -f 'required_status_checks[strict]=true' \
#     -f 'required_status_checks[checks][][context]=lint' \
#     -f 'required_status_checks[checks][][context]=test' \
#     -F 'enforce_admins=false' \
#     -F 'required_pull_request_reviews[required_approving_review_count]=1' \
#     -F 'restrictions='

echo "✔ Remote + PR #1 created, GitHub secrets set. Next: stand up amorae_db +"
echo "  the cluster secrets (step 4), then do the INITIAL stack deploy manually"
echo "  (docker stack deploy -c docker-compose.swarm.yml amorae) — after which"
echo "  deploy.yml's docker-service-update auto-deploys on every main merge."

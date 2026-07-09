# amorae-web

The **amorae.ai** adult-chat web surface for the YRAL AI influencer Tara.
A separate brand + separate service + separate database from YRAL/v2.

## Why this exists
NSFW chat can't live in the YRAL app (App/Play Store bans). The app keeps
Tara SFW and, when a user pushes for explicit content, she surfaces a link
to `amorae.ai/tara`. This site is where she chats freely. Isolating adult
content on a website the app stores don't review is the whole point.

Full design: `../yral-rishi-agent/docs/spicy-chat-gate-design-2026-06-28.md`
(20 locked decisions). This repo implements decision #17/#18/#20.

## Architecture
Mobile app (SFW, deflects) → link-out → **amorae.ai** (this service) →
`amorae_db` (own Patroni DB). One FastAPI service, server-rendered HTML.

- `app/config.py` — `_env()` module constants (mirrors v2).
- `app/database.py` — lazy asyncpg pool to **amorae_db ONLY**.
- `app/sessions.py` — our OWN httpOnly session + 18+ consent cookies.
- `app/models.py` — small Pydantic shapes.
- `app/templating.py` — shared Jinja2 instance.
- `app/routes/` — one file per surface (landing, gate, chat, legal, health).
- `app/services/` — llm (OpenRouter), v2_client (bridges), geo, personas.
- `app/repositories/` — one file per table (session, consent, conversation, message).
- `app/templates/`, `app/static/` — server-rendered UI (own Amorae brand).

## Level-2 isolation (HARD)
- Adult messages live in **`amorae_db` only** — NEVER `yral_agent_db`.
- This service has **no credentials** to `yral_agent_db`. The only link to
  YRAL is HTTP to v2 (`app/services/v2_client.py`): auth-handoff exchange,
  one-time SFW context READ, optional still-active ping. No adult text
  ever crosses those bridges.

## v2 contract (coordinate with dev session — don't invent)
- `POST /api/v1/spicy/handoff/exchange {ticket}` → identity. We NEVER
  accept a raw JWT in the URL — only the 60s single-use valet ticket (§4.7).
- `POST /api/v1/users/nsfw-consent` — per-account audit (best-effort).
- `GET /api/v1/spicy/context` — one-time SFW context seed (shape TODO with dev).

## Rules (inherited from YRAL fleet)
1. SYMMETRY — every route/repo file has the same shape.
2. Never touch chat-ai routes on rishi-1/2/3 (Rule 7).
3. Feature branches only; never push to main. PR → CI → Rishi "merge it" → deploy.
4. pg_dump-style care for `amorae_db` schema; additive migrations only.
5. Sentry → sentry.rishi.yral.com, never apm.yral.com.
6. Own brand identity — do NOT copy OnlyFans/Linkme logos/name/exact styling.
7. Text-only, FREE for v1. Voice = fast-follow; images = separate later call.
8. Geo-gate ships default-OPEN; restricting a region is a config flip.

## Deploy (same rishi-4/5 cluster)
- Swarm stack: `docker stack deploy -c docker-compose.swarm.yml amorae` →
  service `amorae_web` (2 replicas on rishi-4/5, `yral-v2-data-plane` overlay).
  First deploy is manual (`scripts/initial-stack-deploy.sh`); after that
  `deploy.yml` does `docker service update amorae_web` on every main merge.
- **Caddy (L1 edge + L2 swarm) is owned by Session 6**, via the Swarm
  CONFIGS pattern — NOT labels, NOT a bind-mounted `.caddy` file in this
  repo. Do not add Caddy config here.
- `amorae_db` is a SEPARATE database on the SAME Patroni cluster.
- Container listens on **8003** (fleet map: analytics 8001, mktg 8002).

## Local dev / skeleton test
`DEV_ALLOW_ANON=true` lets "Continue (18+)" open an anonymous session with
no ticket, so the skeleton is testable before v2's handoff endpoint exists.
**MUST be false in production.** See README for the docker smoke-test recipe.

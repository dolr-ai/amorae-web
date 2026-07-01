# amorae-web

The `amorae.ai` adult-chat web surface for Tara. Separate brand, separate
service, separate database (`amorae_db`) from YRAL/v2. See `CLAUDE.md` for
architecture and the design doc for the 20 locked decisions.

## Walking skeleton — what works today
`amorae.ai/tara` landing → **Continue (18+)** → text chat with Tara,
streamed from OpenRouter, persisted to `amorae_db`. Auth via the valet
ticket handoff (`?t=<ticket>`); `DEV_ALLOW_ANON` for local testing.

Surfaces: landing (`/{bot}`), gate (`POST /{bot}/continue`), chat page +
SSE (`/{bot}/chat`, `POST /{bot}/message`), legal (`/privacy`, `/terms`,
`/report`), `/health`.

## Local smoke test (Docker, isolated — touches nothing else)
```bash
docker network create amorae-smoke
docker run -d --name amorae-pg --network amorae-smoke \
  -e POSTGRES_DB=amorae_db -e POSTGRES_USER=amorae -e POSTGRES_PASSWORD=amorae postgres:16
# wait for ready, then:
docker exec -i amorae-pg psql -U amorae -d amorae_db < migrations/001_initial.sql
docker build -t amorae-web:smoke .
docker run -d --name amorae-app --network amorae-smoke -p 8099:8000 \
  -e DATABASE_URL="postgresql://amorae:amorae@amorae-pg:5432/amorae_db" \
  -e DEV_ALLOW_ANON=true -e COOKIE_SECURE=false \
  -e OPENROUTER_API_KEY="<real-key>" amorae-web:smoke
open http://localhost:8099/tara
# teardown:
docker rm -f amorae-app amorae-pg && docker network rm amorae-smoke
```

## Status
Walking skeleton complete + verified end-to-end (landing, gate, cookies,
SSE streaming, assistant persistence, Level-2 DB isolation). Not yet
deployed. Next: create GitHub remote + CI, wire the v2 contract with the
dev session, then polish the landing/chat UI.

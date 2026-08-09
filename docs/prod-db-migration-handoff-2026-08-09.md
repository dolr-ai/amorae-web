# Handoff: initialise prod amorae_db + fix amorae placement

**Date:** 2026-08-09
**For:** whoever owns the swarm cluster + amorae_db (Session 6 / infra)
**From:** amorae-web session
**Why:** enabling anonymous web chat surfaced that the prod `amorae_db` has no
schema, and that `amorae_web` has drifted onto the chat-AI prod nodes.

---

## 1. The finding

`amorae_db` in prod has **no tables**. The initial migration was never applied:

```
asyncpg.exceptions.UndefinedTableError: relation "web_sessions" does not exist
```

So chat, login sessions, consent records and message history have **never
worked in prod** — they were unreachable before (no session path), so it never
surfaced. It does now, because web chat is being turned on.

`migrations/001_initial.sql` creates 4 tables — `web_sessions`, `web_consent`,
`conversations`, `messages` — all `CREATE TABLE IF NOT EXISTS`, so applying it
is idempotent and safe on the empty DB. Nothing to snapshot (empty), but a
`pg_dump` first is fine if you prefer.

## 2. Apply the migration

`amorae_db` is reachable only over the `yral-v2-data-plane` overlay, and its DSN
is the Swarm secret `amorae_db_dsn_rw` (mounted in the `amorae_web` container at
`/run/secrets/amorae_db_dsn_rw`). The container has `asyncpg` + python, so the
cleanest apply uses the container itself — no extra image, DSN never printed:

```bash
# On a node currently running an amorae_web replica.
# Find one:  docker service ps amorae_web --filter desired-state=running --format '{{.Node}}'
CID=$(docker ps -qf name=amorae_web | head -1)

docker exec -i "$CID" python - < migrations/001_initial.sql <<'PY'
import asyncio, asyncpg, sys
sql = sys.stdin.read()
async def go():
    dsn = open("/run/secrets/amorae_db_dsn_rw").read().strip()
    conn = await asyncpg.connect(dsn)
    await conn.execute(sql)
    await conn.close()
    print("amorae_db migration applied")
asyncio.run(go())
PY
```

> Note: the heredoc above pipes the python runner while `< migrations/001_initial.sql`
> feeds the SQL on stdin — run it from the repo root so the SQL path resolves.
> If simpler, `docker exec -i "$CID" psql "$(docker exec "$CID" cat /run/secrets/amorae_db_dsn_rw)" -f -`
> only works if psql is in the image (it is NOT — python is the reliable path).

**Verify:**

```bash
docker exec "$CID" python -c "
import asyncio, asyncpg
async def go():
    dsn=open('/run/secrets/amorae_db_dsn_rw').read().strip()
    c=await asyncpg.connect(dsn)
    print(await c.fetch(\"select tablename from pg_tables where schemaname='public' order by 1\"))
    await c.close()
asyncio.run(go())"
# expect: conversations, messages, web_consent, web_sessions
```

## 3. Fix the placement (arguably more urgent than chat)

`amorae_web` is currently running on **rishi-1/2 — the chat-AI PROD nodes**. The
compose constraint only excluded rishi-6, so a rolling restart let it drift onto
the chat-AI nodes (the exact Rule-7 risk). A PR now pins it to rishi-4/5:

```yaml
constraints:
  - node.hostname != rishi-6   # analytics
  - node.hostname != rishi-1   # chat-AI prod
  - node.hostname != rishi-2   # chat-AI prod
  - node.hostname != rishi-3   # chat-AI prod
```

Applying it re-schedules amorae onto rishi-4/5.

## 4. Deploy ordering (so chat doesn't 500)

The merged compose has `ALLOW_ANON_CHAT: "true"`. Chat 500s if that's on before
the schema exists, so order matters:

1. **Apply the migration** (step 2) — schema exists.
2. **Merge the placement PR**, then `docker stack deploy -c docker-compose.swarm.yml amorae`
   — this pins to rishi-4/5 AND enables anon chat in one go.
3. Tell the amorae-web session; it will verify the full chat flow end-to-end
   (start-chat → age gate → anon session → chat page 200) and that Tara replies.

(The amorae-web session already reverted the standalone `--env-add ALLOW_ANON_CHAT`,
so chat is currently a soft redirect, not a 500. Nothing is broken meanwhile.)

## 5. Security — rotate the OpenRouter key

While inspecting the service env, the live `OPENROUTER_API_KEY` (a real
`sk-or-v1-…` value) was printed into a session log. **Rotate it** and re-set the
secret/env. It's the chat LLM key, so rotating it is low-blast-radius (update
the value, redeploy).

---

## TL;DR

1. Run the migration (step 2) — safe, idempotent, empty DB.
2. Merge placement PR + `docker stack deploy` — pins to rishi-4/5 and enables chat.
3. Rotate the OpenRouter key.
4. Ping amorae-web to verify chat end-to-end.

# amorae-web ⇄ yral-rishi-agent — data-layer contract (one backend)

**Date:** 2026-08-09
**Status:** agreed decisions; contract to build against
**Owners:** amorae-web (consumes) · developer/backend session (provides) · Session-6 (ops)

The shared shape so all sessions build to the same thing. amorae-web keeps its
**frontend** (feed, profiles, subscribe, CCBill surface) and swaps its **data
layer** to consume `yral-rishi-agent` + the shared `ai_influencers` catalog.
`amorae_db` is abandoned; amorae-web becomes a stateless frontend.

---

## 1. The `surface` column (web/mobile split)

`ai_influencers.surface` — enum **`web` | `mobile` | `both`**.

- **Default `mobile`.** Critical: the ~3,800 existing influencers must not
  appear on the adult web surface. Web is explicit opt-in.
- Exposed as a **field on the influencers API response**, and **filtered
  server-side** the same way the US-market flag is — one shared helper.
- amorae-web always requests the **web** surface → backend returns
  `surface IN ('web','both')`.
- The backend session **sets the web personas** (Tara, etc.) to `web`/`both`.

**Owner:** developer/backend session (add column + default + filter + flag
personas), alongside the market-filter work so it's one mechanism.

## 2. Catalog — personas from `ai_influencers`

amorae-web replaces hardcoded `services/personas.py` with a client over the
existing influencers API (verified live):

```
GET {V2_BASE_URL}/api/v1/influencers?surface=web   (contract: web-filtered)
  -> { influencers: [ { id, name, display_name, avatar_url, description,
                        category, system_prompt, … , surface } ],
       total, limit, offset }
```

amorae-web maps each influencer → its persona/profile shape (handle, display
name, avatar, bio/tagline, system prompt). **Open items to confirm with the
backend:** subscription price + any adult-specific fields (bio/tagline copy) —
are those on `ai_influencers`, or amorae-side presentation config?

**Blocked on:** the `surface` column existing (§1).

## 3. Feed — real videos for web-surface influencers

The homepage feed shows videos published by web-surface influencers. Sources:
the video service (`recommend-with-metadata`) + the servable-video lookup.

**Blocked on:** Saikat's auth/metadata changes settling (username→principal
lookup currently returns blank; media-index post_id/publisher NULL — catalogue
is ClickHouse `video_unique_v2`). Coordinate timing with Session-6 — do NOT
build against the moving target.

## 4. Chat — via agent v2 chat API

Chat runs through `yral-rishi-agent`'s chat API, not a separate amorae path:

```
POST /api/v1/chat/conversations                      (create)
POST /api/v1/chat/conversations/{id}/messages/stream (send, SSE)
GET  /api/v1/chat/conversations/{id}/messages        (history)
```

- Anonymous-capable (endpoints declare no auth; YRAL supports anonymous
  accounts). amorae-web's 18+ gate cookie stays amorae-side.
- **Level-2 isolation is intentionally set aside** for the experiment (the
  store rule is about the app, not the backend DB). Split to a dedicated amorae
  backend only if amorae scales.
- This **deletes amorae-web's DB layer** (`database.py`, `repositories/`, the
  `amorae_db_dsn_rw` secret) once chat is migrated.

**Open items to confirm with the developer session:** how a web-anon chat
session maps to a v2 conversation (guest identity?), and how the adult persona
system prompt is selected (does `ai_influencers.system_prompt` carry the
unconstrained web variant, or is that amorae-side?).

**Blocked on:** the developer session's v2 chat integration for the web surface.

## 5. What amorae-web deletes once the rewire lands

`app/database.py`, `app/repositories/*`, `app/data/mock_feed.json`, the
hardcoded catalog in `services/personas.py`, the `amorae_db_dsn_rw` secret, and
the DB env/health wiring. amorae-web = stateless frontend over v2 APIs.

## 6. Sequencing (small reviewed PRs)

| PR | What | Unblocks on |
|---|---|---|
| 1 | Catalog client → personas from `ai_influencers` (web-filtered) | §1 surface column |
| 2 | Feed → real web-surface videos | §3 Saikat/metadata |
| 3 | Chat → v2 chat API; delete amorae_db layer | §4 developer session |

Until each lands, the current hardcoded personas + `mock_feed.json` stay, marked
**TEMPORARY** (a startup WARNING log + code banners — see this PR), never buried.

## 7. Operating rules (this session)

Code + PRs only; all prod ops (docker service, stack deploy, migrations, schema)
→ Session-6. Never print secrets. Never schedule on rishi-1/2/3.

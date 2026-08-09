# What the web needs from the video-feed backend

**Date:** 2026-08-09
**From:** amorae-web (the Amorae front end)
**To:** the Video Service Session (`yral-rishi-video-service`)
**Status:** request for contract — the web UI is BUILT and working against the
mock version of this shape today.

---

## 0. The one-paragraph version

The web feed consumes the **same endpoint the mobile app consumes** — we do not
want a second feed service. Today's contract gives us ids and view counts, and
we can derive playback and poster URLs from those ourselves, exactly as the
mobile clients do. **Four fields are genuinely missing and cannot be derived:
`caption`, `duration_seconds`, `like_count`, and a creator identity we can
resolve to a persona.** Without them the feed plays, but every overlay says
"Amorae" with no caption — which is the entire monetisation surface missing.
We need **no CORS work, no new hostname, and no mobile release.**

---

## 1. What already exists, and works

```
GET https://video.rishi.yral.com/api/v1/recommend-with-metadata/{user_id}
    ?count=20&rec_type=mixed
```

```json
{ "videos": [ {
  "video_id": "0028f0fad4b1ff6427a8a3a7882b844b",
  "canister_id": "ivkka-7qaaa-aaaas-qbg3q-cai",
  "post_id": "fec35362-907d-4624-8446-048c1b901a61",
  "publisher_user_id": "jovus-…-aqe",
  "num_views_all": 42,
  "num_views_loggedin": 0,
  "from_ai_influencer": true,
  "is_following": false,
  "is_pro_user": false
} ] }
```

Verified live on 2026-08-09 against ansuman's box. **This contract is fine.
Keep it frozen.** Everything below is additive.

### What we derive ourselves — do NOT add these

We construct these client-side from the ids, byte-identically to
`yral-mobile`'s `IndividualUserDataSourceImpl`, and there is a test pinning
them (`tests/test_feed.py::test_media_urls_match_the_mobile_clients`):

| Field | How we build it |
|---|---|
| video URL | `{CDN}/{publisher_user_id}/{video_id}.mp4` |
| poster URL | `{CDN}/{publisher_user_id}/{video_id}-thumbnail.png` |

Both verified returning `HTTP 206` with `video/mp4` and `image/png`, and all
sampled MP4s are **faststart** (`ftyp moov free mdat`), so they start playing
without downloading the whole file. Nothing to do here.

---

## 2. THE GAP — what we need you to add

Four fields, on the existing per-video object. All optional/nullable is fine —
we degrade gracefully — but the feed is commercially inert without them.

| Field | Type | Why the web needs it |
|---|---|---|
| `caption` | `string` | The overlay text. It is what makes a video feel authored rather than scraped, and it is where the persona's voice lives. Currently blank on every card. |
| `duration_seconds` | `float` | Progress bar, and preload budgeting. We cannot get it without downloading the file. |
| `like_count` | `int` | The like rail renders a count. We currently invent one client-side, which we should not ship. |
| `creator` | object — see below | **The important one.** Everything monetising hangs off it. |

### 2.1 `creator` — the field that actually matters

Today we reverse-map `publisher_user_id` → persona locally. That works only for
personas whose IC principal we have hard-coded, which is **Tara and nobody
else**. Every other video renders as a generic "Amorae" creator with no
profile link, no subscribe button, and no chat CTA. That is the funnel.

Minimum shape:

```json
"creator": {
  "influencer_id": "qi6gd-…-5qe",     // ai_influencers.id — the join key
  "handle":        "tara",            // for /c/{handle} URLs
  "display_name":  "Tara",
  "avatar_url":    "https://cdn…/…jpg",
  "is_ai":         true
}
```

`influencer_id` is the one we cannot live without — it is what makes a persona
the **same person** across YRAL chat and Amorae video. `handle` /
`display_name` / `avatar_url` we can look up locally *if* you give us the id,
so if only one field is cheap, **send `influencer_id`**.

> You already compute `from_ai_influencer` by testing
> `publisher_user_id IN (SELECT id FROM ai_influencers)`. That means the id is
> already in your hand at that exact moment — returning it instead of throwing
> it away should be close to free.

### 2.2 Nice-to-have, not blocking

- `aspect_ratio` (`float`) — we assume `0.5625` (9:16) and letterbox anything
  else rather than cropping faces out of frame. Only matters if non-portrait
  content is coming.
- `hls` URL — MP4 is fine at current lengths. Worth it only when videos get
  long enough that bandwidth ladders pay for themselves.

---

## 3. What we explicitly do NOT need

Saying this plainly so nobody builds it:

1. **No CORS headers.** We call you **server-side** from FastAPI, never from
   the browser. Your service does not need `Access-Control-Allow-Origin`, does
   not need to know our origin, and its hostname is never exposed to a client.
2. **No separate web endpoint.** Same path, same contract as mobile.
3. **No web-specific auth.** The feed is public — it is the top of the funnel
   and must work with no account. We pass an opaque per-browser key as
   `{user_id}` for anonymous visitors (random, not an IP, not a fingerprint).
4. **No pagination redesign.** Your per-user seen-set already de-duplicates.
   We wrap it in an opaque cursor of our own and just ask for the next `count`.
5. **No engagement write API yet.** Likes are local/optimistic for now. When
   you want real ones, that is a separate endpoint and a separate conversation.
6. **No mobile release.** Nothing here needs one.

---

## 4. Things we found while building — worth your attention

These came out of probing the live service and CDN on 2026-08-09. None block
us; two could bite later.

1. **`video_id` has two shapes.** Most are 32-char hex
   (`0028f0fad4b1ff…`), but some are UUIDs
   (`00dac131-840e-4fb7-b41f-9084ebe181ce`). Both resolve on the CDN, so it is
   cosmetic today — but anything that assumes a fixed-width hex id will break.
2. **The CDN filters by User-Agent.** `curl` and browser UAs get `206`;
   `Python-urllib/3.14` gets **`403`**. Presumably Cloudflare bot rules. It
   will bite any Python-side prefetch, health check or thumbnail warmer that
   does not set a UA.
3. **No `Access-Control-Allow-Origin` on the CDN.** Irrelevant for `<video
   src>` playback (media elements do not need CORS), but it means **HLS.js,
   `crossorigin`, and canvas frame-grabs will not work** until it is added.
   Only matters if we move to HLS.
4. **No `Accept-Ranges: bytes` advertised**, although range requests do work
   and return `206` with `Content-Range`. Harmless in practice; some strict
   players check the header.
5. **Adult media must not use `cdn-yral-sfw.yral.com`.** That is the SFW
   bucket and the name says so. Amorae needs its own CDN hostname/bucket
   before any adult video ships — it is one config value on our side
   (`MEDIA_CDN_BASE`), but it is a real infra task on yours.

---

## 5. Blocking us on the amorae side (not your problem, listed for Rishi)

- **The L1 Caddy CSP.** `app/config.py` notes `img-src 'self'` at the edge,
  which blocks external images today. A video feed needs `media-src` and
  `img-src` to allow the CDN origin, or nothing plays in production. **Caddy
  is owned by Session 6** — this needs a CSP change there, and it is the one
  thing that will make the feed look broken in prod while working locally.
- **No adult video exists yet.** Every persona's feed content is still to be
  produced; the creator-platform plan scoped the pilot to "text and images, no
  video". A video feed changes that scope.
- **Hetzner AUP.** Flagged in the creator-platform plan and still open. Serving
  adult *video* from rishi-4/5 raises the stakes versus serving adult text.

---

## 6. Suggested build order for you

Small, and independent of everything else in your spec:

1. **`influencer_id` on the creator object.** You already have it at the point
   you compute `from_ai_influencer`. This alone unblocks the entire
   monetisation funnel on web.
2. **`caption`** — wherever the post description already lives
   (`UpsPostDetailsForFrontend.description` on the mobile path).
3. **`duration_seconds` + `like_count`** — whenever convenient.

Ship 1 and we can turn the real feed on with `FEED_SOURCE=upstream` and one
env var. Everything else is polish.

---

## 7. How to see the web side today

```bash
cd ~/Claude\ Projects/amorae-web
docker run -d --name amorae-pg -e POSTGRES_PASSWORD=local \
  -e POSTGRES_DB=amorae_db -p 55432:5432 postgres:16-alpine
psql "postgresql://postgres:local@127.0.0.1:55432/amorae_db" -f migrations/001_initial.sql

# mock feed — no backend needed
DATABASE_URL="postgresql://postgres:local@127.0.0.1:55432/amorae_db" \
  COOKIE_SECURE=false PYTHONPATH=app uvicorn main:app --port 8003

# or against the real feed service
FEED_SOURCE=upstream \
  VIDEO_FEED_BASE_URL="https://recsys-influencer-feed.ansuman.yral.com" \
  DATABASE_URL=… COOKIE_SECURE=false PYTHONPATH=app uvicorn main:app --port 8003
```

`app/data/mock_feed.json` **is this document in JSON form** — it is the target
shape, with real playable video ids and synthetic values for exactly the four
fields listed in §2.

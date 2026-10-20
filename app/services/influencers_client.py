"""Reads the shared `ai_influencers` catalogue from yral-rishi-agent, filtered
to the web surface.

    GET {V2_BASE_URL}/api/v1/influencers?surface=web
    -> { influencers: [ {id, display_name, avatar_url, surface, ...} ], total }

`surface=web` returns `surface IN ('web','both')` server-side (default `mobile`,
so nothing mainstream leaks onto the adult surface). Verified live 2026-08-12:
returns exactly Tara today.

The catalogue changes rarely and every page needs it, so we cache the raw list
in-memory and refresh on a TTL (a background loop, started in the app lifespan)
rather than calling v2 per request. If v2 is briefly unavailable the last-good
snapshot is kept; on a cold start with v2 down, `personas` falls back to its own
presentation config so the site still renders.

This module owns only WHO exists (identity from the catalogue). Presentation —
handle, price, adult bio/tagline, images — stays amorae-side in `personas.py`
(the catalogue's response formatter is shared with the mainstream app, so adult
copy must never be written there).
"""

import asyncio
import logging
import time

import httpx

import config

logger = logging.getLogger(__name__)

_WEB_SURFACE = "web"  # asks v2 for surface IN ('web','both')

# Last-good raw catalogue snapshot (web-filtered) + when it was fetched.
_snapshot: list[dict] = []
_fetched_at: float = 0.0


def snapshot() -> list[dict]:
    """The cached web-surface influencers (raw catalogue dicts). Sync — callers
    read this without awaiting. Empty until the first successful refresh."""
    return _snapshot


def is_ready() -> bool:
    return _fetched_at > 0.0


async def refresh() -> bool:
    """Fetch the web-surface catalogue and replace the snapshot. Returns True on
    success. On failure the previous snapshot is kept (never blanked)."""
    global _snapshot, _fetched_at
    url = f"{config.V2_BASE_URL.rstrip('/')}/api/v1/influencers"
    try:
        async with httpx.AsyncClient(timeout=config.V2_TIMEOUT) as client:
            resp = await client.get(url, params={"surface": _WEB_SURFACE})
            resp.raise_for_status()
            influencers = resp.json().get("influencers", [])
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("influencers catalogue refresh failed (keeping snapshot): %s", e)
        return False

    _snapshot = influencers
    _fetched_at = time.time()
    logger.info(
        "influencers catalogue refreshed: %d web-surface personas", len(influencers)
    )
    return True


async def run_refresh_loop() -> None:
    """Refresh now, then every TTL. Started as a background task in the app
    lifespan; cancelled on shutdown."""
    while True:
        await refresh()
        await asyncio.sleep(config.INFLUENCERS_CACHE_TTL_SECONDS)

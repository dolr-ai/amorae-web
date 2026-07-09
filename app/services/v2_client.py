"""Bridges to v2 (yral-rishi-agent). The ONLY link between amorae and YRAL.

Three calls, all server-to-server with a web-scoped shared secret — the
native JWT never reaches this domain (§4.7). No adult text ever crosses
these bridges: we only READ SFW context and WRITE a consent audit row.

CONTRACT NOTE — coordinate with the dev session before relying on exact
shapes. These match design §4.7 / §4.2; the context-read shape in
particular still needs dev-session confirmation (marked TODO).
"""

import logging

import httpx

import config
from models import HandoffIdentity

logger = logging.getLogger(__name__)


def _auth_headers() -> dict:
    # Web-scoped secret identifies amorae to v2 server-to-server.
    return {"X-Amorae-Secret": config.V2_WEB_SHARED_SECRET}


async def exchange_ticket(ticket: str) -> HandoffIdentity | None:
    """POST /api/v1/spicy/handoff/exchange {ticket} → identity.

    v2 validates the 60s single-use Redis ticket, marks it consumed, and
    returns the bound identity. Returns None on any failure (expired,
    already-used, network) so the gate can fall back cleanly.
    """
    url = f"{config.V2_BASE_URL.rstrip('/')}/api/v1/spicy/handoff/exchange"
    try:
        async with httpx.AsyncClient(timeout=config.V2_TIMEOUT) as client:
            resp = await client.post(
                url, headers=_auth_headers(), json={"ticket": ticket}
            )
        resp.raise_for_status()
        data = resp.json()
        return HandoffIdentity(
            user_id=data["user_id"],
            bot_handle=data.get("bot_handle"),
            is_anonymous=bool(data.get("is_anonymous", False)),
        )
    except Exception as e:
        logger.warning("handoff exchange failed: %s", e)
        return None


async def write_consent_audit(user_id: str, source_ip: str | None) -> bool:
    """POST /api/v1/users/nsfw-consent — per-account audit row in v2.

    Best-effort: the web cookie + web_consent row are the live gate; this
    is the cross-device account record. A v2 outage must not block the
    gate, so failures are logged and swallowed.
    """
    url = f"{config.V2_BASE_URL.rstrip('/')}/api/v1/users/nsfw-consent"
    try:
        async with httpx.AsyncClient(timeout=config.V2_TIMEOUT) as client:
            resp = await client.post(
                url,
                headers=_auth_headers(),
                json={
                    "user_id": user_id,
                    "source_ip": source_ip,
                    "surface": "web_spicy",
                },
            )
        resp.raise_for_status()
        return True
    except Exception as e:
        logger.warning("v2 consent audit write failed (non-fatal): %s", e)
        return False


async def read_recent_context(user_id: str, bot_handle: str) -> list[dict]:
    """One-time READ of the user's recent SFW app messages so web-Tara
    "remembers" (§4.2). Read-only; we never write adult text back.

    Returns a list of {"role", "content"} dicts (oldest first), or [] on
    failure so context-seeding degrades gracefully.

    TODO(dev-session): confirm the exact endpoint path + response shape.
    Assumed: GET /api/v1/spicy/context?user_id=&bot_handle=&limit=
    → {"messages": [{"role": "...", "content": "..."}]}.
    """
    url = f"{config.V2_BASE_URL.rstrip('/')}/api/v1/spicy/context"
    params = {
        "user_id": user_id,
        "bot_handle": bot_handle,
        "limit": config.CONTEXT_SEED_WINDOW,
    }
    try:
        async with httpx.AsyncClient(timeout=config.V2_TIMEOUT) as client:
            resp = await client.get(url, headers=_auth_headers(), params=params)
        resp.raise_for_status()
        msgs = resp.json().get("messages") or []
        return [{"role": m["role"], "content": m["content"]} for m in msgs]
    except Exception as e:
        logger.info("context seed read skipped (non-fatal): %s", e)
        return []

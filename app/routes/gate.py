"""The 18+ gate — POST /{bot_handle}/continue.

"Continue (18+)" is where login is required (decision #8). Flow:
  1. resolve identity from the valet ticket (§4.7) — v2 server-to-server;
  2. mint amorae's OWN session + set httpOnly cookies (session + consent);
  3. record the 18+ audit (web_consent locally + best-effort v2 per-account);
  4. redirect into the web chat.

No raw JWT is ever accepted here — only the one-time ticket.
"""

import logging

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse

import config
from services import personas, geo, v2_client
from repositories import session_repo, consent_repo
from sessions import new_session_id, set_session_cookie, set_consent_cookie

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/{bot_handle}/continue")
async def continue_18plus(request: Request, bot_handle: str, ticket: str = Form("")):
    bot = personas.get(bot_handle)
    if not bot:
        raise HTTPException(status_code=404, detail="Not found")
    if geo.is_blocked(request):
        raise HTTPException(status_code=451, detail="Unavailable in your region")

    user_id: str | None = None
    is_anonymous = False

    if ticket:
        identity = await v2_client.exchange_ticket(ticket)
        if identity is None:
            # Ticket expired / already used → back to landing to re-tap.
            return RedirectResponse(url=f"/{bot['handle']}?e=expired", status_code=303)
        user_id = identity.user_id
        is_anonymous = identity.is_anonymous
    elif config.DEV_ALLOW_ANON:
        is_anonymous = True  # skeleton-only path; disabled in prod
    else:
        # No ticket and anon disabled → must come in via the app link.
        return RedirectResponse(url=f"/{bot['handle']}?e=login", status_code=303)

    session_id = new_session_id()
    await session_repo.create(
        session_id,
        user_id=user_id,
        is_anonymous=is_anonymous,
        bot_handle=bot["handle"],
    )

    source_ip = request.client.host if request.client else None
    await consent_repo.record(
        session_id,
        user_id=user_id,
        bot_handle=bot["handle"],
        source_ip=source_ip,
        user_agent=request.headers.get("user-agent"),
    )
    # Cross-device per-account audit in v2 (best-effort, never blocks).
    if user_id and not is_anonymous:
        await v2_client.write_consent_audit(user_id, source_ip)

    response = RedirectResponse(url=f"/{bot['handle']}/chat", status_code=303)
    set_session_cookie(response, session_id)
    set_consent_cookie(response)
    return response

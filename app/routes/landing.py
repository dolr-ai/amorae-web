"""Landing page — amorae.ai/{bot_handle}.

Linkme/OnlyFans-style PATTERN (own brand identity — Risk 6): hero, name +
handle, a "Mature Content Disclaimer → Continue (18+)" card, footer
Privacy | Terms | Report. Anonymous visitors may VIEW this; login is
required only at "Continue (18+)" (decision #8).
"""

from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

from services import personas, geo
from sessions import current_session, has_consent
from templating import templates

router = APIRouter()


@router.get("/{bot_handle}", response_class=HTMLResponse)
async def landing(request: Request, bot_handle: str, t: str | None = None):
    bot = personas.get(bot_handle)
    if not bot:
        raise HTTPException(status_code=404, detail="Not found")

    if geo.is_blocked(request):
        return templates.TemplateResponse(
            "blocked.html", {"request": request, "bot": bot}, status_code=451
        )

    # Already through the gate this session → straight to chat.
    session = await current_session(request)
    if session and has_consent(request):
        return RedirectResponse(url=f"/{bot['handle']}/chat", status_code=303)

    # `t` = the one-time valet ticket handed off by the app (§4.7). Held
    # on the page and submitted with the Continue (18+) form so identity
    # resolves at the moment of consent, not on mere page view.
    return templates.TemplateResponse(
        "landing.html",
        {"request": request, "bot": bot, "ticket": t or ""},
    )

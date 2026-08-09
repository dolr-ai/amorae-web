"""The homepage — a full-screen vertical video feed, PUBLIC.

    GET  /                → the feed page (18+ interstitial if not passed)
    GET  /api/v1/feed     → one page of videos as JSON

This is the top of the funnel. It must work for someone who has never heard
of us, arriving from a social post, with no account: TikTok-style discovery
→ tap a creator → her profile → subscribe / chat. The only wall before the
feed is the 18+ gate, which is a legal requirement rather than a signup.
"""

import secrets

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse

import config
from models import FeedPage
from services import age_gate, feed_client, geo, personas
from sessions import current_session
from templating import templates

router = APIRouter()

# Identifies an anonymous browser to the feed service so the ranking is
# stable and non-repeating between page loads. Random per browser — never an
# IP, never a fingerprint — so it carries no personal data and a user can
# reset it by clearing cookies.
FEED_KEY_COOKIE = "amorae_feed_key"


def _feed_key(request: Request, user_id: str | None) -> str:
    if user_id:
        return user_id
    return request.cookies.get(FEED_KEY_COOKIE) or f"anon-{secrets.token_hex(8)}"


def _set_feed_key(response, feed_key: str) -> None:
    response.set_cookie(
        FEED_KEY_COOKIE,
        feed_key,
        httponly=True,
        secure=config.COOKIE_SECURE,
        samesite="lax",
        max_age=365 * 86400,
        path="/",
    )


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    if geo.is_blocked(request):
        return templates.TemplateResponse(
            "blocked.html", {"request": request, "bot": None}, status_code=451
        )

    # The gate renders INSTEAD of the feed, not on top of it — no feed markup
    # or media URL reaches a browser that has not confirmed 18+.
    if not age_gate.has_passed(request):
        return templates.TemplateResponse(
            "age_gate.html",
            {
                "request": request,
                "next": "/",
                "method": age_gate.required_method(request),
                "brand": config.BRAND_NAME,
            },
        )

    session = await current_session(request)
    feed_key = _feed_key(request, session.user_id if session else None)

    # Server-render the first page so the first video paints without waiting
    # on a round trip. The client takes over paging from `next_cursor`.
    page = await feed_client.get_page(
        feed_key, cursor=None, limit=config.FEED_PAGE_SIZE
    )

    response = templates.TemplateResponse(
        "feed.html",
        {
            "request": request,
            "page": page,
            "creators": personas.all_personas(),
            "is_logged_in": session is not None,
            "brand": config.BRAND_NAME,
        },
    )
    _set_feed_key(response, feed_key)
    return response


@router.get("/api/v1/feed")
async def feed_api(
    request: Request, cursor: str | None = None, limit: int | None = None
):
    """Paging for the infinite scroll.

    403 rather than an empty list when the gate has not been passed, so the
    client can send the user back to the interstitial instead of silently
    rendering nothing.
    """
    if geo.is_blocked(request):
        return JSONResponse({"error": "region_unavailable"}, status_code=451)
    if not age_gate.has_passed(request):
        return JSONResponse({"error": "age_gate_required"}, status_code=403)

    session = await current_session(request)
    feed_key = _feed_key(request, session.user_id if session else None)
    page: FeedPage = await feed_client.get_page(
        feed_key, cursor=cursor, limit=limit or config.FEED_PAGE_SIZE
    )

    response = JSONResponse(page.model_dump())
    _set_feed_key(response, feed_key)
    return response

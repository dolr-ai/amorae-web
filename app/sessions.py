"""Web session + cookie handling. The httpOnly session cookie is amorae's
OWN credential — the native YRAL JWT never reaches this domain (§4.7)."""

import secrets

from fastapi import Request, Response, HTTPException

import config
from models import WebSession
from repositories import session_repo


def new_session_id() -> str:
    return secrets.token_urlsafe(32)


def _cookie_kwargs(max_age: int) -> dict:
    kwargs = {
        "httponly": True,
        "secure": config.COOKIE_SECURE,
        "samesite": "lax",
        "max_age": max_age,
        "path": "/",
    }
    if config.COOKIE_DOMAIN:
        kwargs["domain"] = config.COOKIE_DOMAIN
    return kwargs


def set_session_cookie(response: Response, session_id: str) -> None:
    response.set_cookie(
        config.SESSION_COOKIE_NAME,
        session_id,
        **_cookie_kwargs(config.SESSION_TTL_DAYS * 86400),
    )


def set_consent_cookie(response: Response) -> None:
    response.set_cookie(
        config.CONSENT_COOKIE_NAME,
        "1",
        **_cookie_kwargs(config.CONSENT_TTL_DAYS * 86400),
    )


def has_consent(request: Request) -> bool:
    return request.cookies.get(config.CONSENT_COOKIE_NAME) == "1"


async def current_session(request: Request) -> WebSession | None:
    session_id = request.cookies.get(config.SESSION_COOKIE_NAME)
    if not session_id:
        return None
    row = await session_repo.get(session_id)
    if not row:
        return None
    return WebSession(**row)


async def require_session(request: Request) -> WebSession:
    """Dependency for the chat surface — a valid session AND 18+ consent."""
    session = await current_session(request)
    if not session:
        raise HTTPException(status_code=401, detail="No session")
    if not has_consent(request):
        raise HTTPException(status_code=403, detail="18+ consent required")
    return session

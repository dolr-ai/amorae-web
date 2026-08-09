"""Age assurance for the PUBLIC surface.

Two things are deliberately separated here, because conflating them is what
would break the funnel:

  * **Age assurance** — "is this person 18+". Required to see ANY adult
    content, including the homepage feed. Costs nothing, needs no account.
  * **Authentication** — "who is this person". Required only to interact:
    chat, subscribe, tip. Lives in `sessions.py` / `routes/gate.py`.

The walking skeleton fused them: the only way past the 18+ wall was a
logged-in valet ticket. That is correct for the chat surface and fatal for a
discovery feed, which has to be browsable by a stranger who arrived from a
social post. So the gate below is cookie-only and account-free.

`AGE_ASSURANCE_MODE` is the seam for a real verifier. Today it is
`attestation` (the user declares 18+, which is what most of the world still
allows). Setting it to `provider` — or listing a country in
`AGE_VERIFICATION_COUNTRIES` — makes `required_method()` return "provider",
which is the branch a vendor (Persona, Yoti, VerifyMy, k-ID) slots into. The
UK Online Safety Act and ~20 US states already demand that; Canada, the
launch market, does not.
"""

from fastapi import Request, Response

import config
from services import geo

# Method names are persisted in the consent audit, so treat them as stable
# values rather than free text.
METHOD_ATTESTATION = "attestation"
METHOD_PROVIDER = "provider"


def required_method(request: Request) -> str:
    """Which standard of proof this visitor's jurisdiction demands."""
    if config.AGE_ASSURANCE_MODE == METHOD_PROVIDER:
        return METHOD_PROVIDER
    country = geo.client_country(request)
    if country and country in config.AGE_VERIFICATION_COUNTRIES:
        return METHOD_PROVIDER
    return METHOD_ATTESTATION


def has_passed(request: Request) -> bool:
    """True when this browser has already cleared the gate.

    Reads the SAME cookie the logged-in chat gate sets, so a user who came in
    through the app handoff is never asked twice.
    """
    return request.cookies.get(config.CONSENT_COOKIE_NAME) == "1"


def grant(response: Response) -> None:
    """Record that this browser cleared the gate.

    Cookie-only and httpOnly: no account, no database row for an anonymous
    browser. The per-account audit trail (`consent_repo`, and v2's
    cross-device record) is still written at login, where there is an
    identity worth attaching it to.
    """
    kwargs = {
        "httponly": True,
        "secure": config.COOKIE_SECURE,
        "samesite": "lax",
        "max_age": config.CONSENT_TTL_DAYS * 86400,
        "path": "/",
    }
    if config.COOKIE_DOMAIN:
        kwargs["domain"] = config.COOKIE_DOMAIN
    response.set_cookie(config.CONSENT_COOKIE_NAME, "1", **kwargs)


def safe_next(raw: str | None) -> str:
    r"""Sanitise the post-gate redirect target.

    An open redirect on an age gate is worth real money to an affiliate
    spammer, so only same-origin absolute paths survive. `//evil.com` is a
    protocol-relative URL, and several browsers fold a backslash into a
    forward slash — so `/\evil.com` is the same attack wearing a hat. Both
    are rejected rather than relying on the URL layer to encode them.
    """
    if not raw or not raw.startswith("/"):
        return "/"
    if raw.startswith("//") or "\\" in raw:
        return "/"
    return raw

"""The public 18+ gate — POST /age-gate.

Distinct from `routes/gate.py`, and the distinction is the point:

  * **here**  — anonymous age assurance, no account, unlocks BROWSING
    (the homepage feed, creator profiles, previews).
  * **gate.py** — the logged-in "Continue (18+)" that resolves a valet
    ticket into an amorae session and unlocks INTERACTION (chat, subscribe).

Both set the same consent cookie, so passing either satisfies the other and
nobody is asked their age twice.
"""

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse

import config
from services import age_gate, geo
from templating import templates

router = APIRouter()


@router.post("/age-gate")
async def confirm_age(
    request: Request,
    confirm: str = Form(""),
    next: str = Form("/"),
):
    if geo.is_blocked(request):
        return templates.TemplateResponse(
            "blocked.html", {"request": request, "bot": None}, status_code=451
        )

    destination = age_gate.safe_next(next)

    # A jurisdiction that requires a real verifier must not be satisfiable by
    # a checkbox. Until a provider is wired in, that branch fails CLOSED.
    if age_gate.required_method(request) == age_gate.METHOD_PROVIDER:
        return templates.TemplateResponse(
            "age_verify_required.html",
            {"request": request, "brand": config.BRAND_NAME},
            status_code=403,
        )

    if confirm != "yes":
        return RedirectResponse(url="/exit", status_code=303)

    response = RedirectResponse(url=destination, status_code=303)
    age_gate.grant(response)
    return response


@router.get("/exit", response_class=HTMLResponse)
async def exit_page(request: Request):
    """Where "I am under 18" lands. A dead end by design — no way back into
    the content from here, and nothing adult on the page."""
    return templates.TemplateResponse(
        "exit.html", {"request": request, "brand": config.BRAND_NAME}
    )

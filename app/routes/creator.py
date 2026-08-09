"""Creator surface — the OnlyFans-style profile and paywall.

    GET  /c/{handle}            → profile: hero, bio, tiers, content grid
    GET  /c/{handle}/subscribe  → plan picker + checkout shell
    POST /c/{handle}/subscribe  → records intent; no money moves yet

Registered under `/c/` rather than at the root so the existing
`GET /{bot_handle}` link-in-bio landing page keeps working unchanged — that
page is the social-bio router (it offers both YRAL and Amorae) and this one
is the monetisation surface. Two different jobs, two different URLs.

**No payment is taken here.** The processor decision (CCBill or Segpay, with
USDC carrying the pilot) is still in underwriting, so checkout deliberately
stops at recorded intent. That is also the metric the pilot actually needs —
"clicked buy" is the demand signal while crypto-only suppresses conversion.
"""

import logging

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse

import config
from services import age_gate, geo, personas
from sessions import current_session
from templating import templates

logger = logging.getLogger(__name__)

router = APIRouter()

# Presentation only — the real ladder gets priced against processor fees and
# the 30% platform cut once a rail clears underwriting.
TIERS = [
    {
        "id": "monthly",
        "label": "Monthly",
        "months": 1,
        "discount_pct": 0,
        "blurb": "Cancel any time",
    },
    {
        "id": "quarterly",
        "label": "3 months",
        "months": 3,
        "discount_pct": 15,
        "blurb": "Most popular",
    },
    {
        "id": "annual",
        "label": "12 months",
        "months": 12,
        "discount_pct": 30,
        "blurb": "Best value",
    },
]


def _price(persona: dict, months: int, discount_pct: int) -> dict:
    base = (persona["subscription_price_cents"] or 0) * months
    total = round(base * (100 - discount_pct) / 100)
    return {
        "total_cents": total,
        "per_month_cents": round(total / months) if months else total,
    }


def _resolve(request: Request, handle: str) -> dict:
    persona = personas.get(handle)
    if not persona:
        raise HTTPException(status_code=404, detail="Not found")
    if geo.is_blocked(request):
        raise HTTPException(status_code=451, detail="Unavailable in your region")
    return persona


@router.get("/c/{handle}", response_class=HTMLResponse)
async def profile(request: Request, handle: str):
    persona = _resolve(request, handle)

    if not age_gate.has_passed(request):
        return templates.TemplateResponse(
            "age_gate.html",
            {
                "request": request,
                "next": f"/c/{persona['handle']}",
                "method": age_gate.required_method(request),
                "brand": config.BRAND_NAME,
            },
        )

    session = await current_session(request)
    tiers = [
        {**tier, **_price(persona, tier["months"], tier["discount_pct"])}
        for tier in TIERS
    ]
    return templates.TemplateResponse(
        "creator.html",
        {
            "request": request,
            "bot": persona,
            "tiers": tiers,
            "is_logged_in": session is not None,
            "brand": config.BRAND_NAME,
        },
    )


@router.get("/c/{handle}/subscribe", response_class=HTMLResponse)
async def subscribe_page(request: Request, handle: str, tier: str = "quarterly"):
    persona = _resolve(request, handle)

    if not age_gate.has_passed(request):
        return templates.TemplateResponse(
            "age_gate.html",
            {
                "request": request,
                "next": f"/c/{persona['handle']}/subscribe",
                "method": age_gate.required_method(request),
                "brand": config.BRAND_NAME,
            },
        )

    tiers = [
        {
            **t,
            **_price(persona, t["months"], t["discount_pct"]),
            "selected": t["id"] == tier,
        }
        for t in TIERS
    ]
    session = await current_session(request)
    return templates.TemplateResponse(
        "subscribe.html",
        {
            "request": request,
            "bot": persona,
            "tiers": tiers,
            "is_logged_in": session is not None,
            "brand": config.BRAND_NAME,
        },
    )


@router.post("/c/{handle}/subscribe", response_class=HTMLResponse)
async def subscribe_intent(
    request: Request,
    handle: str,
    tier: str = Form("quarterly"),
    rail: str = Form("card"),
):
    """Records that someone tried to pay, and shows them where we are.

    Until a processor clears, this is the pilot's headline metric — see the
    "clicked buy credits" caveat in the creator-platform plan.
    """
    persona = _resolve(request, handle)
    session = await current_session(request)

    # Structured so it is greppable in Sentry/logs before there is a table
    # worth writing to. Deliberately carries no adult content.
    logger.info(
        "subscribe_intent handle=%s tier=%s rail=%s logged_in=%s",
        persona["handle"],
        tier,
        rail,
        session is not None,
    )

    return templates.TemplateResponse(
        "subscribe_pending.html",
        {
            "request": request,
            "bot": persona,
            "rail": rail,
            "brand": config.BRAND_NAME,
        },
    )

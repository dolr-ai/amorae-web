"""Policy, support and report surfaces.

The processor (CCBill/Segpay) reviews these on the live site, so the policy
set is data-driven from `services/legal_content.py` and rendered through one
template. `/privacy` and `/terms` are kept as stable aliases into that system
so old links and the age-gate references don't break.
"""

import logging

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse

import config
from services import legal_content
from templating import templates

logger = logging.getLogger(__name__)

router = APIRouter()


def _policy_response(request: Request, slug: str):
    policy = legal_content.get(slug)
    if not policy:
        return templates.TemplateResponse(
            "policy_missing.html",
            {"request": request, "brand": config.BRAND_NAME},
            status_code=404,
        )
    return templates.TemplateResponse(
        "policy.html",
        {
            "request": request,
            "policy": policy,
            "policy_nav": legal_content.nav(),
            "brand": config.BRAND_NAME,
            "support_email": config.SUPPORT_EMAIL,
        },
    )


@router.get("/legal/{slug}", response_class=HTMLResponse)
async def policy(request: Request, slug: str):
    return _policy_response(request, slug)


# Stable aliases — the age gate and older links point at these paths.
@router.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return _policy_response(request, "privacy")


@router.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return _policy_response(request, "terms")


@router.get("/support", response_class=HTMLResponse)
async def support(request: Request):
    return templates.TemplateResponse(
        "support.html",
        {
            "request": request,
            "brand": config.BRAND_NAME,
            "entity": config.LEGAL_ENTITY,
            "support_email": config.SUPPORT_EMAIL,
            "ccbill_support": config.CCBILL_SUPPORT_URL,
            "descriptor": config.BILLING_DESCRIPTOR,
            "sent": False,
        },
    )


@router.post("/support", response_class=HTMLResponse)
async def support_submit(
    request: Request,
    email: str = Form(""),
    subject: str = Form(""),
    message: str = Form(""),
):
    logger.info(
        "amorae support request: subject=%s from=%s len=%d",
        subject[:80],
        (email[:80] or "anon"),
        len(message),
    )
    return templates.TemplateResponse(
        "support.html",
        {
            "request": request,
            "brand": config.BRAND_NAME,
            "entity": config.LEGAL_ENTITY,
            "support_email": config.SUPPORT_EMAIL,
            "ccbill_support": config.CCBILL_SUPPORT_URL,
            "descriptor": config.BILLING_DESCRIPTOR,
            "sent": True,
        },
    )


@router.get("/report", response_class=HTMLResponse)
async def report_form(request: Request):
    return templates.TemplateResponse(
        "report.html", {"request": request, "sent": False}
    )


@router.post("/report", response_class=HTMLResponse)
async def report_submit(
    request: Request,
    reason: str = Form(""),
    details: str = Form(""),
):
    # Walking skeleton: log the report; a real intake queue is a fast-follow.
    logger.warning(
        "amorae report received: reason=%s details=%s", reason[:100], details[:500]
    )
    return templates.TemplateResponse("report.html", {"request": request, "sent": True})

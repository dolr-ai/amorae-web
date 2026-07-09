"""Report / Privacy / Terms — required by Google AI-content policy +
Apple 1.2. The report affordance lives HERE, on the web (§5.5)."""

from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse

from templating import templates

router = APIRouter()


@router.get("/privacy", response_class=HTMLResponse)
async def privacy(request: Request):
    return templates.TemplateResponse("privacy.html", {"request": request})


@router.get("/terms", response_class=HTMLResponse)
async def terms(request: Request):
    return templates.TemplateResponse("terms.html", {"request": request})


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
    import logging

    logging.getLogger(__name__).warning(
        "amorae report received: reason=%s details=%s", reason[:100], details[:500]
    )
    return templates.TemplateResponse("report.html", {"request": request, "sent": True})

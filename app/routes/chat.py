"""Web chat surface — the unconstrained adult persona.

GET  /{bot_handle}/start-chat → ensure 18+ + a session, then open the chat.
GET  /{bot_handle}/chat       → the chat page (requires session + 18+).
POST /{bot_handle}/message    → SSE stream of the reply (rate-limited).

TEXT ONLY, FREE for v1 (decisions #9/#14). All messages persist to
amorae_db ONLY (§4.4). Context is one-time seeded from v2's SFW history
so Tara "remembers" (§4.2) — read-only, never written back.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse

import config
from models import ChatMessageIn, WebSession
from repositories import conversation_repo, message_repo, session_repo
from services import llm, personas, rate_limit, v2_client
from sessions import (
    current_session,
    has_consent,
    new_session_id,
    require_session,
    set_session_cookie,
)
from templating import templates

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/{bot_handle}/start-chat")
async def start_chat(request: Request, bot_handle: str):
    """The 'Chat with <persona>' entry. Makes the web funnel work without the
    app: ensure the 18+ gate is passed, ensure a session exists (create an
    anonymous one when anon chat is enabled), then land in the chat.

    Anyone can browse the feed, but a message costs LLM tokens, so a session is
    still created here — it's what the rate limiter and history hang off.
    """
    bot = personas.get(bot_handle)
    if not bot:
        raise HTTPException(status_code=404, detail="Not found")

    # Not 18+ yet → the age gate, returning here afterwards.
    if not has_consent(request):
        from services import age_gate

        return templates.TemplateResponse(
            "age_gate.html",
            {
                "request": request,
                "next": f"/{bot['handle']}/start-chat",
                "method": age_gate.required_method(request),
                "brand": config.BRAND_NAME,
            },
        )

    session = await current_session(request)
    response = RedirectResponse(url=f"/{bot['handle']}/chat", status_code=303)

    if session is None:
        if not (config.ALLOW_ANON_CHAT or config.DEV_ALLOW_ANON):
            # Anon chat disabled and no app session → send to the app-handoff
            # landing rather than a dead chat page.
            return RedirectResponse(url=f"/{bot['handle']}?e=login", status_code=303)
        session_id = new_session_id()
        await session_repo.create(
            session_id, user_id=None, is_anonymous=True, bot_handle=bot["handle"]
        )
        set_session_cookie(response, session_id)

    return response


@router.get("/{bot_handle}/chat", response_class=HTMLResponse)
async def chat_page(
    request: Request,
    bot_handle: str,
    session: WebSession = Depends(require_session),
):
    bot = personas.get(bot_handle)
    if not bot:
        raise HTTPException(status_code=404, detail="Not found")

    conversation_id = await conversation_repo.get_or_create(
        user_id=session.user_id,
        session_id=session.session_id,
        bot_handle=bot["handle"],
    )
    history = await message_repo.recent(conversation_id)
    return templates.TemplateResponse(
        "chat.html",
        {"request": request, "bot": bot, "history": history},
    )


async def _build_llm_messages(
    bot: dict,
    session: WebSession,
    conversation_id: int,
    user_text: str,
) -> list[dict]:
    """system → (one-time seeded SFW context, if new thread) → history → user."""
    messages: list[dict] = [{"role": "system", "content": bot["system_prompt"]}]

    history = await message_repo.recent(conversation_id)
    if not history and session.user_id and not session.is_anonymous:
        seeded = await v2_client.read_recent_context(session.user_id, bot["handle"])
        messages.extend(seeded)

    messages.extend(history)
    messages.append({"role": "user", "content": user_text})
    return messages


@router.post("/{bot_handle}/message")
async def send_message(
    request: Request,
    bot_handle: str,
    body: ChatMessageIn,
    session: WebSession = Depends(require_session),
):
    bot = personas.get(bot_handle)
    if not bot:
        raise HTTPException(status_code=404, detail="Not found")

    # This is the one endpoint that spends LLM tokens and is reachable
    # anonymously — bound it per client IP before doing any work.
    if not rate_limit.check(
        rate_limit.client_key(request),
        config.CHAT_RATELIMIT_MAX,
        config.CHAT_RATELIMIT_WINDOW_SECONDS,
    ):
        raise HTTPException(status_code=429, detail="Slow down a moment 💛")

    user_text = (body.content or "").strip()
    if not user_text:
        raise HTTPException(status_code=400, detail="Empty message")

    conversation_id = await conversation_repo.get_or_create(
        user_id=session.user_id,
        session_id=session.session_id,
        bot_handle=bot["handle"],
    )
    llm_messages = await _build_llm_messages(bot, session, conversation_id, user_text)
    await message_repo.add(conversation_id, "user", user_text)

    async def event_stream():
        parts: list[str] = []
        try:
            async for delta in llm.complete_stream(llm_messages):
                parts.append(delta)
                yield f"data: {json.dumps({'delta': delta})}\n\n"
        except Exception as e:
            logger.warning("stream failed, falling back to non-streaming: %s", e)
            if not parts:
                try:
                    full = await llm.complete(llm_messages)
                    parts.append(full)
                    yield f"data: {json.dumps({'delta': full})}\n\n"
                except Exception as e2:
                    logger.error("llm failed: %s", e2)
                    yield f"data: {json.dumps({'error': 'reply_failed'})}\n\n"
        reply = "".join(parts).strip()
        if reply:
            await message_repo.add(conversation_id, "assistant", reply)
            await conversation_repo.touch(conversation_id)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")

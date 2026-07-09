"""Pydantic models for the amorae web surface.

Small by design — the walking skeleton has one inbound JSON body (a chat
message) and a couple of internal shapes. HTML pages are rendered
server-side, so most request/response bodies are form posts or SSE, not
JSON DTOs.
"""

from pydantic import BaseModel


class ChatMessageIn(BaseModel):
    """A user's message posted to the web chat surface."""

    content: str


class WebSession(BaseModel):
    """Resolved session backing the httpOnly cookie."""

    session_id: str
    user_id: str | None = None
    is_anonymous: bool = False
    bot_handle: str | None = None


class HandoffIdentity(BaseModel):
    """What v2's /spicy/handoff/exchange returns for a valet ticket."""

    user_id: str
    bot_handle: str | None = None
    is_anonymous: bool = False

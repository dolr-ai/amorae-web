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


# ---------------------------------------------------------------------------
# Video feed
# ---------------------------------------------------------------------------
# These are OUR shapes, not the upstream feed's. The upstream contract is
# frozen and deliberately thin (ids + view counts); `services/feed_client.py`
# widens it into these. Keeping our own model means an upstream field change
# is a one-file edit and never reaches a template.


class FeedCreator(BaseModel):
    """The persona a video belongs to, as the feed overlay needs her."""

    handle: str
    display_name: str
    avatar_url: str
    # `ai_influencers.id` — the SAME id as YRAL chat, so one persona spans
    # both surfaces. None until the persona is created in that catalogue.
    influencer_id: str | None = None
    is_verified: bool = True
    subscription_price_cents: int | None = None


class FeedVideoSources(BaseModel):
    """Playback URLs. `mp4` is required; `hls` is set once the CDN has ladders."""

    mp4: str
    hls: str | None = None


class FeedVideo(BaseModel):
    """One video in the vertical feed."""

    video_id: str
    post_id: str | None = None
    sources: FeedVideoSources
    poster_url: str
    caption: str = ""
    # Portrait short-form is 9:16 = 0.5625. The player letterboxes anything
    # else rather than cropping faces out of frame.
    aspect_ratio: float = 0.5625
    duration_seconds: float | None = None
    view_count: int = 0
    like_count: int = 0
    creator: FeedCreator


class FeedPage(BaseModel):
    """One page of the feed. Cursor paging — never offset/limit, because the
    upstream list is reshuffled per user and offsets would skip or repeat."""

    videos: list[FeedVideo]
    next_cursor: str | None = None
    has_more: bool = True

"""The video feed — one seam between our UI and the mobile backend.

The upstream contract is FROZEN and deliberately thin. It returns ids and
view counts and nothing else:

    GET {VIDEO_FEED_BASE_URL}/api/v1/recommend-with-metadata/{user_id}
        ?count=20&rec_type=mixed
    -> {"videos": [{video_id, canister_id, post_id, publisher_user_id,
                    num_views_all, num_views_loggedin, from_ai_influencer,
                    is_following, is_pro_user}]}

Everything the overlay actually renders — playback URL, poster, creator
name, avatar, caption, duration — is NOT in that payload. Two of those we
can derive ourselves (URLs are constructed from ids, exactly as the mobile
clients do); the rest genuinely has to come from the backend, and the gap
is written up in `docs/video-feed-web-contract-2026-08-09.md`.

This module is where that gap is absorbed, so it stays a one-file problem:

  * `FEED_SOURCE=mock`     — serve `app/data/mock_feed.json`. The entire
    front end works with no backend at all.
  * `FEED_SOURCE=upstream` — call the real service and widen the response.

We call upstream SERVER-SIDE, never from the browser. That is a deliberate
choice with three consequences worth keeping: the video service needs no
CORS headers for us, its hostname is never exposed to the client, and an
upstream outage degrades to a cached/empty feed instead of a JS error.
"""

import base64
import json
import logging
import os
from typing import Any

import httpx

import config
from models import FeedCreator, FeedPage, FeedVideo, FeedVideoSources
from services import personas

logger = logging.getLogger(__name__)

_MOCK_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "mock_feed.json"
)

# Videos whose publisher maps to no persona still need a name and a face, or
# the overlay renders blank. They are shown as a generic creator and their
# CTAs point at discovery rather than a profile that does not exist.
_UNKNOWN_CREATOR = {
    "handle": "",
    "display_name": "Amorae",
    "avatar_image": "/static/personas/unknown-avatar.svg",
    "influencer_id": None,
    "subscription_price_cents": None,
}


# ---------------------------------------------------------------------------
# Cursor
# ---------------------------------------------------------------------------
# Offset paging is wrong here: upstream reshuffles its ranked list per user
# and maintains a server-side seen-set, so page 2 of an offset scheme would
# skip and repeat. The cursor is an opaque token carrying only how deep we
# are, and it stays opaque so its contents can change without a client
# release.


def encode_cursor(offset: int) -> str:
    raw = json.dumps({"o": offset}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> int:
    if not cursor:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        return max(0, int(json.loads(base64.urlsafe_b64decode(padded))["o"]))
    except (ValueError, KeyError, TypeError):
        # A malformed cursor restarts the feed rather than 500ing. Users
        # reach this by editing the URL or by a stale bookmark.
        return 0


# ---------------------------------------------------------------------------
# URL construction
# ---------------------------------------------------------------------------


def video_url(video_id: str, publisher_user_id: str) -> str:
    return f"{config.MEDIA_CDN_BASE}/{publisher_user_id}/{video_id}.mp4"


def poster_url(video_id: str, publisher_user_id: str) -> str:
    return f"{config.MEDIA_CDN_BASE}/{publisher_user_id}/{video_id}-thumbnail.png"


def hls_url(video_id: str, publisher_user_id: str) -> str | None:
    if not config.MEDIA_HLS_BASE:
        return None
    return f"{config.MEDIA_HLS_BASE}/{publisher_user_id}/{video_id}/manifest.m3u8"


# ---------------------------------------------------------------------------
# Normalisation
# ---------------------------------------------------------------------------


def _creator_for(publisher_user_id: str) -> FeedCreator:
    persona = personas.by_influencer_id(publisher_user_id) or _UNKNOWN_CREATOR
    return FeedCreator(
        handle=persona["handle"],
        display_name=persona["display_name"],
        avatar_url=persona["avatar_image"],
        influencer_id=persona["influencer_id"],
        subscription_price_cents=persona["subscription_price_cents"],
    )


def _from_upstream(raw: dict[str, Any]) -> FeedVideo | None:
    """Widen one upstream row into our model. Returns None for rows we
    cannot play, which is safer than rendering a black screen."""
    video_id = raw.get("video_id")
    publisher = raw.get("publisher_user_id")
    if not video_id or not publisher:
        return None

    return FeedVideo(
        video_id=video_id,
        post_id=raw.get("post_id"),
        sources=FeedVideoSources(
            mp4=video_url(video_id, publisher),
            hls=hls_url(video_id, publisher),
        ),
        poster_url=poster_url(video_id, publisher),
        # Not in the upstream contract — see the gap list in the web contract
        # doc. Empty caption renders as no caption, which is fine.
        caption=raw.get("caption", ""),
        duration_seconds=raw.get("duration_seconds"),
        view_count=raw.get("num_views_all", 0) or 0,
        like_count=raw.get("like_count", 0) or 0,
        creator=_creator_for(publisher),
    )


def _from_mock(raw: dict[str, Any]) -> FeedVideo:
    """Mock rows are already in OUR shape — they are the contract we are
    asking the backend for, so the UI is built against the target, not
    against today's thinner payload."""
    persona = personas.get(raw.get("creator_handle", "")) or _UNKNOWN_CREATOR
    return FeedVideo(
        video_id=raw["video_id"],
        post_id=raw.get("post_id"),
        sources=FeedVideoSources(mp4=raw["mp4"], hls=raw.get("hls")),
        poster_url=raw["poster"],
        caption=raw.get("caption", ""),
        aspect_ratio=raw.get("aspect_ratio", 0.5625),
        duration_seconds=raw.get("duration_seconds"),
        view_count=raw.get("view_count", 0),
        like_count=raw.get("like_count", 0),
        creator=FeedCreator(
            handle=persona["handle"],
            display_name=persona["display_name"],
            avatar_url=persona["avatar_image"],
            influencer_id=persona["influencer_id"],
            subscription_price_cents=persona["subscription_price_cents"],
        ),
    )


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------


def _load_mock() -> list[dict[str, Any]]:
    with open(_MOCK_PATH) as f:
        return json.load(f)["videos"]


async def _fetch_upstream(feed_key: str, count: int) -> list[dict[str, Any]]:
    url = f"{config.VIDEO_FEED_BASE_URL}/api/v1/recommend-with-metadata/{feed_key}"
    async with httpx.AsyncClient(timeout=config.VIDEO_FEED_TIMEOUT) as client:
        response = await client.get(url, params={"count": count, "rec_type": "mixed"})
        response.raise_for_status()
        return response.json().get("videos", [])


async def get_page(feed_key: str, cursor: str | None, limit: int) -> FeedPage:
    """One page of the feed.

    `feed_key` is the identity upstream personalises on. For a logged-in user
    that is their user id; for an anonymous browser it is a per-browser random
    token (see `routes/feed.py`) — NOT an IP or a fingerprint, so it carries
    no personal data and an anonymous visitor still gets a stable,
    non-repeating feed.
    """
    limit = max(1, min(limit, config.FEED_PAGE_SIZE_MAX))
    offset = decode_cursor(cursor)

    if config.FEED_SOURCE == "upstream":
        try:
            # Upstream has no cursor of its own: it de-duplicates per user
            # with a 24h seen-set, so asking for the next `limit` items is
            # enough. We over-fetch by the offset only on a cold cursor.
            rows = await _fetch_upstream(feed_key, limit)
            videos = [v for v in (_from_upstream(r) for r in rows) if v]
        except (httpx.HTTPError, ValueError) as e:
            # A feed outage must not take the homepage down. An empty page
            # renders the "that's everything for now" end card.
            logger.warning("upstream feed failed: %s", e)
            return FeedPage(videos=[], next_cursor=None, has_more=False)
    else:
        rows = _load_mock()
        # The mock list is finite; loop it so scrolling never dead-ends
        # while the real backend is still being built.
        window = [rows[(offset + i) % len(rows)] for i in range(limit)]
        videos = [_from_mock(r) for r in window]

    has_more = bool(videos)
    return FeedPage(
        videos=videos,
        next_cursor=encode_cursor(offset + len(videos)) if has_more else None,
        has_more=has_more,
    )

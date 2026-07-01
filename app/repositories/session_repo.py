"""web_sessions — backs the httpOnly session cookie."""

from datetime import datetime, timedelta, timezone

import config
from database import get_pool


async def create(
    session_id: str,
    *,
    user_id: str | None,
    is_anonymous: bool,
    bot_handle: str | None,
) -> None:
    expires_at = datetime.now(timezone.utc) + timedelta(days=config.SESSION_TTL_DAYS)
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO web_sessions (session_id, user_id, is_anonymous, bot_handle, expires_at)
        VALUES ($1, $2, $3, $4, $5)
        """,
        session_id,
        user_id,
        is_anonymous,
        bot_handle,
        expires_at,
    )


async def get(session_id: str) -> dict | None:
    pool = await get_pool()
    row = await pool.fetchrow(
        """
        SELECT session_id, user_id, is_anonymous, bot_handle
        FROM web_sessions
        WHERE session_id = $1 AND expires_at > now()
        """,
        session_id,
    )
    return dict(row) if row else None


async def touch(session_id: str) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE web_sessions SET last_seen_at = now() WHERE session_id = $1",
        session_id,
    )

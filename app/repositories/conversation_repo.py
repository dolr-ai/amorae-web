"""conversations — one adult thread per (identity, bot) on the web brand."""

from database import get_pool


async def get_or_create(
    *,
    user_id: str | None,
    session_id: str,
    bot_handle: str,
) -> int:
    """Return the conversation id for this identity+bot, creating it once.

    Keyed by user_id when logged in (cross-device), else by session_id
    (dev/anon). Adult threads live only here, never in yral_agent_db.
    """
    pool = await get_pool()
    if user_id:
        row = await pool.fetchrow(
            "SELECT id FROM conversations WHERE user_id = $1 AND bot_handle = $2",
            user_id,
            bot_handle,
        )
    else:
        row = await pool.fetchrow(
            "SELECT id FROM conversations WHERE session_id = $1 AND bot_handle = $2",
            session_id,
            bot_handle,
        )
    if row:
        return row["id"]

    return await pool.fetchval(
        """
        INSERT INTO conversations (user_id, session_id, bot_handle)
        VALUES ($1, $2, $3)
        RETURNING id
        """,
        user_id,
        session_id,
        bot_handle,
    )


async def touch(conversation_id: int) -> None:
    pool = await get_pool()
    await pool.execute(
        "UPDATE conversations SET updated_at = now() WHERE id = $1",
        conversation_id,
    )

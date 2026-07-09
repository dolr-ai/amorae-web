"""web_consent — the 18+ audit trail on the web side."""

from database import get_pool


async def record(
    session_id: str,
    *,
    user_id: str | None,
    bot_handle: str | None,
    source_ip: str | None,
    user_agent: str | None,
) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO web_consent (session_id, user_id, bot_handle, source_ip, user_agent)
        VALUES ($1, $2, $3, $4, $5)
        """,
        session_id,
        user_id,
        bot_handle,
        source_ip,
        user_agent,
    )

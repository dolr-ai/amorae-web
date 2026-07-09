"""messages — THE adult chat text. Never leaves amorae_db."""

import config
from database import get_pool


async def add(conversation_id: int, role: str, content: str) -> None:
    pool = await get_pool()
    await pool.execute(
        """
        INSERT INTO messages (conversation_id, role, content)
        VALUES ($1, $2, $3)
        """,
        conversation_id,
        role,
        content,
    )


async def recent(conversation_id: int, limit: int | None = None) -> list[dict]:
    """Recent turns oldest-first, for the LLM context window."""
    limit = limit or config.CHAT_HISTORY_WINDOW
    pool = await get_pool()
    rows = await pool.fetch(
        """
        SELECT role, content FROM (
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at DESC
            LIMIT $2
        ) t
        ORDER BY created_at ASC
        """,
        conversation_id,
        limit,
    )
    return [dict(r) for r in rows]

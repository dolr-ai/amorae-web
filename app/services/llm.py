"""OpenRouter chat client for the amorae web surface.

Mirrors v2's `services/llm_clients/openai_compatible.py` (the exact path
`user_chat_main_nsfw` rides on) but trimmed to what this surface needs:
one streaming call, one non-streaming fallback. Same wire format, same
retry-on-5xx shape, same OpenRouter-returns-2xx-with-error handling
(Sentry YRAL-RISHI-AGENT-4J). No content-safety filter — this surface is
the unconstrained adult persona by design (§4.2).
"""

import asyncio
import json
import logging
import random
import time
from typing import AsyncIterator

import httpx

import config

logger = logging.getLogger(__name__)


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {config.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        # OpenRouter attribution headers (optional but polite).
        "HTTP-Referer": f"https://{config.BRAND_DOMAIN}",
        "X-Title": config.BRAND_NAME,
    }


async def complete(messages: list[dict], *, max_retries: int = 3) -> str:
    """Single-shot completion. Retries on 5xx / network up to max_retries."""
    body = {
        "model": config.OPENROUTER_MODEL,
        "messages": messages,
        "temperature": config.OPENROUTER_TEMPERATURE,
        "max_tokens": config.OPENROUTER_MAX_TOKENS,
    }
    url = f"{config.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"

    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=config.OPENROUTER_TIMEOUT) as client:
                response = await client.post(url, headers=_headers(), json=body)
            if response.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"upstream {response.status_code}",
                    request=response.request,
                    response=response,
                )
            response.raise_for_status()
            data = response.json()
            # OpenRouter can return 2xx with {"error": {...}} and no choices.
            if "choices" not in data or not data.get("choices"):
                err = data.get("error") or {}
                msg = err.get("message") if isinstance(err, dict) else None
                raise httpx.HTTPStatusError(
                    f"openrouter error body: {msg or list(data.keys())[:5]}",
                    request=response.request,
                    response=response,
                )
            return data["choices"][0]["message"]["content"] or ""
        except (httpx.HTTPStatusError, httpx.RequestError, asyncio.TimeoutError) as e:
            last_error = e
            if attempt < max_retries - 1:
                backoff = (0.2 * (2**attempt)) + random.uniform(-0.05, 0.05)
                logger.warning("llm.complete retry %d/%d: %s", attempt + 1, max_retries, e)
                await asyncio.sleep(max(backoff, 0.05))
                continue
            break

    assert last_error is not None
    raise last_error


async def complete_stream(messages: list[dict]) -> AsyncIterator[str]:
    """Streaming completion. Yields content deltas (str). Does NOT retry —
    the consumer is mid-stream. The route wraps this in SSE."""
    body = {
        "model": config.OPENROUTER_MODEL,
        "messages": messages,
        "temperature": config.OPENROUTER_TEMPERATURE,
        "max_tokens": config.OPENROUTER_MAX_TOKENS,
        "stream": True,
    }
    url = f"{config.OPENROUTER_BASE_URL.rstrip('/')}/chat/completions"

    async with httpx.AsyncClient(timeout=config.OPENROUTER_TIMEOUT) as client:
        async with client.stream("POST", url, headers=_headers(), json=body) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                payload = line[len("data: ") :].strip()
                if payload == "[DONE]":
                    return
                try:
                    chunk = json.loads(payload)
                except json.JSONDecodeError:
                    continue
                choices = chunk.get("choices") or []
                if choices:
                    content = (choices[0].get("delta") or {}).get("content")
                    if content:
                        yield content

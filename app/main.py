import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config
from database import close_pool, get_pool
from routes import age, chat, creator, feed, gate, health, landing, legal
from services import influencers_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if config.SENTRY_DSN:
    import sentry_sdk  # → sentry.rishi.yral.com (Rule 5)

    sentry_sdk.init(
        dsn=config.SENTRY_DSN,
        environment=config.SENTRY_ENVIRONMENT,
        release=config.APP_VERSION,
        traces_sample_rate=1.0,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()
    # Personas now come from the shared ai_influencers catalogue (web-filtered),
    # refreshed on a TTL by a background task. Prime it once at startup.
    await influencers_client.refresh()
    catalogue_task = asyncio.create_task(influencers_client.run_refresh_loop())
    logger.info("%s v%s started", config.APP_NAME, config.APP_VERSION)
    # The FEED is still TEMPORARY (hardcoded mock_feed.json) until the video
    # rewire (PR #2, gated on Saikat's metadata). Don't let it hide.
    if config.FEED_SOURCE == "mock":
        logger.warning(
            "TEMPORARY DATA: feed served from mock_feed.json. Pending the video "
            "rewire (real videos for web-surface influencers). See "
            "docs/one-backend-data-layer-contract-2026-08-09.md."
        )
    yield
    catalogue_task.cancel()
    await close_pool()


app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in config.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class LimitRequestBody:
    """Reject oversized request bodies before a route ever parses them.

    Mitigates CVE-2026-54283: starlette < 1.3.1 silently ignores the
    max_fields / max_part_size limits for `application/x-www-form-urlencoded`,
    so an unauthenticated POST with a huge field, or hundreds of thousands of
    tiny ones, blocks the event loop or exhausts memory. Every form endpoint
    here is unauthenticated (the age gate is the public entry point), so the
    exposure is real until the starlette upgrade lands.

    Our forms only ever carry a ticket, a tier name, or a short report — all
    well under the cap — so bounding the body neutralises both the many-fields
    and the huge-field vector without a framework bump. It is belt to the
    edge's braces (Caddy/Cloudflare also limit bodies), and defence the app
    owns rather than trusts someone else to apply.

    Written as raw ASGI, NOT `@app.middleware("http")`, on purpose. That
    decorator's BaseHTTPMiddleware would force us to consume and replay the
    body, and the replay does not reach the downstream handler's request — it
    silently blanks every form POST. Here we instead wrap the `receive`
    channel the handler itself drives and tally bytes as they are pulled, so
    the body is never pre-consumed. Content-Length is the fast reject; the
    byte tally is the backstop for a chunked request that omits it.
    """

    def __init__(self, app, max_bytes: int):
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        # Only request-bearing methods carry a body worth bounding. Leaving
        # GET/HEAD/OPTIONS untouched keeps SSE and the feed hot path exactly
        # as they were.
        if (
            scope["type"] != "http"
            or self.max_bytes <= 0
            or scope.get("method") not in ("POST", "PUT", "PATCH")
        ):
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        declared = headers.get(b"content-length")
        if declared is not None:
            try:
                if int(declared) > self.max_bytes:
                    await self._reject(send)
                    return
            except ValueError:
                await self._reject(send, status=400, text=b"Bad Content-Length")
                return

        # Buffer the body up to the cap, then hand the app a receive channel
        # that replays it. Reading here is safe because — unlike the
        # `@app.middleware("http")` decorator — the downstream app is driven
        # by exactly this `receive`, so there is no second request to blank.
        # A chunked request (no Content-Length) is caught here: we stop the
        # moment the tally crosses the cap, before the form parser ever sees
        # the oversized body.
        body = b""
        while True:
            message = await receive()
            if message["type"] == "http.disconnect":
                # Client hung up mid-body; nothing to serve.
                return
            body += message.get("body", b"")
            if len(body) > self.max_bytes:
                await self._reject(send)
                return
            if not message.get("more_body", False):
                break

        replayed = False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            # After the body, mirror a normal quiescent channel.
            return await receive()

        await self.app(scope, replay, send)

    async def _reject(
        self, send, status: int = 413, text: bytes = b"Payload too large"
    ):
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"text/plain; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": text})


@app.middleware("http")
async def content_security_policy(request, call_next):
    """Send our own CSP so policy changes ship with the code that needs them.

    Applies to static files too — the mount is inside the middleware stack —
    so `/static/*` carries the same policy the pages do.

    `setdefault` rather than assignment: if a route ever needs its own
    stricter policy it can set one and this will not stamp over it.
    """
    response = await call_next(request)
    response.headers.setdefault(
        "Content-Security-Policy", config.CONTENT_SECURITY_POLICY
    )
    return response


# Added last so it wraps OUTERMOST — an oversized body is rejected before it
# reaches routing, CORS or the form parser.
app.add_middleware(LimitRequestBody, max_bytes=config.MAX_REQUEST_BODY_BYTES)


_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# Order matters: fixed paths (health, legal, feed, age, creator) register
# BEFORE the `/{bot_handle}` landing catch-all so /health, /privacy, /terms,
# /report, /api/..., /age-gate and /exit aren't swallowed by it. Any new
# top-level route MUST go above `landing` for the same reason.
app.include_router(health.router)
app.include_router(legal.router)
app.include_router(feed.router)
app.include_router(age.router)
app.include_router(creator.router)
app.include_router(gate.router)
app.include_router(chat.router)
app.include_router(landing.router)

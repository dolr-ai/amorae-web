import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import config
from database import close_pool, get_pool
from routes import health, legal, landing, gate, chat

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
    logger.info("%s v%s started", config.APP_NAME, config.APP_VERSION)
    yield
    await close_pool()


app = FastAPI(title=config.APP_NAME, version=config.APP_VERSION, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in config.CORS_ORIGINS.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

# Order matters: fixed paths (health, legal) register BEFORE the
# `/{bot_handle}` landing catch-all so /health, /privacy, /terms, /report
# aren't swallowed by it.
app.include_router(health.router)
app.include_router(legal.router)
app.include_router(gate.router)
app.include_router(chat.router)
app.include_router(landing.router)

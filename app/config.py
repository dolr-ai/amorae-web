import os


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default) or default


def _env_int(key: str, default: int = 0) -> int:
    try:
        return int(_env(key, str(default)))
    except ValueError:
        return default


def _env_float(key: str, default: float = 0.0) -> float:
    try:
        return float(_env(key, str(default)))
    except ValueError:
        return default


def _env_bool(key: str, default: bool = False) -> bool:
    return _env(key, str(default)).lower() in ("true", "1", "yes")


def _secret(name: str, env_key: str | None = None) -> str:
    """Read a Swarm secret from /run/secrets/<name> (the prod pattern),
    falling back to an env var for local dev. Matches how amorae_db_dsn_rw
    + V2_WEB_SHARED_SECRET are mounted on the cluster (Session 6)."""
    path = f"/run/secrets/{name}"
    if os.path.exists(path):
        with open(path) as f:
            return f.read().strip()
    return _env(env_key or name)


# App
APP_NAME = _env("APP_NAME", "Amorae")
APP_VERSION = _env("APP_VERSION", "0.1.0")
ENVIRONMENT = _env("ENVIRONMENT", "development")
DEBUG = _env_bool("DEBUG", False)
HOST = _env("HOST", "0.0.0.0")
PORT = _env_int(
    "PORT", 8003
)  # fleet port map: analytics 8001, marketing 8002, amorae 8003

# Brand identity — its OWN name, deliberately NOT "yral" (Level-2 / Risk 6).
BRAND_NAME = _env("BRAND_NAME", "Amorae")
BRAND_DOMAIN = _env("BRAND_DOMAIN", "amorae.ai")

# Tara's hero photo — her real v2 profile avatar (publicly served from
# Hetzner object storage). Env-overridable so Session 6 can swap the
# canonical spicy-Tara bot without a code change. NOTE: several v2 bots are
# named "Tara"; this is the "Companion" one (id 7n76l…xqe) — confirm the
# canonical is_nsfw bot with Session 6 (matters for context-seed mapping).
TARA_HERO_URL = _env(
    "TARA_HERO_URL",
    "https://yral-profile.hel1.your-objectstorage.com/users/"
    "7n76l-nlw2k-r3usv-dc5n2-biixj-rv7cx-maetx-x6epw-lwac6-muicl-xqe/"
    "profile-1782408126.jpg",
)

# LLM — reuse the SAME provider/model as v2's `user_chat_main_nsfw`
# (OpenRouter, google/gemini-2.5-flash). No content-safety filter here:
# this surface is the unconstrained adult persona by design (§4.2).
OPENROUTER_API_KEY = _env("OPENROUTER_API_KEY")
OPENROUTER_MODEL = _env("OPENROUTER_MODEL", "google/gemini-2.5-flash")
OPENROUTER_MAX_TOKENS = _env_int("OPENROUTER_MAX_TOKENS", 2048)
OPENROUTER_TEMPERATURE = _env_float("OPENROUTER_TEMPERATURE", 0.85)
OPENROUTER_TIMEOUT = _env_int("OPENROUTER_TIMEOUT", 60)
OPENROUTER_BASE_URL = _env("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")

# v2 (yral-rishi-agent) — the auth handoff + context-read live there.
# We call v2 server-to-server with a web-scoped shared secret; the native
# JWT NEVER reaches this domain (§4.7). amorae has NO credential to
# yral_agent_db — only these HTTP calls.
V2_BASE_URL = _env("V2_BASE_URL", "https://agent.rishi.yral.com")
# Mounted as a Swarm secret file on the cluster (Session 6 placed it);
# env fallback for local dev.
V2_WEB_SHARED_SECRET = _secret("V2_WEB_SHARED_SECRET")
V2_TIMEOUT = _env_int("V2_TIMEOUT", 10)

# Sessions & consent cookies (the LIVE 18+ gate lives here, on the web)
SESSION_COOKIE_NAME = _env("SESSION_COOKIE_NAME", "amorae_session")
CONSENT_COOKIE_NAME = _env("CONSENT_COOKIE_NAME", "amorae_adult_ok")
SESSION_TTL_DAYS = _env_int("SESSION_TTL_DAYS", 90)
CONSENT_TTL_DAYS = _env_int("CONSENT_TTL_DAYS", 90)
COOKIE_SECURE = _env_bool("COOKIE_SECURE", True)
COOKIE_DOMAIN = _env("COOKIE_DOMAIN")  # empty = host-only cookie

# Geo-gate — server-side region check. DEFAULT OPEN (decision #13): the
# capability ships from day one but restricts nothing until a country is
# added here. Comma-separated ISO-3166-1 alpha-2 codes.
GEO_BLOCKED_COUNTRIES = [
    c.strip().upper() for c in _env("GEO_BLOCKED_COUNTRIES", "").split(",") if c.strip()
]

# Walking-skeleton escape hatch: allow "Continue (18+)" to open an
# ANONYMOUS session with no ticket, so the skeleton is testable before
# v2's handoff/exchange endpoint exists. MUST be False in production.
DEV_ALLOW_ANON = _env_bool("DEV_ALLOW_ANON", False)

# How many prior turns we send to the LLM per reply (mirrors v2's window).
CHAT_HISTORY_WINDOW = _env_int("CHAT_HISTORY_WINDOW", 30)

# How many recent SFW app messages we one-time READ from v2 to seed memory.
CONTEXT_SEED_WINDOW = _env_int("CONTEXT_SEED_WINDOW", 20)

# CORS
CORS_ORIGINS = _env("CORS_ORIGINS", "*")

# Sentry (→ sentry.rishi.yral.com, never apm.yral.com — Rule 5)
SENTRY_DSN = _env("SENTRY_DSN")
SENTRY_ENVIRONMENT = _env("SENTRY_ENVIRONMENT", ENVIRONMENT)

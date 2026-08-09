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

# Site lifecycle. "prelaunch" shows a tasteful early-access banner and concept
# framing (positive, not "under construction" — that reads as not-a-real-
# business to a payment reviewer). "live" removes the banner. Going live is
# ONE env flip, no code change and no page to delete.
SITE_STATUS = _env("SITE_STATUS", "prelaunch")  # prelaunch | live
PRELAUNCH_NOTICE = _env(
    "PRELAUNCH_NOTICE",
    "Amorae is in early access — we're rolling out creators. Subscriptions open soon.",
)

# ---------------------------------------------------------------------------
# Legal entity & merchant details (CCBill/Segpay approval)
# ---------------------------------------------------------------------------
# The processor reviews these on the live site, so they render in the footer,
# the policy pages and the checkout. Every value below is env-overridable; the
# ones marked RISHI are placeholders that MUST be set to real values before the
# merchant application goes in. Legal copy is DRAFT until counsel signs off.
#
# HARD REQUIREMENT (CCBill onboarding): the business must be registered in
# US / CA / UK / EU. LEGAL_ENTITY_COUNTRY must be one of those.
LEGAL_ENTITY = _env("LEGAL_ENTITY", "GoBazzinga Inc")
LEGAL_ENTITY_COUNTRY = _env("LEGAL_ENTITY_COUNTRY", "")  # RISHI: US/CA/UK/EU
LEGAL_ENTITY_ADDRESS = _env("LEGAL_ENTITY_ADDRESS", "")  # RISHI: registered address
SUPPORT_EMAIL = _env("SUPPORT_EMAIL", "")  # RISHI: monitored support inbox
# What appears on the customer's card statement. A discreet descriptor lowers
# chargebacks; CCBill assigns/approves the final string. RISHI: confirm.
BILLING_DESCRIPTOR = _env("BILLING_DESCRIPTOR", "AMORAE.AI")
# CCBill's own consumer billing-support portal (stable URL, safe default).
CCBILL_SUPPORT_URL = _env("CCBILL_SUPPORT_URL", "https://support.ccbill.com")
# Flips the "DRAFT — pending legal review" banner off once counsel signs off.
LEGAL_COPY_APPROVED = _env_bool("LEGAL_COPY_APPROVED", False)
# 2257 records custodian (for AI-only content we state no real performers, but
# still name a custodian + address as processors expect the section present).
RECORDS_CUSTODIAN = _env("RECORDS_CUSTODIAN", LEGAL_ENTITY)

# Tara's hero photo, served LOCALLY from static (the media CDN is CSP-allowed
# but a local file is the safe default). This is a PLACEHOLDER. Tara is one
# identity across chat ("taaarraaah") and video (username "elitesuperdeer"),
# principal qi6gd… (see personas.py). Her real avatar loads from her CDN
# profile once the metadata/auth server settles and we verify content under
# that principal. Env-overridable; an override MUST be `self` or a CSP
# img-src allowlisted origin.
TARA_HERO_URL = _env("TARA_HERO_URL", "/static/tara.jpg")

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

# ---------------------------------------------------------------------------
# Video feed (the TikTok-style homepage)
# ---------------------------------------------------------------------------
# Where the feed comes from. "mock" serves `app/data/mock_feed.json` so the
# whole front end works before the mobile backend ships anything; "upstream"
# calls the real video service. One env flip switches them — no code change.
FEED_SOURCE = _env("FEED_SOURCE", "mock")  # mock | upstream

# The video-feed service (the "mobile backend" endpoint we share). Today that
# is ansuman's box; it is being replaced by `yral-rishi-video-service` at
# video.rishi.yral.com — same path, same contract, so only this value moves.
VIDEO_FEED_BASE_URL = _env("VIDEO_FEED_BASE_URL", "https://video.rishi.yral.com")
VIDEO_FEED_TIMEOUT = _env_int("VIDEO_FEED_TIMEOUT", 8)

# Media CDN. Playback and poster URLs are CONSTRUCTED from ids the feed
# returns (the mobile clients do the same — see yral-mobile
# `IndividualUserDataSourceImpl.videoUrl`). Adult media must NOT be served
# from the SFW bucket, so this is its own hostname from day one.
#   video:  {MEDIA_CDN_BASE}/{publisher_user_id}/{video_id}.mp4
#   poster: {MEDIA_CDN_BASE}/{publisher_user_id}/{video_id}-thumbnail.png
MEDIA_CDN_BASE = _env("MEDIA_CDN_BASE", "https://cdn-yral-sfw.yral.com")
# Set once the CDN publishes HLS ladders; empty = MP4-only playback.
MEDIA_HLS_BASE = _env("MEDIA_HLS_BASE", "")

# Feed paging. `limit` is what one API call returns; the client keeps a small
# buffer ahead of the visible video and refills as you scroll.
FEED_PAGE_SIZE = _env_int("FEED_PAGE_SIZE", 10)
FEED_PAGE_SIZE_MAX = _env_int("FEED_PAGE_SIZE_MAX", 30)

# ---------------------------------------------------------------------------
# Age assurance
# ---------------------------------------------------------------------------
# "attestation" = the self-declared 18+ interstitial (what ships now).
# "provider"    = a real age-verification vendor, required in the UK, and in
# ~20 US states. The gate is written against a seam so turning this on is a
# config flip plus one service module — see services/age_gate.py.
AGE_ASSURANCE_MODE = _env("AGE_ASSURANCE_MODE", "attestation")
# Countries where self-attestation is NOT legally sufficient. Listing a code
# here makes the gate demand verified proof instead of a checkbox.
AGE_VERIFICATION_COUNTRIES = [
    c.strip().upper()
    for c in _env("AGE_VERIFICATION_COUNTRIES", "").split(",")
    if c.strip()
]

# ---------------------------------------------------------------------------
# Content Security Policy
# ---------------------------------------------------------------------------
# Owned HERE rather than at the Caddy edge, so a policy change ships with the
# code that needs it instead of needing a cross-team edge round-trip (the
# media-src fix on 2026-08-09 cost exactly that).
#
# The media/image origins are DERIVED from MEDIA_CDN_BASE, so moving Amorae to
# its own adult-designated CDN updates the policy automatically — one env var,
# not two edits that can drift apart.
#
# Migration note: while the edge ALSO sends a CSP, browsers enforce the
# intersection of both headers. So shipping this is safe in either order and
# can only tighten, never loosen. `frame-ancestors 'none'` is deliberately
# duplicated here and at the edge — clickjacking protection should not depend
# on this app being correct.
_CSP_IMG_EXTRA = _env(
    "CSP_IMG_EXTRA", "https://replicate.delivery https://gateway.storjshare.io"
)


def _build_csp() -> str:
    media = MEDIA_CDN_BASE.rstrip("/")
    img = " ".join(part for part in ["'self'", "data:", _CSP_IMG_EXTRA, media] if part)
    return "; ".join(
        [
            "default-src 'self'",
            # 'unsafe-inline' is inherited from the edge policy. Nothing we
            # ship needs it (feed.js and chat.js are external files) — worth
            # dropping, but as its own change with its own verification.
            "script-src 'self' 'unsafe-inline'",
            "style-src 'self' 'unsafe-inline'",
            f"img-src {img}",
            f"media-src 'self' {media}",
            "connect-src 'self'",
            "frame-ancestors 'none'",
            "base-uri 'none'",
            "form-action 'self'",
        ]
    )


CONTENT_SECURITY_POLICY = _env("CONTENT_SECURITY_POLICY", _build_csp())

# Max accepted request body. Our forms carry a ticket, a tier name, or a
# short report — kilobytes at most — so 256 KB is generous headroom while
# still bounding the CVE-2026-54283 DoS vectors (a huge urlencoded field, or
# hundreds of thousands of tiny ones). 0 disables the check. Revisit only if
# a future endpoint legitimately accepts a large body (e.g. media upload),
# which would want its own per-route limit rather than raising this global.
MAX_REQUEST_BODY_BYTES = _env_int("MAX_REQUEST_BODY_BYTES", 256 * 1024)

# CORS
CORS_ORIGINS = _env("CORS_ORIGINS", "*")

# Sentry (→ sentry.rishi.yral.com, never apm.yral.com — Rule 5)
SENTRY_DSN = _env("SENTRY_DSN")
SENTRY_ENVIRONMENT = _env("SENTRY_ENVIRONMENT", ENVIRONMENT)

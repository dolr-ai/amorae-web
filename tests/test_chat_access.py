"""Anonymous web chat + rate limiting.

The chat funnel must work without the mobile app: pass the 18+ gate, get an
anonymous session, chat. And the message endpoint — the one that spends LLM
tokens and is now publicly reachable — must be rate-limited.

Mostly DB-free; the one path that writes a session monkeypatches the repo.

Run: PYTHONPATH=app pytest tests/ -v
"""

from types import SimpleNamespace

import pytest
from starlette.testclient import TestClient

import config
from services import rate_limit


@pytest.fixture(scope="module")
def client():
    from main import app

    return TestClient(app)


@pytest.fixture(autouse=True)
def _clear_limiter():
    rate_limit.reset()
    yield
    rate_limit.reset()


# --------------------------------------------------------------- rate limiter


def test_rate_limiter_allows_up_to_the_cap_then_blocks():
    key = "1.2.3.4"
    assert all(rate_limit.check(key, 3, 300) for _ in range(3))
    assert rate_limit.check(key, 3, 300) is False  # 4th over the cap of 3


def test_rate_limiter_is_per_key():
    assert rate_limit.check("a", 1, 300) is True
    assert rate_limit.check("a", 1, 300) is False
    assert rate_limit.check("b", 1, 300) is True  # different key, own budget


def test_rate_limiter_window_expiry(monkeypatch):
    """Hits older than the window fall out of the count."""
    t = {"now": 1000.0}
    monkeypatch.setattr(rate_limit.time, "time", lambda: t["now"])
    assert rate_limit.check("k", 2, 10) is True
    assert rate_limit.check("k", 2, 10) is True
    assert rate_limit.check("k", 2, 10) is False
    t["now"] += 11  # window passes
    assert rate_limit.check("k", 2, 10) is True


def test_client_key_prefers_cloudflare_header():
    req = SimpleNamespace(
        headers={"CF-Connecting-IP": "9.9.9.9", "X-Forwarded-For": "1.1.1.1"},
        client=SimpleNamespace(host="127.0.0.1"),
    )
    assert rate_limit.client_key(req) == "9.9.9.9"


# --------------------------------------------------------------- start-chat


def test_start_chat_shows_age_gate_when_not_18plus(client):
    """No consent cookie → the 18+ gate, returning to start-chat after."""
    r = client.get("/tara/start-chat")
    assert r.status_code == 200
    assert "This site is for adults" in r.text
    assert "/tara/start-chat" in r.text  # the post-gate `next`


def test_start_chat_unknown_persona_404(client):
    assert client.get("/nobody/start-chat").status_code == 404


def test_start_chat_anon_disabled_redirects_to_app_login(client, monkeypatch):
    """18+ passed, no session, anon chat OFF → send to the app-handoff landing,
    not a dead chat page."""
    monkeypatch.setattr(config, "ALLOW_ANON_CHAT", False)
    monkeypatch.setattr(config, "DEV_ALLOW_ANON", False)
    client.cookies.set(config.CONSENT_COOKIE_NAME, "1")
    r = client.get("/tara/start-chat", follow_redirects=False)
    client.cookies.clear()
    assert r.status_code == 303
    assert r.headers["location"] == "/tara?e=login"


def test_start_chat_creates_anon_session_when_enabled(client, monkeypatch):
    """18+ passed, no session, anon chat ON → mint an anonymous session and go
    to chat. The session write is stubbed to keep this DB-free."""
    monkeypatch.setattr(config, "ALLOW_ANON_CHAT", True)

    created = {}

    async def fake_create(session_id, user_id, is_anonymous, bot_handle):
        created.update(
            session_id=session_id, is_anonymous=is_anonymous, bot_handle=bot_handle
        )

    from routes import chat as chat_route

    monkeypatch.setattr(chat_route.session_repo, "create", fake_create)
    client.cookies.set(config.CONSENT_COOKIE_NAME, "1")
    r = client.get("/tara/start-chat", follow_redirects=False)
    client.cookies.clear()

    assert r.status_code == 303
    assert r.headers["location"] == "/tara/chat"
    assert created["is_anonymous"] is True
    assert created["bot_handle"] == "tara"
    assert config.SESSION_COOKIE_NAME in r.cookies  # session cookie set

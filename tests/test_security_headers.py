"""CSP guard tests.

Amorae sets its own Content-Security-Policy rather than inheriting one from
the Caddy edge, so a policy change ships with the code that needs it. The
trade is that a regression here would ship an adult surface — one that will
carry payment flows — with NO policy at all, where previously the edge would
have caught us. These tests are that safety net: a missing or loosened CSP
fails the build instead of reaching production.

Run: PYTHONPATH=app pytest tests/ -v
"""

import pytest
from starlette.testclient import TestClient

import config


@pytest.fixture(scope="module")
def client():
    """No `with` block, deliberately — that would run the lifespan and open a
    real amorae_db pool. These tests are DB-free like the rest of the suite,
    and every route they touch renders a template without a query."""
    from main import app

    return TestClient(app)


def _csp(response) -> str:
    assert "content-security-policy" in response.headers, "CSP header is missing"
    return response.headers["content-security-policy"]


@pytest.mark.parametrize("path", ["/exit", "/privacy", "/terms"])
def test_every_page_carries_a_csp(client, path):
    response = client.get(path)
    assert response.status_code == 200
    assert _csp(response)


def test_static_assets_carry_the_csp_too(client):
    """The StaticFiles mount sits inside the middleware stack, so /static/*
    must be covered as well — feed.js is served from there."""
    assert _csp(client.get("/static/feed.js"))


def test_policy_locks_down_the_directives_that_matter(client):
    policy = _csp(client.get("/exit"))
    for directive in (
        "default-src 'self'",
        "frame-ancestors 'none'",  # clickjacking — never loosen
        "base-uri 'none'",
        "form-action 'self'",
        "connect-src 'self'",
    ):
        assert directive in policy, f"missing or loosened: {directive}"


def test_policy_allows_the_media_cdn_the_feed_actually_uses(client):
    """The bug this whole file exists because of: no `media-src` meant it fell
    back to `default-src 'self'` and every video on the homepage was blocked."""
    policy = _csp(client.get("/exit"))
    cdn = config.MEDIA_CDN_BASE.rstrip("/")
    assert "media-src" in policy, "no media-src → video falls back to default-src"
    assert f"media-src 'self' {cdn}" in policy
    assert cdn in policy.split("img-src")[1].split(";")[0], "posters would be blocked"


def test_policy_follows_the_cdn_config(monkeypatch):
    """Moving Amorae to its own adult-designated CDN must update the policy
    automatically — a second place to edit is a second place to forget."""
    monkeypatch.setattr(config, "MEDIA_CDN_BASE", "https://cdn-amorae.example.com")
    rebuilt = config._build_csp()
    assert "media-src 'self' https://cdn-amorae.example.com" in rebuilt
    assert "cdn-yral-sfw" not in rebuilt


def test_trailing_slash_on_cdn_base_does_not_corrupt_the_policy(monkeypatch):
    """A CSP source with a trailing slash is a path pattern, not an origin,
    and silently stops matching."""
    monkeypatch.setattr(config, "MEDIA_CDN_BASE", "https://cdn-amorae.example.com/")
    assert "media-src 'self' https://cdn-amorae.example.com;" in (
        config._build_csp() + ";"
    )


def test_policy_is_env_overridable():
    """Kept so the edge can reclaim ownership, or a policy can be hot-patched
    without a deploy."""
    assert isinstance(config.CONTENT_SECURITY_POLICY, str)
    assert config.CONTENT_SECURITY_POLICY.startswith("default-src")

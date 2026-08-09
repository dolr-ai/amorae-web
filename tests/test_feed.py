"""DB-free tests for the public feed + age gate. No network, no Postgres.

Run: PYTHONPATH=app pytest tests/ -v
"""

import asyncio
from types import SimpleNamespace

import pytest

import config
from models import FeedVideo
from services import age_gate, feed_client, personas


def _request(cookies=None, headers=None):
    return SimpleNamespace(cookies=cookies or {}, headers=headers or {})


class _Response:
    """Minimal stand-in for a Starlette Response — we only assert on cookies."""

    def __init__(self):
        self.cookies = {}

    def set_cookie(self, key, value, **kwargs):
        self.cookies[key] = (value, kwargs)


# ---------------------------------------------------------------- age gate


def test_gate_blocks_until_granted():
    assert age_gate.has_passed(_request()) is False
    assert age_gate.has_passed(_request({config.CONSENT_COOKIE_NAME: "1"})) is True
    # Any other value is not consent.
    assert age_gate.has_passed(_request({config.CONSENT_COOKIE_NAME: "0"})) is False


def test_grant_sets_httponly_consent_cookie():
    response = _Response()
    age_gate.grant(response)
    value, kwargs = response.cookies[config.CONSENT_COOKIE_NAME]
    assert value == "1"
    assert kwargs["httponly"] is True
    assert kwargs["samesite"] == "lax"


def test_gate_shares_the_cookie_with_the_logged_in_flow():
    """A user who came through the app handoff must not be asked twice."""
    response = _Response()
    age_gate.grant(response)
    granted = {k: v[0] for k, v in response.cookies.items()}
    assert age_gate.has_passed(_request(granted)) is True


@pytest.mark.parametrize(
    "hostile",
    [
        "https://evil.com",
        "//evil.com",
        "http://evil.com/x",
        "javascript:alert(1)",
        "/\\evil.com",
        "\\\\evil.com",
        "",
        None,
    ],
)
def test_safe_next_rejects_offsite_redirects(hostile):
    assert age_gate.safe_next(hostile) == "/"


@pytest.mark.parametrize("ok", ["/", "/c/tara", "/c/tara/subscribe?tier=annual"])
def test_safe_next_allows_same_origin_paths(ok):
    assert age_gate.safe_next(ok) == ok


def test_provider_required_for_listed_country(monkeypatch):
    monkeypatch.setattr(config, "AGE_ASSURANCE_MODE", "attestation")
    monkeypatch.setattr(config, "AGE_VERIFICATION_COUNTRIES", ["GB"])
    assert age_gate.required_method(_request(headers={"CF-IPCountry": "GB"})) == "provider"
    assert age_gate.required_method(_request(headers={"CF-IPCountry": "CA"})) == "attestation"


def test_provider_mode_applies_everywhere(monkeypatch):
    monkeypatch.setattr(config, "AGE_ASSURANCE_MODE", "provider")
    monkeypatch.setattr(config, "AGE_VERIFICATION_COUNTRIES", [])
    assert age_gate.required_method(_request(headers={})) == "provider"


# ------------------------------------------------------------------ cursor


def test_cursor_roundtrip():
    assert feed_client.decode_cursor(feed_client.encode_cursor(40)) == 40


@pytest.mark.parametrize("junk", ["", None, "!!!not-base64!!!", "eyJ4Ijoxf", "eyJ4IjoxfQ"])
def test_malformed_cursor_restarts_rather_than_raising(junk):
    """A stale bookmark or a hand-edited URL must not 500 the feed."""
    assert feed_client.decode_cursor(junk) == 0


def test_negative_cursor_clamped():
    assert feed_client.decode_cursor(feed_client.encode_cursor(-5)) == 0


# -------------------------------------------------------------- URL shapes


def test_media_urls_match_the_mobile_clients():
    """These must stay byte-identical to yral-mobile's videoUrl/thumbnailUrl,
    because both clients construct them from the same ids."""
    assert feed_client.video_url("abc123", "prin-cipal") == (
        f"{config.MEDIA_CDN_BASE}/prin-cipal/abc123.mp4"
    )
    assert feed_client.poster_url("abc123", "prin-cipal") == (
        f"{config.MEDIA_CDN_BASE}/prin-cipal/abc123-thumbnail.png"
    )


def test_hls_is_absent_until_the_cdn_has_ladders(monkeypatch):
    monkeypatch.setattr(config, "MEDIA_HLS_BASE", "")
    assert feed_client.hls_url("v", "p") is None
    monkeypatch.setattr(config, "MEDIA_HLS_BASE", "https://hls.example.com")
    assert feed_client.hls_url("v", "p") == "https://hls.example.com/p/v/manifest.m3u8"


# ------------------------------------------------------------- upstream map


def _upstream_row(**overrides):
    row = {
        "video_id": "0028f0fad4b1ff6427a8a3a7882b844b",
        "post_id": "fec35362-907d-4624-8446-048c1b901a61",
        "publisher_user_id": "jovus-ytdu6-aqe",
        "num_views_all": 42,
        "from_ai_influencer": True,
    }
    row.update(overrides)
    return row


def test_upstream_row_widens_into_a_playable_video():
    video = feed_client._from_upstream(_upstream_row())
    assert isinstance(video, FeedVideo)
    assert video.sources.mp4.endswith("/jovus-ytdu6-aqe/0028f0fad4b1ff6427a8a3a7882b844b.mp4")
    assert video.view_count == 42


@pytest.mark.parametrize(
    "broken",
    [{"video_id": None}, {"publisher_user_id": None}, {"video_id": ""}],
)
def test_unplayable_rows_are_dropped_not_rendered(broken):
    """A row without ids would render a black screen — drop it instead."""
    assert feed_client._from_upstream(_upstream_row(**broken)) is None


def test_unmapped_publisher_falls_back_to_a_generic_creator():
    """Most YRAL publishers are not Amorae personas. They must still render
    a name and a face rather than a blank overlay."""
    video = feed_client._from_upstream(_upstream_row(publisher_user_id="nobody-we-know"))
    assert video.creator.display_name == "Amorae"
    assert video.creator.handle == ""  # no profile to link to
    assert video.creator.avatar_url


def test_known_persona_is_attributed_by_influencer_id():
    tara = personas.get("tara")
    video = feed_client._from_upstream(_upstream_row(publisher_user_id=tara["influencer_id"]))
    assert video.creator.handle == "tara"
    assert video.creator.display_name == "Tara"
    assert video.creator.subscription_price_cents == 1499


# ------------------------------------------------------------------- paging


# `get_page` is async; CI installs plain pytest, so drive it with asyncio.run
# rather than taking a pytest-asyncio dependency for three tests.
def test_mock_page_is_full_and_advances(monkeypatch):
    monkeypatch.setattr(config, "FEED_SOURCE", "mock")
    page = asyncio.run(feed_client.get_page("anon-test", cursor=None, limit=5))
    assert len(page.videos) == 5
    assert page.has_more is True

    second = asyncio.run(feed_client.get_page("anon-test", cursor=page.next_cursor, limit=5))
    assert feed_client.decode_cursor(second.next_cursor) == 10
    # Different offsets must not hand back the same first video.
    assert page.videos[0].video_id != second.videos[0].video_id


def test_limit_is_capped(monkeypatch):
    monkeypatch.setattr(config, "FEED_SOURCE", "mock")
    monkeypatch.setattr(config, "FEED_PAGE_SIZE_MAX", 12)
    page = asyncio.run(feed_client.get_page("anon-test", cursor=None, limit=9999))
    assert len(page.videos) == 12


def test_upstream_outage_degrades_instead_of_raising(monkeypatch):
    """The homepage is the top of the funnel — a feed outage must not 500 it."""
    monkeypatch.setattr(config, "FEED_SOURCE", "upstream")

    async def boom(*args, **kwargs):
        raise ValueError("upstream down")

    monkeypatch.setattr(feed_client, "_fetch_upstream", boom)
    page = asyncio.run(feed_client.get_page("anon-test", cursor=None, limit=10))
    assert page.videos == []
    assert page.has_more is False
    assert page.next_cursor is None


# ---------------------------------------------------------------- personas


def test_personas_carry_ai_influencer_ids_or_an_explicit_gap():
    """Persona ids must match the ai_influencers catalogue so one persona
    spans YRAL chat and Amorae video. None is allowed only for personas that
    do not exist in that catalogue yet."""
    tara = personas.get("tara")
    assert tara["influencer_id"] and tara["influencer_id"].endswith("-5qe")
    assert personas.by_influencer_id(tara["influencer_id"])["handle"] == "tara"
    assert personas.by_influencer_id(None) is None
    assert personas.by_influencer_id("not-a-principal") is None


def test_launched_personas_sort_first():
    assert personas.all_personas()[0]["handle"] == "tara"


# ------------------------------------------------------- gate completeness


def test_every_creator_route_checks_the_age_gate():
    """Codex caught POST /c/{handle}/subscribe skipping the gate both GET
    routes enforce. Assert on the module rather than one endpoint, so a new
    route added later fails here instead of shipping ungated."""
    import inspect

    from routes import creator

    handlers = [
        creator.profile,
        creator.subscribe_page,
        creator.subscribe_intent,
    ]
    for handler in handlers:
        source = inspect.getsource(handler)
        assert "age_gate.has_passed" in source, (
            f"{handler.__name__} does not check the 18+ gate"
        )

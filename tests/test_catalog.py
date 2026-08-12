"""Catalogue client + persona merge (PR #1 — data layer onto ai_influencers).

DB-free. The catalogue client is stubbed; no live v2 calls.

Run: PYTHONPATH=app pytest tests/ -v
"""

import pytest

from services import influencers_client, personas

_TARA_ID = "qi6gd-esmrx-v2oyd-7fwhm-ibfs5-trflm-xm3iy-xq6d3-3hmwu-jb7tk-5qe"


@pytest.fixture(autouse=True)
def _reset_snapshot():
    """Each test controls the catalogue snapshot explicitly."""
    influencers_client._snapshot = []
    influencers_client._fetched_at = 0.0
    yield
    influencers_client._snapshot = []
    influencers_client._fetched_at = 0.0


def _seed(*entries):
    influencers_client._snapshot = list(entries)


# ------------------------------------------------------------- merge behaviour


def test_persona_built_from_catalogue_plus_presentation():
    """Identity from the catalogue; price + adult copy + handle from amorae."""
    _seed({"id": _TARA_ID, "display_name": "Tara", "surface": "both"})
    tara = personas.get("tara")
    assert tara is not None
    assert tara["influencer_id"] == _TARA_ID  # catalogue
    assert tara["display_name"] == "Tara"  # catalogue
    assert tara["surface"] == "both"  # catalogue
    assert tara["subscription_price_cents"] == 1499  # amorae presentation
    assert "Toronto" in tara["bio"]  # amorae presentation
    assert tara["is_launched"] is True


def test_catalogue_display_name_overrides_the_fallback():
    _seed({"id": _TARA_ID, "display_name": "Tara (updated)", "surface": "web"})
    assert personas.get("tara")["display_name"] == "Tara (updated)"


def test_web_influencer_without_presentation_is_not_rendered(caplog):
    """A web-flagged influencer we have no config for is surfaced as a warning,
    not rendered half-configured."""
    _seed(
        {"id": _TARA_ID, "display_name": "Tara", "surface": "both"},
        {"id": "someone-new-principal", "display_name": "Newbie", "surface": "web"},
    )
    handles = {p["handle"] for p in personas.all_personas()}
    assert "tara" in handles
    assert not any(p["display_name"] == "Newbie" for p in personas.all_personas())


def test_persona_not_in_catalogue_is_absent():
    """Only influencers actually returned for the web surface render."""
    _seed({"id": "different-principal", "display_name": "Other", "surface": "web"})
    assert personas.get("tara") is None  # Tara's id not in this snapshot


# ------------------------------------------------------------------- fallback


def test_fallback_to_presentation_when_catalogue_empty(caplog):
    """Cold start / v2 down → render presentation entries alone so the site
    still works (logged, not silent)."""
    influencers_client._snapshot = []  # unavailable
    tara = personas.get("tara")
    assert tara is not None
    assert tara["influencer_id"] == _TARA_ID
    assert tara["display_name"] == "Tara"  # the fallback display name


def test_by_influencer_id_and_sorting():
    _seed({"id": _TARA_ID, "display_name": "Tara", "surface": "both"})
    assert personas.by_influencer_id(_TARA_ID)["handle"] == "tara"
    assert personas.by_influencer_id(None) is None
    assert personas.by_influencer_id("nope") is None
    assert personas.all_personas()[0]["handle"] == "tara"


# --------------------------------------------------------------- client fetch


def test_refresh_requests_web_surface_and_caches(monkeypatch):
    """refresh() must ask for surface=web and store the returned list."""
    captured = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"influencers": [{"id": _TARA_ID, "display_name": "Tara"}], "total": 1}

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url, params=None):
            captured["url"] = url
            captured["params"] = params
            return _Resp()

    monkeypatch.setattr(influencers_client.httpx, "AsyncClient", _Client)
    import asyncio

    ok = asyncio.run(influencers_client.refresh())
    assert ok is True
    assert captured["params"] == {"surface": "web"}
    assert captured["url"].endswith("/api/v1/influencers")
    assert influencers_client.snapshot()[0]["id"] == _TARA_ID


def test_refresh_keeps_last_good_snapshot_on_failure(monkeypatch):
    _seed({"id": _TARA_ID, "display_name": "Tara", "surface": "both"})

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            pass

        async def get(self, url, params=None):
            raise influencers_client.httpx.ConnectError("v2 down")

    monkeypatch.setattr(influencers_client.httpx, "AsyncClient", _Client)
    import asyncio

    ok = asyncio.run(influencers_client.refresh())
    assert ok is False
    # snapshot preserved, not blanked
    assert influencers_client.snapshot()[0]["id"] == _TARA_ID

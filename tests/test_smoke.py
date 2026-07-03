"""DB-free smoke tests — pure logic + app wiring. No network, no Postgres.

Run: PYTHONPATH=app pytest tests/ -v
"""

from types import SimpleNamespace

import config
import sessions
from services import geo, personas


def test_persona_lookup():
    assert personas.get("tara")["display_name"] == "Tara"
    assert personas.get("TARA")["handle"] == "tara"  # case-insensitive
    assert personas.get("nobody") is None


def test_persona_has_unconstrained_prompt():
    # The web surface persona must NOT be SFW-constrained (that's the app).
    assert "system_prompt" in personas.get("tara")
    assert personas.get("tara")["system_prompt"]


def test_geo_default_open(monkeypatch):
    monkeypatch.setattr(config, "GEO_BLOCKED_COUNTRIES", [])
    req = SimpleNamespace(headers={"CF-IPCountry": "IN"})
    assert geo.is_blocked(req) is False


def test_geo_blocks_listed_country(monkeypatch):
    monkeypatch.setattr(config, "GEO_BLOCKED_COUNTRIES", ["IN"])
    assert geo.is_blocked(SimpleNamespace(headers={"CF-IPCountry": "IN"})) is True
    assert geo.is_blocked(SimpleNamespace(headers={"CF-IPCountry": "US"})) is False
    assert geo.is_blocked(SimpleNamespace(headers={})) is False  # no header, not blocked


def test_session_id_unique_and_opaque():
    a, b = sessions.new_session_id(), sessions.new_session_id()
    assert a != b
    assert len(a) >= 32


def test_app_registers_expected_routes():
    from main import app

    paths = {r.path for r in app.routes}
    assert "/health" in paths and "/healthz" in paths
    assert "/privacy" in paths and "/terms" in paths and "/report" in paths
    assert "/{bot_handle}" in paths
    assert "/{bot_handle}/chat" in paths
    assert "/{bot_handle}/continue" in paths
    assert "/{bot_handle}/message" in paths

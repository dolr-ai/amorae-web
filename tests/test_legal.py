"""Legal / compliance surface tests — the CCBill/Segpay merchant review set.

DB-free: every route here renders a template without a query.

Run: PYTHONPATH=app pytest tests/ -v
"""

import pytest
from starlette.testclient import TestClient

import config
from services import legal_content


@pytest.fixture(scope="module")
def client():
    from main import app

    return TestClient(app)


# --------------------------------------------------------------- content set


REQUIRED_POLICIES = [
    "terms",
    "privacy",
    "cookies",
    "refunds",
    "chargebacks",
    "dmca",
    "2257",
    "aup",
]


@pytest.mark.parametrize("slug", REQUIRED_POLICIES)
def test_every_required_policy_exists_and_renders(client, slug):
    """CCBill items 5–14: the full policy set must be present and reachable."""
    assert legal_content.get(slug) is not None
    response = client.get(f"/legal/{slug}")
    assert response.status_code == 200
    # Jinja escapes `&` in titles to `&amp;`; compare against the escaped form.
    title = legal_content.POLICIES[slug]["title"].replace("&", "&amp;")
    assert title in response.text


def test_unknown_policy_is_404_not_500(client):
    assert client.get("/legal/does-not-exist").status_code == 404


def test_privacy_and_terms_aliases_still_work(client):
    """The age gate and old links point at /privacy and /terms — keep them."""
    assert client.get("/privacy").status_code == 200
    assert client.get("/terms").status_code == 200


# ------------------------------------------------------------ entity plumbing


def test_entity_is_named_gobazzinga(monkeypatch):
    """Every policy that names an operator must say GoBazzinga Inc, from config
    — never a hard-coded string that could drift."""
    assert config.LEGAL_ENTITY == "GoBazzinga Inc"
    terms = legal_content.get("terms")
    body = " ".join(
        v if isinstance(v, str) else " ".join(v) for _, v in terms["blocks"]
    )
    assert "GoBazzinga Inc" in body


def test_blank_required_fields_render_a_visible_marker(monkeypatch):
    """A missing address/email must be obvious to the reviewer and to Rishi —
    a visible «TO BE COMPLETED» marker, never a silent empty string."""
    monkeypatch.setattr(config, "LEGAL_ENTITY_ADDRESS", "")
    monkeypatch.setattr(config, "SUPPORT_EMAIL", "")
    body = " ".join(
        v if isinstance(v, str) else " ".join(v)
        for _, v in legal_content.get("2257")["blocks"]
    )
    assert "TO BE COMPLETED" in body


def test_filled_fields_replace_the_marker(monkeypatch):
    monkeypatch.setattr(config, "LEGAL_ENTITY_ADDRESS", "1 Real St, Dover DE")
    body = " ".join(
        v if isinstance(v, str) else " ".join(v)
        for _, v in legal_content.get("2257")["blocks"]
    )
    assert "1 Real St, Dover DE" in body
    assert "TO BE COMPLETED" not in body


def test_draft_banner_shows_until_legal_signs_off(client, monkeypatch):
    monkeypatch.setattr(config, "LEGAL_COPY_APPROVED", False)
    assert "DRAFT" in client.get("/legal/terms").text


# ---------------------------------------------------------------- 2257 / AUP


def test_2257_states_ai_generated_no_real_performers(client):
    """The favourable-for-approval framing: AI-only, no real performers."""
    body = client.get("/legal/2257").text.lower()
    assert "computer-generated" in body or "ai-generated" in body.replace("-", "")
    assert "no real" in body or "does not depict any real" in body


def test_aup_has_zero_tolerance_csam_language(client):
    body = client.get("/legal/aup").text
    assert "CSAM" in body or "child sexual abuse" in body.lower()
    assert "18" in body


# ----------------------------------------------------------- footer on pages


@pytest.mark.parametrize("path", ["/support", "/legal/terms", "/report"])
def test_footer_carries_all_policies_and_entity(client, path):
    """CCBill: policy links + entity must appear on EVERY page."""
    body = client.get(path).text
    for slug in ("cookies", "refunds", "dmca", "2257", "aup"):
        assert f"/legal/{slug}" in body
    assert config.LEGAL_ENTITY in body


# ------------------------------------------------------------------ support


def test_support_page_shows_billing_descriptor_and_cancel(client):
    body = client.get("/support").text
    assert config.BILLING_DESCRIPTOR in body
    assert "cancel" in body.lower()
    assert config.CCBILL_SUPPORT_URL in body


def test_support_form_accepts_a_message(client):
    r = client.post(
        "/support",
        data={"email": "a@b.com", "subject": "hi", "message": "please help"},
    )
    assert r.status_code == 200
    assert "received" in r.text.lower()


# --------------------------------------------------------------- checkout


def _consent(client):
    # The consent cookie is Secure, and the TestClient speaks http, so a
    # normal round-trip wouldn't send it back. Set it directly — it's exactly
    # the "18+ confirmed" state the gate and consent check both read.
    client.cookies.set(config.CONSENT_COOKIE_NAME, "1")


def test_checkout_discloses_recurring_billing_and_descriptor(client):
    _consent(client)
    body = client.get("/c/tara/subscribe").text
    assert "recurring" in body.lower()
    assert config.BILLING_DESCRIPTOR in body
    assert "cancel" in body.lower()


def test_subscribe_requires_recurring_consent(client):
    """Server-side enforcement — a POST without consent must not record intent,
    even though the client also disables the button."""
    _consent(client)
    no_consent = client.post(
        "/c/tara/subscribe",
        data={"tier": "quarterly", "rail": "card"},
        follow_redirects=False,
    )
    assert no_consent.status_code == 303
    assert "e=consent" in no_consent.headers["location"]

    with_consent = client.post(
        "/c/tara/subscribe",
        data={"tier": "quarterly", "rail": "card", "consent": "on"},
    )
    assert with_consent.status_code == 200
    assert "list" in with_consent.text.lower()


# ---------------------------------------------------------- prelaunch / about


def test_about_page_explains_the_concept(client):
    body = client.get("/about").text
    assert client.get("/about").status_code == 200
    assert "AI companions" in body or "AI-generated" in body
    for step in ("Discover", "Connect", "Subscribe"):
        assert step in body


def test_prelaunch_banner_renders_when_not_live(client):
    """SITE_STATUS defaults to prelaunch, so standard pages show the
    early-access banner + About link. Going live is a one-env flip that drops
    it (verified manually; the global `is_prelaunch` gates the markup)."""
    body = client.get("/support").text
    assert "prelaunch-bar" in body
    assert 'href="/about"' in body


def test_about_stays_public_and_carries_no_gate(client):
    """A reviewer must be able to read what the business is without the age
    gate blocking it — the page carries no adult media."""
    r = client.get("/about")
    assert r.status_code == 200
    assert "This site is for adults" not in r.text  # not the gate

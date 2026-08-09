"""Shared Jinja2 templates instance. Imported by every route that renders
HTML so the templates dir is configured in one place.

Brand + legal-entity values are registered as GLOBALS so the shared footer
(entity, address, support email, policy links) renders on every page without
each route having to pass them. The processor requires these on every page,
so a global is the right place — one source, no per-route drift.
"""

import os

from fastapi.templating import Jinja2Templates

import config

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_TEMPLATES_DIR)

templates.env.globals.update(
    brand=config.BRAND_NAME,
    legal_entity=config.LEGAL_ENTITY,
    legal_country=config.LEGAL_ENTITY_COUNTRY,
    legal_address=config.LEGAL_ENTITY_ADDRESS,
    support_email=config.SUPPORT_EMAIL,
    billing_descriptor=config.BILLING_DESCRIPTOR,
)

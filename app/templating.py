"""Shared Jinja2 templates instance. Imported by every route that renders
HTML so the templates dir is configured in one place."""

import os

from fastapi.templating import Jinja2Templates

_TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
templates = Jinja2Templates(directory=_TEMPLATES_DIR)

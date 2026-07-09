"""Server-side geo-gate. DEFAULT OPEN (decision #13).

The capability ships from day one but blocks nothing until a country
code is added to GEO_BLOCKED_COUNTRIES. Country comes from Cloudflare's
`CF-IPCountry` header at the edge (all *.rishi.yral.com traffic is
Cloudflare-routed). Restricting a region later is a config flip, not new
code.
"""

from fastapi import Request

import config


def client_country(request: Request) -> str | None:
    country = request.headers.get("CF-IPCountry")
    return country.upper() if country else None


def is_blocked(request: Request) -> bool:
    if not config.GEO_BLOCKED_COUNTRIES:
        return False  # default open
    country = client_country(request)
    return bool(country and country in config.GEO_BLOCKED_COUNTRIES)

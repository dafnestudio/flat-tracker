"""
Rentola (rentola.nl) - a large aggregator of rental ads.

The overview pages contain a block of structured data (JSON-LD, the same
data search engines read) with address, postcode, price, size and bedrooms
for every ad, so we read that instead of the visible page layout.
"""

import json

from common import get_soup, make_listing, parse_postcode

NAME = "Rentola"
# Rentola's own district pages; we read the first few pages of each.
START_PAGES = [
    "https://rentola.nl/huren/amsterdam-centrum",
    "https://rentola.nl/huren/amsterdam-oost",
    "https://rentola.nl/huren/amsterdam-west",
    "https://rentola.nl/huren/amsterdam-noord",
    "https://rentola.nl/huren/amsterdam",
]
PAGES_EACH = 5


def collect():
    listings, seen = [], set()
    for start in START_PAGES:
        for page in range(1, PAGES_EACH + 1):
            try:
                soup = get_soup(start if page == 1 else "%s?page=%d" % (start, page))
            except Exception:
                if start == START_PAGES[-1] and page == 1:
                    raise          # the main page failing is a real problem
                break              # a missing district page is not
            new_on_page = 0
            for script in soup.find_all("script", type="application/ld+json"):
                try:
                    data = json.loads(script.string or "")
                except ValueError:
                    continue
                if not isinstance(data, dict):
                    continue
                main = data.get("mainEntity")
                if not isinstance(main, dict):
                    continue          # other data blocks, such as the FAQ
                items = main.get("itemListElement") or []
                for entry in items:
                    item = entry.get("item") or {}
                    offer = item.get("offers") or {}
                    home = offer.get("itemOffered") or {}
                    url = item.get("url")
                    if not url or "/listings/" not in url or url in seen:
                        continue
                    seen.add(url)
                    new_on_page += 1
                    place = home.get("address") or {}
                    street = place.get("streetAddress") or ""
                    listings.append(make_listing(
                        NAME, "rent", url,
                        address=street.replace(", Netherlands", ""),
                        price=offer.get("price"),
                        m2=_number(home.get("floorSize")),
                        bedrooms=_number(home.get("numberOfBedrooms")),
                        postcode=parse_postcode(street),
                        posted=(offer.get("validFrom") or "")[:10] or None,
                        title=item.get("name", ""),
                        type_text=home.get("@type", ""),   # Apartment / House / Room
                        city=place.get("addressLocality"),
                    ))
            if new_on_page == 0:
                break
    return listings


def _number(value):
    """JSON-LD wraps numbers as {"value": 32}."""
    if isinstance(value, dict):
        value = value.get("value")
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None

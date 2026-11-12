"""vb&t Verhuurmakelaars - letting agency. National overview; Amsterdam kept."""

import re

from common import (cards_from_links, get_soup, make_listing, parse_bedrooms,
                    parse_m2, parse_price)

NAME = "VB&T"
OVERVIEW = "https://vbtverhuurmakelaars.nl/woningen"
MAX_PAGES = 15


def collect():
    listings = []
    for page in range(1, MAX_PAGES + 1):
        soup = get_soup(OVERVIEW if page == 1 else "%s/%d" % (OVERVIEW, page))
        cards = cards_from_links(soup, OVERVIEW, r"^/woning/[^/]+$")
        if not cards:
            break
        for url, text, _ in cards:
            if "/woning/amsterdam-" not in url:
                continue
            # "Beschikbaar Amsterdam Straatnaam 12 EUR 1.295,- Soort object ..."
            match = re.search(r"Amsterdam\s+(.*?)\s*€", text)
            bedrooms, estimated = parse_bedrooms(text)
            kind_of_home = re.search(r"Soort object\s+(\S+)", text)
            listings.append(make_listing(
                NAME, "rent", url,
                (match.group(1) + ", Amsterdam") if match else "Amsterdam",
                parse_price(text), parse_m2(text), bedrooms, estimated,
                text=text, status_text=text[:30], city="Amsterdam",
                type_text=kind_of_home.group(1) if kind_of_home else ""))
        if not soup.find("a", href=re.compile(r"^/woningen/%d$" % (page + 1))):
            break
    return listings

"""
Makelaardij Van der Linden - agency with rentals and homes for sale.
Each overview shows everything on a single page.
"""

import re

from common import (cards_from_links, get_soup, make_listing, parse_m2,
                    parse_price)

NAME = "Van der Linden"
OVERVIEWS = [
    ("rent", "https://www.vanderlinden.nl/woning-huren/", r"^/huurwoning/"),
    ("buy", "https://www.vanderlinden.nl/woning-kopen/", r"^/koopwoning/"),
]


def collect():
    listings = []
    for kind, overview, link_pattern in OVERVIEWS:
        soup = get_soup(overview)
        for url, text, _ in cards_from_links(soup, overview, link_pattern):
            # "Wijnsilostraat 12 Amsterdam EUR 1.910 per maand 85 m2 85 m2 3 A"
            match = re.match(r"(.*?)\s+Amsterdam\s*€", text)
            if not match:
                continue                  # another town
            listings.append(make_listing(
                NAME, kind, url, match.group(1) + ", Amsterdam",
                parse_price(text), parse_m2(text), text=text, city="Amsterdam"))
    return listings

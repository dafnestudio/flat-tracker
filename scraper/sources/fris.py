"""Fris Real People - Amsterdam letting agency."""

import re

from common import (cards_from_links, get_soup, make_listing, parse_bedrooms,
                    parse_m2, parse_postcode, parse_price)

NAME = "Fris"
OVERVIEW = "https://fris.nl/volledige-woningaanbod/"
MAX_PAGES = 10
AD_LINK = r"/volledige-woningaanbod/(?!page/|feed/)[^/]+/$"


def collect():
    listings = []
    for page in range(1, MAX_PAGES + 1):
        soup = get_soup(OVERVIEW if page == 1 else "%spage/%d/" % (OVERVIEW, page))
        cards = cards_from_links(soup, OVERVIEW, AD_LINK)
        if not cards and page == 1:
            # Fris sometimes serves an unrelated page at this address.
            # Report that as a failure rather than as "nothing to rent".
            raise RuntimeError("Fris served a different page instead of its listings")
        if not cards:
            break
        for url, text, _ in cards:
            # "Beschikbaar Weteringschans 143 2 1017 SE Amsterdam EUR 2.450,00 per maand 55m2 - 3 kamers"
            parts = re.match(r"(\S+(?: onder \S+)?)\s+(.*?)\s*€", text)
            bedrooms, estimated = parse_bedrooms(text)
            listings.append(make_listing(
                NAME, "rent", url, parts.group(2) if parts else text[:60],
                parse_price(text), parse_m2(text), bedrooms, estimated,
                parse_postcode(text), text=text,
                status_text=parts.group(1) if parts else "", city="Amsterdam"))
        if not soup.find("a", href=re.compile(r"/volledige-woningaanbod/page/%d/" % (page + 1))):
            break
    return listings

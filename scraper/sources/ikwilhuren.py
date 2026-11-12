"""
ikwilhuren.nu - the rental platform of MVGM (a large property manager).
The Amsterdam overview is plain HTML, 10 ads per page.
"""

import re

from common import (cards_from_links, get_soup, make_listing, parse_bedrooms,
                    parse_m2, parse_postcode, parse_price)

NAME = "ikwilhuren.nu (MVGM)"
OVERVIEW = "https://ikwilhuren.nu/aanbod/amsterdam/"
MAX_PAGES = 40


def collect():
    listings = []
    for page in range(1, MAX_PAGES + 1):
        soup = get_soup(OVERVIEW if page == 1 else "%s?page=%d" % (OVERVIEW, page))
        cards = cards_from_links(soup, OVERVIEW, r"^/object/")
        if not cards:
            break
        for url, text, _ in cards:
            # Card text looks like:
            # "Appartement Polderweg 1 99 1093KL Amsterdam - 2Km. Beschikbaar ..."
            address = re.split(r"\s-\s\d+\s?Km|Beschikbaar", text)[0]
            home_type = address.split(" ")[0]          # "Appartement", "Woonhuis", ...
            address = address[len(home_type):].strip()
            bedrooms, estimated = parse_bedrooms(text)
            listings.append(make_listing(
                NAME, "rent", url, address, parse_price(text), parse_m2(text),
                bedrooms, estimated, parse_postcode(text), text=text,
                type_text=home_type,
                city="Amsterdam" if "/object/amsterdam-" in url else "elsewhere"))
        if not soup.find("a", href=re.compile(r"\?page=%d$" % (page + 1))):
            break
    return listings

"""
HousingAnywhere - mid-term rentals. Only the first overview page is read:
its robots.txt asks robots not to follow search pages with parameters.
"""

import re

from common import (cards_from_links, get_soup, make_listing, parse_bedrooms,
                    parse_m2, parse_price)

NAME = "HousingAnywhere"
OVERVIEW = "https://housinganywhere.com/s/Amsterdam--Netherlands/apartment-for-rent"


def collect():
    soup = get_soup(OVERVIEW)
    listings = []
    for url, text, _ in cards_from_links(soup, OVERVIEW, r"/room/ut\d+"):
        if "/Amsterdam/" not in url:
            continue                      # Amstelveen, Diemen and so on
        # "Apartment in Commelinstraat, Amsterdam 60 m2 - 1 bedroom EUR 1950 /month"
        match = re.search(r"\bin (.+?, Amsterdam)", text)
        kind_of_home = re.search(r"(\w+) in ", text)   # "Apartment in ..."
        bedrooms, estimated = parse_bedrooms(text)
        listings.append(make_listing(
            NAME, "rent", url, match.group(1) if match else "Amsterdam",
            parse_price(text), parse_m2(text), bedrooms, estimated, text=text,
            type_text=kind_of_home.group(1) if kind_of_home else "",
            city="Amsterdam"))
    return listings

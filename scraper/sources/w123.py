"""123Wonen - letting agency. Its Amsterdam overview is plain HTML."""

import re

from common import (cards_from_links, get_soup, make_listing, parse_bedrooms,
                    parse_m2, parse_price)

NAME = "123Wonen"
OVERVIEW = "https://www.123wonen.nl/huurwoningen/in/amsterdam"
MAX_PAGES = 8
AD_LINK = r"123wonen\.nl/huur/amsterdam/[^/]+/[^/]+$"


def collect():
    listings = []
    for page in range(1, MAX_PAGES + 1):
        soup = get_soup(OVERVIEW if page == 1 else "%s/page/%d" % (OVERVIEW, page))
        cards = cards_from_links(soup, OVERVIEW, AD_LINK)
        if not cards:
            break
        for url, text, _ in cards:
            # "EUR 2.350,- p/mnd Amsterdam, De Lairessestraat Max. huurperiode
            #  12 maanden Minimaal 12 maanden Type Appartement Slaapkamers 1 ..."
            street = re.search(r"Amsterdam,\s*(.*?)\s+(?:Max\.|Minimaal|Type)", text)
            kind_of_home = re.search(r"Type\s+(.*?)\s+Slaapkamers", text)
            bedrooms, estimated = parse_bedrooms(text)
            listings.append(make_listing(
                NAME, "rent", url,
                (street.group(1) + ", Amsterdam") if street else "Amsterdam",
                parse_price(text), parse_m2(text), bedrooms, estimated,
                text=text, city="Amsterdam",
                type_text=kind_of_home.group(1) if kind_of_home else ""))
        if not soup.find("a", href=re.compile(r"/in/amsterdam/page/%d$" % (page + 1))):
            break
    return listings

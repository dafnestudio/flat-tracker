"""
Rotsvast - national agency with both rentals and homes for sale.
One overview for the whole country; we keep Amsterdam only.
"""

import re

from common import (cards_from_links, get_soup, make_listing, parse_m2,
                    parse_price)

NAME = "Rotsvast"
OVERVIEW = "https://www.rotsvast.nl/wonen/"
MAX_PAGES = 25


def collect():
    listings = []
    for page in range(1, MAX_PAGES + 1):
        soup = get_soup(OVERVIEW if page == 1 else "%spage/%d/" % (OVERVIEW, page))
        cards = cards_from_links(soup, OVERVIEW, r"/wonen/object/[^/]+/?$")
        if not cards:
            break
        for url, text, _ in cards:
            # "Beschikbaar Amsterdam Straatnaam 12 80 m2 3 A EUR 400.000 k.k."
            match = re.match(r"(.*?)\s+Amsterdam\s+(.*?)\s+\d+\s*m²", text)
            if not match:
                continue                  # not in Amsterdam
            for_sale = re.search(r"k\.k\.|vrij op naam|v\.o\.n\.", text, re.I)
            listings.append(make_listing(
                NAME, "buy" if for_sale else "rent", url,
                match.group(2) + ", Amsterdam", parse_price(text), parse_m2(text),
                text=text, status_text=match.group(1), city="Amsterdam"))
        if not soup.find("a", href=re.compile(r"/wonen/page/%d/" % (page + 1))):
            break
    return listings

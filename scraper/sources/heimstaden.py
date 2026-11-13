"""
Heimstaden - large landlord. Its list covers the whole country and loads
further pages by script, so only the first page is read and Amsterdam
homes are kept.
"""

import re

from common import cards_from_links, get_soup, make_listing, parse_m2, to_int

NAME = "Heimstaden"
OVERVIEW = "https://heimstaden.com/nl/huurwoningen/?text=Amsterdam"
AD_LINK = r"/nl/huurwoningen/[^/?]+-[0-9a-f]{8}-[0-9a-f-]{27}/?$"


def collect():
    soup = get_soup(OVERVIEW)
    cards = cards_from_links(soup, OVERVIEW, AD_LINK)
    if not cards:
        raise RuntimeError("Heimstaden's page showed no listings - layout may have changed")
    listings = []
    for url, text, _ in cards:
        # "Amsterdam / Amsterdam Beemsterstraat 546 F8 1.072 euro/maand 2 67 m2 Beschikbaar Direct"
        match = re.match(r"Amsterdam\s*/\s*Amsterdam\s+(.*?)\s+([\d.]+)\s*euro/maand\s+(\d)\b", text)
        if not match:
            continue                       # another town
        rooms = int(match.group(3))
        listings.append(make_listing(
            NAME, "rent", url, match.group(1) + ", Amsterdam", to_int(match.group(2)),
            parse_m2(text), bedrooms=max(rooms - 1, 0), bedrooms_estimated=True,
            text=text, city="Amsterdam",
            status_text=re.sub(r"^.*m²\s*", "", text)))
    return listings

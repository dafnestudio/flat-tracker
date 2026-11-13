"""JLG Real Estate - Amsterdam agency with rentals and homes for sale."""

import re

from common import (cards_from_links, get_soup, make_listing, parse_postcode,
                    parse_price)

NAME = "JLG Real Estate"
OVERVIEWS = [
    ("rent", "https://jlgrealestate.com/woningen/huur/"),
    ("buy", "https://jlgrealestate.com/woningen/koop/"),
]
MAX_PAGES = 6


def collect():
    listings = []
    for kind, overview in OVERVIEWS:
        section = overview.rstrip("/").rsplit("/", 1)[-1]          # "huur" / "koop"
        for page in range(1, MAX_PAGES + 1):
            soup = get_soup(overview if page == 1 else "%spage/%d/" % (overview, page))
            cards = cards_from_links(soup, overview, r"/woningen/%s/[^/]+/[^/]+/?$" % section)
            if not cards:
                break
            for url, text, _ in cards:
                # "... Surinameplein 50-3 1058 GS, Amsterdam EUR 2.650,- p/m 79 2 Gemeubileerd"
                if "/%s/amsterdam/" % section not in url:
                    continue                                       # Weesp, Amstelveen, ...
                place = re.search(r"([^|]{3,60}?)\s+(\d{4}\s?[A-Z]{2}),\s*Amsterdam\s*€", text)
                size = re.search(r"(?:p/m|k\.k\.|v\.o\.n\.)\s+(\d{2,3})\b", text)
                status = re.search(r"(verhuurd|verkocht|onder optie|onder bod)[\w ]{0,20}", text, re.I)
                address = place.group(1).split(" Amsterdam ")[-1] if place else url.rstrip("/").rsplit("/", 1)[-1]
                # The card repeats the address; keep the last, clean copy.
                address = re.sub(r"^.*\b(?:huur|koop) Amsterdam ", "", address)
                listings.append(make_listing(
                    NAME, kind, url, address + ", Amsterdam", parse_price(text),
                    m2=int(size.group(1)) if size else None,
                    postcode=parse_postcode(text), text=text, city="Amsterdam",
                    status_text=status.group(0) if status else ""))
            if not soup.find("a", href=re.compile(r"/woningen/%s/page/%d/" % (section, page + 1))):
                break
    return listings

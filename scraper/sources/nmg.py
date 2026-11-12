"""NMG Wonen - letting agency. National overview, so we keep Amsterdam only."""

import re

from common import (cards_from_links, get_soup, make_listing, parse_m2,
                    parse_price)

NAME = "NMG Wonen"
OVERVIEW = "https://nmgwonen.nl/huur/"
MAX_PAGES = 20


def collect():
    listings = []
    for page in range(1, MAX_PAGES + 1):
        soup = get_soup(OVERVIEW if page == 1 else "%spage/%d/" % (OVERVIEW, page))
        cards = cards_from_links(soup, OVERVIEW, r"nmgwonen\.nl/woning/[^/]+/?$")
        if not cards:
            break
        for url, text, _ in cards:
            if "/woning/amsterdam-" not in url:
                continue
            # "NIEUW! Beschikbaar per: 1 december 2026 ks. Ibisplantsoen 22 Amsterdam EUR 1.670"
            match = re.search(r"\d{4}\s+(.*?Amsterdam)\s*€", text)
            listings.append(make_listing(
                NAME, "rent", url, match.group(1) if match else _from_url(url),
                parse_price(text), parse_m2(text), text=text, status_text=text[:40],
                city="Amsterdam"))
        if not soup.find("a", href=re.compile(r"/huur/page/%d/" % (page + 1))):
            break
    return listings


def _from_url(url):
    words = url.rstrip("/").split("/")[-1].replace("amsterdam-", "").replace("-", " ")
    return words.title() + ", Amsterdam"

"""
Kamernet - rooms, studios and flats, mostly from private landlords.
The page carries its data as JSON (a "__NEXT_DATA__" block).

Only Kamernet's APARTMENT category is read. The room, studio and
anti-squat categories are never opened, and anything in the apartment
category that is not marked as an apartment (listingType 2) is skipped.
"""

import json

from common import get_soup, make_listing

NAME = "Kamernet"
OVERVIEW = "https://kamernet.nl/huren/appartement-amsterdam"
MAX_PAGES = 8
APARTMENT = 2


def collect():
    listings, seen = [], set()
    for page in range(1, MAX_PAGES + 1):
        soup = get_soup(OVERVIEW if page == 1 else "%s?pageNo=%d" % (OVERVIEW, page))
        block = soup.find("script", id="__NEXT_DATA__")
        data = json.loads(block.string)
        found = (data["props"]["pageProps"]["targetPageProps"]
                 ["findListingsResponse"]["listings"])
        fresh = [ad for ad in found if ad["listingId"] not in seen]
        if not fresh:
            break
        for ad in fresh:
            seen.add(ad["listingId"])
            if ad.get("listingType") != APARTMENT or ad.get("citySlug") != "amsterdam":
                continue
            url = "https://kamernet.nl/huren/appartement-amsterdam/%s/appartement-%s" % (
                ad["streetSlug"], ad["listingId"])
            listings.append(make_listing(
                NAME, "rent", url, ad["street"] + ", Amsterdam",
                ad.get("totalRentalPrice"), ad.get("surfaceArea"),
                type_text="Appartement", city="Amsterdam",
                start_date=ad.get("availabilityStartDate"),
                end_date=ad.get("availabilityEndDate")))
    return listings

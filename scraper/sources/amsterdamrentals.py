"""Amsterdam Rentals - letting agency. One overview page for Amsterdam."""

import re

from common import (cards_from_links, get_soup, make_listing, parse_bedrooms,
                    parse_postcode, parse_price)

NAME = "Amsterdam Rentals"
OVERVIEW = "https://www.amsterdamrentals.nl/all-properties-for-rent/in/amsterdam"


def collect():
    soup = get_soup(OVERVIEW)
    listings = []
    for url, text, _ in cards_from_links(soup, OVERVIEW, r"^/property/"):
        # "EUR 2.400 per month Keizersgracht, modern furnished 1-bedroom
        #  Amsterdam, Centre, Netherlands, 1017 DM"
        title = re.sub(r"^.*?per month\s*", "", text)
        street = title.split(",")[0]
        bedrooms, estimated = parse_bedrooms(text)
        listings.append(make_listing(
            NAME, "rent", url, street + ", Amsterdam", parse_price(text),
            bedrooms=bedrooms, bedrooms_estimated=estimated,
            postcode=parse_postcode(text), text=text, title=title,
            # The address of the ad names the type: "1-bed-apartment-in-..."
            type_text=url.rsplit("/", 1)[-1].replace("-", " "),
            city="Amsterdam"))
    return listings

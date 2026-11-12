"""
THE GATE. The one place where a listing is accepted or rejected.

    check(listing)  ->  (True, "")  or  (False, "the reason")

Every rule comes from config.py. The daily run calls check() for every
listing, old and new, just before saving, so nothing reaches the website
without passing it. test_filters.py runs example listings through it.

A listing is a dictionary with:
    kind        "rent" or "buy"
    url         direct link to this one ad
    title       the ad's headline
    type_text   the ad's type line ("Appartement", "Kamer", ...)
    status      the ad's status label ("Beschikbaar", "Onder optie", ...)
    text        the ad's description (may be empty)
    city        town named by the ad, if any
    postcode    4 digits, or None
    price       rent per month WITHOUT separately listed service costs,
                or the asking price
    service_costs   separately listed service costs per month, or 0
    m2          living area
    bedrooms    number of bedrooms, or None
    start_date, end_date   availability dates, if the source gives them
"""

import re

import lets
from config import (BUY, BUY_NOT_WANTED, CITY, FAVOURITE_POSTCODES, GONE_WORDS,
                    HOME_WORDS, NEGATIONS, NOT_A_HOME_ANYWHERE, NOT_A_HOME_IN_TITLE,
                    POSTCODES, RENT, RENT_STRETCH_MAX_PRICE, RESERVED_FOR_GROUPS,
                    ROOM_PHRASES_IN_TEXT,
                    ROOM_WORDS_IN_TITLE, ROOMS_MINUS)


def _words(words):
    """Matches any of the plain words, as whole words."""
    return re.compile(r"(?<![\w-])(%s)(?![\w-])" % "|".join(
        re.escape(word) for word in sorted(words, key=len, reverse=True)), re.I)


def _phrases(phrases):
    """Matches any of the phrase patterns, as whole words."""
    return re.compile(r"(?<![\w-])(%s)(?![\w-])" % "|".join(phrases), re.I)


_ROOM_TITLE = _words(ROOM_WORDS_IN_TITLE)
_ROOM_TEXT = _phrases(ROOM_PHRASES_IN_TEXT)
_NOT_HOME_TITLE = _words(NOT_A_HOME_IN_TITLE)
_NOT_HOME_ANYWHERE = _phrases(NOT_A_HOME_ANYWHERE)
_GONE = _words(GONE_WORDS)
_GROUPS = {reason: _phrases(patterns) for reason, patterns in RESERVED_FOR_GROUPS.items()}
_BUY_NOT_WANTED = {reason: _phrases(patterns) for reason, patterns in BUY_NOT_WANTED.items()}
# Home words may carry a Dutch ending: "zelfstandige", "appartementen".
_HOME = re.compile(r"(?<![\w-])(%s)(e|en|s|je)?(?![\w-])" % "|".join(
    re.escape(word) for word in sorted(HOME_WORDS, key=len, reverse=True)), re.I)
_NEGATED = re.compile(r"(?<![\w-])(%s)\s*$" % "|".join(NEGATIONS), re.I)
# "appartement met parkeerplaats" is a flat, not a parking space.
_COMES_WITH = re.compile(r"(met|with|incl\.?|inclusief|including|en|and|\+|&|eigen|own|private|plus)\s*$", re.I)


def is_gone(status):
    """True if a status label says let, sold, under option and so on."""
    return _GONE.search(status or "") is not None


def home_type(title, type_text="", text=""):
    """
    Returns ("Apartment" | "Maisonette" | "House", "") for a whole,
    self-contained home, or (None, reason) for a room, a studio, anything
    shared, something that is not a home, or anything unclear.
    """
    headline = "%s | %s" % (title or "", type_text or "")
    found = _ROOM_TITLE.search(headline)
    if found:
        return None, "room, studio or shared ('%s' in the title)" % found.group(1).lower()
    for found in _NOT_HOME_TITLE.finditer(headline):
        if not _COMES_WITH.search(headline[:found.start()]):
            return None, "not a home ('%s')" % found.group(1).lower()
    found = _NOT_HOME_ANYWHERE.search(headline + " " + (text or ""))
    if found:
        return None, "not a home ('%s')" % found.group(1).lower()
    for found in _ROOM_TEXT.finditer(text or ""):
        if not _NEGATED.search(text[max(0, found.start() - 12):found.start()]):
            return None, "room or shared ('%s' in the ad text)" % found.group(1).lower()
    found = _HOME.search(headline)
    if not found:
        return None, "type unclear (no apartment or house word in the title)"
    return HOME_WORDS[found.group(1).lower()], ""


def home_word_in(text):
    """The first apartment or house word in a piece of ad text, or None."""
    found = _HOME.search(text or "")
    return found.group(1).lower() if found else None


def bedrooms_from_rooms(rooms):
    """'2 kamers' = 1 bedroom, '3 kamers' = 2 bedrooms."""
    return rooms - ROOMS_MINUS


def total_price(listing):
    """Rent including separately listed service costs; asking price for sales."""
    price = listing.get("price")
    if price is None:
        return None
    if listing.get("kind") == "rent":
        return price + (listing.get("service_costs") or 0)
    return price


def period(listing, today=None):
    """The rental period of a rental listing (see lets.py)."""
    return lets.rental_period(listing.get("text"), listing.get("start_date"),
                              listing.get("end_date"), today)


def check(listing, today=None):
    """The strict gate. Returns (True, "") or (False, reason)."""
    renting = listing.get("kind") == "rent"
    rule = RENT if renting else BUY
    everything = "%s | %s | %s" % (listing.get("title") or "", listing.get("type_text") or "",
                                   listing.get("text") or "")

    # 0. A direct link to the ad itself.
    if not re.match(r"https?://[^/]+/.+", listing.get("url") or ""):
        return False, "no direct ad link"

    # 1. Not already gone.
    if is_gone(listing.get("status")):
        return False, "gone (%s)" % _GONE.search(listing["status"]).group(1).lower()

    # 2. A whole, self-contained flat or house.
    kind_of_home, reason = home_type(
        listing.get("title"), listing.get("type_text"), listing.get("text"))
    if kind_of_home is None:
        return False, reason

    # 3. Not reserved for a specific group.
    for reason, pattern in _GROUPS.items():
        for found in pattern.finditer(everything):
            if not _NEGATED.search(everything[max(0, found.start() - 12):found.start()]):
                return False, "%s ('%s')" % (reason, found.group(1).lower())

    # 4. Renting: long-term only.  Buying: no auctions, tenants, co-ops.
    if renting:
        term = period(listing, today)
        if not term["ok"]:
            return False, term["reason"]
    else:
        for reason, pattern in _BUY_NOT_WANTED.items():
            found = pattern.search(everything)
            if found:
                return False, "%s ('%s')" % (reason, found.group(1).lower())

    # 5. City of Amsterdam and a whitelisted postcode.
    city = (listing.get("city") or "").strip().lower()
    if city and city != CITY.lower():
        return False, "outside Amsterdam (%s)" % listing["city"]
    postcode = listing.get("postcode")
    if not postcode:
        return False, "no postcode"
    if str(postcode)[:4] not in POSTCODES:
        return False, "postcode %s is not on the list" % str(postcode)[:4]

    # 6. Price, size, bedrooms. Missing = dropped.
    price = total_price(listing)
    if not price:
        return False, "no price"
    # (Rent may go up to the second rent tab's limit; tab() below decides
    # which of the two rent tabs a listing belongs in.)
    if price > (RENT_STRETCH_MAX_PRICE if renting else rule["max_price"]):
        return False, "too expensive (%d)" % price
    if not listing.get("m2"):
        return False, "no size"
    if listing["m2"] < rule["min_m2"]:
        return False, "too small (%d m2)" % listing["m2"]
    if listing.get("bedrooms") is None:
        return False, "no bedroom count"
    if listing["bedrooms"] not in rule["bedrooms"]:
        return False, "%d bedrooms" % listing["bedrooms"]
    return True, ""


def tab(listing, today=None):
    """
    Which tab of the site a listing belongs in. Exactly one, or None:
      "rent"          total rent up to RENT max_price (1,800)
      "rent_stretch"  total rent above that, up to RENT_STRETCH_MAX_PRICE (2,000)
      "buy"           homes for sale
      None            fails a rule; shown nowhere
    """
    ok, _ = check(listing, today)
    if not ok:
        return None
    if listing.get("kind") != "rent":
        return "buy"
    return "rent" if total_price(listing) <= RENT["max_price"] else "rent_stretch"


def place(postcode):
    """Area details for a whitelisted postcode."""
    area, neighbourhood = POSTCODES[postcode]
    return {"area": area, "neighbourhood": neighbourhood,
            "favourite": postcode in FAVOURITE_POSTCODES}

"""
Postcode lookup in the City of Amsterdam's official address register
(open data). Used only when an ad shows a street and a house number but
prints no postcode. Switch it off with USE_ADDRESS_REGISTER in config.py.

It answers only for an exact street + house number. A street name on its
own is never enough, because one street can cross several postcodes.
"""

import re
from urllib.parse import quote

import common

BAG = ("https://api.data.amsterdam.nl/v1/bag/nummeraanduidingen/"
       "?ligtAanOpenbareruimte.naam=%s&huisnummer=%s&_fields=postcode&_pageSize=1&_format=json")


def lookup_postcode(address):
    """Four-digit postcode of exactly this address, or None."""
    street = re.sub(r",.*$", "", address or "")
    street = re.sub(r"\s*\b(Amsterdam|Nederland|Netherlands)\b.*$", "", street, flags=re.I).strip()
    # The register spells ordinals out: "1e Helmersstraat" is "Eerste Helmersstraat".
    for short, full in (("1e", "Eerste"), ("2e", "Tweede"), ("3e", "Derde")):
        street = re.sub(r"^%s\s" % short, full + " ", street, flags=re.I)
    match = re.match(r"(.+?)\s+(\d+)", street)
    if not match:
        return None                      # no house number: do not guess
    try:
        reply = common.fetch(BAG % (quote(match.group(1)), match.group(2)))
        found = reply.json()["_embedded"]["nummeraanduidingen"]
        if found and found[0].get("postcode"):
            return found[0]["postcode"][:4]
    except Exception:
        pass                             # no answer: the listing is dropped
    return None

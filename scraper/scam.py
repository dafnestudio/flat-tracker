"""
Scam filter, registration check and the "keep, but tag" labels.
The signs and thresholds are in config.py (sections 8 and 9).

  judge(listing, text)     -> ("drop" | "ok", [reasons])
  tags(listing, text, ...) -> list of tags for a listing that is kept
  registration(text)       -> "allowed" | "not allowed" | "not stated"
"""

import re

from config import (AGENCY_WORDS, FAR_TOO_CHEAP_PER_M2, LOW_PRICE_EXPLANATIONS,
                    NO_DEPOSIT_WORDS, ON_THE_LOW_SIDE_PER_M2, OPEN_PLATFORMS,
                    PRIVATE_AD_PLATFORMS,
                    PRIVATE_CONTACT_SIGNS, SCAM_SIGNS, TAG_CHECK_CAREFULLY,
                    TAG_CHECK_PERIOD, TAG_FIXED_TERM, TAG_PRIVATE,
                    TAG_REGISTRATION)

_EXPLAINED = re.compile("|".join(LOW_PRICE_EXPLANATIONS), re.I)
_AGENCY = re.compile("|".join(AGENCY_WORDS), re.I)
_NO_DEPOSIT = re.compile("|".join(NO_DEPOSIT_WORDS), re.I)


def private_landlord(listing, text):
    """An ad placed directly on a platform with no sign of an agency behind it."""
    return listing["source"] in PRIVATE_AD_PLATFORMS and not _AGENCY.search(text or "")


def per_m2(listing):
    if listing["kind"] == "rent" and listing.get("price") and listing.get("m2"):
        return listing["price"] / listing["m2"]
    return None


def judge(listing, text):
    """Looks for obvious scam signs. Returns ("drop", reasons) or ("ok", [])."""
    text = (text or "").lower()
    found = [name for name, pattern in SCAM_SIGNS.items() if re.search(pattern, text)]
    if found:
        return "drop", found

    private = private_landlord(listing, text)
    if private:
        found = [name for name, pattern in PRIVATE_CONTACT_SIGNS.items()
                 if re.search(pattern, text)]
        if found:
            return "drop", found

    rate = per_m2(listing)
    if (rate is not None and rate < FAR_TOO_CHEAP_PER_M2
            and listing["source"] in OPEN_PLATFORMS and not _EXPLAINED.search(text)):
        return "drop", ["Price far below similar flats, no explanation"]
    return "ok", []


def tags(listing, text, period_label, fixed_months):
    """The "keep, but tag" labels for a listing that passed everything."""
    result = []
    if listing["kind"] == "rent":
        if fixed_months:
            result.append(TAG_FIXED_TERM % fixed_months)
        elif period_label == "Not stated":
            result.append(TAG_CHECK_PERIOD)
        if private_landlord(listing, text):
            result.append(TAG_PRIVATE)
        rate = per_m2(listing)
        low = rate is not None and rate < ON_THE_LOW_SIDE_PER_M2
        if low or _NO_DEPOSIT.search(text or ""):
            result.append(TAG_CHECK_CAREFULLY)
        result.append(TAG_REGISTRATION[registration(text)])
    return result


def registration(text):
    """Does the ad say you can register (inschrijven) at the address?"""
    text = (text or "").lower()
    no = (r"(geen|niet|no|not|without|zonder)[^.]{0,30}(inschrijv\w+|registration|register|registreren)"
          r"|(inschrijv\w+|registration|registreren)[^.]{0,25}(niet|not|is not|isn't)[^.]{0,12}(mogelijk|possible|allowed|toegestaan)")
    yes = (r"(inschrijv\w+|registration|registreren|register)[^.]{0,30}(mogelijk|possible|allowed|toegestaan|is ok)"
           r"|(can|kunt|kan|mag|possible to)[^.]{0,20}(register at|inschrijven op|registreren op)")
    # "inschrijven" also means signing up on a website; require the address
    # context so "Direct inschrijven via deze site" does not count.
    context = r"(adres|address|gemeente|municipality|brp|bsn|woonadres)"
    sentences = re.split(r"[.!?\n]", text)
    for sentence in sentences:
        if re.search(no, sentence) and re.search(context + r"|registration|inschrijving", sentence):
            return "not allowed"
    for sentence in sentences:
        if re.search(yes, sentence) and re.search(context + r"|registration", sentence):
            return "allowed"
    return "not stated"

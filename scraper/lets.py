"""
Reads the rental period from an ad: dates and durations first, words
second. Rules and word lists are in config.py (section 4).

    rental_period(text, start, end, today) -> dict with
        ok      False when the let is shorter than MIN_LET_MONTHS
        reason  why it was dropped
        label   "Indefinite" | "Fixed term: 12 months" |
                "Minimum 12 months" | "Not stated"
        months  the fixed term in months, or None
"""

import re
from datetime import date

from config import INDEFINITE_WORDS, MIN_LET_MONTHS, SHORT_LET_WORDS

MONTHS = {
    "jan": 1, "feb": 2, "mrt": 3, "maa": 3, "mar": 3, "apr": 4, "mei": 5, "may": 5,
    "jun": 6, "jul": 7, "aug": 8, "sep": 9, "okt": 10, "oct": 10, "nov": 11, "dec": 12,
}
NUMBER_WORDS = {"een": 1, "één": 1, "one": 1, "a": 1, "twee": 2, "two": 2,
                "drie": 3, "three": 3, "vier": 4, "four": 4, "vijf": 5, "five": 5,
                "zes": 6, "six": 6, "twaalf": 12, "twelve": 12}

# A date: 2026-12-01, 01-12-2026, 1/12/2026, 1 december 2026, December 1, 2026
DATE = (r"(\d{4}-\d{2}-\d{2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4}"
        r"|\d{1,2}(?:st|nd|rd|th|e)?\s+[a-zA-Z]{3,9}\.?\s+\d{4}"
        r"|[a-zA-Z]{3,9}\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})")

# "available until 1 March 2027", "te huur tot 01-03-2027", "end date: ..."
END = re.compile(
    r"(?:beschikbaar|te huur|huurperiode|verhuur|available|for rent|rental period|rent(?:ed)? out|sublet\w*|onderhuur)"
    r"[^.|]{0,60}?\b(?:tot en met|tot|t/m|until|till|through|up to)\s+" + DATE +
    r"|(?:einddatum|end date|eind datum|contract ends?(?: on)?)\s*:?\s*" + DATE, re.I)
# "available from 1 December 2026", "beschikbaar per 01-12-2026"
START = re.compile(
    r"(?:beschikbaar|available|aanvaarding|te huur|move-?in|start date|startdatum|ingangsdatum)"
    r"[^.|]{0,25}?\b(?:vanaf|per|from|as of|date)?\s*:?\s*" + DATE, re.I)

DURATION = re.compile(
    r"\b(\d{1,2}|half|" + "|".join(NUMBER_WORDS) + r")\s*(?:-\s*)?"
    r"(maanden|maand|months?|mnd|jaar|jaren|years?|weken|week|weeks?)\b", re.I)
# The words just before a duration tell us what it is.
NOT_A_PERIOD = re.compile(
    r"\b(borg|waarborg\w*|deposit|opzegtermijn|notice|vooruit|in advance|binnen|within|"
    r"elke|every|iedere|na|after|sinds|since|over|in|al)\s*(?:van|of|is|:)?\s*$", re.I)
# Deposit and notice periods mentioned just before a duration.
DEPOSIT_OR_NOTICE = re.compile(
    r"\b(borg|waarborg\w*|deposit|opzeg\w*|notice|terminat\w+|vooruit\w*|in advance|"
    r"huurverhoging|rent increase|jaarcijfers|loonstroken|payslips)\b", re.I)
MINIMUM = re.compile(r"\bmin(?:imaal|imum|imale)?\b\.?[^.]{0,30}$", re.I)
MAXIMUM_OR_FIXED = re.compile(
    r"(\bmax\w*|tijdelijk\w*|temporar\w+|bepaalde tijd|fixed|duur van|periode van|period of|"
    r"\bfor\b|\bvoor\b|contract\w*|huurperiode|rental period|huurtermijn|lease|duration|"
    r"\bduur\b|sublet\w*|onderhuur|available|beschikbaar|stay|verblijf)[^.]{0,30}$", re.I)
AFTER_NOT_A_PERIOD = re.compile(r"^\s*('s )?(huur\b|rent\b|borg|deposit|geleden|ago|oud\b|old\b)", re.I)
AFTER_FIXED = re.compile(r"^\s*(only|maximum|max\b|contract|lease|huurcontract)", re.I)

SHORT_WORDS = re.compile(r"(?<![\w-])(%s)(?![\w-])" % "|".join(
    re.escape(word) for word in sorted(SHORT_LET_WORDS, key=len, reverse=True)), re.I)
INDEFINITE = re.compile(r"(%s)" % "|".join(re.escape(word) for word in INDEFINITE_WORDS), re.I)


def parse_date(words):
    """Turns any of the date styles above into a date, or None."""
    words = words.strip().lower().replace(",", " ")
    try:
        found = re.match(r"(\d{4})-(\d{2})-(\d{2})$", words)
        if found:
            return date(int(found.group(1)), int(found.group(2)), int(found.group(3)))
        found = re.match(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})$", words)
        if found:
            return date(int(found.group(3)), int(found.group(2)), int(found.group(1)))
        found = re.match(r"(\d{1,2})(?:st|nd|rd|th|e)?\s+([a-z]{3})[a-z]*\.?\s+(\d{4})$", words)
        if found and found.group(2) in MONTHS:
            return date(int(found.group(3)), MONTHS[found.group(2)], int(found.group(1)))
        found = re.match(r"([a-z]{3})[a-z]*\s+(\d{1,2})(?:st|nd|rd|th)?\s+(\d{4})$", words)
        if found and found.group(1) in MONTHS:
            return date(int(found.group(3)), MONTHS[found.group(1)], int(found.group(2)))
    except ValueError:
        pass
    return None


def months_between(start, end):
    """Whole months from start to end (1 Dec to 1 Mar = 3)."""
    months = (end.year - start.year) * 12 + end.month - start.month
    if end.day < start.day - 1:
        months -= 1
    return months


def _to_months(number, unit):
    number = number.lower()
    amount = 0.5 if number == "half" else NUMBER_WORDS.get(number) or int(number)
    unit = unit.lower()
    if unit.startswith(("jaar", "jaren", "year")):
        return int(amount * 12)
    if unit.startswith("we"):
        return int(amount / 4)
    return int(amount)


def rental_period(text, start=None, end=None, today=None):
    """See the top of this file. start / end: dates the source itself gives."""
    text = text or ""
    today = today or date.today()
    fixed, minimum = None, None

    # ---- 1. actual dates -------------------------------------------------
    if isinstance(start, str):
        start = parse_date(start[:10])
    if isinstance(end, str):
        end = parse_date(end[:10])
    if end is None:
        found = END.search(text)
        if found:
            end = parse_date(found.group(1) or found.group(2))
    if end is not None:
        if start is None:
            found = START.search(text)
            start = parse_date(found.group(1)) if found else None
        move_in = max(start or today, today)
        fixed = months_between(move_in, end)
        if fixed < MIN_LET_MONTHS:
            return {"ok": False, "label": "", "months": fixed,
                    "reason": "short let: ends %s, about %d months after move-in"
                              % (end.isoformat(), max(fixed, 0))}

    # ---- 2. stated periods ("max 3 months", "contract of 12 months") ------
    for found in DURATION.finditer(text):
        before = text[max(0, found.start() - 45):found.start()]
        after = text[found.end():found.end() + 20]
        months = _to_months(found.group(1), found.group(2))
        if (AFTER_NOT_A_PERIOD.search(after) or NOT_A_PERIOD.search(before)
                or DEPOSIT_OR_NOTICE.search(before)):
            continue                       # a deposit, a notice period, ...
        if MINIMUM.search(before):
            minimum = max(minimum or 0, months)
        elif MAXIMUM_OR_FIXED.search(before) or AFTER_FIXED.search(after):
            fixed = months if fixed is None else min(fixed, months)
    if fixed is not None and fixed < MIN_LET_MONTHS:
        return {"ok": False, "label": "", "months": fixed,
                "reason": "short let: period of %d months" % fixed}

    # ---- 3. short-stay wording with nothing that shows 6 months or more ---
    indefinite = INDEFINITE.search(text) is not None
    long_enough = indefinite or (fixed or 0) >= MIN_LET_MONTHS or (minimum or 0) >= MIN_LET_MONTHS
    found = SHORT_WORDS.search(text)
    if found and not long_enough:
        return {"ok": False, "label": "", "months": None,
                "reason": "short let: '%s' and no period of %d+ months stated"
                          % (found.group(1).lower(), MIN_LET_MONTHS)}

    # ---- 4. kept: say what the period is ----------------------------------
    if fixed is not None:
        label = "Fixed term: %d months" % fixed
    elif indefinite:
        label = "Indefinite"
    elif minimum:
        label = "Minimum %d months" % minimum
    else:
        label = "Not stated"
    return {"ok": True, "reason": "", "label": label, "months": fixed}

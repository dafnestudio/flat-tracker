"""
Shared tools used by every source module:

  fetch()            - polite download (obeys robots.txt, waits between requests)
  cards_from_links() - finds the listing "cards" on an overview page
  parse_*()          - pull price, m2, bedrooms and postcode out of text
  make_listing()     - builds one listing in the standard shape
"""

import re
import time
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from config import DELAY_SECONDS, ROOMS_MINUS, TIMEOUT_SECONDS, USER_AGENT


class Blocked(Exception):
    """The website said no (robots.txt, 401/403/429 or a bot-check page)."""


# ------------------------------------------------------------------ fetching
_session = requests.Session()
_session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "nl,en;q=0.8"})
_robots = {}      # host -> parsed robots.txt
_last_visit = {}  # host -> time of our last request
request_count = 0


def _parse_robots(text):
    """
    Reads the rules that apply to every robot ("User-agent: *").
    Returns {"rules": [(allow?, path pattern), ...], "delay": seconds or None}.
    """
    rules, delay, agents, in_rules = [], None, [], False
    for line in text.lstrip("﻿").splitlines():
        line = line.split("#")[0].strip()
        if ":" not in line:
            continue
        key, value = [part.strip() for part in line.split(":", 1)]
        key = key.lower()
        if key == "user-agent":
            if in_rules:              # a new group starts
                agents, in_rules = [], False
            agents.append(value)
        elif key in ("allow", "disallow", "crawl-delay"):
            in_rules = True
            if "*" not in agents:
                continue
            if key == "crawl-delay":
                try:
                    delay = float(value)
                except ValueError:
                    pass
            elif value:
                rules.append((key == "allow", value))
    return {"rules": rules, "delay": delay}


def _rule_matches(pattern, path):
    """robots.txt patterns: * = anything, $ = end of the address."""
    regex = re.escape(pattern).replace(r"\*", ".*")
    if regex.endswith(r"\$"):
        regex = regex[:-2] + "$"
    return re.match(regex, path) is not None


def _robots_for(url):
    parts = urlparse(url)
    host = parts.scheme + "://" + parts.netloc
    if host not in _robots:
        everything_off = {"rules": [(False, "/")], "delay": None}
        try:
            reply = _session.get(host + "/robots.txt", timeout=TIMEOUT_SECONDS)
            if reply.status_code in (401, 403):
                _robots[host] = everything_off   # no access to the rules = no access
            elif reply.status_code >= 400:
                _robots[host] = {"rules": [], "delay": None}  # no rules published
            else:
                _robots[host] = _parse_robots(reply.text)
        except requests.RequestException:
            _robots[host] = everything_off       # be careful when unsure
    return _robots[host]


def allowed(url):
    """
    True if the site's robots.txt lets robots read this address.
    As in the official standard, the most specific (longest) rule wins.
    """
    parts = urlparse(url)
    path = (parts.path or "/") + ("?" + parts.query if parts.query else "")
    verdict, longest = True, -1
    for allow, pattern in _robots_for(url)["rules"]:
        if _rule_matches(pattern, path) and (
                len(pattern) > longest or (len(pattern) == longest and allow)):
            verdict, longest = allow, len(pattern)
    return verdict


def fetch(url):
    """
    Download one page, politely. Returns the `requests` response.
    Raises Blocked if the site does not want robots there. We never retry
    with a disguise: a refusal is simply respected.
    """
    global request_count
    if not allowed(url):
        raise Blocked("robots.txt does not allow " + url)

    host = urlparse(url).netloc
    # Use the site's own requested pause if it is longer than ours.
    delay = max(_robots_for(url)["delay"] or 0, DELAY_SECONDS)
    wait = _last_visit.get(host, 0) + delay - time.time()
    if wait > 0:
        time.sleep(wait)

    try:
        try:
            reply = _session.get(url, timeout=TIMEOUT_SECONDS)
        except requests.ConnectionError:
            time.sleep(5)            # one calm second try for a dropped line
            reply = _session.get(url, timeout=TIMEOUT_SECONDS)
    finally:
        _last_visit[host] = time.time()
        request_count += 1

    # Sites that do not state their text encoding use UTF-8 in practice.
    if "charset" not in reply.headers.get("Content-Type", "").lower():
        reply.encoding = "utf-8"

    if reply.status_code in (401, 403, 429) or "Just a moment..." in reply.text[:600]:
        raise Blocked("%s refused the request (HTTP %s)" % (host, reply.status_code))
    return reply


def get_soup(url):
    """Download a page and return it parsed. Raises on any error status."""
    reply = fetch(url)
    reply.raise_for_status()
    return BeautifulSoup(reply.text, "html.parser")


# ------------------------------------------------------------------ parsing
def clean(text):
    """Collapse all whitespace to single spaces."""
    return re.sub(r"\s+", " ", text or "").strip()


def to_int(text):
    """'1.795,-' -> 1795 ; '425.000' -> 425000 ; '1,650' -> 1650."""
    text = re.sub(r"[,.]\d{1,2}$", "", text.strip().rstrip("-").rstrip(",.") )
    digits = re.sub(r"\D", "", text)
    return int(digits) if digits else None


def parse_price(text):
    """First euro amount in the text, as a whole number."""
    match = re.search(r"(?:€|&euro;|EUR)\s*([\d.,]+)", text or "")
    return to_int(match.group(1)) if match else None


def parse_m2(text):
    """First 'NN m2' in the text. If several are given, the first is living space."""
    match = re.search(r"(\d{2,3})(?:[.,]\d)?\s*(?:㎡|m\s?(?:²|2\b))", text or "")
    return int(match.group(1)) if match else None


def parse_bedrooms(text):
    """
    Returns (bedrooms, estimated).
    Dutch sites often give "kamers" (rooms) instead of bedrooms:
    "2 kamers" = 1 bedroom, "3 kamers" = 2 bedrooms (see ROOMS_MINUS in
    config.py). Those are marked as worked out from the room count.
    """
    text = text or ""
    match = (re.search(r"(\d)\s*(?:slaapkamers?|bedrooms?)", text, re.I)
             or re.search(r"(?:slaapkamers?|bedrooms?)\s*:?\s*(\d)", text, re.I))
    if match:
        return int(match.group(1)), False
    match = (re.search(r"(\d)\s*(?:kamers?|rooms?)\b", text, re.I)
             or re.search(r"\b(?:kamers|rooms)\s*:?\s*(\d)", text, re.I))
    if match:
        return max(int(match.group(1)) - ROOMS_MINUS, 0), True
    return None, False


def parse_service_costs(text):
    """
    Monthly service costs that an ad lists separately from the rent.
    Returns 0 when none are given or when the ad says they are included.
    """
    for match in re.finditer(
            r"(servicekosten|service ?costs?|service ?charges?)\s*:?\s*"
            r"(?:bedragen|zijn|are|of|van|is)?\s*\(?\s*(?:€|EUR)\s*([\d.,]+)", text or "", re.I):
        before = (text[max(0, match.start() - 25):match.start()]).lower()
        if re.search(r"incl|includ", before):
            return 0
        amount = to_int(match.group(2))
        if amount and amount <= 600:
            return amount
    return 0


def postcode_near_street(text, address):
    """
    The postcode an ad page prints next to the listing's own street.
    Any other postcode on the page (the agency's office, a neighbouring
    home) is ignored, so a listing can never borrow someone else's area.
    """
    street = re.split(r"\s+\d", re.sub(r",.*$", "", address or ""))[0].strip()
    if len(street) < 4:
        return None
    for match in re.finditer(re.escape(street), text or "", re.I):
        found = parse_postcode(text[match.end():match.end() + 90])
        if found:
            return found
    return None


def parse_postcode(text):
    """First Amsterdam-style postcode, returned as its four digits ('1054')."""
    match = re.search(r"\b(1\d{3})\s?[A-Z]{2}\b", text or "")
    return match.group(1) if match else None


def cards_from_links(soup, base_url, link_pattern):
    """
    Finds listing cards on an overview page without depending on class names
    (those change often). For every link whose address matches link_pattern
    we climb up the page until we reach the block that holds a price. That
    block is the card.

    Returns a list of (ad_url, card_text, card_element).
    """
    pattern = re.compile(link_pattern)
    links = [a for a in soup.find_all("a", href=True) if pattern.search(a["href"])]
    all_urls = {urljoin(base_url, a["href"]).split("#")[0] for a in links}
    found = {}
    for link in links:
        url = urljoin(base_url, link["href"]).split("#")[0]
        if url in found:
            continue
        card = link
        for _ in range(8):
            text = clean(card.get_text(" "))
            if "€" in text and len(text) > 25:
                break
            if card.parent is None:
                break
            # Stop before the block swallows a neighbouring listing.
            others = {urljoin(base_url, a["href"]).split("#")[0]
                      for a in card.parent.find_all("a", href=True)
                      if pattern.search(a["href"])}
            if len(others & all_urls) > 1:
                break
            card = card.parent
        found[url] = (url, clean(card.get_text(" ")), card)
    return list(found.values())


def make_listing(source, kind, url, address, price, m2=None, bedrooms=None,
                 bedrooms_estimated=False, postcode=None, posted=None,
                 text="", status_text="", title="", type_text="", city=None,
                 start_date=None, end_date=None):
    """
    The standard shape every source returns.
      kind:   "rent" or "buy"
      url:    direct link to this one ad (never a search page)
      posted: date the ad went online, "YYYY-MM-DD", if the site says so
      text:   any ad text we already have (used for the scam check)
      title, type_text: the ad's headline and type ("Appartement", "Kamer")
      city:   the town, when the source states it
      start_date, end_date: availability dates, when the source gives them
    """
    return {
        "source": source, "kind": kind, "url": url, "address": clean(address),
        "price": price, "m2": m2, "bedrooms": bedrooms,
        "bedrooms_estimated": bedrooms_estimated, "postcode": postcode,
        "posted": posted, "text": clean(text), "status_text": clean(status_text),
        "title": clean(title), "type_text": clean(type_text), "city": city,
        "start_date": start_date, "end_date": end_date,
    }

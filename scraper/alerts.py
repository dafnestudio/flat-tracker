"""
Reads listing alert emails (Funda, Pararius, Huurwoningen.nl, Hausing).

Those sites do not allow robots, so we never search them. Instead you
set up their free email alerts, and this module reads those emails from
your Gmail inbox and takes the ad links out of them.

STRICTLY READ-ONLY: the mailbox is opened in read-only mode and emails
are fetched with "PEEK", so nothing is deleted, sent, moved or even
marked as read. Only emails from the alert senders are looked at.

Your Gmail address and app password come from two GitHub repository
secrets (GMAIL_ADDRESS and GMAIL_APP_PASSWORD), never from the code.
Rules and link patterns: config.py, section 11.
"""

import email
import email.utils
import imaplib
import os
import re
from datetime import datetime, timedelta, timezone
from email.header import decode_header, make_header
from urllib.parse import unquote, urlparse

import requests
from bs4 import BeautifulSoup

import common
from config import (EMAIL_ALERTS, EMAIL_FOLLOW_TRACKING_LINKS,
                    EMAIL_LOOKBACK_DAYS, EMAIL_NEVER_FOLLOW_WORDS,
                    TIMEOUT_SECONDS, USER_AGENT)

MAX_TRACKING_LOOKUPS = 120      # per run, so a run can never take hours


class NotSetUp(Exception):
    """The Gmail secrets have not been added yet."""


_mailbox = None      # one connection shared by the four alert sources
_lookups = 0
_resolved = {}       # tracking link -> ad link (or None)


def _connect():
    """Logs in to Gmail and opens the mailbox read-only."""
    global _mailbox
    if _mailbox is not None:
        return _mailbox
    address = os.environ.get("GMAIL_ADDRESS", "").strip()
    password = os.environ.get("GMAIL_APP_PASSWORD", "").replace(" ", "")
    if not address or not password:
        raise NotSetUp("Email alerts are not set up yet (no Gmail secrets).")
    box = imaplib.IMAP4_SSL("imap.gmail.com", 993, timeout=TIMEOUT_SECONDS)
    try:
        box.login(address, password)
    except imaplib.IMAP4.error:
        raise RuntimeError("Gmail refused the sign-in. Check the two Gmail secrets.")
    # "All Mail" also finds alerts that a Gmail filter archived.
    status, _ = box.select('"[Gmail]/All Mail"', readonly=True)
    if status != "OK":
        box.select("INBOX", readonly=True)
    _mailbox = box
    return box


def emails_from(senders):
    """Recent emails from the given senders: list of (date, html, text)."""
    box = _connect()
    since = (datetime.now(timezone.utc) - timedelta(days=EMAIL_LOOKBACK_DAYS)).strftime("%d-%b-%Y")
    found, seen = [], set()
    for sender in senders:
        status, data = box.search(None, "FROM", '"%s"' % sender, "SINCE", since)
        if status != "OK":
            continue
        for number in data[0].split():
            if number in seen:
                continue
            seen.add(number)
            status, parts = box.fetch(number, "(BODY.PEEK[])")   # PEEK = stays unread
            if status != "OK" or not parts or not isinstance(parts[0], tuple):
                continue
            found.append(_read(email.message_from_bytes(parts[0][1])))
    return found


def _read(message):
    """Returns (date 'YYYY-MM-DD', html body, plain-text body)."""
    try:
        date = email.utils.parsedate_to_datetime(message["Date"]).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        date = None
    html, text = "", ""
    for part in message.walk():
        kind = part.get_content_type()
        if kind not in ("text/html", "text/plain"):
            continue
        payload = part.get_payload(decode=True) or b""
        body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        if kind == "text/html":
            html += body
        else:
            text += body
    return date, html, text


# ------------------------------------------------------------ ad links
def ad_link(href, pattern, label=""):
    """
    Turns a link from an email into the direct ad address, or None.
      1. The link is already an ad address.
      2. The ad address is tucked inside a tracking link.
      3. Ask the tracking address where it points (no visit to the ad site).
    """
    global _lookups
    match = pattern.search(href) or pattern.search(unquote(unquote(href)))
    if match:
        return match.group(0).rstrip("/.,)") + ("/" if match.group(0).endswith("/") else "")
    if not EMAIL_FOLLOW_TRACKING_LINKS or not href.startswith("http"):
        return None
    words = (label + " " + href).lower()
    if any(word in words for word in EMAIL_NEVER_FOLLOW_WORDS):
        return None                       # never touch unsubscribe / settings links
    if href in _resolved:
        return _resolved[href]
    _resolved[href] = None
    address = href
    for _ in range(3):                    # a tracking link may hop a few times
        if _lookups >= MAX_TRACKING_LOOKUPS or not common.allowed(address):
            break
        _lookups += 1
        try:
            reply = requests.head(address, allow_redirects=False, timeout=TIMEOUT_SECONDS,
                                  headers={"User-Agent": USER_AGENT})
        except requests.RequestException:
            break
        address = reply.headers.get("Location", "")
        match = pattern.search(address) or pattern.search(unquote(address))
        if match:
            _resolved[href] = match.group(0)
            break
        if not address.startswith("http"):
            break
    return _resolved[href]


def ads_in_email(pattern, html, text):
    """
    Finds each ad in one alert email. Returns {ad address: text of its block}.
    The block is the part of the email around the link that holds the price.
    """
    ads = {}
    if html:
        soup = BeautifulSoup(html, "html.parser")
        for link in soup.find_all("a", href=True):
            block = link
            for _ in range(6):            # climb to the block that holds the price
                words = common.clean(block.get_text(" "))
                if "€" in words or block.parent is None:
                    break
                if len(common.clean(block.parent.get_text(" "))) > 700:
                    break                 # that would be the whole email
                block = block.parent
            words = common.clean(block.get_text(" "))
            if "€" not in words and not pattern.search(unquote(link["href"])):
                continue                  # not a listing block: leave the link alone
            address = ad_link(link["href"], pattern, common.clean(link.get_text(" ")))
            if address and len(words) > len(ads.get(address, "")):
                ads[address] = words
    if not ads and text:                  # plain-text emails
        for match in pattern.finditer(text):
            start = max(0, match.start() - 300)
            ads.setdefault(match.group(0), common.clean(text[start:match.end()]))
    return ads


def link_hosts(html):
    """Website names of the links in an email (for the log only, no content)."""
    soup = BeautifulSoup(html or "", "html.parser")
    return sorted({urlparse(a["href"]).netloc for a in soup.find_all("a", href=True)
                   if a["href"].startswith("http")})


# ------------------------------------------------------------ the source
def collect(name):
    """All listings found in recent alert emails from one site."""
    spec = EMAIL_ALERTS[name]
    pattern = re.compile(spec["ad_link"], re.I)
    messages = emails_from(spec["senders"])
    listings, hosts = {}, set()
    for date, html, text in messages:
        ads = ads_in_email(pattern, html, text)
        if not ads:
            hosts.update(link_hosts(html))
        for url, words in ads.items():
            url = url.split("?")[0].split("#")[0]
            if url in listings:
                continue
            for_sale = "/koop/" in url or re.search(r"k\.k\.|v\.o\.n\.|kosten koper", words, re.I)
            bedrooms, estimated = common.parse_bedrooms(words)
            listings[url] = common.make_listing(
                name, "buy" if for_sale else "rent", url,
                address=_address(words, url), price=common.parse_price(words),
                m2=common.parse_m2(words), bedrooms=bedrooms,
                bedrooms_estimated=estimated, postcode=common.parse_postcode(words),
                posted=date, text=words, title=words[:160],
                # The ad address itself often names the type ("appartement-te-huur").
                type_text=urlparse(url).path.replace("-", " ").replace("/", " "),
                city="Amsterdam" if re.search(r"amsterdam", words + url, re.I) else None)
    # Shown in the run log: counts and site names only, never email content.
    print("  %s: %d alert emails, %d ads" % (name, len(messages), len(listings)))
    if messages and not listings:
        print("  %s: no ad links recognised. Links in those emails point to: %s"
              % (name, ", ".join(sorted(hosts)[:12]) or "nothing"))
    return list(listings.values())


def _address(words, url):
    """Street and number from the email block, else from the ad address."""
    match = re.search(r"([A-Z][\w.'’\- ]{2,40}?\s\d+[\w\- ]{0,6}),?\s+\d{4}\s?[A-Z]{2}", words)
    if match:
        return match.group(0)
    slug = urlparse(url).path.rstrip("/").split("/")[-1]
    return slug.replace("-", " ").title() + ", Amsterdam"

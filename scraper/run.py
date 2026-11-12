"""
The daily run. Start it with:   python scraper/run.py

What it does, in order:
  1. Asks every source for its current listings (one failing source does
     not stop the others).
  2. Throws out what can already be ruled out from the overview pages.
  3. Opens the ad page of every listing - new ones and the ones already on
     your site - to check it is still available and to read its details.
  4. Puts every listing through the strict gate in filters.py (rules in
     config.py), then the scam filter, then removes duplicates.
  5. Writes docs/data/listings.json, which the website reads.
"""

import importlib
import json
import unicodedata
import os
import re
import sys
import traceback
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

import common
import filters
import register
import scam
import sources
from config import (BUY, COPIED_TEXT_SENTENCES, MAX_FAILED_CHECKS, OPEN_PLATFORMS,
                    POSTCODES, RENT, SOURCE_PRIORITY, TYPE_FROM_AD_TEXT_SOURCES,
                    USE_ADDRESS_REGISTER)

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "..", "docs", "data", "listings.json")

# The line on an ad page that states what kind of home it is.
TYPE_LINE = re.compile(
    r"\b(soort woning|type woning|woningtype|soort woonhuis|soort appartement|soort object|"
    r"soort bouw|object ?type|type object|property type|type of property|type of house)"
    r"\s*:?\s*([^\d|]{3,45})", re.I)

# Rejections of an agency's own ad that also apply to copies elsewhere.
PASSED_ON = ("gone", "short let", "young people", "students only", "seniors only",
             "allocated via")

# Sources whose price is already the total, service costs included.
TOTAL_PRICE_SOURCES = {"Kamernet"}


def main():
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    old = load_existing()
    known = {item["url"]: item for item in old.get("listings", [])}

    # ---- 1. collect from every source -----------------------------------
    report, candidates = [], {}
    for name in sources.ACTIVE:
        entry = {"name": name, "ok": False, "found": 0, "shown": 0, "note": ""}
        try:
            module = importlib.import_module("sources." + name)
            entry["name"] = module.NAME
            found = module.collect()
            entry["found"] = len(found)
            entry["ok"] = True
            if not found:
                entry["note"] = ("Nothing found in Amsterdam today. If this stays at 0 for "
                                 "days, the site's layout may have changed.")
            for item in found:
                # ---- 2. rule out what the overview already tells us -----
                if item["url"] and could_match(item):
                    candidates.setdefault(item["url"], item)
        except common.Blocked as problem:
            entry["note"] = "Blocked: %s" % problem
        except Exception as problem:  # any bug or layout change in one source
            entry["note"] = "%s: %s" % (type(problem).__name__, str(problem)[:150])
            traceback.print_exc()
        print("%-22s %s  found %-4d %s" % (entry["name"], "OK  " if entry["ok"] else "FAIL",
                                           entry["found"], entry["note"]))
        report.append(entry)

    # ---- 3 + 4. check every ad, old and new -----------------------------
    result, removed = [], 0
    rejected_homes = {}     # home -> why an agency's own ad for it was rejected
    for url in list(known) + [u for u in candidates if u not in known]:
        previous = known.get(url)
        fresh = candidates.get(url)
        item = merge(previous, fresh, today)
        verdict = check_ad(item, fresh)
        if verdict != "keep":
            removed += previous is not None
            print("  - %-34s %s" % (verdict[:34], url))
            if (item.get("home_key") and item["source"] not in OPEN_PLATFORMS
                    and verdict.startswith(PASSED_ON)):
                rejected_homes[item["home_key"]] = verdict
            continue
        result.append(item)

    # A copy of a home whose own agency ad was rejected goes too.
    for item in list(result):
        why = rejected_homes.get(item["home_key"])
        if why:
            result.remove(item)
            print("  - %-34s %s" % (("agency ad: " + why)[:34], item["url"]))

    result, extra = drop_copied_text(result)
    removed += extra
    result, extra = drop_duplicates(result)
    removed += extra
    for item in result:
        item.pop("_sentences", None)

    for entry in report:
        entry["shown"] = sum(1 for item in result if item["source"] == entry["name"])

    # ---- 5. save ---------------------------------------------------------
    result.sort(key=lambda item: item["first_seen"], reverse=True)
    output = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "filters": {"rent": RENT, "buy": BUY, "postcodes": sorted(POSTCODES)},
        "sources": report,
        "not_included": [{"name": n, "note": why} for n, why in sources.NOT_INCLUDED],
        "listings": result,
    }
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as handle:
        json.dump(output, handle, ensure_ascii=False, indent=1)

    new = sum(1 for item in result if item["first_seen"] == today)
    print("\nDone: %d listings (%d new today, %d removed), %d page requests." % (
        len(result), new, removed, common.request_count))

    # If every single source failed, mark the run as failed so you get an email.
    if not any(entry["ok"] for entry in report):
        sys.exit("Every source failed - see the messages above.")


def load_existing():
    try:
        with open(DATA_FILE, encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, ValueError):
        return {}


def could_match(item):
    """
    Early exit using only the overview page, to avoid opening ad pages for
    nothing. It only ever says no when a rule is already clearly broken;
    the real decision is filters.check() in check_ad().
    """
    rule = RENT if item["kind"] == "rent" else BUY
    if not item["price"] or item["price"] > rule["max_price"]:
        return False
    if item["m2"] and item["m2"] < rule["min_m2"]:
        return False
    if item["bedrooms"] is not None and item["bedrooms"] not in rule["bedrooms"]:
        return False
    if item["postcode"] and item["postcode"] not in POSTCODES:
        return False
    if item["city"] and item["city"].lower() != "amsterdam":
        return False
    if item["title"] or item["type_text"]:
        _, reason = filters.home_type(item["title"], item["type_text"])
        if reason and not reason.startswith("type unclear"):
            return False            # a room, a studio, shared, a parking space
    return True


def merge(previous, fresh, today):
    """Combine what we stored before with what the source says today."""
    if previous is None:
        item = {key: fresh[key] for key in (
            "source", "kind", "url", "address", "city", "m2", "bedrooms",
            "bedrooms_estimated", "postcode", "posted", "title", "type_text",
            "start_date", "end_date")}
        item["base_price"] = fresh["price"]
        item["first_seen"] = today
        item["failed_checks"] = 0
        return item
    item = dict(previous)
    item.setdefault("base_price", item.get("price"))
    if fresh:
        item["base_price"] = fresh["price"] or item["base_price"]   # prices change
        for key in ("m2", "posted", "title", "type_text", "city",
                    "start_date", "end_date"):
            if fresh.get(key):
                item[key] = fresh[key]
    return item


def check_ad(item, fresh):
    """
    Opens the ad page, fills in missing details and applies the rules.
    Returns "keep", or the reason the listing is left out.
    """
    list_text = fresh["text"] if fresh else ""
    status = fresh["status_text"] if fresh else ""
    if filters.is_gone(status):
        return "gone"

    page = None
    try:
        reply = common.fetch(item["url"])
        if reply.status_code in (404, 410):
            return "gone"
        reply.raise_for_status()
        # Sent back to an overview page = the ad no longer exists.
        last_part = item["url"].rstrip("/").split("/")[-1]
        if reply.history and last_part not in reply.url:
            return "gone"
        page = read_ad(reply.text)
        item["failed_checks"] = 0
    except common.Blocked:
        pass  # not allowed to open ad pages here; use the overview data only
    except requests.RequestException:
        item["failed_checks"] = item.get("failed_checks", 0) + 1
        if item["failed_checks"] >= MAX_FAILED_CHECKS:
            return "unreachable"

    if page:
        status += " | " + page["status"]
    page_text = page["text"] if page else ""
    text = list_text + " " + page_text

    # ---- what kind of home is it? ---------------------------------------
    # The headline we judge: the source's title and type, plus the ad
    # page's own heading and its "Soort woning" line.
    if page or "type_source" not in item:
        parts = [item.get("title"), item.get("type_text")]
        if page:
            parts += [page["heading"], page["type_line"]]
        item["type_source"] = " | ".join(part for part in parts if part)
        # Agency sites that put no type in the title: use the ad's own text.
        if (page and item["source"] in TYPE_FROM_AD_TEXT_SOURCES
                and not filters.home_word_in(item["type_source"])):
            word = filters.home_word_in(page_text)
            if word:
                item["type_source"] += " | ad text: " + word

    # ---- postcode: the ad itself first, then the address register -------
    if not item.get("postcode"):
        item["postcode"] = common.postcode_near_street(page_text, item["address"])
    if not item.get("postcode") and USE_ADDRESS_REGISTER:
        item["postcode"] = register.lookup_postcode(item["address"])

    # ---- size, bedrooms, service costs ----------------------------------
    if not item.get("m2"):
        item["m2"] = common.parse_m2(page_text)
    if item.get("bedrooms") is None or item.get("bedrooms_estimated"):
        bedrooms, estimated = common.parse_bedrooms(page_text)
        if bedrooms is not None and (item.get("bedrooms") is None or not estimated):
            item["bedrooms"], item["bedrooms_estimated"] = bedrooms, estimated
    if item["kind"] != "rent" or item["source"] in TOTAL_PRICE_SOURCES:
        item["service_costs"] = 0
    elif text.strip():
        item["service_costs"] = common.parse_service_costs(text)
    item.setdefault("service_costs", 0)

    # ---- THE GATE: every rule in config.py ------------------------------
    facts = {
        "kind": item["kind"], "url": item["url"], "status": status,
        "title": item["type_source"], "type_text": "",
        "text": text, "city": item.get("city"), "postcode": item.get("postcode"),
        "price": item["base_price"], "service_costs": item["service_costs"],
        "m2": item.get("m2"), "bedrooms": item.get("bedrooms"),
        "start_date": item.get("start_date"), "end_date": item.get("end_date"),
    }
    item["home_key"] = home_key(item) if item.get("postcode") else None
    ok, reason = filters.check(facts)
    if not ok:
        return reason
    item["type"] = filters.home_type(item["type_source"])[0]
    item["price"] = filters.total_price(
        {"kind": item["kind"], "price": item["base_price"],
         "service_costs": item["service_costs"]})
    item.update(filters.place(item["postcode"]))
    for old_key in ("check_ij", "location_approximate"):
        item.pop(old_key, None)

    # ---- scam filter, rental period, tags -------------------------------
    # Only re-judge when we actually have ad text; otherwise keep what the
    # last successful check found.
    if text.strip() or "tags" not in item:
        verdict, reasons = scam.judge(item, text)
        if verdict == "drop":
            return "scam signs: " + "; ".join(reasons)
        if item["kind"] == "rent":
            term = filters.period(facts)
            item["rental_period"] = term["label"]
            item["fixed_term_months"] = term["months"]
        else:
            item["rental_period"], item["fixed_term_months"] = "", None
        item["registration"] = scam.registration(text)
        item["tags"] = scam.tags(item, text, item["rental_period"], item["fixed_term_months"])
        if item.get("bedrooms_estimated"):
            item["tags"].append("Bedrooms worked out from rooms")
        if item["service_costs"]:
            item["tags"].append("Includes €%d service costs" % item["service_costs"])
        item.pop("warnings", None)
    if page and item["source"] in OPEN_PLATFORMS:
        item["_sentences"] = {s.strip().lower() for s in re.split(r"[.!?]", page_text)
                              if len(s.strip()) >= 80}
    return "keep"


def plain(words):
    """Lower case without accents: 'Céramiquelaan' -> 'ceramiquelaan'."""
    words = unicodedata.normalize("NFKD", words)
    return "".join(c for c in words if not unicodedata.combining(c)).lower()


def street_of(item):
    """'Tugelaweg 139-F, Amsterdam' -> 'tugelaweg'."""
    return plain(re.split(r"\s+\d", re.sub(r",.*$", "", item["address"]))[0].strip())


def home_key(item):
    """
    Identifies the home itself, whichever site shows it:
    rent-or-buy + postcode + street + house number. None when the ad
    gives no house number.
    """
    address = re.sub(r"\b\d{4}\s?[A-Z]{2}\b", "", item["address"])
    address = re.sub(r"\b(amsterdam|nederland|netherlands)\b", "", address, flags=re.I)
    if not re.search(r"\d", address):
        return None
    return "%s:%s:%s" % (item["kind"], item["postcode"],
                         re.sub(r"[^a-z0-9]", "", plain(address)))


def drop_duplicates(items):
    """
    The same home on several sites is shown once, linking to the most
    direct ad (order: SOURCE_PRIORITY in config.py). The surviving listing
    keeps the earliest "first seen" date.
    """
    def rank(item):
        name = item["source"]
        return SOURCE_PRIORITY.index(name) if name in SOURCE_PRIORITY else len(SOURCE_PRIORITY)

    kept, dropped = [], 0
    for item in sorted(items, key=rank):
        twin = None
        for other in kept:
            same_address = item["home_key"] and item["home_key"] == other["home_key"]
            # Ads without a house number: same street, postcode, size and rent.
            same_details = (
                (not item["home_key"] or not other["home_key"])
                and other["source"] != item["source"]
                and (other["kind"], other["postcode"], other["m2"], other["base_price"])
                == (item["kind"], item["postcode"], item["m2"], item["base_price"])
                and street_of(other) == street_of(item))
            if same_address or same_details:
                twin = other
                break
        if twin is None:
            kept.append(item)
        else:
            twin["first_seen"] = min(twin["first_seen"], item["first_seen"])
            dropped += 1
            print("  - %-34s %s" % ("duplicate of " + twin["source"], item["url"]))
    return kept, dropped


def drop_copied_text(items):
    """
    Scam sign: the same long sentences in ads for different streets and
    postcodes on an open platform. Sentences that most ads of a site share
    (the site's own boilerplate) are ignored.
    """
    with_text = [item for item in items if item.get("_sentences")]
    boilerplate = set()
    for source in {item["source"] for item in with_text}:
        pages = [item["_sentences"] for item in with_text if item["source"] == source]
        counts = {}
        for sentences in pages:
            for sentence in sentences:
                counts[sentence] = counts.get(sentence, 0) + 1
        boilerplate |= {s for s, n in counts.items() if n >= max(3, len(pages) // 4)}
    copied = set()
    for index, item in enumerate(with_text):
        for other in with_text[index + 1:]:
            if item["postcode"] == other["postcode"] or street_of(item) == street_of(other):
                continue                      # the same building or project
            shared = (item["_sentences"] & other["_sentences"]) - boilerplate
            if len(shared) >= COPIED_TEXT_SENTENCES:
                copied |= {item["url"], other["url"]}
    for url in copied:
        print("  - %-34s %s" % ("scam signs: copied ad text", url))
    return [item for item in items if item["url"] not in copied], len(copied)


def read_ad(html):
    """
    Reads an ad page. Returns a dict with:
      text      - the visible ad text
      heading   - the page title and main heading
      type_line - the "Soort woning: Appartement" line, if there is one
      status    - title, heading and small status labels ("Verhuurd",
                  "Onder optie"). Labels inside links are ignored because
                  those belong to other homes shown as suggestions.
    """
    soup = BeautifulSoup(html, "html.parser")
    title = common.clean(soup.title.get_text(" ")) if soup.title else ""
    for junk in soup(["script", "style", "noscript", "nav", "footer", "header", "form"]):
        junk.decompose()
    # Link lists are site navigation ("Studentenwoningen in Amsterdam",
    # "Kamers in Utrecht"), not part of the ad.
    for block in soup.find_all(["ul", "ol"]):
        links = block.find_all("a")
        if len(links) >= 4:
            linked = sum(len(a.get_text(" ", strip=True)) for a in links)
            if linked >= 0.8 * max(len(block.get_text(" ", strip=True)), 1):
                block.decompose()
    h1 = common.clean(soup.h1.get_text(" ")) if soup.h1 else ""
    labels = []
    for element in soup.find_all(class_=re.compile(r"status|label|badge|sticker|ribbon", re.I)):
        words = common.clean(element.get_text(" "))
        if 0 < len(words) <= 40 and element.find_parent("a") is None:
            labels.append(words)
    body = soup.find("main") or soup.body or soup
    text = common.clean(body.get_text(" "))[:20000]
    type_line = TYPE_LINE.search(text)
    return {
        "text": text,
        "heading": " | ".join(part for part in (title, h1) if part),
        "type_line": common.clean(type_line.group(2))[:45] if type_line else "",
        "status": " | ".join([title, h1] + labels),
    }


if __name__ == "__main__":
    main()

"""
The list of sources. Each one is its own small file in this folder with:

    NAME      - shown on the website
    collect() - returns a list of listings (see common.make_listing)

To add a source: copy an existing file, adapt it, and add its name below.
To switch one off: put a # in front of its line.
"""

ACTIVE = [
    # agencies and landlords, read from their own websites
    "ikwilhuren",
    "vanderlinden",
    "vbt",
    "nmg",
    "fris",
    "rotsvast",
    "w123",
    "amsterdamrentals",
    "jlg",
    "heimstaden",
    # platforms
    "kamernet",
    "housinganywhere",
    # read from the alert emails they send you (never visited to search)
    "funda",
    "pararius",
    "huurwoningen",
    "hausing",
]

# Sources that were looked at and left out, with the reason.
# Shown on the website so it is clear they are not covered.
NOT_INCLUDED = [
    ("Rentola", "Removed: reposts other sites' ads and charges to see contact details."),
    ("Vesteda", "Listings load only through an internal search service."),
    ("Wonen bij Bouwinvest", "Listings are loaded by script, not present in the page."),
    ("Domica", "Listings are loaded by script, not present in the page."),
    ("Interhouse", "Listings load through an admin address its robots.txt closes."),
    ("Haas Housing", "Listings are loaded by script, not present in the page."),
    ("Expat Rentals", "Its robots.txt bars AI agents, so no module was built."),
    ("Holland2Stay", "Refuses automated visits (HTTP 403)."),
    ("REBO", "Refuses automated visits (bot check)."),
    ("Perfect Housing", "The site served looks like an archived copy; not reliable."),
    ("Huislijn", "Refuses automated visits (HTTP 403)."),
]

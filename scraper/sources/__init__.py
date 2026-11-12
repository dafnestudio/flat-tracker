"""
The list of sources. Each one is its own small file in this folder with:

    NAME      - shown on the website
    collect() - returns a list of listings (see common.make_listing)

To add a source: copy an existing file, adapt it, and add its name below.
To switch one off: put a # in front of its line.
"""

ACTIVE = [
    "rentola",
    "ikwilhuren",
    "housinganywhere",
    "kamernet",
    "nmg",
    "vbt",
    "fris",
    "rotsvast",
    "vanderlinden",
]

# Sources that were asked for but cannot be read by a well-behaved robot.
# Shown on the website so it is clear they are not covered.
NOT_INCLUDED = [
    ("Funda", "Blocks automated visits (bot-check page)."),
    ("Pararius", "Blocks automated visits; no permitted route found."),
    ("Huurwoningen.nl", "Refuses automated visits (HTTP 403)."),
    ("Hausing", "Its robots.txt bars AI agents, so no module was built."),
    ("Vesteda", "Listings load only through an internal search service."),
    ("Haas Housing", "Listings are loaded by script, not present in the page."),
    ("Huislijn", "Refuses automated visits (HTTP 403)."),
]

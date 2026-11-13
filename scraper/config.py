"""
THE RULEBOOK. Every filter rule of the flat tracker is in this one file.

Change a number, a postcode or a word here and the next daily run uses
it. The rules are applied by filters.py (the gate every listing must
pass), lets.py (rental period) and scam.py, and checked by
test_filters.py. A listing must pass every rule; anything unclear or
missing is dropped.

Word lists: plain words and phrases, matched as whole words, in Dutch
and English, upper or lower case. A few entries use ".." patterns
(\\w+ = any letters, ? = optional letter); copy the style if you add one.
"""

# ===================================================================
# 1. PRICE, SIZE, BEDROOMS
# ===================================================================
# Rent: total per month. Service costs an ad lists separately are added.
RENT = {"max_price": 1800, "min_m2": 50, "bedrooms": (1, 2)}
# Second rent tab on the site, "Rent €1,800–2,000": rentals whose total
# is above RENT's max_price, up to and including this amount. Every other
# rent rule (size, bedrooms, areas, type, period, scams) is identical.
# A flat is in one tab only: up to 1800 = Rent, 1801-2000 = this tab.
RENT_STRETCH_MAX_PRICE = 2000

# Buy: asking price "k.k." (kosten koper).
BUY = {"max_price": 500_000, "min_m2": 55, "bedrooms": (1, 2)}
# "2 kamers" = 1 bedroom, "3 kamers" = 2 bedrooms: bedrooms = rooms - 1.
ROOMS_MINUS = 1

# ===================================================================
# 2. AREAS: STRICT POSTCODE WHITELIST
# ===================================================================
# Only these 4-digit postcodes are shown. No postcode = dropped.
# Area names in an ad are never used.
POSTCODES = {
    # Noord: Overhoeks, Buiksloterham, Van der Pek, Volewijck, Vogelbuurt,
    # Nieuwendammerham, Nieuwendam
    "1021": ("Noord", "Vogelbuurt / IJplein"),
    "1022": ("Noord", "Nieuwendammerham"),
    "1023": ("Noord", "Nieuwendam"),
    "1031": ("Noord", "Overhoeks / Van der Pek / Buiksloterham"),
    # Centrum, including the Jordaan and the canal ring
    "1011": ("Centrum", "Nieuwmarkt / Lastage"),
    "1012": ("Centrum", "Burgwallen"),
    "1013": ("Centrum", "Haarlemmerbuurt / Westelijke Eilanden"),
    "1015": ("Centrum", "Jordaan / canal ring"),
    "1016": ("Centrum", "Jordaan / canal ring"),
    "1017": ("Centrum", "Canal ring south"),
    # Oost
    "1018": ("Oost", "Plantage / Oostelijke Eilanden"),
    "1019": ("Oost", "Oostelijk Havengebied"),
    "1091": ("Oost", "Oosterparkbuurt"),
    "1092": ("Oost", "Oosterparkbuurt / Dapperbuurt"),
    "1093": ("Oost", "Dapperbuurt"),
    "1094": ("Oost", "Indische Buurt"),
    "1095": ("Oost", "Indische Buurt / Zeeburgereiland"),
    # West
    "1051": ("West", "Staatsliedenbuurt / Westerpark"),
    "1052": ("West", "Staatsliedenbuurt / Westerpark"),
    "1053": ("West", "Oud-West"),
    "1054": ("West", "Oud-West / Overtoom"),
    "1055": ("West", "Bos en Lommer"),
    "1056": ("West", "De Baarsjes"),
    "1057": ("West", "De Baarsjes"),
    "1058": ("West", "De Baarsjes"),
    # Sloterdijk
    "1014": ("Sloterdijk", "Sloterdijk"),
    "1043": ("Sloterdijk", "Sloterdijk / Teleport"),
}
FAVOURITE_POSTCODES = {"1054"}      # starred on the site
CITY = "Amsterdam"                  # if an ad names a town, it must be this

# Where a postcode may come from: the overview or the ad page itself.
# If the ad prints a street AND house number but no postcode, the City of
# Amsterdam's official address register is asked for exactly that
# address. Set to False to drop every ad that prints no postcode.
USE_ADDRESS_REGISTER = True

# ===================================================================
# 3. ONLY WHOLE, SELF-CONTAINED FLATS OR HOUSES
# ===================================================================
# The ad's title or type line must contain one of these, otherwise the
# type is "unclear" and the ad is dropped.  word -> Type shown on the site.
HOME_WORDS = {
    "appartement": "Apartment", "apartment": "Apartment",
    "bovenwoning": "Apartment", "benedenwoning": "Apartment",
    "portiekwoning": "Apartment", "portiekflat": "Apartment",
    "galerijflat": "Apartment", "corridorflat": "Apartment",
    "tussenverdieping": "Apartment", "penthouse": "Apartment",
    "dubbel bovenhuis": "Apartment", "bovenhuis": "Apartment",
    "benedenhuis": "Apartment", "flat": "Apartment",
    "maisonnette": "Maisonette", "maisonette": "Maisonette",
    "eengezinswoning": "House", "tussenwoning": "House",
    "hoekwoning": "House", "woonhuis": "House", "herenhuis": "House",
    "grachtenpand": "House", "huis": "House", "house": "House",
    "zelfstandige woonruimte": "Apartment", "zelfstandig": "Apartment",
    "2-kamerappartement": "Apartment", "3-kamerappartement": "Apartment",
    "tweekamerappartement": "Apartment", "driekamerappartement": "Apartment",
    "2-kamerwoning": "Apartment", "3-kamerwoning": "Apartment",
    "tweekamerwoning": "Apartment", "driekamerwoning": "Apartment",
}
# Some agency sites put no type in the title. For these agencies only
# (never for open platforms), an apartment or house word in the ad's own
# text is accepted as the type.
TYPE_FROM_AD_TEXT_SOURCES = {"Van der Linden", "NMG Wonen", "Fris", "Rotsvast",
                             "VB&T", "ikwilhuren.nu (MVGM)", "123Wonen",
                             "Amsterdam Rentals", "JLG Real Estate", "Heimstaden"}

# Rooms, studios, shared. Any of these in the TITLE or TYPE = dropped.
# ("kamer" does not match "3 kamers" or "slaapkamer"; "room" does not
# match "bedroom".)
ROOM_WORDS_IN_TITLE = [
    "kamer", "room", "studio", "shared", "gedeeld", "gedeelde",
    "woningdelen", "woningdelers", "onzelfstandig", "onzelfstandige",
    "huisgenoot", "huisgenoten", "flatmate", "flatmates", "housemate",
    "housemates", "roommate", "student room", "studentenkamer",
    "hospita", "co-living", "coliving",
]
# Any of these ANYWHERE in the ad = dropped. (Narrower, because a
# description may fairly mention a "shared garden" or the "living room".)
ROOM_PHRASES_IN_TEXT = [
    r"onzelfstandig\w*", r"huisgeno\w+", r"flatmates?", r"housemates?",
    r"roommates?", r"student room", r"studentenkamer", r"hospita",
    r"co-?living",
    r"shared (apartment|flat|house|home|accommodation|kitchen|bathroom|toilet|shower)",
    r"(gedeelde?|gezamenlijke?|delen van de) (woning|keuken|badkamer|toilet|douche)",
    r"(keuken|badkamer|toilet|douche) (wordt|worden) gedeeld",
    r"room in (a |an )?(shared|student)",
    r"kamer in (een )?(gedeeld|studenten)",
]
# ...unless one of these comes right before it: "0 huisgenoten",
# "no housemates", "geen gedeelde keuken".
NEGATIONS = ["0", "no", "geen", "zonder", "without", "not", "niet", "nul", "zero"]

# Things that are not homes. In the title = dropped.
NOT_A_HOME_IN_TITLE = [
    "parkeerplaats", "parkeerplek", "parking space", "parking", "garagebox",
    "garage", "berging", "opslagruimte", "opslag", "storage unit", "storage",
    "ligplaats", "berth", "bedrijfsruimte", "kantoorruimte", "kantoor",
    "winkelruimte", "office space", "commercial space", "praktijkruimte",
]
# Anywhere in the ad = dropped.
NOT_A_HOME_ANYWHERE = [
    r"anti-?kraak", r"antikraak", r"leegstandbeheer", r"kraakwacht",
    r"property guardian\w*", r"guardianship", r"bruikleenovereenkomst",
]

# ===================================================================
# 4. LONG-TERM ONLY: NO LETS SHORTER THAN 6 MONTHS
# ===================================================================
MIN_LET_MONTHS = 6
# The dates and periods in the ad decide. An end date less than 6 months
# after move-in, or a maximum / fixed period under 6 months = dropped.
# Fixed terms of 6 months or more are kept and tagged.
#
# Short-stay wording: dropped UNLESS the ad also shows a period of
# 6 months or more (or says the contract is indefinite).
SHORT_LET_WORDS = [
    "short stay", "shortstay", "short term", "short-term", "korte termijn",
    "korte periode", "sublet", "subletting", "sublease", "onderhuur",
    "onderverhuur", "tussenhuur", "while i'm away", "while i am away",
    "while we are away", "tijdens mijn afwezigheid", "holiday rental",
    "holiday let", "holiday home", "vakantiewoning", "vakantieverhuur",
]
# Says the contract has no end date.
INDEFINITE_WORDS = [
    "onbepaalde tijd", "indefinite", "unlimited period", "open-ended",
    "permanent contract", "vast contract", "geen einddatum", "no end date",
]

# ===================================================================
# 5. HOMES RESERVED FOR SPECIFIC GROUPS = DROPPED
# ===================================================================
# reason shown in the log -> phrases
RESERVED_FOR_GROUPS = {
    "young people only (under 28)": [
        r"jongerenwoning\w*", r"jongerencontract\w*", r"jongerenhuisvesting",
        r"youth contract", r"(tot|t/m|tot en met|until|under|onder) (de )?(27|28) (jaar|years)",
        r"18 (tot|t/m|-|to) 2[78] jaar", r"between 18 and 2[78]",
    ],
    "students only": [
        r"studentenwoning\w*", r"studentencomplex", r"studentenhuisvesting",
        r"campuscontract", r"student housing", r"students only",
        r"only (for )?students", r"(alleen|uitsluitend|enkel) (voor )?studenten",
    ],
    "seniors only": [
        r"(55|60|65) ?\+", r"(55|60|65)-?plus\w*", r"senioren\w*",
        r"seniors only", r"senior housing", r"ouderenwoning\w*",
    ],
    "allocated via WoningNet / waiting list / urgency": [
        r"woningnet", r"woonnet", r"op de wachtlijst", r"on the waiting list",
        r"wachtlijst voor (de|deze|een) woning\w*",
        r"waiting list for (the|this|an?) (apartment|home|house|property)",
        r"inschrijfduur", r"urgentie\w*", r"urgency", r"sociale huurwoning\w*",
        r"sociale huur", r"social housing",
    ],
}
# (A phrase right after "geen", "no", "zonder" and the like does not
# count: "geen wachtlijst". See NEGATIONS in section 3.)

# ===================================================================
# 6. ALREADY GONE = DROPPED
# ===================================================================
# Looked for in the ad's status label, title and main heading.
GONE_WORDS = [
    "verhuurd", "verhuurd onder voorbehoud", "onder optie", "in optie",
    "onder bod", "verkocht", "verkocht onder voorbehoud", "rented",
    "rented out", "let agreed", "under option", "under offer", "sold",
    "sold subject to conditions", "sold stc", "niet meer beschikbaar",
    "no longer available", "not available anymore", "vervallen",
    "ingetrokken", "gereserveerd", "reserved",
]

# ===================================================================
# 7. BUYING: NOT WANTED
# ===================================================================
# (New-build with no price or size yet is dropped by rule 1: missing
# price or size = dropped.)
BUY_NOT_WANTED = {
    "auction": [r"veiling", r"executieveiling", r"auction", r"bij opbod"],
    "sold with a sitting tenant": [
        r"verhuurd te koop", r"in verhuurde staat", r"verhuurde staat",
        r"beleggingsobject\w*", r"beleggingspand", r"sitting tenant",
        r"tenanted", r"investment property", r"wordt verhuurd verkocht",
    ],
    "share in a housing co-op": [
        r"lidmaatschapsrecht\w*", r"co[oö]peratieve flat\w*",
        r"woonco[oö]peratie", r"housing co-?op\w*", r"aandelen in de",
        r"cooperative apartment",
    ],
    "no price yet": [r"prijs op aanvraag", r"price on request", r"prijs n\.?o\.?t\.?k"],
}

# ===================================================================
# 8. SCAM SIGNS
# ===================================================================
# Sites where anyone can place an ad. Agency websites are trusted more.
OPEN_PLATFORMS = {"Kamernet", "HousingAnywhere"}

# Any one of these = dropped.
SCAM_SIGNS = {
    "Owner says they are abroad":
        r"(i am|i'm|we are|owner is|landlord is|eigenaar (is|zit|woont)|ik ben|ik zit|ik woon)[^.]{0,30}"
        r"(abroad|out of the country|overseas|in het buitenland)",
    "Keys sent by post or courier":
        r"(keys?|sleutels?)[^.]{0,50}(by post|by mail|via post|per post|courier|koerier|\bdhl\b|\bups\b|fedex|opsturen|toesturen|opgestuurd)",
    "Payment or deposit before a viewing":
        r"(pay|payment|deposit|transfer|betaal\w*|betalen|aanbetaling|borg|overmaken)[^.]{0,40}"
        r"(before|prior to|voordat|voorafgaand aan|vóór)[^.]{0,25}(viewing|bezichtig\w*|visit)",
    "Money-transfer service mentioned":
        r"western union|moneygram|money gram|bitcoin|crypto|gift ?card",
    "Third-party 'escrow' payment (Airbnb/Booking trick)":
        r"(airbnb|booking\.com|tripadvisor)[^.]{0,60}(payment|betaling|deposit|borg|transaction|handle)",
    "ID or passport requested up front":
        r"(send|stuur|mail|provide|verstrek)[^.]{0,40}(copy of (your )?(passport|id)|kopie (van )?(je |uw )?(paspoort|id|identiteitsbewijs))",
}
# Contact pushed off the platform, by a private advertiser = dropped.
PRIVATE_CONTACT_SIGNS = {
    "Contact by WhatsApp only":
        r"(only|alleen|uitsluitend|just)[^.]{0,25}whats ?app|whats ?app[^.]{0,20}(only|alleen)",
    "Contact by private email address":
        r"[\w.+-]+@(gmail|hotmail|outlook|yahoo|live|proton|protonmail|icloud)\.\w+",
}
# Rent per m2 (EUR). On open platforms, below FAR_TOO_CHEAP with no
# explanation = dropped. Below ON_THE_LOW_SIDE = kept, tagged "Check carefully".
FAR_TOO_CHEAP_PER_M2 = 13
ON_THE_LOW_SIDE_PER_M2 = 17
# An explanation for a low rent: income rules, mid-rent and the like.
LOW_PRICE_EXPLANATIONS = [
    r"inkomenseis\w*", r"inkomensgrens", r"inkomenstoets", r"income requirement\w*",
    r"minimum income", r"maximum income", r"maximaal inkomen", r"middenhuur",
    r"mid-?rent", r"huurtoeslag", r"woningwaarderingsstelsel",
    r"bruto ?(maand|jaar)?inkomen", r"gross (monthly|annual) income",
]
# The same long sentences in ads for different streets and postcodes on
# an open platform = copied text = dropped. This many shared sentences:
COPIED_TEXT_SENTENCES = 3

# ===================================================================
# 9. KEPT, BUT TAGGED
# ===================================================================
TAG_FIXED_TERM = "Fixed term: %d months"
TAG_CHECK_PERIOD = "Check rental period"
TAG_PRIVATE = "Private landlord: view before paying"
TAG_CHECK_CAREFULLY = "Check carefully"
TAG_REGISTRATION = {"allowed": "Registration allowed",
                    "not allowed": "No registration",
                    "not stated": "Registration: ask"}
# Platforms where private people place ads themselves. An ad there that
# uses none of the agency words below is tagged as a private landlord.
PRIVATE_AD_PLATFORMS = {"Kamernet", "HousingAnywhere"}
AGENCY_WORDS = [
    r"makelaar\w*", r"makelaardij", r"vastgoed\w*", r"real estate", r"agency",
    r"estate agent\w*", r"property management", r"verhuurmakelaar\w*",
    r"woningbeheer", r"beheerder", r"housing b\.?v\.?", r"\bb\.v\.", r"\bnvm\b",
    r"\bvbo\b", r"mvgm", r"vesteda", r"funda",
]
NO_DEPOSIT_WORDS = [r"geen borg", r"zonder borg", r"no deposit", r"without deposit",
                    r"geen waarborgsom"]

# ===================================================================
# 10. DUPLICATES
# ===================================================================
# The same home on several sites is shown once, linking to the most
# direct ad: agency sites first, then Funda/Pararius, then aggregators.
# Earlier in this list wins. If an agency's own ad for a home is rejected
# as gone, reserved or a short let, copies of it elsewhere go too.
SOURCE_PRIORITY = [
    "Van der Linden", "Fris", "NMG Wonen", "VB&T", "Rotsvast",
    "ikwilhuren.nu (MVGM)", "123Wonen", "Amsterdam Rentals",
    "JLG Real Estate", "Heimstaden", "Hausing",      # agencies and landlords
    "Funda", "Pararius", "Huurwoningen.nl",          # the big portals (email alerts)
    "Kamernet", "HousingAnywhere",                   # open platforms
]

# ===================================================================
# 11. EMAIL ALERTS (Funda, Pararius, Huurwoningen.nl, Hausing)
# ===================================================================
# These sites do not allow robots, so they are never visited to search.
# Instead the run reads the alert emails they send you (read-only: it
# never deletes, sends or marks anything) and takes the ad links from
# them. Your Gmail address and app password are NOT in this file: they
# are stored as GitHub repository secrets.
#
#   senders:  the email comes from an address containing one of these
#   ad_link:  what a direct link to one ad looks like on that site
EMAIL_ALERTS = {
    "Funda": {
        "senders": ["funda.nl"],
        "ad_link": r"https?://(?:www\.)?funda\.nl/(?:detail/)?(?:huur|koop)/[^\s\"'<>?#&]*\d{6,}[^\s\"'<>?#&]*",
    },
    "Pararius": {
        "senders": ["pararius.nl", "pararius.com"],
        "ad_link": r"https?://(?:www\.)?pararius\.(?:nl|com)/[a-z-]+-(?:te-huur|for-rent)/amsterdam/[0-9a-z]{6,}/[^\s\"'<>?#&]+",
    },
    "Huurwoningen.nl": {
        "senders": ["huurwoningen.nl"],
        "ad_link": r"https?://(?:www\.)?huurwoningen\.nl/(?:en/)?(?:huren|rent)/amsterdam/[0-9a-z]{6,}/[^\s\"'<>?#&]+",
    },
    "Hausing": {
        "senders": ["hausing.com"],
        "ad_link": r"https?://(?:www\.)?hausing\.com/(?:nl/)?(?:properties-for-rent|huurwoningen|property|rent)[a-z-]*/[^\s\"'<>?#&]{8,}",
    },
}
EMAIL_LOOKBACK_DAYS = 14          # how far back alert emails are read
# Alert emails wrap links in tracking addresses. To find the real ad
# address the run asks the tracking address where it points (one request,
# without visiting the ad site). Never done for unsubscribe or settings links.
EMAIL_FOLLOW_TRACKING_LINKS = True
EMAIL_NEVER_FOLLOW_WORDS = ["uitschrijven", "afmelden", "unsubscribe", "opzeggen",
                            "voorkeuren", "preferences", "instellingen", "settings",
                            "wijzig", "beheer", "manage", "verwijder", "delete",
                            "pauzeer", "pause", "stop"]
# If the email gives no size or bedroom count, the ad page is opened once,
# but only if that site's robots.txt allows it. Otherwise the listing is
# kept with this tag. (No postcode still means no listing.)
TAG_CHECK_DETAILS = "Check details on the ad"
# Ads on these sites cannot be re-checked for "let / sold", so a listing
# from an alert email is removed this many days after it was first found.
EMAIL_LISTING_MAX_AGE_DAYS = 14

# ===================================================================
# 12. MANNERS (how the robot behaves on other people's websites)
# ===================================================================
USER_AGENT = "personal-flat-tracker/1.0 (non-commercial; one visit per day)"
DELAY_SECONDS = 2.0  # pause between two requests to the same website
TIMEOUT_SECONDS = 30
# A listing is removed after its ad could not be loaded this many runs in a row.
MAX_FAILED_CHECKS = 3

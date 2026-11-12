"""
Automated tests for the rules in config.py. Run them with:

    python -m unittest discover -s scraper -v

Each test is an example listing and what must happen to it.
The last class checks every listing that is actually on the website.
"""

import json
import os
import unittest
from datetime import date

import common
import filters
import run
import lets
import scam

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "docs", "data", "listings.json")
TODAY = date(2026, 11, 12)


def flat(**changes):
    """A listing that passes every rule; each test changes something."""
    listing = {
        "kind": "rent", "source": "Fris",
        "url": "https://agency.example/aanbod/overtoom-100-amsterdam/",
        "title": "Appartement te huur: Overtoom 100", "type_text": "Appartement",
        "status": "Beschikbaar",
        "text": "Licht appartement met balkon. Huurcontract voor 12 maanden.",
        "address": "Overtoom 100", "city": "Amsterdam", "postcode": "1054",
        "price": 1700, "service_costs": 0, "m2": 62, "bedrooms": 2,
    }
    listing.update(changes)
    return listing


def check(listing):
    return filters.check(listing, today=TODAY)


class MustFail(unittest.TestCase):
    """The examples from the spec that must be rejected."""

    def reject(self, listing, because):
        ok, why = check(listing)
        self.assertFalse(ok, "was accepted but should fail")
        self.assertIn(because, why)

    def test_room_in_oud_west(self):
        self.reject(flat(title="Kamer te huur in Oud-West, Bilderdijkstraat",
                         type_text="Kamer", postcode="1053", price=950, m2=55,
                         bedrooms=1), "room")

    def test_flat_in_nieuw_west(self):
        self.reject(flat(postcode="1064", address="Burgemeester Roellstraat 10"), "1064")

    def test_ndsm_flat(self):
        self.reject(flat(postcode="1033", address="ms. Oslofjordweg 158"), "1033")

    def test_one_month_furnished_let_in_de_baarsjes(self):
        self.reject(flat(
            postcode="1057", title="Furnished apartment De Baarsjes",
            text="Fully furnished apartment, available for 1 month while I travel."),
            "short let")

    def test_jongerencontract_flat(self):
        self.reject(flat(text="Appartement met jongerencontract, 18 t/m 27 jaar."),
                    "young people")

    def test_flat_onder_optie(self):
        self.reject(flat(status="Onder optie"), "gone")

    def test_parking_space(self):
        self.reject(flat(title="Parkeerplaats te huur Overtoom", type_text="Parkeerplaats"),
                    "not a home")

    def test_flat_of_1850(self):
        self.reject(flat(price=1850), "expensive")

    def test_flat_of_45_m2(self):
        self.reject(flat(m2=45), "small")

    def test_three_bedroom_flat(self):
        self.reject(flat(bedrooms=3), "3 bedrooms")

    def test_listing_with_no_postcode(self):
        self.reject(flat(postcode=None,
                         title="Appartement in de Jordaan, Oud-West, Overtoom"),
                    "no postcode")


class MustPass(unittest.TestCase):
    """The examples from the spec that must be accepted."""

    def test_two_bedroom_1700_on_the_overtoom_with_12_month_contract(self):
        home = flat()
        self.assertEqual(check(home), (True, ""))
        self.assertTrue(filters.place("1054")["favourite"])
        term = filters.period(home, TODAY)
        self.assertEqual(term["label"], "Fixed term: 12 months")
        self.assertIn("Fixed term: 12 months",
                      scam.tags(home, home["text"], term["label"], term["months"]))

    def test_one_bedroom_55_m2_in_the_vogelbuurt_indefinite_contract(self):
        home = flat(title="Bovenwoning Meeuwenlaan 12", postcode="1021", bedrooms=1,
                    m2=55, price=1500,
                    text="Huurovereenkomst voor onbepaalde tijd. Borg 2 maanden huur.")
        self.assertEqual(check(home), (True, ""))
        self.assertEqual(filters.period(home, TODAY)["label"], "Indefinite")

    def test_480k_60_m2_two_bedroom_to_buy_in_the_indische_buurt(self):
        home = flat(kind="buy", title="Appartement te koop: Javastraat 50",
                    postcode="1094", price=480000, m2=60, bedrooms=2,
                    text="Instapklaar appartement met balkon. Eigen grond.")
        self.assertEqual(check(home), (True, ""))


class OnlyWholeHomes(unittest.TestCase):

    def test_room_studio_and_shared_titles_fail(self):
        for title in ["Room in city center", "Small room in flat",
                      "Studio te huur", "Studio apartment Jordaan",
                      "Shared apartment in De Baarsjes", "Woningdelen toegestaan appartement",
                      "Onzelfstandige woonruimte", "Appartement, huisgenoot gezocht",
                      "Student room near Overtoom", "Kamer bij hospita",
                      "Lovely room in a cozy home, female flatmate only"]:
            self.assertFalse(check(flat(title=title, type_text=""))[0], title)

    def test_shared_facilities_in_the_description_fail(self):
        for text in ["You share the kitchen: shared kitchen and bathroom.",
                     "De keuken wordt gedeeld met twee anderen.",
                     "Je krijgt twee leuke huisgenoten.",
                     "Dit is een onzelfstandige woonruimte."]:
            self.assertFalse(check(flat(text=text))[0], text)

    def test_no_housemates_is_not_shared(self):
        for text in ["0 huisgenoten. Contract 12 maanden.",
                     "No housemates, the entire space is yours. Contract 12 months.",
                     "Geen gedeelde keuken. Contract 12 maanden."]:
            self.assertEqual(check(flat(text=text)), (True, ""), text)

    def test_unclear_type_fails(self):
        ok, why = check(flat(title="Te huur: Overtoom 100", type_text=""))
        self.assertFalse(ok)
        self.assertIn("unclear", why)

    def test_real_home_types_pass(self):
        for title in ["Bovenwoning Overtoom", "Benedenwoning met tuin",
                      "Maisonnette in Oud-West", "Huis te huur",
                      "Zelfstandige woonruimte", "Portiekwoning in Amsterdam",
                      "Apartment for rent", "Appartement met parkeerplaats",
                      "Ruim 2-kamerappartement", "Te huur | ad text: appartement",
                      "Appartement Molenwerf + parkeerplaats"]:
            self.assertEqual(check(flat(title=title, type_text="")), (True, ""), title)

    def test_ordinary_words_do_not_trigger_the_room_rule(self):
        self.assertEqual(check(flat(
            title="3 kamers appartement, 2 bedroom apartment",
            text="Ruime woonkamer en 2 slaapkamers. Large living room. Shared "
                 "garden, eigen berging. Contract voor onbepaalde tijd.")), (True, ""))

    def test_things_that_are_not_homes_fail(self):
        for title in ["Garagebox te huur", "Berging / opslagruimte", "Ligplaats aan de Amstel",
                      "Kantoorruimte Overtoom", "Bedrijfsruimte te huur", "Storage unit"]:
            self.assertFalse(check(flat(title=title, type_text=""))[0], title)
        for text in ["Wonen op basis van anti-kraak.", "Property guardianship via leegstandbeheer."]:
            self.assertFalse(check(flat(text=text))[0], text)


class StrictPostcodes(unittest.TestCase):

    def test_everything_outside_the_list_fails(self):
        outside = {"1024": "Buikslotermeer", "1025": "Buikslotermeer",
                   "1032": "Noord beyond the list", "1033": "NDSM",
                   "1034": "Noord north of the A10", "1061": "Nieuw-West",
                   "1069": "Nieuw-West", "1072": "De Pijp", "1077": "Zuid",
                   "1086": "IJburg", "1087": "IJburg", "1096": "Amstelkwartier",
                   "1097": "Watergraafsmeer", "1098": "Watergraafsmeer",
                   "1102": "Zuidoost", "1181": "Amstelveen", "1111": "Diemen",
                   "1506": "Zaandam", "1121": "Landsmeer", "1315": "Almere",
                   "2011": "Haarlem"}
        for postcode, name in outside.items():
            self.assertFalse(check(flat(postcode=postcode))[0], name)

    def test_every_listed_postcode_passes(self):
        wanted = ["1021", "1022", "1023", "1031", "1011", "1012", "1013", "1015",
                  "1016", "1017", "1018", "1019", "1091", "1092", "1093", "1094",
                  "1095", "1051", "1052", "1053", "1054", "1055", "1056", "1057",
                  "1058", "1014", "1043"]
        self.assertEqual(sorted(filters.POSTCODES), sorted(wanted))
        for postcode in wanted:
            self.assertEqual(check(flat(postcode=postcode)), (True, ""), postcode)

    def test_other_town_fails(self):
        self.assertFalse(check(flat(city="Amstelveen"))[0])

    def test_only_1054_is_a_favourite(self):
        self.assertEqual([p for p in filters.POSTCODES if filters.place(p)["favourite"]],
                         ["1054"])

    def test_office_postcode_on_the_page_is_not_used(self):
        page = ("Tugelaweg 139-F 1091 VX Amsterdam. Contact: Makelaar X, "
                "Bos en Lommerplein 309, 1055 RW Amsterdam")
        self.assertEqual(common.postcode_near_street(page, "Tugelaweg 139-F, Amsterdam"), "1091")
        self.assertIsNone(common.postcode_near_street(
            "Kantoor: Bos en Lommerplein 309, 1055 RW", "Grubbehoeve 714, Amsterdam"))


class RentalPeriod(unittest.TestCase):

    def term(self, text, **dates):
        return lets.rental_period(text, today=TODAY, **dates)

    def test_short_lets_fail(self):
        for text in ["Available for 3 months only.",
                     "Maximale huurperiode 4 maanden.",
                     "Te huur voor een periode van 2 maanden.",
                     "Sublet of my apartment while I'm away.",
                     "Short stay appartement in het centrum.",
                     "Tijdelijke verhuur, max 5 maanden.",
                     "Available from 01-12-2026 until 01-03-2027.",
                     "Beschikbaar per 1 december 2026 tot 1 februari 2027.",
                     "Holiday rental, perfect for expats."]:
            self.assertFalse(self.term(text)["ok"], text)

    def test_end_date_from_the_source_is_used(self):
        self.assertFalse(self.term("", start="2026-12-01", end="2027-03-31")["ok"])
        long_let = self.term("", start="2026-12-01T00:00:00", end="2028-09-30T00:00:00")
        self.assertTrue(long_let["ok"])
        self.assertEqual(long_let["label"], "Fixed term: 21 months")

    def test_fixed_terms_of_six_months_or_more_pass_and_are_labelled(self):
        self.assertEqual(self.term("Tijdelijk contract 24 months.")["label"],
                         "Fixed term: 24 months")
        self.assertEqual(self.term("Huurcontract voor 1 jaar.")["label"],
                         "Fixed term: 12 months")
        self.assertEqual(self.term("Temporary contract of 6 months.")["label"],
                         "Fixed term: 6 months")
        self.assertTrue(self.term("Short stay possible, contract for 12 months.")["ok"])

    def test_minimum_periods_deposits_and_notice_are_not_fixed_terms(self):
        self.assertEqual(self.term("Huurtermijn (min.) 12 Maanden")["label"], "Minimum 12 months")
        self.assertEqual(self.term("Minimale huurperiode 12 maanden.")["label"], "Minimum 12 months")
        self.assertEqual(self.term(
            "De huurovereenkomst wordt aangegaan voor de duur van 12 maanden. Notice "
            "period of 1 month. Waarborgsom: minimaal 1, maximaal 2 maanden.")["label"],
            "Fixed term: 12 months")
        for text in ["Borg 2 maanden huur.", "Deposit: 2 months rent.",
                     "Opzegtermijn 1 maand.", "Beschikbaar over 2 weken.",
                     "Waarborgsom van 1 maand."]:
            self.assertEqual(self.term(text)["label"], "Not stated", text)

    def test_indefinite_and_not_stated(self):
        self.assertEqual(self.term("Contract voor onbepaalde tijd.")["label"], "Indefinite")
        self.assertEqual(self.term("Mooi appartement met balkon.")["label"], "Not stated")
        home = flat(text="Mooi appartement met balkon.")
        self.assertIn("Check rental period", scam.tags(home, home["text"], "Not stated", None))

    def test_buying_ignores_rental_period_words(self):
        self.assertTrue(check(flat(kind="buy", price=450000, text="Short stay vergunning aanwezig."))[0])


class ReservedGroups(unittest.TestCase):

    def test_reserved_homes_fail(self):
        for text in ["Jongerenwoning voor 18 t/m 27 jaar.", "Dit betreft een jongerencontract.",
                     "Students only, proof of enrolment required.",
                     "Alleen voor studenten met campuscontract.",
                     "Seniorenwoning, 55+ complex.", "Geschikt voor 65+.",
                     "Reageren kan via WoningNet.", "Toewijzing op inschrijfduur.",
                     "Alleen met urgentieverklaring.", "Sociale huurwoning.",
                     "Je komt dan op de wachtlijst."]:
            self.assertFalse(check(flat(text=text))[0], text)

    def test_a_waiting_list_for_parking_is_not_a_housing_waiting_list(self):
        self.assertEqual(check(flat(text="De garage heeft 33 parkeerplaatsen. Op dit moment "
                                         "is er een wachtlijst. Contract 12 maanden.")), (True, ""))

    def test_negated_phrases_are_not_reserved(self):
        self.assertEqual(check(flat(
            text="Geen wachtlijst voor de parkeervergunning. Contract 12 maanden.")), (True, ""))

    def test_no_students_is_not_students_only(self):
        self.assertEqual(check(flat(
            text="Niet geschikt voor studenten. No students. Contract 12 maanden.")), (True, ""))


class AlreadyGone(unittest.TestCase):

    def test_gone_statuses_fail(self):
        for status in ["Verhuurd", "Rented", "Onder optie", "Under option", "Onder bod",
                       "Verkocht", "Sold", "Verkocht onder voorbehoud",
                       "Sold subject to conditions", "Verhuurd onder voorbehoud",
                       "Gereserveerd"]:
            ok, why = check(flat(status=status))
            self.assertFalse(ok, status)
            self.assertIn("gone", why)

    def test_available_statuses_pass(self):
        for status in ["Beschikbaar", "Te huur", "Nieuw", "Available", ""]:
            self.assertEqual(check(flat(status=status)), (True, ""), status)


class Buying(unittest.TestCase):

    def home(self, **changes):
        base = dict(kind="buy", price=475000, m2=60, bedrooms=2, postcode="1094",
                    title="Appartement te koop", text="Mooi appartement.")
        base.update(changes)
        return flat(**base)

    def test_limits(self):
        self.assertEqual(check(self.home()), (True, ""))
        self.assertEqual(check(self.home(price=500000)), (True, ""))
        self.assertFalse(check(self.home(price=510000))[0])
        self.assertFalse(check(self.home(m2=54))[0])
        self.assertFalse(check(self.home(bedrooms=3))[0])

    def test_auctions_tenants_coops_fail(self):
        for text in ["Verkoop via executieveiling.", "Online auction on 3 December.",
                     "Verhuurd te koop, ideaal beleggingsobject.",
                     "Wordt in verhuurde staat verkocht.",
                     "Het betreft een lidmaatschapsrecht in een coöperatieve flatvereniging.",
                     "Prijs op aanvraag."]:
            self.assertFalse(check(self.home(text=text))[0], text)

    def test_new_build_without_price_or_size_fails(self):
        self.assertFalse(check(self.home(price=None, title="Nieuwbouw appartement"))[0])
        self.assertFalse(check(self.home(m2=None, title="Nieuwbouw appartement"))[0])


class PriceSizeBedrooms(unittest.TestCase):

    def test_exactly_1800_passes(self):
        self.assertEqual(check(flat(price=1800)), (True, ""))

    def test_service_costs_are_added(self):
        self.assertEqual(check(flat(price=1700, service_costs=100)), (True, ""))
        ok, why = check(flat(price=1750, service_costs=75))
        self.assertFalse(ok)
        self.assertIn("1825", why)

    def test_size_limits(self):
        self.assertEqual(check(flat(m2=50)), (True, ""))
        self.assertFalse(check(flat(m2=49))[0])

    def test_bedroom_limits(self):
        self.assertEqual(check(flat(bedrooms=1)), (True, ""))
        self.assertFalse(check(flat(bedrooms=0))[0])

    def test_missing_price_size_or_bedrooms_fails(self):
        for missing in ("price", "m2", "bedrooms"):
            self.assertFalse(check(flat(**{missing: None}))[0], missing)

    def test_dutch_rooms_become_bedrooms(self):
        self.assertEqual(common.parse_bedrooms("Appartement, 2 kamers"), (1, True))
        self.assertEqual(common.parse_bedrooms("Appartement, 3 kamers"), (2, True))
        self.assertEqual(common.parse_bedrooms("Aantal kamers: 4"), (3, True))
        self.assertEqual(common.parse_bedrooms("3 kamers (2 slaapkamers)"), (2, False))

    def test_service_costs_are_read_from_ad_text(self):
        read = common.parse_service_costs
        self.assertEqual(read("Huur € 1.295,- Servicekosten € 60,- per maand"), 60)
        self.assertEqual(read("Service costs: €85 per month"), 85)
        self.assertEqual(read("Huurprijs is inclusief servicekosten"), 0)
        self.assertEqual(read("Rent € 1.700 including service costs of € 50"), 0)


class LinksAndScams(unittest.TestCase):

    def test_no_direct_ad_link_fails(self):
        for url in ["", None, "https://agency.example/", "agency.example/ad/1"]:
            ok, why = check(flat(url=url))
            self.assertFalse(ok, url)
            self.assertIn("link", why)

    def test_obvious_scams_are_dropped(self):
        private = flat(source="Kamernet")
        for text in ["I am currently abroad so I cannot show the flat.",
                     "The keys will be sent by DHL after payment.",
                     "Please pay the deposit before the viewing.",
                     "Send a copy of your passport to reserve.",
                     "Payment via Western Union.",
                     "Contact me only on WhatsApp.",
                     "Mail me at nicelandlord@gmail.com"]:
            self.assertEqual(scam.judge(private, text)[0], "drop", text)

    def test_far_too_cheap_on_an_open_platform_is_dropped(self):
        cheap = flat(source="Rentola", price=600, m2=60)
        self.assertEqual(scam.judge(cheap, "Mooi appartement.")[0], "drop")
        self.assertEqual(scam.judge(cheap, "Middenhuur, inkomenseis geldt.")[0], "ok")

    def test_tags(self):
        home = flat(source="Kamernet", price=950, m2=60)
        got = scam.tags(home, "Leuk appartement, geen borg.", "Not stated", None)
        for tag in ["Check rental period", "Private landlord: view before paying",
                    "Check carefully", "Registration: ask"]:
            self.assertIn(tag, got)
        agency = flat()
        self.assertNotIn("Private landlord: view before paying",
                         scam.tags(agency, agency["text"], "Indefinite", None))
        self.assertIn("Registration allowed", scam.tags(
            agency, "Inschrijven op het adres is mogelijk.", "Indefinite", None))
        self.assertIn("No registration", scam.tags(
            agency, "Inschrijving op het adres is niet mogelijk.", "Indefinite", None))


class Duplicates(unittest.TestCase):

    def home(self, source, address, first_seen="2026-11-11"):
        item = {"kind": "rent", "source": source, "address": address, "postcode": "1031",
                "m2": 60, "base_price": 1605, "first_seen": first_seen,
                "url": "https://%s.example/ad" % source.lower().replace(" ", "").replace("&", "")}
        item["home_key"] = run.home_key(item)
        return item

    def test_same_home_on_two_sites_is_shown_once_agency_first(self):
        agency = self.home("VB&T", "Ceramiquelaan 441, Amsterdam", "2026-11-11")
        copy = self.home("Rentola", "Céramiquelaan 441, 1031 KG Amsterdam", "2026-11-09")
        other = self.home("Rentola", "Céramiquelaan 443, 1031 KG Amsterdam")
        kept, dropped = run.drop_duplicates([copy, other, agency])
        self.assertEqual(dropped, 1)
        self.assertEqual(sorted(item["source"] for item in kept), ["Rentola", "VB&T"])
        self.assertEqual(agency["first_seen"], "2026-11-09")   # earliest sighting kept
        self.assertIn(other, kept)                             # the neighbour stays


class TheWebsiteItself(unittest.TestCase):
    """Every listing in the data file the website shows."""

    def setUp(self):
        with open(DATA_FILE, encoding="utf-8") as handle:
            self.listings = json.load(handle)["listings"]

    def test_every_listing_passes_every_rule(self):
        for item in self.listings:
            again = dict(item, price=item["base_price"], title=item["type_source"],
                         type_text="", text="", status="")
            ok, why = filters.check(again)
            self.assertTrue(ok, "%s: %s" % (item["url"], why))
            self.assertIn(item["type"], ("Apartment", "Maisonette", "House"))
            if item["kind"] == "rent":
                months = item.get("fixed_term_months")
                self.assertTrue(months is None or months >= 6, item["url"])
                self.assertTrue(item["rental_period"], item["url"])

    def test_no_home_is_shown_twice(self):
        links = [item["url"] for item in self.listings]
        self.assertEqual(len(links), len(set(links)))
        keys = [item["home_key"] for item in self.listings if item.get("home_key")]
        self.assertEqual(len(keys), len(set(keys)))


if __name__ == "__main__":
    unittest.main()

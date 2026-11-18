"""Stufe 3 – Integrationstests: echter Redis-Server, eigene Datenbank 15.

Importiert die Fixture-Datei mit load() und prüft 2 a–d gegen bekannte Erwartungen.
Datenbank 15 wird vorher und nachher geleert; die echten Daten in db 0 bleiben unberührt.
"""
import json
import unittest

from helpers import FIXTURE, SYNTHETIC, TEST_DB, redis_or_none, skip_reason, yr

R = redis_or_none(TEST_DB)
FIXTURE_LINES = [l.strip() for l in open(FIXTURE, encoding="utf-8") if l.strip()]
NAMES = {yr.name_key(json.loads(l)["name"]) for l in FIXTURE_LINES} - {""}


@unittest.skipIf(R is None, skip_reason() if R is None else "")
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.n = yr.load(R, FIXTURE, flush=True, verbose=False, batch_size=3)  # mehrere Pipeline-Stapel

    @classmethod
    def tearDownClass(cls):
        R.flushdb()

    # --- 2 a ---------------------------------------------------------------
    def test_i01_import_count(self):
        self.assertEqual(self.n, 13)

    def test_i02_business_key_holds_original_json(self):
        """Jeder Eintrag byte-genau wie in der Datei – auch mit Umlauten/CJK (kein json.dumps-Umbau,
        der z. B. 'é' zu '\\u00e9' machen würde)."""
        for line in FIXTURE_LINES:
            bid = json.loads(line)["business_id"]
            self.assertEqual(R.get("business:" + bid), line, bid)
        self.assertEqual(R.type("business:id-cjk"), "string")

    def test_i03_key_count(self):
        """Keys = 13 Betriebe + 11 Namen + 1 Index (der Betrieb ohne Namen bekommt kein Set)."""
        self.assertEqual(R.dbsize(), 13 + len(NAMES) + 1)

    # --- 2 b ---------------------------------------------------------------
    def test_i04_name_set_lowercase_and_merged(self):
        self.assertEqual(yr.ids_for_name(R, "Starbucks"), {"id-sb-1", "id-sb-2", "id-sb-3"})
        self.assertEqual(R.type("starbucks"), "set")

    def test_i05_reimport_is_idempotent(self):
        yr.load(R, FIXTURE, verbose=False)
        self.assertEqual(R.scard("starbucks"), 3)
        self.assertEqual(R.zcard(yr.AUTOCOMPLETE_KEY), len(NAMES))

    def test_i06_empty_name_not_indexed(self):
        self.assertIsNotNone(R.get("business:id-noname"))
        self.assertNotIn("", R.zrange(yr.AUTOCOMPLETE_KEY, 0, -1))

    # --- 2 c ---------------------------------------------------------------
    def test_i07_prefix_star(self):
        self.assertEqual(yr.autocomplete(R, "Star"), ["star pizza", "starbucks", "starbucks coffee"])

    def test_i08_case_insensitive(self):
        self.assertEqual(yr.autocomplete(R, "sTaRbUcKs"), ["starbucks", "starbucks coffee"])

    def test_i09_the_sti(self):
        self.assertEqual(yr.autocomplete(R, "The Sti"), ["the still", "the stirling room"])

    def test_i10_no_match_and_empty(self):
        self.assertEqual(yr.autocomplete(R, "xyz-gibt-es-nicht"), [])
        self.assertEqual(yr.autocomplete(R, ""), [])

    def test_i11_limit(self):
        self.assertEqual(yr.autocomplete(R, "s", limit=2), ["star pizza", "starbucks"])

    def test_i12_unicode(self):
        self.assertEqual(yr.autocomplete(R, "Café M"), ["café müller"])
        self.assertEqual(yr.autocomplete(R, "寿"), ["寿司 sushi bar"])
        self.assertEqual(yr.autocomplete(R, "pho ð"), ["pho ðắc biệt"])

    def test_i13_last_entry_and_no_false_positive(self):
        self.assertEqual(yr.autocomplete(R, "zzz"), ["zzz last name"])
        self.assertNotIn("star pizza", yr.autocomplete(R, "starbucks"))

    # --- 2 d ---------------------------------------------------------------
    def test_i14_details_the_still(self):
        by_city = {d["city"]: d for d in yr.details(R, "The Still")}
        self.assertEqual(set(by_city), {"Las Vegas", "Calgary"})
        self.assertEqual(by_city["Las Vegas"]["address"], "3400 S Las Vegas Blvd")
        self.assertEqual(by_city["Calgary"]["stars"], 2.5)

    def test_i15_details_unknown(self):
        self.assertEqual(yr.details(R, "gibt es nicht"), [])


@unittest.skipIf(R is None, skip_reason() if R is None else "")
class SyntheticFileTests(unittest.TestCase):
    """200 Datensätze im echten Yelp-Format."""

    def test_i16_synthetic_file(self):
        try:
            self.assertEqual(yr.load(R, SYNTHETIC, flush=True, verbose=False), 200)
            self.assertEqual(R.scard("starbucks"), 5)  # inkl. "STARBUCKS"
            self.assertEqual(yr.autocomplete(R, "the sti"), ["the sticky rice", "the still", "the stillery"])
        finally:
            R.flushdb()


if __name__ == "__main__":
    unittest.main(verbosity=2)

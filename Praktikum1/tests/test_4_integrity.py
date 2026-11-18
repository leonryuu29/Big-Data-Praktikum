"""Stufe 5 – Datenintegrität: echte Daten (business.json) in db 0.

Vergleicht jeden gespeicherten Eintrag mit der Quelldatei, prüft die Namens-Sets und den
Index gegen eine unabhängige Berechnung in reinem Python (ohne Redis) und bestätigt
die Antworten der Abgabe. Wird übersprungen, wenn Datei oder Import fehlen.
"""
import collections
import json
import os
import unittest

from helpers import REAL_DATA, REAL_RECORDS, real_data_imported, redis_or_none, yr

R = redis_or_none(0)
READY = R is not None and os.path.isfile(REAL_DATA) and real_data_imported(R)


@unittest.skipUnless(READY, "echte Daten oder Import fehlen")
class IntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Orakel: alles direkt aus der Datei, ohne Redis
        cls.lines = {}
        cls.by_name = collections.defaultdict(set)
        with open(REAL_DATA, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                obj = json.loads(line)
                cls.lines[obj["business_id"]] = line
                if obj.get("name"):
                    cls.by_name[obj["name"].lower()].add(obj["business_id"])

    def _prefix(self, p):
        return sorted(n for n in self.by_name if n.startswith(p.lower()))

    # --- Vollständigkeit -----------------------------------------------------
    def test_g01_record_count(self):
        """192 609 Datensätze (Aufgabenblatt nennt 209 393 – andere Version des Datensatzes)."""
        self.assertEqual(len(self.lines), REAL_RECORDS)

    def test_g02_unique_business_ids(self):
        with open(REAL_DATA, encoding="utf-8") as f:
            n = sum(1 for l in f if l.strip())
        self.assertEqual(n, len(self.lines))

    def test_g03_key_count(self):
        """Keys = Betriebe + verschiedene Namen + 1 Index."""
        self.assertEqual(R.dbsize(), REAL_RECORDS + len(self.by_name) + 1)

    # --- Feldgenauigkeit (2 a) ----------------------------------------------------
    def test_g04_every_json_string_identical(self):
        ids = list(self.lines)
        for i in range(0, len(ids), 10000):
            chunk = ids[i:i + 10000]
            stored = R.mget([yr.BUSINESS_PREFIX + b for b in chunk])
            bad = [b for b, s in zip(chunk, stored) if s != self.lines[b]]
            self.assertEqual(bad, [], f"{len(bad)} Abweichungen ab Block {i}")

    # --- Namens-Sets (2 b) und Index (2 c) ----------------------------------------
    def test_g05_every_name_set_identical(self):
        names = list(self.by_name)
        for i in range(0, len(names), 5000):
            pipe = R.pipeline(transaction=False)
            for n in names[i:i + 5000]:
                pipe.smembers(n)
            for n, members in zip(names[i:i + 5000], pipe.execute()):
                self.assertEqual(set(members), self.by_name[n], n)

    def test_g06_index_equals_names(self):
        self.assertEqual(set(R.zrange(yr.AUTOCOMPLETE_KEY, 0, -1)), set(self.by_name))

    # --- Antworten der Abgabe gegen das Orakel -------------------------------------
    def test_g07_star_prefix(self):
        got = yr.autocomplete(R, "Star")
        self.assertEqual(got, self._prefix("star"))
        self.assertEqual(len(got), 181)
        self.assertIn("starlight nails & spa", got)

    def test_g08_starbucks(self):
        self.assertEqual(R.scard("starbucks"), len(self.by_name["starbucks"]))
        self.assertEqual(R.scard("starbucks"), 1066)
        total = sum(len(self.by_name[n]) for n in yr.autocomplete(R, "starbucks"))
        self.assertEqual(total, 1073)

    def test_g09_the_still(self):
        self.assertEqual(R.scard("the still"), 2)
        self.assertEqual(yr.autocomplete(R, "The Sti"), self._prefix("the sti"))
        self.assertEqual(yr.autocomplete(R, "The Sti"),
                         ["the still", "the stirling club spa", "the stirling room"])

    def test_g10_details_the_still(self):
        rows = sorted(yr.details(R, "The Still"), key=lambda d: d["city"])
        self.assertEqual([(d["city"], d["state"], d["stars"]) for d in rows],
                         [("Calgary", "AB", 2.5), ("Las Vegas", "NV", 3.5)])


if __name__ == "__main__":
    unittest.main(verbosity=2)

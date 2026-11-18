"""Stufe 2 – Unit-Tests: reine Python-Logik, ohne Redis.

Geprüft werden das Einlesen der JSON-Lines-Datei, die Bildung der Namensschlüssel (2 b),
die Grenzen der Präfixsuche (2 c) und die Aufbereitung der Details (2 d).
"""
import json
import unittest

from helpers import FIXTURE, SYNTHETIC, yr

FIXTURE_NAMES = sorted({yr.name_key(json.loads(l)["name"]) for l in open(FIXTURE, encoding="utf-8") if l.strip()})


def in_range(name, prefix):
    """Würde ZRANGEBYLEX mit prefix_range(prefix) diesen Namen liefern? (Byte-Vergleich wie Redis)"""
    lo, hi = yr.prefix_range(prefix)
    b = name.encode("utf-8")
    return lo[1:] <= b <= hi[1:]


class ReadFileTests(unittest.TestCase):
    def test_u01_json_lines_and_blank_lines(self):
        rows = list(yr.iter_businesses(FIXTURE))
        self.assertEqual(len(rows), 13)               # 2 Leerzeilen am Ende ignoriert
        raw, obj = rows[0]
        self.assertEqual(json.loads(raw), obj)        # rohe Zeile = gültiges JSON des Objekts

    def test_u02_unicode_read_correctly(self):
        names = [o["name"] for _, o in yr.iter_businesses(FIXTURE)]
        self.assertIn("Café Müller", names)
        self.assertIn("寿司 Sushi Bar", names)

    def test_u03_synthetic_file_structure(self):
        rows = list(yr.iter_businesses(SYNTHETIC))
        self.assertEqual(len(rows), 200)
        self.assertTrue(all("business_id" in o and "name" in o for _, o in rows))


class NameKeyTests(unittest.TestCase):
    def test_u04_lowercase(self):
        self.assertEqual(yr.name_key("STARBUCKS"), "starbucks")
        self.assertEqual(yr.name_key("Starbucks"), yr.name_key("starbucks"))

    def test_u05_unicode_lowercase(self):
        self.assertEqual(yr.name_key("CAFÉ MÜLLER"), "café müller")

    def test_u06_missing_name(self):
        self.assertEqual(yr.name_key(None), "")
        self.assertEqual(yr.name_key(""), "")


class PrefixRangeTests(unittest.TestCase):
    def test_u07_empty_prefix(self):
        self.assertIsNone(yr.prefix_range(""))

    def test_u08_bounds(self):
        lo, hi = yr.prefix_range("Star")
        self.assertEqual(lo, b"[star")
        self.assertEqual(hi, b"[star\xff")

    def test_u09_matches_exactly_the_prefix_names(self):
        """Eigenschaft: im Bereich liegen genau die Namen, die mit dem Präfix beginnen."""
        for prefix in ("s", "star", "starbucks", "the sti", "café", "寿", "pho ð", "z", "x"):
            expect = [n for n in FIXTURE_NAMES if n.startswith(yr.name_key(prefix))]
            got = [n for n in FIXTURE_NAMES if in_range(n, prefix)]
            self.assertEqual(got, expect, prefix)

    def test_u10_byte_ff_needed(self):
        """Mit dem Zeichen 'ÿ' (UTF-8 C3 BF) statt des Bytes 0xFF ginge z. B. 'abc€…' verloren."""
        lo = "[abc".encode()
        wrong_hi = "[abcÿ".encode()
        name = "[abc€".encode()            # € = E2 82 AC, liegt hinter C3 BF
        self.assertFalse(lo <= name <= wrong_hi)
        self.assertTrue(lo <= name <= lo + b"\xff")


class DetailsTests(unittest.TestCase):
    def test_u11_summarize(self):
        raw = next(r for r, o in yr.iter_businesses(FIXTURE) if o["business_id"] == "id-still-1")
        d = yr.summarize("id-still-1", raw)
        self.assertEqual((d["address"], d["city"], d["stars"]), ("3400 S Las Vegas Blvd", "Las Vegas", 3.5))

    def test_u12_format_details(self):
        rows = [yr.summarize(o["business_id"], r) for r, o in yr.iter_businesses(FIXTURE)
                if o["name"] == "The Still"]
        text = yr.format_details(rows)
        self.assertIn("Calgary", text)
        self.assertIn("2.5 Sterne (8 Reviews, geschlossen)", text)
        self.assertEqual(len(text.splitlines()), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Stufe 4 – Effizienztests: wie viele und welche Befehle schickt der Code an Redis?

Redis zählt jeden Befehl in INFO commandstats. Nach CONFIG RESETSTAT zeigt die Statistik
genau, was eine Funktion ausgelöst hat. So wird nachgewiesen:
- die Autovervollständigung (2 c) braucht genau EIN ZRANGEBYLEX und nie KEYS/SCAN,
- die Details (2 d) brauchen genau ein SMEMBERS und ein MGET (kein GET pro Betrieb),
- der Import (2 a/b) bündelt die Befehle per Pipeline in wenige Roundtrips.
Gegenprobe: dieselbe Präfixsuche per SCAN über alle Schlüssel liefert dasselbe Ergebnis,
braucht aber Hunderte Aufrufe und durchläuft die ganze Datenbank.
Läuft auf den echten Daten in db 0 (nur lesend).
"""
import time
import unittest

from helpers import FIXTURE, TEST_DB, real_data_imported, redis_or_none, skip_reason, yr

R = redis_or_none(0)
READY = R is not None and real_data_imported(R)


def command_calls(r, fn):
    """fn ausführen und {befehl: anzahl} der dabei ausgeführten Redis-Befehle zurückgeben."""
    r.config_resetstat()
    result = fn()
    stats = r.info("commandstats")
    calls = {k.replace("cmdstat_", ""): v["calls"] for k, v in stats.items()}
    calls.pop("info", None)          # die Abfrage der Statistik selbst
    calls.pop("config|resetstat", None)
    calls.pop("config", None)
    return result, calls


@unittest.skipUnless(READY, "echte Daten nicht importiert" if R is not None else skip_reason())
class EfficiencyTests(unittest.TestCase):
    def test_l01_autocomplete_single_zrangebylex(self):
        result, calls = command_calls(R, lambda: yr.autocomplete(R, "Star"))
        self.assertEqual(calls, {"zrangebylex": 1})
        self.assertEqual(len(result), 181)

    def test_l02_details_two_commands(self):
        result, calls = command_calls(R, lambda: yr.details(R, "Starbucks"))
        self.assertEqual(calls, {"smembers": 1, "mget": 1})
        self.assertEqual(len(result), 1066)

    def test_l03_no_keys_or_scan_anywhere(self):
        _, calls = command_calls(R, lambda: [yr.autocomplete(R, p) for p in ("a", "the sti", "寿", "")])
        self.assertNotIn("keys", calls)
        self.assertNotIn("scan", calls)
        self.assertEqual(calls.get("zrangebylex"), 3)   # leeres Präfix: gar keine Anfrage

    def test_l04_scan_alternative_is_much_more_work(self):
        """Gegenprobe ohne Index: gleiches Ergebnis, aber ein Scan über alle Schlüssel."""
        def scan_prefix():
            return sorted({k for k in R.scan_iter(match="star*", count=1000)
                           if R.type(k) == "set"})
        t0 = time.perf_counter()
        expected = yr.autocomplete(R, "star")
        t_index = time.perf_counter() - t0
        t0 = time.perf_counter()
        found, calls = command_calls(R, scan_prefix)
        t_scan = time.perf_counter() - t0
        self.assertEqual(found, expected)
        self.assertGreater(calls["scan"], 100)          # ~340 000 Schlüssel / 1000 pro Aufruf
        self.assertGreater(t_scan, 10 * t_index)

    def test_l05_import_uses_pipeline(self):
        """Import der Fixture (13 Betriebe) mit batch_size=5: 3 Roundtrips statt ~36."""
        rt = R.__class__(host="localhost", port=6379, db=TEST_DB, decode_responses=True, protocol=2)
        executed = []
        real_pipeline = rt.pipeline

        def counting_pipeline(*a, **k):
            p = real_pipeline(*a, **k)
            orig = p.execute

            def execute(*ea, **ek):
                executed.append(1)
                return orig(*ea, **ek)
            p.execute = execute
            return p
        rt.pipeline = counting_pipeline
        try:
            n = yr.load(rt, FIXTURE, flush=True, verbose=False, batch_size=5)
            self.assertEqual(n, 13)
            self.assertEqual(len(executed), 3)          # 5 + 5 + Rest 3
        finally:
            rt.flushdb()


if __name__ == "__main__":
    unittest.main(verbosity=2)

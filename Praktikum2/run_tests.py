"""Testkette für Praktikum 2: führt die fünf Stufen nacheinander aus.

  1 Smoke        – Umgebung läuft (Treiber, Server, Dateien)          tests/test_0_smoke.py
  2 Unit         – reine Python-Logik ohne Datenbank                    tests/test_1_unit.py
  3 Integration  – Schema + Abfragen auf echtem Cassandra (Test-Keyspace) tests/test_2_integration.py
  4 Lokalität    – Abfragen lesen genau eine Partition (Tracing)        tests/test_3_locality.py
  5 Integrität   – echte Daten Feld für Feld gegen die CSV-Dateien       tests/test_4_integrity.py

Schlägt der Smoke-Test fehl, bricht die Kette ab (die übrigen Stufen hätten keine Aussagekraft).
Aufruf:  python run_tests.py            (Ausgabe zusätzlich in results/test_output.txt)
Exit-Code 0 nur, wenn alle ausgeführten Tests bestanden sind.
"""
import io
import os
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.abspath(__file__))
TESTS = os.path.join(ROOT, "tests")
sys.path.insert(0, TESTS)

STAGES = [("1 Smoke", "test_0_smoke"), ("2 Unit", "test_1_unit"), ("3 Integration", "test_2_integration"),
          ("4 Lokalität", "test_3_locality"), ("5 Integrität", "test_4_integrity")]


def main():
    buf = io.StringIO()

    def out(s=""):
        print(s)
        buf.write(s + "\n")

    summary, ok_all = [], True
    for name, module in STAGES:
        out(f"\n{'=' * 70}\nStufe {name}  ({module}.py)\n{'=' * 70}")
        suite = unittest.defaultTestLoader.loadTestsFromName(module)
        stream = io.StringIO()
        t0 = time.time()
        res = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        out(stream.getvalue().rstrip())
        passed = res.testsRun - len(res.failures) - len(res.errors) - len(res.skipped)
        summary.append((name, res.testsRun, passed, len(res.failures) + len(res.errors), len(res.skipped),
                        time.time() - t0))
        ok_all &= res.wasSuccessful()
        if module == "test_0_smoke" and not res.wasSuccessful():
            out("\nSmoke-Test fehlgeschlagen -> Abbruch der Testkette.")
            break

    out(f"\n{'=' * 70}\nZusammenfassung\n{'=' * 70}")
    out(f"{'Stufe':<16}{'Tests':>6}{'ok':>6}{'Fehler':>8}{'skip':>6}{'Zeit':>9}")
    for name, n, p, f, s, dt in summary:
        out(f"{name:<16}{n:>6}{p:>6}{f:>8}{s:>6}{dt:>8.2f}s")
    tot = [sum(x[i] for x in summary) for i in (1, 2, 3, 4)]
    out(f"{'Gesamt':<16}{tot[0]:>6}{tot[1]:>6}{tot[2]:>8}{tot[3]:>6}")
    out("ERGEBNIS: " + ("BESTANDEN" if ok_all else "FEHLGESCHLAGEN"))
    os.makedirs(os.path.join(ROOT, "results"), exist_ok=True)
    with open(os.path.join(ROOT, "results", os.environ.get("TEST_OUTPUT", "test_output.txt")), "w",
              encoding="utf-8") as f:
        f.write(buf.getvalue())
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())

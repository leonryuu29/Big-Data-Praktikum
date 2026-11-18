"""Stufe 1 – Smoke-Tests: läuft die Umgebung überhaupt?

Schnell (Sekunden) und zuerst: Treiber importierbar, Cassandra erreichbar,
Version, Schema-Dateien vorhanden, Skripte kompilieren.
"""
import os
import py_compile
import unittest

from helpers import CQL_DIR, ROOT, session_or_none, skip_reason


class SmokeTests(unittest.TestCase):
    def test_s01_driver_importable(self):
        import cassandra  # noqa: F401
        self.assertTrue(cassandra.__version__)

    def test_s02_cql_files_present(self):
        for f in ("aufgabe1_person.cql", "aufgabe3_schema.cql", "aufgabe3_import.cql", "aufgabe3_check.cql",
                  "aufgabe3_query_tables.cql", "aufgabe3_query_import.cql", "aufgabe3_queries.cql"):
            self.assertTrue(os.path.isfile(os.path.join(CQL_DIR, f)), f)

    def test_s03_scripts_compile(self):
        for f in ("movielens_cassandra.py", "denormalize.py", "answers.py"):
            py_compile.compile(os.path.join(ROOT, f), doraise=True)

    def test_s04_cassandra_reachable(self):
        s = session_or_none()
        if s is None:
            self.skipTest(skip_reason())
        v = s.execute("SELECT release_version FROM system.local").one().release_version
        self.assertRegex(v, r"^\d+\.\d+")

    def test_s05_simple_roundtrip(self):
        s = session_or_none()
        if s is None:
            self.skipTest(skip_reason())
        self.assertEqual(s.execute("SELECT now() FROM system.local").one() is not None, True)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Stufe 1 – Smoke-Tests: läuft die Umgebung überhaupt?

Schnell und zuerst: Paket redis importierbar, Server erreichbar (PING), Version lesbar,
Skripte kompilieren, Dateien vorhanden. Schlägt diese Stufe fehl, bricht run_tests.py ab.
"""
import os
import py_compile
import unittest

from helpers import FIXTURE, ROOT, SYNTHETIC, redis_or_none, skip_reason


class SmokeTests(unittest.TestCase):
    def test_s01_package_importable(self):
        import redis
        self.assertTrue(redis.__version__)

    def test_s02_scripts_compile(self):
        for f in ("yelp_redis.py", "analyze_structure.py", "load_data.py", "autocomplete.py", "answers.py"):
            py_compile.compile(os.path.join(ROOT, f), doraise=True)

    def test_s03_files_present(self):
        for p in (FIXTURE, SYNTHETIC, os.path.join(ROOT, "cli", "aufgabe1.redis")):
            self.assertTrue(os.path.isfile(p), p)

    def test_s04_server_ping(self):
        r = redis_or_none()
        if r is None:
            self.skipTest(skip_reason())
        self.assertTrue(r.ping())

    def test_s05_server_version(self):
        r = redis_or_none()
        if r is None:
            self.skipTest(skip_reason())
        version = r.info("server")["redis_version"]
        self.assertRegex(str(version), r"^\d+\.\d+")


if __name__ == "__main__":
    unittest.main(verbosity=2)

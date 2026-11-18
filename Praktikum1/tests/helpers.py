"""Gemeinsame Hilfen für die Testsuite von Praktikum 1 (Redis-Verbindung, Pfade, Datenbanken).

Datenbanken auf demselben Redis-Server:
  db 0   die echten Yelp-Daten (load_data.py)       -> Stufen 4 und 5 lesen nur
  db 15  Testdaten der Stufe 3 (wird geleert)       -> echte Daten bleiben unberührt
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import yelp_redis as yr  # noqa: E402

FIXTURE_DIR = os.path.join(HERE, "fixtures")
FIXTURE = os.path.join(FIXTURE_DIR, "business_fixture.json")
SYNTHETIC = os.path.join(FIXTURE_DIR, "sample_synthetic.json")
DATA_DIR = os.environ.get("YELP_DIR", os.path.join(ROOT, "data"))
REAL_DATA = os.path.join(DATA_DIR, "business.json")
SAMPLE_DATA = os.path.join(DATA_DIR, "businessS.json")
TEST_DB = 15
REAL_RECORDS = 192609

_conn = {}
_error = None


def redis_or_none(db=0):
    """Verbindung oder None (Tests werden dann übersprungen statt rot)."""
    global _error
    if db not in _conn and _error is None:
        try:
            _conn[db] = yr.connect(db=db)
        except Exception as e:  # Server läuft nicht / Paket fehlt
            _error = e
    return _conn.get(db)


def skip_reason():
    return f"Redis nicht erreichbar: {_error!r}"


def real_data_imported(r):
    """True, wenn db 0 den vollständigen Import enthält."""
    try:
        return r.zcard(yr.AUTOCOMPLETE_KEY) > 100000 and r.get("business:1SWheh84yJXfytovILXOAQ") is not None
    except Exception:
        return False

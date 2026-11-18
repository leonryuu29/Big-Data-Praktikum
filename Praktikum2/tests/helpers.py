"""Gemeinsame Hilfen für die Testsuite (Cassandra-Verbindung, Test-Keyspace, CQL-Dateien)."""
import os
import re
import sys
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import movielens_cassandra as mc  # noqa: E402

CQL_DIR = os.path.join(ROOT, "cql")
DATA_DIR = os.environ.get("MOVIELENS_DIR", os.path.join(ROOT, "data", "ml-latest-small"))
FIXTURE_DIR = os.path.join(HERE, "fixtures")


def cql_statements(filename, keyspace=None):
    """Anweisungen einer .cql-Datei (ohne Kommentare und cqlsh-Befehle wie COPY).

    Mit keyspace wird 'movielens' durch einen Test-Keyspace ersetzt, damit Tests die
    importierten Daten nie verändern.
    """
    src = open(os.path.join(CQL_DIR, filename), encoding="utf-8").read()
    src = re.sub(r"--[^\n]*", "", src)
    out = []
    for s in (x.strip() for x in src.split(";")):
        if not s or s.upper().startswith(("COPY", "DESCRIBE")):
            continue
        if keyspace:
            s = re.sub(r"\bmovielens\b", keyspace, s)
        out.append(s)
    return out


def copy_columns(filename):
    """{tabelle: [spalten]} aus den COPY-Befehlen einer .cql-Datei."""
    src = open(os.path.join(CQL_DIR, filename), encoding="utf-8").read()
    return {t: [c.strip() for c in cols.split(",")]
            for t, cols in re.findall(r"COPY\s+(\w+)\s*\(([^)]*)\)", src)}


_session = None
_error = None


def session_or_none():
    """Verbindung zu Cassandra oder None (Tests werden dann übersprungen)."""
    global _session, _error
    if _session is None and _error is None:
        try:
            _session = mc.connect(keyspace=None)
        except Exception as e:  # Treiber fehlt oder Server nicht erreichbar
            _error = e
    return _session


def skip_reason():
    session_or_none()
    return f"Cassandra nicht erreichbar: {_error!r}"


def create_test_keyspace(session):
    """Frischer Keyspace mit dem Schema aus den echten CQL-Dateien."""
    ks = "test_" + uuid.uuid4().hex[:10]
    for f in ("aufgabe3_schema.cql", "aufgabe3_query_tables.cql"):
        for stmt in cql_statements(f, keyspace=ks):
            session.execute(stmt)
    session.set_keyspace(ks)
    return ks


def drop_keyspace(session, ks):
    session.execute(f"DROP KEYSPACE IF EXISTS {ks}")


def real_data_imported(session):
    """True, wenn movielens existiert und alle fünf Tabellen gefüllt sind."""
    try:
        rows = session.execute("SELECT table_name FROM system_schema.tables WHERE keyspace_name = 'movielens'")
        names = {r.table_name for r in rows}
        need = {"movies", "ratings", "movies_by_user", "users_by_movie", "movies_by_title"}
        return need <= names and session.execute("SELECT movie_id FROM movielens.movies LIMIT 1").one() is not None
    except Exception:
        return False

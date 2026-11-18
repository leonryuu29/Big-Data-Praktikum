"""Stufe 3 – Integrationstests: echter Cassandra-Server, eigenes Test-Keyspace.

Das Schema kommt aus den echten CQL-Dateien (movielens -> test_xxxx), die Fixture-Daten
werden über den Python-Treiber eingefügt. Geprüft werden die Abfragefunktionen aus
movielens_cassandra.py (Aufgabe 3 d/e/f) und typische Cassandra-Semantik.
"""
import os
import unittest

from helpers import (FIXTURE_DIR, create_test_keyspace, drop_keyspace, mc, session_or_none,
                     skip_reason)

S = session_or_none()

EXPECTED_USER1 = [  # UTF-8-Byte-Reihenfolge: Ziffern < Großbuchstaben < Kleinbuchstaben < CJK
    "11'09\"01 - September 11 (2002)",
    "2001: A Space Odyssey (1968)",
    "Emma (1996)",
    "Emma (1996)",
    "Matrix, The (1999)",
    "Show Me Love (Fucking Åmål) (1998)",
    "Toy Story (1995)",
    "eXistenZ (1999)",
    "千と千尋の神隠し (2001)",
]


@unittest.skipIf(S is None, skip_reason() if S is None else "")
class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = create_test_keyspace(S)
        movies = mc.read_movies(os.path.join(FIXTURE_DIR, "movies.csv"))
        ratings = mc.read_ratings(os.path.join(FIXTURE_DIR, "ratings.csv"))
        by_user, by_movie, by_title = mc.denormalize(movies, ratings)
        ins = {
            "movies": ("INSERT INTO movies (movie_id, title, genres) VALUES (?, ?, ?)",
                       [(k, t, g) for k, (t, g) in movies.items()]),
            "ratings": ("INSERT INTO ratings (user_id, movie_id, rating, rated_at) VALUES (?, ?, ?, ?)", ratings),
            "movies_by_user": ("INSERT INTO movies_by_user (user_id, title, movie_id, rating, rated_at) "
                               "VALUES (?, ?, ?, ?, ?)", by_user),
            "users_by_movie": ("INSERT INTO users_by_movie (movie_id, user_id, title, rating, rated_at) "
                               "VALUES (?, ?, ?, ?, ?)", by_movie),
            "movies_by_title": ("INSERT INTO movies_by_title (title, movie_id, genres) VALUES (?, ?, ?)", by_title),
        }
        for cql, rows in ins.values():
            ps = S.prepare(cql)
            for r in rows:
                S.execute(ps, r)

    @classmethod
    def tearDownClass(cls):
        drop_keyspace(S, cls.ks)

    def test_i01_schema_from_cql_files(self):
        names = {r.table_name for r in S.execute(
            "SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s", (self.ks,))}
        self.assertEqual(names, {"movies", "ratings", "movies_by_user", "users_by_movie", "movies_by_title"})

    def test_i02_clustering_order_declared(self):
        rows = S.execute("SELECT column_name, kind, clustering_order FROM system_schema.columns "
                         "WHERE keyspace_name = %s AND table_name = 'movies_by_user'", (self.ks,))
        kinds = {r.column_name: (r.kind, r.clustering_order) for r in rows}
        self.assertEqual(kinds["user_id"][0], "partition_key")
        self.assertEqual(kinds["title"], ("clustering", "asc"))
        self.assertEqual(kinds["movie_id"], ("clustering", "asc"))

    def test_i03_static_title(self):
        rows = S.execute("SELECT kind FROM system_schema.columns WHERE keyspace_name = %s "
                         "AND table_name = 'users_by_movie' AND column_name = 'title'", (self.ks,))
        self.assertEqual(rows.one().kind, "static")

    # --- d) ---------------------------------------------------------------
    def test_i04_first_rows_limit(self):
        self.assertEqual(len(mc.first_rows(S, "movies", 10)), 10)
        self.assertEqual(len(mc.first_rows(S, "ratings", 5)), 5)

    def test_i05_first_rows_rejects_unknown_table(self):
        with self.assertRaises(ValueError):
            mc.first_rows(S, "movies; DROP TABLE x", 1)

    # --- e) ---------------------------------------------------------------
    def test_i06_movies_rated_by_alphabetical(self):
        self.assertEqual([r.title for r in mc.movies_rated_by(S, 1)], EXPECTED_USER1)

    def test_i07_duplicate_titles_both_returned(self):
        emma = [r.movie_id for r in mc.movies_rated_by(S, 1) if r.title == "Emma (1996)"]
        self.assertEqual(emma, [4, 5])

    def test_i08_limit_first_five(self):
        self.assertEqual([r.title for r in mc.movies_rated_by(S, 1, limit=5)], EXPECTED_USER1[:5])

    def test_i09_unknown_user_empty(self):
        self.assertEqual(mc.movies_rated_by(S, 424242), [])

    # --- f) ---------------------------------------------------------------
    def test_i10_users_who_rated_sorted(self):
        users = mc.users_who_rated(S, 1)
        self.assertEqual([u.user_id for u in users], [1, 2, 3])
        self.assertEqual({u.title for u in users}, {"Toy Story (1995)"})  # static column

    def test_i11_title_lookup_duplicates(self):
        self.assertEqual(sorted(mc.movie_ids_for_title(S, "Emma (1996)")), [4, 5])
        self.assertEqual(mc.movie_ids_for_title(S, "Gibt es nicht (2099)"), [])

    def test_i12_title_lookup_is_exact(self):
        """Partition Keys vergleichen exakt: falsche Groß-/Kleinschreibung findet nichts."""
        self.assertEqual(mc.movie_ids_for_title(S, "toy story (1995)"), [])

    # --- Cassandra-Semantik -------------------------------------------------
    def test_i13_insert_is_upsert(self):
        """INSERT mit vorhandenem Primärschlüssel überschreibt (kein Fehler, kein Duplikat)."""
        S.execute("INSERT INTO ratings (user_id, movie_id, rating, rated_at) VALUES (2, 1, 1.5, 1)")
        rows = list(S.execute("SELECT rating FROM ratings WHERE user_id = 2 AND movie_id = 1"))
        self.assertEqual([r.rating for r in rows], [1.5])
        S.execute("INSERT INTO ratings (user_id, movie_id, rating, rated_at) VALUES (2, 1, 3.0, 1445714835)")


if __name__ == "__main__":
    unittest.main(verbosity=2)

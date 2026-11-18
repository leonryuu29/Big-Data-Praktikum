"""Stufe 2 – Unit-Tests: reine Python-Logik, ohne Cassandra.

Prüft CSV-Lesen, Denormalisierung (Join) und CSV-Schreiben mit den Sonderfällen aus
tests/fixtures (Komma und doppelte Anführungszeichen im Titel, Unicode, doppelte Titel,
Bewertung zu unbekanntem Film) sowie die Übereinstimmung von Code und CQL-Dateien.
"""
import csv
import os
import tempfile
import unittest

from helpers import CQL_DIR, FIXTURE_DIR, copy_columns, cql_statements, mc


class CsvReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.movies = mc.read_movies(os.path.join(FIXTURE_DIR, "movies.csv"))
        cls.ratings = mc.read_ratings(os.path.join(FIXTURE_DIR, "ratings.csv"))

    def test_u01_counts(self):
        self.assertEqual(len(self.movies), 10)
        self.assertEqual(len(self.ratings), 13)

    def test_u02_types(self):
        u, m, r, t = self.ratings[0]
        self.assertEqual((type(u), type(m), type(r), type(t)), (int, int, float, int))

    def test_u03_title_with_comma(self):
        self.assertEqual(self.movies[2][0], "Matrix, The (1999)")

    def test_u04_title_with_doubled_quotes(self):
        """CSV '""' wird beim Lesen zu einem einzelnen Anführungszeichen."""
        self.assertEqual(self.movies[3][0], "11'09\"01 - September 11 (2002)")

    def test_u05_unicode(self):
        self.assertEqual(self.movies[6][0], "Show Me Love (Fucking Åmål) (1998)")
        self.assertEqual(self.movies[7][0], "千と千尋の神隠し (2001)")

    def test_u06_genres_as_plain_text(self):
        self.assertEqual(self.movies[1][1], "Adventure|Animation|Children|Comedy|Fantasy")
        self.assertEqual(self.movies[10][1], "(no genres listed)")


class DenormalizeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        movies = mc.read_movies(os.path.join(FIXTURE_DIR, "movies.csv"))
        ratings = mc.read_ratings(os.path.join(FIXTURE_DIR, "ratings.csv"))
        cls.by_user, cls.by_movie, cls.by_title = mc.denormalize(movies, ratings)

    def test_u07_orphan_rating_dropped(self):
        """Bewertung von Film 999 (nicht in movies.csv) wird verworfen."""
        self.assertEqual(len(self.by_user), 12)
        self.assertNotIn(999, [r[2] for r in self.by_user])

    def test_u08_join_adds_title(self):
        self.assertIn((1, "Toy Story (1995)", 1, 4.0, 964982703), self.by_user)
        self.assertIn((1, 3, "Toy Story (1995)", 5.0, 1306463578), self.by_movie)

    def test_u09_duplicate_titles_kept_apart(self):
        """Zwei Filme 'Emma (1996)' bleiben zwei Zeilen (movie_id unterscheidet sie)."""
        emma = [r for r in self.by_user if r[0] == 1 and r[1] == "Emma (1996)"]
        self.assertEqual(sorted(r[2] for r in emma), [4, 5])

    def test_u10_by_title_covers_all_movies(self):
        self.assertEqual(len(self.by_title), 10)

    def test_u11_by_user_and_by_movie_same_facts(self):
        a = {(u, m, r, t) for u, _, m, r, t in self.by_user}
        b = {(u, m, r, t) for m, u, _, r, t in self.by_movie}
        self.assertEqual(a, b)


class CsvWriteTests(unittest.TestCase):
    def test_u12_roundtrip_special_titles(self):
        rows = [(1, "Matrix, The (1999)", 2, 5.0, 1), (1, "11'09\"01 - September 11 (2002)", 3, 3.5, 2),
                (1, "千と千尋の神隠し (2001)", 7, 5.0, 3)]
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.csv")
            mc.write_csv(p, mc.HEADERS["movies_by_user"], rows)
            raw = open(p, encoding="utf-8").read()
            self.assertIn('"11\'09""01 - September 11 (2002)"', raw)  # RFC 4180: "" im Feld
            with open(p, encoding="utf-8", newline="") as f:
                back = list(csv.reader(f))
        self.assertEqual(back[0], list(mc.HEADERS["movies_by_user"]))
        self.assertEqual([r[1] for r in back[1:]], [r[1] for r in rows])


class CodeMatchesCqlTests(unittest.TestCase):
    """Die CSV-Spaltenreihenfolge muss exakt zu den COPY-Befehlen passen."""

    def test_u13_headers_match_copy(self):
        cols = copy_columns("aufgabe3_query_import.cql")
        for table, header in mc.HEADERS.items():
            self.assertEqual(cols[table], list(header), table)

    def test_u14_base_copy_matches_csv_order(self):
        cols = copy_columns("aufgabe3_import.cql")
        self.assertEqual(cols["movies"], ["movie_id", "title", "genres"])
        self.assertEqual(cols["ratings"], ["user_id", "movie_id", "rating", "rated_at"])

    def test_u15_every_copy_with_quotes_uses_escape(self):
        """Titel mit "" brauchen ESCAPE = '"' (sonst bleibt ein " am Ende stehen)."""
        for f in ("aufgabe3_import.cql", "aufgabe3_query_import.cql"):
            src = open(os.path.join(CQL_DIR, f), encoding="utf-8").read()
            for block in src.split("COPY ")[1:]:
                if "title" in block.split(")")[0]:
                    self.assertIn("ESCAPE = '\"'", block.split(";")[0], f)

    def test_u16_cql_files_parse(self):
        stmts = cql_statements("aufgabe3_query_tables.cql", keyspace="x")
        self.assertTrue(any("CLUSTERING ORDER BY (title ASC" in s for s in stmts))
        self.assertFalse(any("movielens" in s for s in stmts))


if __name__ == "__main__":
    unittest.main(verbosity=2)

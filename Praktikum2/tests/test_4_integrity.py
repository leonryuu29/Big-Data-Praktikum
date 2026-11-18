"""Stufe 5 – Datenintegrität: echte Daten (ml-latest-small) im Keyspace movielens.

Vergleicht jede Tabelle Feld für Feld mit den CSV-Dateien, prüft referenzielle
Integrität und die Konsistenz der denormalisierten Kopien und bestätigt die Antworten
aus der Abgabe gegen eine unabhängige Berechnung in Python.
Wird übersprungen, wenn die CSV-Dateien oder der importierte Keyspace fehlen (z. B. in CI).
"""
import os
import unittest

from helpers import DATA_DIR, mc, real_data_imported, session_or_none

S = session_or_none()
HAVE_CSV = os.path.isfile(os.path.join(DATA_DIR, "movies.csv"))
READY = S is not None and HAVE_CSV and real_data_imported(S)


@unittest.skipUnless(READY, "echte Daten oder Import fehlen")
class IntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.movies = mc.read_movies(os.path.join(DATA_DIR, "movies.csv"))
        cls.ratings = mc.read_ratings(os.path.join(DATA_DIR, "ratings.csv"))
        cls.by_user, cls.by_movie, cls.by_title = mc.denormalize(cls.movies, cls.ratings)
        S.set_keyspace("movielens")

    # --- Vollständigkeit ------------------------------------------------------
    def test_g01_dataset_matches_readme(self):
        """README von ml-latest-small: 100836 Bewertungen, 9742 Filme, 610 Nutzys."""
        self.assertEqual(len(self.movies), 9742)
        self.assertEqual(len(self.ratings), 100836)
        self.assertEqual(len({r[0] for r in self.ratings}), 610)

    def test_g02_row_counts(self):
        for table, n in (("movies", 9742), ("ratings", 100836), ("movies_by_user", 100836),
                         ("users_by_movie", 100836), ("movies_by_title", 9742)):
            self.assertEqual(mc.count(S, f"SELECT COUNT(*) FROM {table}"), n, table)

    # --- Feldgenauigkeit ------------------------------------------------------
    def test_g03_movies_field_by_field(self):
        db = {r.movie_id: (r.title, r.genres) for r in S.execute("SELECT movie_id, title, genres FROM movies")}
        self.assertEqual(db, self.movies)

    def test_g04_ratings_field_by_field(self):
        db = {(r.user_id, r.movie_id, r.rating, r.rated_at) for r in S.execute("SELECT * FROM ratings")}
        self.assertEqual(db, set(self.ratings))

    def test_g05_movies_by_user_equals_join(self):
        db = {(r.user_id, r.title, r.movie_id, r.rating, r.rated_at) for r in S.execute(
            "SELECT user_id, title, movie_id, rating, rated_at FROM movies_by_user")}
        self.assertEqual(db, set(self.by_user))

    def test_g06_users_by_movie_equals_join(self):
        db = {(r.movie_id, r.user_id, r.title, r.rating, r.rated_at) for r in S.execute(
            "SELECT movie_id, user_id, title, rating, rated_at FROM users_by_movie")}
        self.assertEqual(db, set(self.by_movie))

    def test_g07_movies_by_title_equals_movies(self):
        db = {(r.title, r.movie_id, r.genres) for r in S.execute("SELECT * FROM movies_by_title")}
        self.assertEqual(db, set(self.by_title))

    def test_g08_special_titles_intact(self):
        """Titel mit "" (ESCAPE-Fall), Komma und Unicode kommen unverändert an."""
        for mid in (7789, 2571, 7034):
            title = S.execute("SELECT title FROM movies WHERE movie_id = %s", (mid,)).one().title
            self.assertEqual(title, self.movies[mid][0])

    # --- Referenzielle Integrität / Wertebereiche ----------------------------------
    def test_g09_every_rating_references_a_movie(self):
        self.assertTrue({r[1] for r in self.ratings} <= set(self.movies))

    def test_g10_rating_range(self):
        values = {r.rating for r in S.execute("SELECT rating FROM ratings")}
        self.assertEqual(values, {x / 2 for x in range(1, 11)})  # 0.5 … 5.0 in 0.5-Schritten

    def test_g11_no_lost_rows_through_duplicate_titles(self):
        """5 doppelte Titel: dank movie_id im Primärschlüssel geht keine Bewertung verloren."""
        dups = {t for t in (v[0] for v in self.movies.values())
                if sum(1 for w in self.movies.values() if w[0] == t) > 1}
        self.assertEqual(len(dups), 5)
        for t in dups:
            self.assertEqual(len(S.execute("SELECT movie_id FROM movies_by_title WHERE title = %s", (t,)).all()), 2)

    # --- Antworten der Abgabe gegen unabhängige Berechnung --------------------------
    def test_g12_answer_e_user_42(self):
        oracle = sorted((self.movies[m][0], m) for u, m, _, _ in self.ratings if u == 42)
        got = [(r.title, r.movie_id) for r in mc.movies_rated_by(S, 42)]
        self.assertEqual(got, oracle)
        self.assertEqual([t for t, _ in got[:5]], [
            "20 Dates (1998)", "2001: A Space Odyssey (1968)", "2010: The Year We Make Contact (1984)",
            "28 Days (2000)", "8 Seconds (1994)"])
        self.assertEqual(len(got), 440)

    def test_g13_answer_f_toy_story(self):
        self.assertEqual(mc.movie_ids_for_title(S, "Toy Story (1995)"), [1])
        users = [u.user_id for u in mc.users_who_rated(S, 1)]
        self.assertEqual(users, sorted(u for u, m, _, _ in self.ratings if m == 1))
        self.assertEqual(len(users), 215)


if __name__ == "__main__":
    unittest.main(verbosity=2)

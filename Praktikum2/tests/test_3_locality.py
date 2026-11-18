"""Stufe 4 – Lokalitätstests (Partition-Zugriff): "effizient" messbar machen.

Aufgabe 3 e) verlangt eine *effiziente* Abfrage. In Cassandra heißt das: genau eine
Partition lesen, kein Scan über den Cluster. Das wird hier mit Query-Tracing nachgewiesen
(Cassandra protokolliert dann "Executing single-partition query on <tabelle>").
Gegenprobe: dieselbe Frage auf der Basistabelle wird ohne ALLOW FILTERING abgelehnt,
mit ALLOW FILTERING liest Cassandra einen Bereich (range scan) statt einer Partition.
"""
import unittest

from cassandra import InvalidRequest

from helpers import real_data_imported, session_or_none, skip_reason

S = session_or_none()
READY = S is not None and real_data_imported(S)


def trace_events(cql, params=()):
    rs = S.execute(cql, params, trace=True)
    list(rs)
    trace = rs.get_query_trace(max_wait_sec=10)
    return [e.description for e in trace.events]


@unittest.skipUnless(READY, "movielens nicht importiert" if S is not None else skip_reason())
class LocalityTests(unittest.TestCase):
    def assertSinglePartition(self, table, events):
        self.assertTrue(any(f"single-partition query on {table}" in e for e in events),
                        f"kein single-partition read auf {table}: {events[:8]}")
        self.assertFalse(any("range" in e.lower() and "scan" in e.lower() for e in events), events[:8])

    def test_l01_q1_movies_by_user_single_partition(self):
        ev = trace_events("SELECT title FROM movielens.movies_by_user WHERE user_id = %s LIMIT 5", (42,))
        self.assertSinglePartition("movies_by_user", ev)

    def test_l02_q2_users_by_movie_single_partition(self):
        ev = trace_events("SELECT user_id FROM movielens.users_by_movie WHERE movie_id = %s", (1,))
        self.assertSinglePartition("users_by_movie", ev)

    def test_l03_title_lookup_single_partition(self):
        ev = trace_events("SELECT movie_id FROM movielens.movies_by_title WHERE title = %s", ("Toy Story (1995)",))
        self.assertSinglePartition("movies_by_title", ev)

    def test_l04_base_table_by_movie_rejected(self):
        with self.assertRaises(InvalidRequest) as cm:
            S.execute("SELECT user_id FROM movielens.ratings WHERE movie_id = 1")
        self.assertIn("ALLOW FILTERING", str(cm.exception))

    def test_l05_allow_filtering_is_a_scan(self):
        ev = trace_events("SELECT user_id FROM movielens.ratings WHERE movie_id = 1 ALLOW FILTERING")
        self.assertFalse(any("single-partition" in e for e in ev), ev[:8])
        self.assertTrue(any("range" in e.lower() for e in ev), ev[:8])

    def test_l06_order_by_other_column_rejected(self):
        """Sortierung ist nur nach Clustering Columns möglich – deshalb title als Clustering Column."""
        with self.assertRaises(InvalidRequest):
            S.execute("SELECT * FROM movielens.ratings WHERE user_id = 42 ORDER BY rating")

    def test_l07_partition_size_reasonable(self):
        """Größte Partition von movies_by_user (Nutzy mit den meisten Bewertungen) bleibt klein."""
        biggest = max(S.execute("SELECT user_id, COUNT(*) AS n FROM movielens.movies_by_user "
                                "GROUP BY user_id"), key=lambda r: r.n)
        cells = biggest.n * (5 - 3)  # Nv = Nr * (Nc - Npk - Ns) + Ns, Nc=5, Npk=3, Ns=0
        self.assertLess(cells, 100_000, f"Nutzy {biggest.user_id}: {biggest.n} Zeilen")


if __name__ == "__main__":
    unittest.main(verbosity=2)

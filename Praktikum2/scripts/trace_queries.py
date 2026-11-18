"""Belegt die Effizienz der Abfragen mit Cassandra-Query-Tracing (Aufgabe 3 e/f).

Aufruf:  python scripts/trace_queries.py > results/tracing.txt
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import movielens_cassandra as mc  # noqa: E402

QUERIES = [
    ("e) Filme von Nutzy 42 (Abfragetabelle)", "SELECT title FROM movies_by_user WHERE user_id = 42 LIMIT 5"),
    ("f) Nutzys von Film 1 (Abfragetabelle)", "SELECT user_id FROM users_by_movie WHERE movie_id = 1"),
    ("f) Titel -> movie_id", "SELECT movie_id FROM movies_by_title WHERE title = 'Toy Story (1995)'"),
    ("Gegenprobe: Nutzys von Film 1 auf der Basistabelle (ALLOW FILTERING)",
     "SELECT user_id FROM ratings WHERE movie_id = 1 ALLOW FILTERING"),
]


def main():
    s = mc.connect()
    for label, cql in QUERIES:
        rs = s.execute(cql, trace=True)
        rows = list(rs)
        tr = rs.get_query_trace(max_wait_sec=10)
        print(f"### {label}\n{cql}\n-> {len(rows)} Zeilen, Dauer laut Trace {tr.duration.total_seconds() * 1000:.1f} ms")
        for e in tr.events:
            print(f"   {e.source_elapsed.total_seconds() * 1000 if e.source_elapsed else 0:8.2f} ms  {e.description}")
        print()


if __name__ == "__main__":
    main()

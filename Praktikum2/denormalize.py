"""
Big Data – 2. Praktikum, Aufgabe 3 e) + f): Denormalisierung
Autor: Zhaoze Yu · Matrikelnr. 50293014

Erzeugt aus movies.csv und ratings.csv die CSV-Dateien für die abfragegetriebenen Tabellen
movies_by_user, users_by_movie und movies_by_title. Diese werden anschließend mit
cql/aufgabe3_query_import.cql per COPY importiert.

Warum ein eigener Schritt? Cassandra kennt weder Joins noch INSERT ... SELECT, und
Materialized Views sind in Cassandra 5 standardmäßig deaktiviert. Der Join passiert
deshalb einmal beim Laden statt bei jeder Abfrage.

Aufruf:
  python denormalize.py data/ml-latest-small out/denormalized
  docker cp out/denormalized CassandraPraktikum2026:/home/cassandra/
  docker exec CassandraPraktikum2026 cqlsh -f /home/cassandra/cql/aufgabe3_query_import.cql
"""
import os
import sys
import time

import movielens_cassandra as mc


def main(src="data/ml-latest-small", out="out/denormalized"):
    t0 = time.time()
    # 1) Quelldaten lesen (movies als Dictionary für den Join über movie_id)
    movies = mc.read_movies(os.path.join(src, "movies.csv"))
    ratings = mc.read_ratings(os.path.join(src, "ratings.csv"))
    # 2) Join: jede Bewertung bekommt ihren Titel, einmal je Zugriffsmuster
    tables = dict(zip(("movies_by_user", "users_by_movie", "movies_by_title"),
                      mc.denormalize(movies, ratings)))
    # 3) eine CSV pro Tabelle, Kopfzeile = Spaltenliste des COPY-Befehls
    os.makedirs(out, exist_ok=True)
    for name, rows in tables.items():
        mc.write_csv(os.path.join(out, name + ".csv"), mc.HEADERS[name], rows)
        print(f"{name + '.csv':<22} {len(rows):>7} Zeilen")
    print(f"Quelle: {len(movies)} Filme, {len(ratings)} Bewertungen; Dauer {time.time() - t0:.2f} s")


if __name__ == "__main__":
    main(*sys.argv[1:])

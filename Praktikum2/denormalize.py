"""
Aufgabe 3 e) + f): Erzeugt aus movies.csv und ratings.csv die CSV-Dateien für die
abfragegetriebenen Tabellen. Cassandra kennt keine Joins und kein INSERT ... SELECT,
daher geschieht der Join einmalig beim Laden (Denormalisierung).

Aufruf:
  python denormalize.py data/ml-latest-small out/denormalized
"""
import os
import sys
import time

import movielens_cassandra as mc


def main(src="data/ml-latest-small", out="out/denormalized"):
    t0 = time.time()
    movies = mc.read_movies(os.path.join(src, "movies.csv"))
    ratings = mc.read_ratings(os.path.join(src, "ratings.csv"))
    tables = dict(zip(("movies_by_user", "users_by_movie", "movies_by_title"),
                      mc.denormalize(movies, ratings)))
    os.makedirs(out, exist_ok=True)
    for name, rows in tables.items():
        mc.write_csv(os.path.join(out, name + ".csv"), mc.HEADERS[name], rows)
        print(f"{name + '.csv':<22} {len(rows):>7} Zeilen")
    print(f"Quelle: {len(movies)} Filme, {len(ratings)} Bewertungen; Dauer {time.time() - t0:.2f} s")


if __name__ == "__main__":
    main(*sys.argv[1:])

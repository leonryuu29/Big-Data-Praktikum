"""
Big Data – 2. Praktikum (HSBI, WS 2026/27): Cassandra + MovieLens (ml-latest-small)
Gemeinsame Funktionen für Aufgabe 3.

Datenmodell im Keyspace movielens
---------------------------------
movies           PK (movie_id)                       Basistabelle aus movies.csv   (c)
ratings          PK ((user_id), movie_id)            Basistabelle aus ratings.csv  (c)
movies_by_user   PK ((user_id), title, movie_id)     Q1: Filme eines Nutzys, alphabetisch (e)
users_by_movie   PK ((movie_id), user_id), title STATIC  Q2: Nutzys eines Films        (f)
movies_by_title  PK ((title), movie_id)              Hilfstabelle Titel -> movie_id (f)
"""
import csv
import os
import sys

KEYSPACE = "movielens"


# ---------------------------------------------------------------------------
# Verbindung
# ---------------------------------------------------------------------------
def connect(hosts=None, port=None, keyspace=KEYSPACE):
    """Verbindung zum Cassandra-Container (Port 9042).

    Host/Port lassen sich über CASSANDRA_HOST / CASSANDRA_PORT überschreiben.
    Ab Python 3.12 fehlt das Modul asyncore, das der Standard-Eventloop des
    cassandra-driver braucht. Das Paket pyasyncore (siehe requirements.txt) stellt
    es wieder bereit – genau so macht es auch das cqlsh im offiziellen Image.
    """
    from cassandra.cluster import Cluster  # Import hier, damit reine CSV-Funktionen ohne Treiber laufen

    hosts = hosts or os.environ.get("CASSANDRA_HOST", "127.0.0.1").split(",")
    port = int(port or os.environ.get("CASSANDRA_PORT", "9042"))
    cluster = Cluster(hosts, port=port, protocol_version=5)
    session = cluster.connect(keyspace) if keyspace else cluster.connect()
    return session


# ---------------------------------------------------------------------------
# CSV (Aufgabe 3 b + Denormalisierung)
# ---------------------------------------------------------------------------
def read_movies(path):
    """movies.csv -> {movie_id: (title, genres)}"""
    with open(path, encoding="utf-8", newline="") as f:
        return {int(r["movieId"]): (r["title"], r["genres"]) for r in csv.DictReader(f)}


def read_ratings(path):
    """ratings.csv -> Liste von (user_id, movie_id, rating, rated_at)"""
    with open(path, encoding="utf-8", newline="") as f:
        return [(int(r["userId"]), int(r["movieId"]), float(r["rating"]), int(r["timestamp"]))
                for r in csv.DictReader(f)]


def denormalize(movies, ratings):
    """Join von ratings und movies in die Zeilen der drei Abfragetabellen.

    Gibt (movies_by_user, users_by_movie, movies_by_title) als Listen von Tupeln zurück,
    in der Spaltenreihenfolge der COPY-Befehle in cql/aufgabe3_query_import.cql.
    Bewertungen zu unbekannten Filmen werden verworfen (kommt im Datensatz nicht vor).
    """
    by_user, by_movie = [], []
    for user_id, movie_id, rating, rated_at in ratings:
        if movie_id not in movies:
            continue
        title = movies[movie_id][0]
        by_user.append((user_id, title, movie_id, rating, rated_at))
        by_movie.append((movie_id, user_id, title, rating, rated_at))
    by_title = [(title, movie_id, genres) for movie_id, (title, genres) in movies.items()]
    return by_user, by_movie, by_title


HEADERS = {
    "movies_by_user": ("user_id", "title", "movie_id", "rating", "rated_at"),
    "users_by_movie": ("movie_id", "user_id", "title", "rating", "rated_at"),
    "movies_by_title": ("title", "movie_id", "genres"),
}


def write_csv(path, header, rows):
    """RFC-4180-CSV schreiben (Anführungszeichen werden verdoppelt -> COPY ... ESCAPE = '"')."""
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


# ---------------------------------------------------------------------------
# Abfragen (Aufgabe 3 d, e, f)
# ---------------------------------------------------------------------------
def first_rows(session, table, n=10):
    """d) die ersten n Zeilen einer Tabelle (Reihenfolge = Token-Reihenfolge der Partitionen)."""
    if table not in ("movies", "ratings", "movies_by_user", "users_by_movie", "movies_by_title"):
        raise ValueError(f"unbekannte Tabelle: {table}")
    return list(session.execute(f"SELECT * FROM {table} LIMIT %s", (n,)))


def movies_rated_by(session, user_id, limit=None):
    """e) Titel, die ein Nutzy bewertet hat – alphabetisch, aus genau einer Partition."""
    cql = "SELECT title, movie_id, rating FROM movies_by_user WHERE user_id = %s"
    params = [user_id]
    if limit:
        cql += " LIMIT %s"
        params.append(limit)
    return list(session.execute(cql, params))


def movie_ids_for_title(session, title):
    """Titel -> Liste von movie_ids (ein Titel kann mehrere Filme bezeichnen)."""
    return [r.movie_id for r in session.execute(
        "SELECT movie_id FROM movies_by_title WHERE title = %s", (title,))]


def users_who_rated(session, movie_id, limit=None):
    """f) Nutzys, die einen Film bewertet haben – aus genau einer Partition, nach user_id sortiert."""
    cql = "SELECT user_id, title, rating FROM users_by_movie WHERE movie_id = %s"
    params = [movie_id]
    if limit:
        cql += " LIMIT %s"
        params.append(limit)
    return list(session.execute(cql, params))


def count(session, cql, params=()):
    return session.execute(cql, params).one()[0]


if __name__ == "__main__":  # kleiner Verbindungstest
    s = connect(keyspace=None)
    print(s.execute("SELECT release_version FROM system.local").one().release_version, file=sys.stdout)

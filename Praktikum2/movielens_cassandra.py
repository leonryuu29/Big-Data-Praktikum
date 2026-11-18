"""
Big Data – 2. Praktikum (HSBI, WS 2026/27): Cassandra + MovieLens (ml-latest-small)
Autor: Zhaoze Yu · Matrikelnr. 50293014

Gemeinsame Funktionen für Aufgabe 3 (werden von denormalize.py, answers.py und den Tests genutzt).

Datenmodell im Keyspace movielens (Schema: cql/aufgabe3_schema.cql, cql/aufgabe3_query_tables.cql)
-------------------------------------------------------------------------------------------------
Tabelle          Primärschlüssel                        Zweck                                Aufgabe
movies           (movie_id)                             Basistabelle aus movies.csv          3 c
ratings          ((user_id), movie_id)                  Basistabelle aus ratings.csv         3 c
movies_by_user   ((user_id), title, movie_id)           Q1: Filme eines Nutzys, alphabetisch 3 e
users_by_movie   ((movie_id), user_id), title STATIC    Q2: Nutzys eines Films               3 f
movies_by_title  ((title), movie_id)                    Hilfstabelle Titel -> movie_id       3 f

Notation: ((x), y) = Partition Key x, Clustering Column y.
Cassandra kennt keine Joins. Die Tabellen für 3 e/f werden deshalb beim Laden einmalig
aus den beiden CSV-Dateien zusammengesetzt (Denormalisierung, siehe denormalize()).
"""
import csv
import os
import sys

KEYSPACE = "movielens"


# ---------------------------------------------------------------------------
# Verbindung
# ---------------------------------------------------------------------------
def connect(hosts=None, port=None, keyspace=KEYSPACE):
    """Baut eine Session zum Cassandra-Container auf (Standard: 127.0.0.1:9042).

    - Host und Port lassen sich über die Umgebungsvariablen CASSANDRA_HOST und
      CASSANDRA_PORT überschreiben (mehrere Hosts durch Komma getrennt).
    - protocol_version=5 ist das Native Protocol von Cassandra 4.x/5.x. Damit entfällt
      das automatische Aushandeln und die Warnung beim Verbinden.
    - Ab Python 3.12 fehlt das Modul asyncore, das der Standard-Eventloop des
      cassandra-driver braucht. Das Paket pyasyncore (requirements.txt) stellt es
      wieder bereit; genauso macht es das cqlsh im offiziellen Docker-Image.
    - keyspace=None verbindet ohne Keyspace (z. B. für Tests mit eigenem Keyspace).
    """
    # Import erst hier: so laufen die reinen CSV-Funktionen (und die Unit-Tests)
    # auch auf einem Rechner ohne installierten Treiber.
    from cassandra.cluster import Cluster

    hosts = hosts or os.environ.get("CASSANDRA_HOST", "127.0.0.1").split(",")
    port = int(port or os.environ.get("CASSANDRA_PORT", "9042"))
    cluster = Cluster(hosts, port=port, protocol_version=5)
    session = cluster.connect(keyspace) if keyspace else cluster.connect()
    return session


# ---------------------------------------------------------------------------
# CSV lesen (Aufgabe 3 b) und denormalisieren (Vorbereitung für 3 e/f)
# ---------------------------------------------------------------------------
def read_movies(path):
    """movies.csv einlesen -> {movie_id: (title, genres)}.

    Das csv-Modul behandelt die Sonderfälle der Datei korrekt: Titel mit Komma stehen
    in Anführungszeichen ("Matrix, The (1999)"), ein Anführungszeichen im Titel ist
    als "" kodiert. encoding="utf-8" ist unter Windows Pflicht (sonst cp1252), denn
    293 Titel enthalten Nicht-ASCII-Zeichen. Genres bleiben laut Hinweis einfacher Text.
    """
    with open(path, encoding="utf-8", newline="") as f:
        return {int(r["movieId"]): (r["title"], r["genres"]) for r in csv.DictReader(f)}


def read_ratings(path):
    """ratings.csv einlesen -> Liste von (user_id, movie_id, rating, rated_at).

    rated_at bleibt eine Ganzzahl in Sekunden seit 1970 (UTC). Der CQL-Typ timestamp
    würde Millisekunden erwarten, deshalb ist die Spalte im Schema ein bigint.
    """
    with open(path, encoding="utf-8", newline="") as f:
        return [(int(r["userId"]), int(r["movieId"]), float(r["rating"]), int(r["timestamp"]))
                for r in csv.DictReader(f)]


def denormalize(movies, ratings):
    """Join von ratings und movies zu den Zeilen der drei Abfragetabellen.

    Rückgabe: (movies_by_user, users_by_movie, movies_by_title) als Listen von Tupeln,
    jeweils in der Spaltenreihenfolge der COPY-Befehle in cql/aufgabe3_query_import.cql
    (geprüft durch die Unit-Tests u13/u14).

    Jede Bewertung erscheint danach in zwei Tabellen: einmal unter dem Nutzy (3 e) und
    einmal unter dem Film (3 f). Diese Duplizierung ist in Cassandra gewollt
    ("eine Tabelle pro Abfrage").
    """
    by_user, by_movie = [], []
    for user_id, movie_id, rating, rated_at in ratings:
        if movie_id not in movies:      # Bewertung zu unbekanntem Film: verwerfen
            continue                    # (kommt im Datensatz nicht vor, siehe test_g09)
        title = movies[movie_id][0]     # der eigentliche "Join": movie_id -> Titel
        by_user.append((user_id, title, movie_id, rating, rated_at))
        by_movie.append((movie_id, user_id, title, rating, rated_at))
    # Hilfstabelle für 3 f: Titel -> movie_id. Ein Titel kann mehrere Filme bezeichnen
    # (5 doppelte Titel im Datensatz), deshalb ist movie_id dort Clustering Column.
    by_title = [(title, movie_id, genres) for movie_id, (title, genres) in movies.items()]
    return by_user, by_movie, by_title


# Kopfzeilen der erzeugten CSV-Dateien = Spaltenlisten der COPY-Befehle
HEADERS = {
    "movies_by_user": ("user_id", "title", "movie_id", "rating", "rated_at"),
    "users_by_movie": ("movie_id", "user_id", "title", "rating", "rated_at"),
    "movies_by_title": ("title", "movie_id", "genres"),
}


def write_csv(path, header, rows):
    """CSV nach RFC 4180 schreiben.

    Ein Anführungszeichen im Feld wird als "" geschrieben. Beim Import muss cqlsh deshalb
    mit ESCAPE = '"' arbeiten; das Standard-Escape-Zeichen ist der Backslash, und der
    Titel 11'09"01 käme sonst mit einem zusätzlichen " am Ende an.
    """
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


# ---------------------------------------------------------------------------
# Abfragen (Aufgabe 3 d, e, f)
# Alle Abfragen nutzen Parameter (%s) statt String-Verkettung. Die e/f-Abfragen
# schränken immer den vollständigen Partition Key ein, lesen also genau eine
# Partition (nachgewiesen mit Query-Tracing in tests/test_3_locality.py).
# ---------------------------------------------------------------------------
def first_rows(session, table, n=10):
    """3 d) die ersten n Zeilen einer Tabelle.

    "Erste" heißt in Cassandra: erste Partitionen in Token-Reihenfolge (Murmur3-Hash des
    Partition Keys), nicht die ersten Zeilen der CSV. Tabellennamen lassen sich nicht als
    Parameter übergeben, deshalb wird gegen eine feste Liste geprüft (Schutz vor Injection).
    """
    if table not in ("movies", "ratings", "movies_by_user", "users_by_movie", "movies_by_title"):
        raise ValueError(f"unbekannte Tabelle: {table}")
    return list(session.execute(f"SELECT * FROM {table} LIMIT %s", (n,)))


def movies_rated_by(session, user_id, limit=None):
    """3 e) Titel, die ein Nutzy bewertet hat, alphabetisch sortiert.

    WHERE user_id = ?  -> genau eine Partition von movies_by_user
    Sortierung         -> Cassandra liefert die Zeilen in Clustering-Reihenfolge
                          (title ASC, movie_id ASC); ein ORDER BY ist nicht nötig.
    LIMIT 5            -> liefert direkt die ersten 5 Titel (Antwort auf 3 e für Nutzy 42).
    """
    cql = "SELECT title, movie_id, rating FROM movies_by_user WHERE user_id = %s"
    params = [user_id]
    if limit:
        cql += " LIMIT %s"
        params.append(limit)
    return list(session.execute(cql, params))


def movie_ids_for_title(session, title):
    """3 f, Schritt 1) Titel -> Liste von movie_ids (z. B. 'Emma (1996)' -> [838, 26958]).

    Der Titel ist Partition Key; der Vergleich ist exakt (Groß- und Kleinschreibung zählt).
    """
    return [r.movie_id for r in session.execute(
        "SELECT movie_id FROM movies_by_title WHERE title = %s", (title,))]


def users_who_rated(session, movie_id, limit=None):
    """3 f, Schritt 2) Nutzys, die einen Film bewertet haben, nach user_id sortiert.

    Eine Partition von users_by_movie. Die statische Spalte title wird pro Partition nur
    einmal gespeichert, erscheint in der Ausgabe aber in jeder Zeile.
    """
    cql = "SELECT user_id, title, rating FROM users_by_movie WHERE movie_id = %s"
    params = [movie_id]
    if limit:
        cql += " LIMIT %s"
        params.append(limit)
    return list(session.execute(cql, params))


def count(session, cql, params=()):
    """Hilfsfunktion: erste Spalte der ersten Ergebniszeile (für SELECT COUNT(*) ...)."""
    return session.execute(cql, params).one()[0]


if __name__ == "__main__":  # Verbindungstest: python movielens_cassandra.py
    s = connect(keyspace=None)
    print(s.execute("SELECT release_version FROM system.local").one().release_version, file=sys.stdout)

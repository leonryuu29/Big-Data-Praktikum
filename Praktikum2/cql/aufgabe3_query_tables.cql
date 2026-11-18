-- Aufgabe 3 e) + f): abfragegetriebene Tabellen (query-first, denormalisiert)
-- Befüllung: python denormalize.py erzeugt die CSV-Dateien, danach aufgabe3_query_import.cql
USE movielens;

-- e) Q1: "Welche Filme hat ein Nutzy bewertet?" – Titel effizient und alphabetisch sortiert
--    Partition Key  user_id         -> genau EINE Partition pro Anfrage (kein Scan, kein ALLOW FILTERING)
--    Clustering     title ASC       -> Cassandra speichert die Zeilen bereits sortiert auf der Platte
--    Clustering     movie_id        -> macht die Zeile eindeutig: 5 Titel kommen im Datensatz doppelt vor
--                                      (z. B. zwei verschiedene Filme "Emma (1996)"); ohne movie_id würde
--                                      die zweite Bewertung die erste überschreiben (Upsert).
CREATE TABLE IF NOT EXISTS movies_by_user (
  user_id  int,
  title    text,
  movie_id int,
  rating   float,
  rated_at bigint,
  PRIMARY KEY ((user_id), title, movie_id)
) WITH CLUSTERING ORDER BY (title ASC, movie_id ASC);

-- f) Q2: "Welches Nutzy hat einen Film bewertet?"
--    Partition Key  movie_id        -> alle Bewertungen eines Films in einer Partition
--    Clustering     user_id ASC     -> Nutzys aufsteigend sortiert
--    title STATIC                   -> der Titel wird pro Partition nur einmal gespeichert
CREATE TABLE IF NOT EXISTS users_by_movie (
  movie_id int,
  user_id  int,
  title    text STATIC,
  rating   float,
  rated_at bigint,
  PRIMARY KEY ((movie_id), user_id)
) WITH CLUSTERING ORDER BY (user_id ASC);

-- Hilfstabelle für f): Nutzer kennen Titel, nicht movie_id.
--    Titel -> movie_id (ein Titel kann zu mehreren Filmen gehören, daher movie_id als Clustering Column)
CREATE TABLE IF NOT EXISTS movies_by_title (
  title    text,
  movie_id int,
  genres   text,
  PRIMARY KEY ((title), movie_id)
);

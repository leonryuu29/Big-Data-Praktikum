-- =============================================================================
-- Big Data – 2. Praktikum (HSBI, WS 2026/27) · Zhaoze Yu · Matrikelnr. 50293014
-- Aufgabe 3 e) + f): Abfragen und Gegenprobe
-- Ausführen: docker exec -it CassandraPraktikum2026 cqlsh -f /home/cassandra/cql/aufgabe3_queries.cql
-- Reihenfolge: aufgabe1_person -> aufgabe3_schema -> aufgabe3_import -> aufgabe3_check -> (python denormalize.py) -> aufgabe3_query_tables -> aufgabe3_query_import -> aufgabe3_queries
-- =============================================================================
USE movielens;

-- e) Die ersten 5 Filme (alphabetisch), die Nutzy 42 bewertet hat
SELECT title, rating FROM movies_by_user WHERE user_id = 42 LIMIT 5;

-- e) Wie viele Filme hat Nutzy 42 insgesamt bewertet?
SELECT COUNT(*) FROM movies_by_user WHERE user_id = 42;

-- f) Welche Nutzys haben "Toy Story (1995)" bewertet?
--    Schritt 1: Titel -> movie_id
SELECT movie_id, title FROM movies_by_title WHERE title = 'Toy Story (1995)';
--    Schritt 2: alle Nutzys dieses Films (hier die ersten 10) und ihre Anzahl
SELECT user_id, rating FROM users_by_movie WHERE movie_id = 1 LIMIT 10;
SELECT COUNT(*) FROM users_by_movie WHERE movie_id = 1;

-- Doppelte Titel: ein Titel, zwei Filme -> zwei Zeilen in derselben Partition
SELECT * FROM movies_by_title WHERE title = 'Emma (1996)';

-- Gegenprobe: dieselbe Frage auf der Basistabelle ratings ist nicht effizient möglich
-- (movie_id ist dort nur Clustering Column) und wird ohne ALLOW FILTERING abgelehnt:
SELECT user_id FROM ratings WHERE movie_id = 1;

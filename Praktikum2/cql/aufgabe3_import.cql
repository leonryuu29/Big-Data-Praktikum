-- =============================================================================
-- Big Data – 2. Praktikum (HSBI, WS 2026/27) · Zhaoze Yu · Matrikelnr. 50293014
-- Aufgabe 3 c): Import von movies.csv und ratings.csv mit COPY
-- Ausführen: docker exec -it CassandraPraktikum2026 cqlsh -f /home/cassandra/cql/aufgabe3_import.cql
-- Reihenfolge: aufgabe1_person -> aufgabe3_schema -> aufgabe3_import -> aufgabe3_check -> (python denormalize.py) -> aufgabe3_query_tables -> aufgabe3_query_import -> aufgabe3_queries
-- =============================================================================
-- COPY ist ein cqlsh-Befehl (kein CQL) und liest die CSV-Dateien im Container.
-- HEADER = true überspringt die Kopfzeile; die Spaltenliste ordnet die CSV-Spalten zu.
-- ESCAPE = '"' für movies.csv: Anführungszeichen im Titel sind als "" kodiert
-- (Titel 11'09"01 - September 11 (2002)); ohne die Option bliebe ein " am Titelende stehen.
USE movielens;

COPY movies (movie_id, title, genres)
  FROM '/home/cassandra/ml-latest-small/movies.csv'
  WITH HEADER = true AND ESCAPE = '"';

COPY ratings (user_id, movie_id, rating, rated_at)
  FROM '/home/cassandra/ml-latest-small/ratings.csv'
  WITH HEADER = true;

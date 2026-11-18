-- =============================================================================
-- Big Data – 2. Praktikum (HSBI, WS 2026/27) · Zhaoze Yu · Matrikelnr. 50293014
-- Aufgabe 3 e) + f): Import der denormalisierten CSV-Dateien
-- Ausführen: docker exec -it CassandraPraktikum2026 cqlsh -f /home/cassandra/cql/aufgabe3_query_import.cql
-- Reihenfolge: aufgabe1_person -> aufgabe3_schema -> aufgabe3_import -> aufgabe3_check -> (python denormalize.py) -> aufgabe3_query_tables -> aufgabe3_query_import -> aufgabe3_queries
-- =============================================================================
-- COPY ist ein cqlsh-Befehl (kein CQL). ESCAPE = '"' ist nötig, weil die CSV-Dateien
-- Anführungszeichen im Titel als "" kodieren (RFC 4180); Standard-Escape von COPY ist \.
USE movielens;

COPY movies_by_user (user_id, title, movie_id, rating, rated_at)
  FROM '/home/cassandra/denormalized/movies_by_user.csv'
  WITH HEADER = true AND ESCAPE = '"';

COPY users_by_movie (movie_id, user_id, title, rating, rated_at)
  FROM '/home/cassandra/denormalized/users_by_movie.csv'
  WITH HEADER = true AND ESCAPE = '"';

COPY movies_by_title (title, movie_id, genres)
  FROM '/home/cassandra/denormalized/movies_by_title.csv'
  WITH HEADER = true AND ESCAPE = '"';

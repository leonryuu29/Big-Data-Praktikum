-- =============================================================================
-- Big Data – 2. Praktikum (HSBI, WS 2026/27) · Zhaoze Yu · Matrikelnr. 50293014
-- Aufgabe 3 d): Kontrolle des Imports (jeweils die ersten 10 Zeilen)
-- Ausführen: docker exec -it CassandraPraktikum2026 cqlsh -f /home/cassandra/cql/aufgabe3_check.cql
-- Reihenfolge: aufgabe1_person -> aufgabe3_schema -> aufgabe3_import -> aufgabe3_check -> (python denormalize.py) -> aufgabe3_query_tables -> aufgabe3_query_import -> aufgabe3_queries
-- =============================================================================
USE movielens;

-- Hinweis: "die ersten 10" sind die ersten Zeilen in Token-Reihenfolge
-- (Murmur3-Hash des Partition Keys), NICHT die ersten Zeilen der CSV-Dateien.
-- Bei ratings stammen deshalb alle 10 Zeilen aus der Partition eines einzigen Nutzys
-- (user_id 23), innerhalb der Partition nach movie_id sortiert (Clustering Column).
SELECT * FROM movies LIMIT 10;
SELECT * FROM ratings LIMIT 10;

-- =============================================================================
-- Big Data – 2. Praktikum (HSBI, WS 2026/27) · Zhaoze Yu · Matrikelnr. 50293014
-- Aufgabe 1: Fingerübungen (Keyspace k1, Tabelle person)
-- Ausführen: docker exec -it CassandraPraktikum2026 cqlsh -f /home/cassandra/cql/aufgabe1_person.cql
-- Reihenfolge: aufgabe1_person -> aufgabe3_schema -> aufgabe3_import -> aufgabe3_check -> (python denormalize.py) -> aufgabe3_query_tables -> aufgabe3_query_import -> aufgabe3_queries
-- =============================================================================
-- Grundlage: Tutorial "Getting Started With Cassandra: Using CQL API and CQLSH" (tutsplus)

-- 1) Keyspace anlegen (wie im Tutorial: k1, SimpleStrategy, RF 1)
CREATE KEYSPACE IF NOT EXISTS k1
  WITH replication = {'class': 'SimpleStrategy', 'replication_factor': '1'}
  AND durable_writes = true;
USE k1;

-- 2) Tabelle person anlegen (Tutorial: id, name, surname; email wird später ergänzt)
DROP TABLE IF EXISTS person;
CREATE TABLE person (
  id text,
  name text,
  surname text,
  PRIMARY KEY (id)
);
ALTER TABLE person ADD email text;

-- 3) Beschreibung der Tabelle
DESCRIBE TABLE person;

-- 4) Drei Einträge
INSERT INTO person (id, name, surname, email) VALUES ('001', 'Ada', 'Lovelace', 'ada@example.com');
INSERT INTO person (id, name, surname, email) VALUES ('002', 'Alan', 'Turing', 'alan@example.com');
INSERT INTO person (id, name, surname, email) VALUES ('003', 'Grace', 'Hopper', 'grace@example.com');

-- 5) Nach einer Person suchen (über den Partition Key)
SELECT * FROM person WHERE id = '002';

-- 6) Ganze Tabelle ausgeben
SELECT * FROM person;

-- Zusatz: Suche über eine Nicht-Schlüsselspalte wird ohne Index abgelehnt
-- (die erwartete Fehlermeldung zeigt das Query-first-Prinzip)
SELECT * FROM person WHERE surname = 'Hopper';

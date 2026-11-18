# Big Data – 2. Praktikum: Abgabepaket

**Name:** Zhaoze Yu · **Matrikelnr.:** 50293014 · WS 2026/27

## Inhalt

| Datei / Ordner | Inhalt | Aufgabe |
|---|---|---|
| `Abgabe.pdf` (Quelle `Abgabe.md`) | **Ausarbeitung**: alle Antworten, Screenshots, Notizen zu Aufgabe 2 im Anhang | 1–3 |
| `cql/aufgabe1_person.cql` | Keyspace `k1`, Tabelle `person`, DESCRIBE, 3 INSERTs, Suche, ganze Tabelle | 1 |
| `docs/aufgabe2_notizen.md` | Stichwortnotizen Architecture / Data Modeling / CQL | 2 |
| `cql/aufgabe3_schema.cql` | Keyspace `movielens`, Tabellen `movies` und `ratings` | 3 a, c |
| `cql/aufgabe3_import.cql` | Import der CSV-Dateien mit `COPY` | 3 c |
| `cql/aufgabe3_check.cql` | jeweils die ersten 10 Zeilen | 3 d |
| `cql/aufgabe3_query_tables.cql` | abfragegetriebene Tabellen `movies_by_user`, `users_by_movie`, `movies_by_title` | 3 e, f |
| `denormalize.py` | erzeugt die CSV-Dateien für diese Tabellen (Join beim Laden) | 3 e, f |
| `cql/aufgabe3_query_import.cql` | Import der denormalisierten CSV-Dateien mit `COPY` | 3 e, f |
| `cql/aufgabe3_queries.cql` | Abfragen e) und f) und Gegenprobe auf der Basistabelle | 3 e, f |
| `movielens_cassandra.py` | gemeinsames Modul: Verbindung, CSV, Join, Abfragefunktionen | 3 |
| `answers.py` | gibt die Antworten zu d), e), f) über den Python-Treiber aus | 3 d–f |
| `results/` | Ausgaben der echten Läufe (cqlsh-Protokolle, Antworten, Tracing, Tests); `results/windows/` = Lauf auf dem eigenen Rechner | Nachweis |
| `docs/screenshots/` | Screenshots der cqlsh-Sitzungen | 1, 3 |
| `TESTBERICHT.pdf`, `tests/`, `run_tests.py` | Testbericht und Testkette (54 Tests in 5 Stufen) | Zusatz |
| `requirements.txt` | `cassandra-driver` (+ `pyasyncore` ab Python 3.12) | — |

## Ausführen (Reihenfolge)

```bash
docker run --name CassandraPraktikum2026 -p 9042:9042 -d cassandra:latest
# im Container wie im Aufgabenblatt: apt-get ..., wget ml-latest-small.zip, unzip  (nach /home/cassandra)
docker cp cql CassandraPraktikum2026:/home/cassandra/
docker exec CassandraPraktikum2026 cqlsh -f /home/cassandra/cql/aufgabe1_person.cql        # Aufgabe 1
docker exec CassandraPraktikum2026 cqlsh -f /home/cassandra/cql/aufgabe3_schema.cql        # 3 a, c
docker exec CassandraPraktikum2026 cqlsh -f /home/cassandra/cql/aufgabe3_import.cql        # 3 c
docker exec CassandraPraktikum2026 cqlsh -f /home/cassandra/cql/aufgabe3_check.cql         # 3 d

pip install -r requirements.txt
docker cp CassandraPraktikum2026:/home/cassandra/ml-latest-small data/
python denormalize.py data/ml-latest-small out/denormalized                               # 3 e, f
docker cp out/denormalized CassandraPraktikum2026:/home/cassandra/
docker exec CassandraPraktikum2026 cqlsh -f /home/cassandra/cql/aufgabe3_query_tables.cql  # 3 e, f
docker exec CassandraPraktikum2026 cqlsh -f /home/cassandra/cql/aufgabe3_query_import.cql
docker exec CassandraPraktikum2026 cqlsh -f /home/cassandra/cql/aufgabe3_queries.cql

python answers.py        # Antworten d), e), f)
python run_tests.py      # optional: Testkette
```

Getestet mit Cassandra 5.0.9 (`cassandra:latest`) und 4.1.12, Python 3.10 und 3.13.

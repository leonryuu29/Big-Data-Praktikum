# Aufgabe 2 – Cassandra Details verstehen (Stichwortnotizen)

Quellen: Cassandra-Dokumentation, Abschnitte *Architecture* (Overview, Dynamo, Storage Engine, Guarantees), *Data Modeling* und *The Cassandra Query Language (CQL)*. Wo eine Aussage durch dieses Praktikum direkt überprüft wurde, steht ein ✔ mit Verweis.

## 1. Architecture

### Überblick
- Verteilte, partitionierte **Wide-Column-Datenbank**, ursprünglich bei Facebook entstanden. Vorbilder: **Amazon Dynamo** (Verteilung, Replikation) und **Google Bigtable** (Datenmodell, Storage Engine).
- **Kein Master**: alle Knoten sind gleichberechtigt (peer-to-peer). Jeder Knoten kann als **Coordinator** Anfragen annehmen.
- Ausgelegt auf **Hochverfügbarkeit**, **lineare horizontale Skalierung** (scale-out) und günstige Standardhardware, bei der Ausfälle der Normalfall sind.
- Keine Transaktionen über Partitionen hinweg. Unterstützt werden atomare Operationen auf einer Partition und **Lightweight Transactions** (Compare-and-Set mit Paxos).
- Schemaänderungen betreffen nur Metadaten und laufen im laufenden Betrieb.

### Dynamo: Verteilung und Replikation
- **Partitionierung per Consistent Hashing**: Der **Partitioner** (Standard `Murmur3Partitioner`, ✔ `cassandra.yaml` im Container) bildet den Partition Key auf einen **Token** (64 Bit) ab. Die Knoten bilden einen **Token-Ring**, jeder Knoten besitzt Token-Bereiche.
- Knoten hinzufügen oder entfernen verschiebt nur einen kleinen Teil der Schlüssel (anders als Hashing mit Modulo).
- **Virtuelle Knoten (vnodes)**: Jeder physische Knoten besitzt mehrere Tokens (`num_tokens`, ✔ im offiziellen Image 16). Das verteilt Daten und Last gleichmäßiger, auch beim Hinzufügen und Entfernen von Knoten. Nachteil: mehr Ring-Nachbarn, Repairs dauern länger. Die neuere deterministische Token-Vergabe braucht deutlich weniger Tokens als die früher üblichen 256.
- **Replikation** pro Keyspace mit dem **Replication Factor (RF)**:
  - `SimpleStrategy`: ein RF für den ganzen Cluster, ignoriert Rechenzentren und Racks. Nur für Tests und Einzelknoten. ✔ hier verwendet: 1 Knoten, RF 1.
  - `NetworkTopologyStrategy`: RF pro Rechenzentrum, verteilt Replikate auf verschiedene Racks. Für Produktion empfohlen, auch bei nur einem Rechenzentrum.
- **Multi-Master**: Jedes Replikat nimmt Schreibzugriffe an. Konflikte werden über **Zeitstempel pro Zelle** gelöst (**Last Write Wins**), daher ist Uhrensynchronisation (NTP) wichtig.
- **Abgleich der Replikate**: **Hinted Handoff** (der Coordinator merkt sich Writes für einen ausgefallenen Knoten), **Read Repair** (Abweichungen beim Lesen werden korrigiert) und **Anti-Entropy-Repair** mit **Merkle Trees** (`nodetool repair`, voll, teilbereichsweise oder inkrementell).
- **Gossip**: Knoten tauschen jede Sekunde Statusinformationen aus (Heartbeat, Tokens, Schema-Version) mit zufälligen Nachbarn und mit **Seed-Knoten**.
- **Ausfallerkennung**: Jeder Knoten entscheidet selbst mit dem **Phi-Accrual-Failure-Detector**. Der Status UP/DOWN wird nicht per Gossip verteilt. Entfernt wird ein Knoten nur explizit (decommission oder replace).

### Tunable Consistency
- Der **Consistency Level** wird pro Anfrage gewählt. Schreibzugriffe gehen immer an alle Replikate; der Level bestimmt nur, auf wie viele Bestätigungen der Coordinator wartet.
- Levels: `ONE`, `TWO`, `THREE`, `QUORUM` (Mehrheit aller Replikate), `ALL`, `LOCAL_QUORUM`, `EACH_QUORUM`, `LOCAL_ONE`, `ANY` (nur Writes: auch ein gespeicherter Hint zählt).
- **Starke Konsistenz**, wenn **R + W > RF** gilt, z. B. bei RF 3 `QUORUM` für Lesen und Schreiben. Niedrigere Levels bringen geringere Latenz und höhere Verfügbarkeit, dafür nur **eventual consistency**.
- Einordnung im **CAP-Theorem**: standardmäßig AP; über den Consistency Level verschiebbar in Richtung CP.

### Storage Engine (Schreib- und Lesepfad)
- **Schreiben**: zuerst sequenziell in das **Commit Log** (Dauerhaftigkeit, abschaltbar mit `durable_writes = false`), dann in die **Memtable** (sortiert, im Arbeitsspeicher). Ist die Memtable voll, wird sie als **SSTable** auf die Platte geschrieben (*flush*).
- **SSTables sind unveränderlich**. Update und Delete schreiben neue Versionen; Deletes erzeugen **Tombstones**, die nach `gc_grace_seconds` (Standard 10 Tage) entfernt werden. Deshalb sind Writes sehr schnell: kein Read-before-Write.
- **Compaction** führt SSTables zusammen und entfernt veraltete Daten. Strategien: `SizeTiered` (Standard), `Leveled`, `TimeWindow`, ab 5.0 zusätzlich `UnifiedCompactionStrategy`.
- **Lesen**: Memtable plus die betroffenen SSTables zusammenführen. Pro SSTable helfen **Bloom-Filter** (ist der Schlüssel enthalten?), Key-Cache und Partition-Index. ✔ Tracing in `results/tracing.txt`: „Merged data from memtables and 3 sstables“, „Key cache hit“.

## 2. Data Modeling

- **Query-first**: Zuerst die Anwendungsabfragen (Access Patterns) festlegen, dann die Tabellen daraus ableiten. In relationalen DBs ist es umgekehrt: erst die Entitäten, dann die Abfragen.
- Vorgehen laut Dokumentation: konzeptionelles Modell (ER) → **Anwendungsabfragen definieren** → **logisches Modell** (Chebotko-Diagramme: Tabellen, Partition Key **K**, Clustering Column **C↑/C↓**, statische Spalten **S**) → **physisches Modell** (Datentypen) → **Bewerten und Verfeinern** → Schema.
- **Eine Tabelle pro Abfrage** (bzw. pro Gruppe von Abfragen). **Denormalisierung und Duplikation sind gewollt**: Speicher ist billig, Joins gibt es nicht. ✔ Hier: `movies_by_user` und `users_by_movie` enthalten dieselben Bewertungen.
- **Primärschlüssel** = **Partition Key** (bestimmt den Knoten; alle Zeilen mit gleichem Key liegen zusammen) + **Clustering Columns** (Sortierung innerhalb der Partition, auf der Platte vorsortiert).
- Ziele für jede Tabelle:
  1. Daten **gleichmäßig über den Cluster verteilen** (Partition Key mit hoher Kardinalität, keine Hotspots);
  2. **möglichst wenige Partitionen pro Abfrage** lesen, idealerweise genau eine. ✔ `tests/test_3_locality.py`
- **Partitionsgröße abschätzen**: Anzahl Werte `Nv = Nr · (Nc − Npk − Ns) + Ns` (Zeilen · (Spalten − Primärschlüsselspalten − statische Spalten) + statische Spalten). Hartes Limit: 2 Milliarden Zellen pro Partition; Performanceprobleme treten schon viel früher auf. Rechnen mit dem Worst Case, nicht nur mit dem Durchschnitt.
- Zu große Partitionen aufteilen durch **Bucketing**: zusätzliche Spalte im Partition Key, z. B. Monat (Beispiel Hotel-Verfügbarkeit). Zu kleine Partitionen verteilen zusammengehörige Daten unnötig.
- Beispieldomäne der Dokumentation: **Hotel-Reservierung** (Hotels nahe einer Sehenswürdigkeit, freie Zimmer, Reservierungen nach Gast usw.), jeweils mit eigener Tabelle pro Abfrage.
- **Eindeutigkeit beachten**: Der Primärschlüssel muss eine Zeile eindeutig identifizieren, sonst überschreibt ein INSERT eine andere Zeile (Upsert). ✔ Doppelte Titel im Datensatz → `movie_id` als zusätzliche Clustering Column.

## 3. The Cassandra Query Language (CQL)

### Datentypen
- **Native Typen**: `text`/`varchar`, `ascii`, `int`, `bigint`, `smallint`, `tinyint`, `varint`, `float`, `double`, `decimal`, `boolean`, `uuid`, `timeuuid`, `timestamp` (Millisekunden), `date`, `time`, `duration`, `inet`, `blob`, `counter`. Ab 5.0 außerdem `vector<float, n>` für Vektorsuche.
- **Collections**: `list<T>`, `set<T>`, `map<K,V>` (für kleine Datenmengen gedacht); `frozen<…>` werden als ein einziger Wert gespeichert.
- **User-Defined Types** (`CREATE TYPE`) und **Tupel**.

### DDL
- `CREATE KEYSPACE … WITH replication = {…}` (Pflichtangabe) `AND durable_writes = true`. `USE` setzt den aktuellen Keyspace.
- `CREATE TABLE … PRIMARY KEY ((pk1, pk2), ck1, ck2) WITH CLUSTERING ORDER BY (ck1 ASC/DESC)`. Die Sortierung ist nachträglich nicht änderbar.
- **Statische Spalten** (`STATIC`): ein Wert pro Partition, nur in Tabellen mit Clustering Columns erlaubt. ✔ `users_by_movie.title`
- Tabellenoptionen: `compaction`, `compression` (Standard LZ4), `default_time_to_live`, `gc_grace_seconds`, `caching`, `bloom_filter_fp_chance` u. a. ✔ sichtbar in `DESCRIBE TABLE person`.
- `ALTER TABLE … ADD/DROP` (nicht für Primärschlüsselspalten), `DROP`, `TRUNCATE`.

### DML
- `SELECT`: Im `WHERE` sind nur der **vollständige Partition Key** (= oder IN) und danach **Clustering Columns in Reihenfolge** erlaubt (Präfix; Bereichsbedingungen nur auf die letzte genutzte Spalte).
- Andere Bedingungen erfordern `ALLOW FILTERING`, d. h. einen Scan über den Cluster. ✔ Fehlermeldung in Aufgabe 1 und 3; Tracing zeigt „range requests … seq scan“.
- `ORDER BY` nur nach Clustering Columns (in deklarierter oder genau umgekehrter Reihenfolge). `LIMIT`, `PER PARTITION LIMIT`, `GROUP BY` (nach Primärschlüsselspalten), Aggregate wie `COUNT`, `MIN`, `MAX`, `AVG`, `SUM`.
- `INSERT` und `UPDATE` sind beide **Upserts**: kein Fehler bei vorhandenem Schlüssel, kein Lesen vorher. ✔ `test_i13_insert_is_upsert`
- `USING TTL` (Ablauf in Sekunden), `USING TIMESTAMP`.
- **Lightweight Transactions**: `INSERT … IF NOT EXISTS`, `UPDATE … IF …` (Paxos, deutlich teurer).
- `BATCH`: atomar, gedacht für mehrere denormalisierte Tabellen, **nicht** zur Beschleunigung; `UNLOGGED` und `COUNTER` als Varianten.
- `DELETE` erzeugt Tombstones.

### Weitere Konzepte
- **Sekundärindizes**: klassische 2i (nur bei mittlerer Kardinalität sinnvoll) und **Storage-Attached Indexing (SAI)** ab 5.0 (`CREATE INDEX … USING 'sai'`).
- **Materialized Views**: automatisch gepflegte Abfragetabellen, gelten als experimentell und sind in 5.0 standardmäßig deaktiviert. ✔ `CREATE MATERIALIZED VIEW` liefert „Materialized views are disabled“.
- Benutzerdefinierte Funktionen und Aggregate (UDF/UDA), Trigger, Rollen und Rechte (`CREATE ROLE`, `GRANT`), JSON-Unterstützung (`SELECT JSON`, `INSERT … JSON`).
- **cqlsh** ist die Kommandozeile. `COPY TO/FROM` (CSV-Import und -Export) und `DESCRIBE` sind **cqlsh-Befehle, kein CQL**; deshalb gibt es sie im Python-Treiber nicht. ✔ Wichtige COPY-Optionen: `HEADER`, `DELIMITER`, `QUOTE`, `ESCAPE` (Standard `\`; für CSV mit `""` ist `ESCAPE = '"'` nötig).

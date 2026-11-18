# Testbericht – Big Data, 2. Praktikum (Cassandra + MovieLens)

**Name:** Zhaoze Yu · **Matrikelnr.:** 50293014 · WS 2026/27

| | |
|---|---|
| Datum | 18.11.2026 |
| Testobjekt | `movielens_cassandra.py`, `denormalize.py`, `answers.py`, CQL-Skripte in `cql/` (Aufgabe 1 und 3 a–f) |
| Testkette | `run_tests.py` → 5 Stufen in `tests/test_0_smoke.py` … `tests/test_4_integrity.py` (Python `unittest`) |
| Ergebnis | **54 / 54 bestanden**, 0 Fehler, 0 übersprungen |
| Rohausgabe | `results/test_output.txt` |

## 1. Testumgebung

| | Cloud-Container (dieser Bericht) | Windows-Rechner | GitHub Actions (CI) |
|---|---|---|---|
| Status | ✅ 54/54 | ⏳ wird nach dem lokalen Lauf nachgetragen | siehe Pull Request |
| Cassandra | 5.0.9, offizielles Image `cassandra:latest` | dasselbe Image über Docker Desktop | `cassandra:latest` und `cassandra:4.1` |
| Python | 3.13 | 3.10.11 | 3.10 und 3.13 |
| Treiber | cassandra-driver 3.29.0 + pyasyncore (aus dem Image, identisch mit cqlsh) | cassandra-driver von PyPI | cassandra-driver von PyPI |
| Daten | ml-latest-small (SHA-256 `696d65a3…e436`) | per `wget` im Container | per `wget` im Container |
| Ablauf | `scripts/run_praktikum2.sh` | `deploy.bat` → `scripts/run_praktikum2.ps1` | `scripts/run_praktikum2.sh` |

Der vollständige Ablauf wurde zusätzlich in einem **frischen Container** von Grund auf wiederholt: neues Image, leere Datenbank, Download-Fallback. Auch dabei waren alle 54 Tests grün.

## 2. Teststrategie: fünf Stufen

| Stufe | Frage | Braucht | Abbruch bei Fehler |
|---|---|---|---|
| 1 **Smoke** | Läuft die Umgebung? Treiber importierbar, Server erreichbar, Dateien vorhanden, Skripte kompilieren | Server | **ja**, die übrigen Stufen hätten dann keine Aussagekraft |
| 2 **Unit** | Ist die Python-Logik richtig? CSV lesen, Join, CSV schreiben, Code passt zu den CQL-Dateien | nichts | nein |
| 3 **Integration** | Funktionieren Schema und Abfragen auf echtem Cassandra? | Server; eigener Test-Keyspace `test_xxxx`, wird danach gelöscht | nein |
| 4 **Lokalität** | Sind die Abfragen *effizient*, d. h. lesen sie genau eine Partition? | importierte Daten; Query-Tracing | nein |
| 5 **Integrität** | Sind die echten Daten vollständig und unverändert angekommen, und stimmen die Antworten der Abgabe? | importierte Daten und CSV-Dateien | nein |

Regeln für alle Stufen:

- Getestet wird gegen einen **echten Server**, nicht gegen Mocks. Das Schema stammt aus den **echten CQL-Dateien**, die nur auf einen Test-Keyspace umgeschrieben werden.
- Die Integritätstests vergleichen mit einem **unabhängigen Orakel**: Sortieren und Filtern der CSV-Daten in reinem Python, ohne Cassandra.
- Die Fixture-Daten in `tests/fixtures/` decken gezielt die Sonderfälle ab: Komma und `""` im Titel, schwedische und japanische Zeichen, gleicher Titel für zwei Filme, Großschreibung mitten im Wort (`eXistenZ`), Ziffern am Titelanfang, Bewertung zu einem unbekannten Film, Film ohne Genre.

## 3. Testfälle und Ergebnisse

### Stufe 1 – Smoke (5/5)

| ID | Testfall | Ergebnis |
|---|---|---|
| s01 | Treiber importierbar | ✅ |
| s02 | alle 7 CQL-Dateien vorhanden | ✅ |
| s03 | alle Skripte kompilieren | ✅ |
| s04 | Server erreichbar, Version lesbar | ✅ |
| s05 | einfache Abfrage (`now()`) | ✅ |

### Stufe 2 – Unit (16/16)

| ID | Testfall | Erwartet | Ergebnis |
|---|---|---|---|
| u01–u02 | CSV lesen: Anzahl, Datentypen | 10 Filme, 13 Bewertungen; int/int/float/int | ✅ |
| u03 | Titel mit Komma | `Matrix, The (1999)` | ✅ |
| u04 | Titel mit `""` | ein einzelnes `"` | ✅ |
| u05 | Unicode | `Åmål`, `千と千尋の神隠し` unverändert | ✅ |
| u06 | Genres als Text, auch `(no genres listed)` | unverändert | ✅ |
| u07 | Bewertung zu unbekanntem Film | wird verworfen | ✅ |
| u08 | Join fügt den Titel hinzu | korrekte Tupel | ✅ |
| u09 | zwei Filme „Emma (1996)“ | bleiben zwei Zeilen | ✅ |
| u10–u11 | Hilfstabelle vollständig; `by_user` und `by_movie` enthalten dieselben Fakten | gleiche Mengen | ✅ |
| u12 | CSV schreiben und wieder lesen | `""` gemäß RFC 4180, Roundtrip ohne Verlust | ✅ |
| u13–u14 | CSV-Spaltenreihenfolge = Spaltenliste der COPY-Befehle | identisch | ✅ |
| u15 | jeder COPY mit Titelspalte nutzt `ESCAPE = '"'` | ja | ✅ |
| u16 | CQL-Dateien lassen sich parsen und auf den Test-Keyspace umschreiben | ja | ✅ |

### Stufe 3 – Integration (13/13)

| ID | Testfall | Erwartet | Ergebnis |
|---|---|---|---|
| i01 | Schema aus den CQL-Dateien | 5 Tabellen | ✅ |
| i02 | `movies_by_user`: Schlüsselrollen laut `system_schema` | `user_id` = Partition Key, `title`/`movie_id` = Clustering ASC | ✅ |
| i03 | `users_by_movie.title` | `static` | ✅ |
| i04–i05 | d) `first_rows`: LIMIT; unbekannter Tabellenname | 10 bzw. 5 Zeilen; ValueError (Schutz gegen Injection) | ✅ |
| i06 | e) Titel von Nutzy 1 | Byte-Reihenfolge: Ziffern < Großbuchstaben < `eXistenZ` < CJK | ✅ |
| i07 | e) doppelte Titel | beide `movie_id`s (4 und 5) | ✅ |
| i08 | e) LIMIT 5 | die ersten 5 der sortierten Liste | ✅ |
| i09 | e) unbekanntes Nutzy | leere Liste | ✅ |
| i10 | f) Nutzys von Film 1 | [1, 2, 3], Titel über statische Spalte | ✅ |
| i11 | f) Titel → movie_id | Emma → [4, 5]; unbekannter Titel → [] | ✅ |
| i12 | Titelsuche unterscheidet Groß- und Kleinschreibung | `toy story (1995)` → [] | ✅ |
| i13 | INSERT auf vorhandenen Schlüssel | Upsert: überschreibt, kein Fehler, kein Duplikat | ✅ |

### Stufe 4 – Lokalität (7/7)

| ID | Testfall | Nachweis | Ergebnis |
|---|---|---|---|
| l01 | e) `movies_by_user WHERE user_id = 42` | Trace: „Executing single-partition query on movies_by_user“ | ✅ |
| l02 | f) `users_by_movie WHERE movie_id = 1` | single-partition | ✅ |
| l03 | Titel → movie_id | single-partition | ✅ |
| l04 | dieselbe Frage auf `ratings` | InvalidRequest „… ALLOW FILTERING“ | ✅ |
| l05 | mit `ALLOW FILTERING` | Trace: „range requests on 17 ranges … seq scan“, kein single-partition | ✅ |
| l06 | `ORDER BY` auf einer Nicht-Clustering-Spalte | InvalidRequest | ✅ |
| l07 | größte Partition von `movies_by_user` | Nutzy 414: 2 698 Zeilen ≈ 5 400 Werte < 100 000 | ✅ |

Gemessene Laufzeiten (`results/tracing.txt`): e) 2,7 ms für 5 Zeilen; f) 1,9 ms für 215 Zeilen; Gegenprobe mit ALLOW FILTERING 9,9 ms. Der Scan wächst linear mit der Gesamtdatenmenge, die Abfrage auf eine Partition nicht.

### Stufe 5 – Datenintegrität (13/13)

| ID | Testfall | Erwartet | Ergebnis |
|---|---|---|---|
| g01 | Datensatz = Angaben der README | 9 742 / 100 836 / 610 | ✅ |
| g02 | Zeilenzahlen aller 5 Tabellen | 9 742 / 100 836 / 100 836 / 100 836 / 9 742 | ✅ |
| g03 | `movies` Feld für Feld = CSV | identisch | ✅ |
| g04 | `ratings` Feld für Feld = CSV | identisch | ✅ |
| g05–g07 | alle drei Abfragetabellen = Join der CSV-Dateien | identisch | ✅ |
| g08 | Sonderfälle: `11'09"01…` (7789), `Matrix, The` (2571), `Åmål` (7034) | unverändert | ✅ |
| g09 | jede Bewertung verweist auf einen existierenden Film | ja | ✅ |
| g10 | Wertebereich der Bewertungen | {0,5 … 5,0} in 0,5-Schritten | ✅ |
| g11 | 5 doppelte Titel | je 2 Einträge, keine Bewertung verloren | ✅ |
| g12 | **Antwort e)**: Nutzy 42 | gleich dem Orakel; erste 5 Titel wie in der Abgabe; 440 Filme | ✅ |
| g13 | **Antwort f)**: Toy Story | movie_id 1; 215 Nutzys, gleich dem Orakel | ✅ |

## 4. Wirksamkeit der Tests (Mutationstest)

Ein grüner Testlauf beweist nur dann etwas, wenn die Tests Fehler auch erkennen. Deshalb wurden gezielt fünf Fehler eingebaut:

| Mutation | erkannt durch | Ergebnis |
|---|---|---|
| M1 `movie_id` aus dem Primärschlüssel von `movies_by_user` entfernt | i06, i07, i08 u. a. | ❌ 4 Fehlschläge → erkannt |
| M2 `ESCAPE = '"'` aus dem Import entfernt | u15 | ❌ erkannt |
| M3 Sortierung `title DESC` statt `ASC` | i06, i08 u. a. | ❌ 3 Fehlschläge → erkannt |
| M4 Join verwirft Bewertungen zu unbekannten Filmen nicht mehr | u07 | ❌ erkannt |
| M5 `users_by_movie` nach `user_id DESC` sortiert | i10 | ❌ erkannt |

Alle 5 Mutationen wurden erkannt. Danach wurde der Originalcode wiederhergestellt.

## 5. Während der Arbeit gefundene Probleme

| Problem | Ursache | Lösung |
|---|---|---|
| Titel `11'09"01 - September 11 (2002)` nach dem Import mit einem `"` zu viel am Ende | CSV kodiert `"` als `""`; das Standard-Escape-Zeichen von `COPY` ist `\` | `ESCAPE = '"'` bei allen COPY-Befehlen mit Titeln; abgesichert durch u15 und g08 |
| Bewertungen gleichnamiger Filme hätten sich überschrieben | 5 Titel kommen doppelt vor; INSERT ist ein Upsert | `movie_id` als zusätzliche Clustering Column; abgesichert durch i07, g11 und M1 |
| Python-Treiber startet unter Python ≥ 3.12 nicht („Unable to load a default connection class“) | das Modul `asyncore` wurde aus Python 3.12 entfernt | `pyasyncore; python_version >= "3.12"` in `requirements.txt`, genau wie im cqlsh des offiziellen Images |
| `timestamp` aus der CSV wäre als CQL-Typ `timestamp` falsch | CQL `timestamp` erwartet Millisekunden, die CSV liefert Sekunden | Spalte `rated_at bigint` (Sekunden unverändert) |
| Im Cloud-Container kein `apt-get` und kein `wget` (kein Internet) | Netzwerkbeschränkung der Testumgebung, nicht des Praktikums | Fallback in beiden Ablaufskripten: Download auf dem Host und `docker cp`; unter Windows und in CI läuft der Weg aus dem Aufgabenblatt |

## 6. Grenzen

- Ein einzelner Knoten mit RF 1: Replikation, Consistency Levels und Ausfälle sind nicht Teil der Tests.
- Die Laufzeitmessungen beziehen sich auf den kleinen Datensatz mit 100 836 Bewertungen und zeigen den Trend, keine Benchmark-Werte.
- Die Sortierung erfolgt nach UTF-8-Bytes und ist nicht sprachabhängig (siehe Abgabe 3 e). Das wird nicht als Fehler behandelt.

## 7. Ausführen

```bat
:: Windows (Docker Desktop läuft): kompletter Ablauf inkl. Tests
deploy.bat
:: nur die Tests, wenn Cassandra schon läuft und die Daten importiert sind
run_tests.bat
```

```bash
bash scripts/run_praktikum2.sh   # Linux/macOS/CI
python run_tests.py              # nur die Testkette
```

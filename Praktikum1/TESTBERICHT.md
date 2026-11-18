# Testbericht – Big Data, 1. Praktikum (Redis + Yelp)

**Name:** Zhaoze Yu · **Matrikelnr.:** 50293014 · WS 2026/27

| | |
|---|---|
| Datum | 18.11.2026 (Überarbeitung auf den Teststandard aus Praktikum 2) |
| Testobjekt | `yelp_redis.py`, `load_data.py`, `autocomplete.py`, `answers.py`, `cli/aufgabe1.redis` (Aufgabe 1 und 2 a–d) |
| Testkette | `run_tests.py` → 5 Stufen in `tests/test_0_smoke.py` … `tests/test_4_integrity.py` (Python `unittest`) |
| Ergebnis | **48 / 48 bestanden**, 0 Fehler, 0 übersprungen |
| Rohausgabe | `results/test_output.txt` |

## 1. Testumgebungen

| | Cloud-Container | Windows-Rechner | GitHub Actions (CI) |
|---|---|---|---|
| Status | ✅ 48/48 | ⏳ wird nach dem lokalen Lauf nachgetragen | ✅ 4 × 48/48 |
| Redis | 8.10.3 (`redis:latest`) | `redis:latest` über Docker Desktop | `redis:latest` und `redis:5` |
| Python | 3.13 | 3.10.11 | 3.10 und 3.13 |
| Client | minimaler RESP2-Client mit derselben API (redis-py dort nicht installierbar) | redis-py von PyPI | redis-py 8.1.0 von PyPI |
| Daten | `business.json` (192 609 Zeilen) | dieselbe Datei | Download von Sciebo wie im Aufgabenblatt |
| Ablauf | `scripts/run_praktikum1.sh` | `deploy.bat` → `scripts/run_praktikum1.ps1` | `scripts/run_praktikum1.sh` |

Der vollständige Ablauf wurde zusätzlich in einem **frischen Container** von Grund auf wiederholt; auch dabei waren alle 48 Tests grün.

## 2. Teststrategie: fünf Stufen

| Stufe | Frage | Braucht | Abbruch bei Fehler |
|---|---|---|---|
| 1 **Smoke** | Läuft die Umgebung? redis-py importierbar, PING, Version, Dateien, Skripte kompilieren | Server | **ja** |
| 2 **Unit** | Ist die reine Logik richtig? Datei lesen, Namensschlüssel, Präfixgrenzen, Detailausgabe | nichts | nein |
| 3 **Integration** | Stimmen Import und Abfragen auf einem echten Server? | Server, **Datenbank 15** (wird geleert) | nein |
| 4 **Effizienz** | Schickt der Code die *richtigen und wenigen* Befehle? (`CONFIG RESETSTAT` + `INFO commandstats`) | importierte Daten (db 0, nur lesend) | nein |
| 5 **Integrität** | Sind alle echten Daten unverändert angekommen, und stimmen die Antworten der Abgabe? | importierte Daten + `business.json` | nein |

Regeln:

- Getestet wird gegen einen echten Server. Die Tests schreiben nur in Datenbank 15; die echten Daten in Datenbank 0 werden nur gelesen.
- Die Fixture `tests/fixtures/business_fixture.json` enthält gezielt Sonderfälle: Groß- und Kleinschreibung (`STARBUCKS`), Umlaute, CJK- und vietnamesische Zeichen, zwei Betriebe mit gleichem Namen („The Still“), einen Betrieb ohne Namen und Leerzeilen am Dateiende.
- Die Integritätstests vergleichen mit einem **unabhängigen Orakel**, das die Datei in reinem Python ohne Redis auswertet.

## 3. Testfälle und Ergebnisse

### Stufe 1 – Smoke (5/5)
| ID | Testfall | Ergebnis |
|---|---|---|
| s01 | redis-py importierbar | ✅ |
| s02 | alle 5 Skripte kompilieren | ✅ |
| s03 | Fixture, Beispieldatei und `cli/aufgabe1.redis` vorhanden | ✅ |
| s04 | `PING` → `PONG` | ✅ |
| s05 | Serverversion lesbar | ✅ |

### Stufe 2 – Unit (12/12)
| ID | Testfall | Erwartet | Ergebnis |
|---|---|---|---|
| u01 | JSON Lines lesen, Leerzeilen ignorieren; rohe Zeile = Objekt | 13 Einträge | ✅ |
| u02 | Unicode korrekt gelesen | `Café Müller`, `寿司 Sushi Bar` | ✅ |
| u03 | Beispieldatei (200 Datensätze) hat die Pflichtfelder | ja | ✅ |
| u04–u06 | Namensschlüssel: Kleinschreibung, Unicode-Kleinschreibung, fehlender Name | `starbucks`, `café müller`, `""` | ✅ |
| u07 | leeres Präfix | keine Abfrage | ✅ |
| u08 | Grenzen für „Star“ | `[star` bis `[star` + Byte `0xFF` | ✅ |
| u09 | **Eigenschaftstest**: Im Bereich liegen genau die Namen mit dem Präfix (9 Präfixe, inkl. CJK) | identisch mit `str.startswith` | ✅ |
| u10 | Zeichen „ÿ“ als Schranke wäre falsch, Byte `0xFF` richtig | `[abc€` nur mit 0xFF im Bereich | ✅ |
| u11–u12 | Details: Felder und Textausgabe | Adresse, Stadt, Sterne, „geschlossen“ | ✅ |

### Stufe 3 – Integration (16/16)
| ID | Testfall | Erwartet | Ergebnis |
|---|---|---|---|
| i01 | Import mit `batch_size=3` (mehrere Pipeline-Stapel) | 13 Datensätze | ✅ |
| i02 | **jeder** `business:<id>` byte-genau gleich der Dateizeile (auch mit Unicode) | identisch | ✅ |
| i03 | Anzahl Schlüssel | 13 + 11 Namen + 1 Index | ✅ |
| i04 | 2 b: `Starbucks`/`STARBUCKS` in einem Set; Typ `set` | 3 ids | ✅ |
| i05 | zweiter Import erzeugt keine Duplikate | unverändert | ✅ |
| i06 | Betrieb ohne Namen: JSON gespeichert, aber nicht im Index | ja | ✅ |
| i07–i09 | 2 c: „Star“, Groß- und Kleinschreibung, „The Sti“ | erwartete Listen | ✅ |
| i10–i11 | kein Treffer, leere Eingabe, `limit` | `[]`, `[]`, 2 Treffer | ✅ |
| i12 | Unicode-Präfixe `Café M`, `寿`, `pho ð` | je 1 Treffer | ✅ |
| i13 | letzter Eintrag des Index; keine falschen Treffer | ja | ✅ |
| i14–i15 | 2 d: „The Still“ → 2 Betriebe mit Adresse und Sternen; unbekannter Name → leer | ja | ✅ |
| i16 | Beispieldatei mit 200 Datensätzen | 5 × starbucks, 3 Namen für „the sti“ | ✅ |

### Stufe 4 – Effizienz (5/5)
| ID | Testfall | Nachweis (`INFO commandstats`) | Ergebnis |
|---|---|---|---|
| l01 | `autocomplete("Star")` | genau `{zrangebylex: 1}` → 181 Namen | ✅ |
| l02 | `details("Starbucks")` | genau `{smembers: 1, mget: 1}` → 1 066 Betriebe | ✅ |
| l03 | vier Suchen | nie `KEYS`/`SCAN`; leeres Präfix ohne Anfrage | ✅ |
| l04 | Gegenprobe ohne Index: `SCAN MATCH star*` | gleiches Ergebnis, aber 337 `SCAN`-Aufrufe; 195 ms statt 0,7 ms | ✅ |
| l05 | Import von 13 Datensätzen mit `batch_size=5` | 3 Pipeline-Roundtrips statt ~36 Einzelbefehlen | ✅ |

### Stufe 5 – Datenintegrität (10/10)
| ID | Testfall | Erwartet | Ergebnis |
|---|---|---|---|
| g01–g02 | Datensätze; `business_id` eindeutig | 192 609 (Aufgabenblatt: 209 393, andere Datensatzversion) | ✅ |
| g03 | Anzahl Schlüssel | 192 609 + 144 337 + 1 = 336 947 | ✅ |
| g04 | **alle** 192 609 JSON-Strings = Dateizeile | 0 Abweichungen | ✅ |
| g05 | **alle** 144 337 Namens-Sets = Orakel | 0 Abweichungen | ✅ |
| g06 | Index = Menge aller Namen | identisch | ✅ |
| g07 | „Star“ | 181 Namen = Orakel, enthält *starlight nails & spa* | ✅ |
| g08 | Starbucks | 1 066 (exakt) / 1 073 (mit Präfix) | ✅ |
| g09 | „The Still“ / „The Sti“ | 2 / the still, the stirling club spa, the stirling room | ✅ |
| g10 | Details „The Still“ | Calgary AB 2,5★; Las Vegas NV 3,5★ | ✅ |

## 4. Wirksamkeit der Tests (Mutationstest)

| Mutation | Ergebnis |
|---|---|
| M1 obere Schranke als Zeichen „ÿ“ statt Byte `0xFF` | ❌ 6 Fehlschläge → erkannt |
| M2 Namen nicht kleingeschrieben | ❌ 17 Fehlschläge → erkannt |
| M3 Details mit einem `GET` pro Betrieb statt `MGET` | ❌ erkannt (l02) |
| M4 JSON vor dem Speichern neu serialisiert (`json.dumps`) | **zunächst nicht erkannt** → Test i02 verschärft → ❌ erkannt |
| M5 Betriebe ohne Namen werden indexiert | ❌ 3 Fehlschläge → erkannt |
| M6 jeder Befehl einzeln statt im Pipeline-Stapel | ❌ erkannt (l05) |

**Erkenntnis aus M4:** Test i02 prüfte nur einen reinen ASCII-Datensatz, und für diesen liefert `json.dumps` zufällig denselben String. Jetzt prüft er jeden Fixture-Datensatz, auch mit Unicode, wo `json.dumps` `é` zu `é` macht. Damit erkennt ihn auch die Integrationsstufe und nicht erst die Integritätsprüfung auf bereits importierten Daten.

## 5. Gefundene und behobene Probleme

| Problem | Ursache | Lösung |
|---|---|---|
| Verbindung zu Redis 5 scheitert (`unknown command 'HELLO'`) | redis-py ≥ 8 nutzt standardmäßig RESP3 | `protocol=2` in `connect()` (CI prüft Redis 5) |
| CI meldete Erfolg, obwohl Stufe 4/5 übersprungen waren; dabei waren nur 200 Datensätze importiert | Die Zuordnung der beiden Sciebo-Links zu den Dateien war im Linux-Ablauf vertauscht; das Aufgabenblatt nennt keine Zuordnung | Zuordnung über die Dateigröße (wie im Windows-Skript) und Abbruch, wenn `business.json` < 10 MB ist; CI prüft jetzt ausdrücklich „48 von 48, 0 übersprungen“ |
| `redis-cli` zeigt ohne Terminal `nil` als leere Zeile | nicht interaktiver Modus | Protokollskript schreibt `(nil)` wie in der interaktiven Sitzung |
| Datensatzzahl weicht vom Aufgabenblatt ab (192 609 statt 209 393) | andere Version des Datensatzes | kein Codefehler; in Abgabe und Test g01 dokumentiert |

## 6. Grenzen

- Im Cloud-Container lief ein minimaler RESP2-Client statt redis-py. Mit dem echten redis-py 8.1.0 laufen die Tests in der CI und auf dem eigenen Rechner.
- Laufzeitmessungen gelten für diesen Datensatz und zeigen die Größenordnung, keine Benchmark-Werte.
- `autocomplete.py` (die `input()`-Schleife) wird nur über einen Demo-Durchlauf geprüft (`results/autocomplete_demo.txt`); die Logik liegt in den getesteten Funktionen.

## 7. Ausführen

```bat
deploy.bat        :: kompletter Ablauf inkl. Tests (Windows, Docker Desktop)
run_tests.bat     :: nur die Testkette
```

```bash
bash scripts/run_praktikum1.sh    # Linux/macOS/CI
python run_tests.py               # nur die Testkette
```

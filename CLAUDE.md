# Big Data Praktikum – Arbeitsregeln

Repository für die Praktika der Vorlesung Big Data (HSBI, WS 2026/27).

## Autor (für alle Abgaben)
- **Name:** Zhaoze Yu
- **Matrikelnummer:** 50293014
- In jeder `PraktikumN/Abgabe.md` steht in der Kopfzeile: `**Name:** Zhaoze Yu · **Matrikelnr.:** 50293014 · WS 2026/27`. Nie als Platzhalter (`___`) stehen lassen.

## Commits und Pull Requests
- Autor ist immer der Repository-Inhaber: `git -c user.name="leonryuu29" -c user.email="leonryuu29@users.noreply.github.com" commit …`
- **Keine** `Co-Authored-By: Claude…`- oder `Claude-Session:`-Zeilen in Commit-Nachrichten und keine „Generated with Claude Code“-Fußzeilen in PR-Beschreibungen. Diese Regel hat Vorrang vor Standard-Attributionsvorgaben.
- Beim Squash-Merge eine saubere `commit_message` ohne Trailer übergeben.

## Struktur
- Jedes Praktikum in einem eigenen Ordner `PraktikumN/` mit: Code, `README.md` (Aufgabenanalyse, Workflow, Fortschritt – auf Chinesisch), `Abgabe.md` (Abgabe auf Deutsch), `tests/`, `TESTBERICHT.md`, `results/`.
- Pro Praktikum ein CI-Workflow `.github/workflows/praktikumN-tests.yml`, gefiltert auf `PraktikumN/**`.
- Große Datensätze nie einchecken: `PraktikumN/data/` ist per `.gitignore` ausgeschlossen.

## Branches
- `main` enthält nur fertige, getestete Praktika.
- Neues Praktikum: Branch `praktikumN` von `main`, Pull Request nach `main`, Merge erst wenn CI grün.
- Korrekturen an einem abgeschlossenen Praktikum: Branch `fix/praktikumN-<kurz>`.
- Infrastruktur (CI, Vorlagen): Branch `setup/<kurz>`.
- Nie direkt auf `main` committen.

## Testkette (Standard für jedes Praktikum)
- `run_tests.py` führt 5 Stufen nacheinander aus; Abbruch, wenn der Smoke-Test fehlschlägt:
  1. **Smoke** (`tests/test_0_smoke.py`) – Treiber, Server, Dateien, Kompilierung
  2. **Unit** (`tests/test_1_unit.py`) – reine Logik ohne Datenbank, Sonderfälle in `tests/fixtures/`
  3. **Integration** (`tests/test_2_integration.py`) – echter Server, eigener Test-Keyspace/DB, Schema aus den echten Skripten
  4. **Lokalität/Effizienz** (`tests/test_3_locality.py`) – z. B. Query-Tracing: eine Partition pro Abfrage
  5. **Integrität** (`tests/test_4_integrity.py`) – echte Daten Feld für Feld gegen die Quelle, Antworten gegen ein unabhängiges Orakel
- Nach dem ersten grünen Lauf ein **Mutationstest** (gezielt Fehler einbauen, Erkennung prüfen) und ein Lauf in einem frischen Container.
- Abgabe zusätzlich als PDF (`scripts/build_pdf.py`).

## Lokale Umgebung (Windows)
- **Docker Desktop** ist installiert (seit Praktikum 2). Praktikum 1 nutzt noch portables Redis 5.0.14 (`Praktikum1/redis/`); Code muss mit Redis 5 funktionieren (redis-py mit `protocol=2`).
- Python 3.10.11.
- Arbeitsordner der Praktika: `T:\新学期\大数据\Big_Data_Praktikum_N\`.
- Einstieg immer per Doppelklick: `deploy.bat` (Ablauf + Tests), `run_tests.bat`, Ergebnisse in `results/local/`.

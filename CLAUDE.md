# Big Data Praktikum – Arbeitsregeln

Repository für die Praktika der Vorlesung Big Data (HSBI, WS 2026/27).

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

## Lokale Umgebung (Windows)
- Kein Docker installiert; Redis läuft portabel (`PraktikumN/redis/`, Version 5.0.14). Code muss deshalb mit Redis 5 funktionieren (redis-py mit `protocol=2`).
- Python 3.10.

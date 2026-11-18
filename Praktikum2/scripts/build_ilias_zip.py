"""Packt die ILIAS-Abgabe: Praktikum2_ZhaozeYu_50293014.zip

Nur der Kern: Ausarbeitung (PDF), die CQL-Skripte und der Python-Code.
Tests, Protokolle, Screenshots und Werkzeuge bleiben im Repository.
Aufruf:  python scripts/build_ilias_zip.py
"""
import glob
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "Praktikum2_ZhaozeYu_50293014"

FILES = [
    "Abgabe.pdf",                                              # Ausarbeitung mit allen Antworten
    "cql/*.cql",                                               # Aufgabe 1 und 3 a-f
    "movielens_cassandra.py", "denormalize.py", "answers.py",  # Aufgabe 3
    "requirements.txt",
]


def main():
    out = os.path.join(ROOT, NAME + ".zip")
    paths = sorted({p for pat in FILES for p in glob.glob(os.path.join(ROOT, pat))})
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, os.path.join(NAME, os.path.relpath(p, ROOT)))
    print(f"{out}: {len(paths)} Dateien, {os.path.getsize(out) / 1024:.0f} KB")


if __name__ == "__main__":
    main()

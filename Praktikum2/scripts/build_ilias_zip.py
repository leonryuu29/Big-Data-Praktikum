"""Packt die ILIAS-Abgabe: Praktikum2_ZhaozeYu_50293014.zip

Enthält nur, was für die Bewertung nötig ist (Ausarbeitung, CQL, Python-Code, Nachweise, Tests).
Werkzeuge für Windows/CI (bat, ps1, sh, Screenshot-/PDF-Erzeugung) bleiben draußen.
Aufruf:  python scripts/build_ilias_zip.py
"""
import glob
import os
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "Praktikum2_ZhaozeYu_50293014"

FILES = [
    "LIESMICH.md", "Abgabe.pdf", "Abgabe.md", "TESTBERICHT.pdf", "TESTBERICHT.md",
    "movielens_cassandra.py", "denormalize.py", "answers.py", "run_tests.py", "requirements.txt",
    "cql/*.cql", "docs/aufgabe2_notizen.md", "docs/screenshots/*.png",
    "results/*.txt", "results/windows/*.txt",
    "tests/*.py", "tests/fixtures/*.csv",
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

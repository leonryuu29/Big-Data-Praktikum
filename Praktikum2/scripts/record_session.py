"""Führt eine .cql-Datei Anweisung für Anweisung in cqlsh (im Docker-Container) aus
und schreibt ein Protokoll im Stil einer interaktiven cqlsh-Sitzung (Prompt + Ausgabe).

Aufruf:  python scripts/record_session.py cql/aufgabe1_person.cql results/aufgabe1_session.txt [keyspace]
"""
import os
import re
import subprocess
import sys

CONTAINER = os.environ.get("CONTAINER", "CassandraPraktikum2026")


def statements(path):
    src = open(path, encoding="utf-8").read()
    src = re.sub(r"--[^\n]*", "", src)
    return [s.strip() for s in src.split(";") if s.strip()]


def main(cql, out_path, keyspace=None):
    current = None
    lines = []
    for stmt in statements(cql):
        m = re.match(r"USE\s+(\w+)", stmt, re.I)
        args = ["docker", "exec", CONTAINER, "cqlsh"]
        if current:
            args += ["-k", current]
        args += ["-e", stmt + ";"]
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
        prompt = f"cqlsh:{current}> " if current else "cqlsh> "
        first, *rest = stmt.split("\n")
        lines.append(prompt + first + (";" if not rest else ""))
        lines += ["   ... " + r + (";" if i == len(rest) - 1 else "") for i, r in enumerate(rest)]
        res = re.sub(r"^<stdin>:\d+:", "", (p.stdout + p.stderr).strip("\n"), flags=re.M)
        if stmt.upper().startswith("COPY"):
            # COPY-Fortschrittszeilen ("Processed: ... rows/s") weglassen, das Endergebnis bleibt
            res = "\n".join(l for l in res.replace("\r", "\n").split("\n")
                            if l.strip() and not l.startswith("Processed:"))
        if res:
            lines.append(res)
        lines.append("")
        if m:
            current = m.group(1)
    open(out_path, "w", encoding="utf-8").write("\n".join(lines))


if __name__ == "__main__":
    main(*sys.argv[1:])

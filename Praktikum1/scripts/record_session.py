"""Führt eine .redis-Datei Befehl für Befehl mit redis-cli (im Docker-Container) aus und
schreibt ein Protokoll im Stil einer interaktiven Sitzung (Prompt + Ausgabe).

Kommentarzeilen (#) und Leerzeilen werden übersprungen. Ausgeführt wird in Datenbank 1
(-n 1), damit die importierten Yelp-Daten in Datenbank 0 unberührt bleiben.
Aufruf:  python scripts/record_session.py cli/aufgabe1.redis results/aufgabe1_session.txt
"""
import os
import shlex
import subprocess
import sys

CONTAINER = os.environ.get("CONTAINER", "RedisPraktikum2026")
DB = os.environ.get("REDIS_CLI_DB", "1")


def commands(path):
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#"):
            yield line


def main(script, out_path):
    lines = []
    for cmd in commands(script):
        args = ["docker", "exec", CONTAINER, "redis-cli", "-n", DB] + shlex.split(cmd)
        p = subprocess.run(args, capture_output=True, text=True, encoding="utf-8")
        lines.append(f"127.0.0.1:6379[{DB}]> {cmd}")
        res = (p.stdout + p.stderr).rstrip("\n")
        # redis-cli gibt ohne Terminal für nil eine leere Zeile aus; wie interaktiv als (nil) zeigen
        lines.append(res if res.strip() else "(nil)")
    open(out_path, "w", encoding="utf-8").write("\n".join(lines) + "\n")
    print(f"{out_path}: {len(lines)} Zeilen")


if __name__ == "__main__":
    main(*sys.argv[1:])

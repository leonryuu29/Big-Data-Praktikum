#!/usr/bin/env bash
# Praktikum 1 – kompletter Ablauf (Linux/macOS/CI); entspricht Schritt für Schritt scripts/run_praktikum1.ps1
#   Umgebungsvariablen: CONTAINER (Standard RedisPraktikum2026), IMAGE (Standard redis:latest),
#                       PYTHON (Standard python3), OUT (Ergebnisordner, Standard results/local)
set -euo pipefail
cd "$(dirname "$0")/.."
CONTAINER=${CONTAINER:-RedisPraktikum2026}
IMAGE=${IMAGE:-redis:latest}
PYTHON=${PYTHON:-python3}
OUT=${OUT:-results/local}
export PYTHONIOENCODING=utf-8
mkdir -p "$OUT" data
step() { echo; echo "== $* =="; }

step "1/8 Docker: Redis-Container"
docker --version
if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then docker start "$CONTAINER" >/dev/null
else docker run --name "$CONTAINER" -p 6379:6379 -d "$IMAGE" >/dev/null; fi
for i in $(seq 1 30); do
  [ "$(docker exec "$CONTAINER" redis-cli ping 2>/dev/null)" = "PONG" ] && break
  sleep 1
done
docker exec "$CONTAINER" redis-cli INFO server | grep -E "^redis_version"

step "2/8 Python-Paket redis-py"
"$PYTHON" -c "import redis; print('redis-py', redis.__version__)"

step "3/8 Daten"
if [ ! -s data/business.json ] || [ ! -s data/businessS.json ]; then
  curl -fsSL -o data/business.json  https://hsbi.sciebo.de/s/REoBXKjpLjViIbJ/download
  curl -fsSL -o data/businessS.json https://hsbi.sciebo.de/s/KYRLLYOItgJ3Ulp/download
fi
ls -l data/business.json data/businessS.json

step "4/8 Aufgabe 1 (redis-cli, Datenbank 1)"
CONTAINER=$CONTAINER "$PYTHON" scripts/record_session.py cli/aufgabe1.redis "$OUT/aufgabe1_session.txt"

step "5/8 Aufgabe 2: Struktur der Datei (Auszug businessS.json)"
"$PYTHON" analyze_structure.py data/businessS.json > "$OUT/struktur.txt"
head -20 "$OUT/struktur.txt"

step "6/8 Aufgabe 2 a+b: Import von business.json (Datenbank 0)"
"$PYTHON" load_data.py data/business.json --flush | tee "$OUT/import.txt" | tail -4

step "7/8 Aufgabe 2 c+d: Antworten und Autovervollständigung"
"$PYTHON" answers.py > "$OUT/antworten.txt"
printf 'Star\n0\nThe Sti\n1\n\n' | "$PYTHON" autocomplete.py > "$OUT/autocomplete_demo.txt"
sed -n '/Starbucks-Filialen/,$p' "$OUT/antworten.txt" | head -30

step "8/8 Testkette"
TEST_OUTPUT="${OUT#results/}/test_output.txt" "$PYTHON" run_tests.py > "$OUT/test_console.txt" 2>&1 || TEST_FAILED=1
tail -10 "$OUT/test_output.txt"
[ "${TEST_FAILED:-0}" = 0 ] || { echo "Testkette FEHLGESCHLAGEN"; exit 1; }
echo; echo "FERTIG. Ergebnisse in $OUT/"

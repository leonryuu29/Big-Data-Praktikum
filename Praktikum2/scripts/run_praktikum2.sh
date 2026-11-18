#!/usr/bin/env bash
# Praktikum 2 – kompletter Ablauf (Linux/macOS/CI); entspricht Schritt für Schritt scripts/run_praktikum2.ps1
#   Umgebungsvariablen: CONTAINER (Standard CassandraPraktikum2026), PYTHON (Standard python3),
#                       OUT (Ergebnisordner, Standard results/local), IMAGE (Standard cassandra:latest)
set -euo pipefail
cd "$(dirname "$0")/.."
CONTAINER=${CONTAINER:-CassandraPraktikum2026}
IMAGE=${IMAGE:-cassandra:latest}
PYTHON=${PYTHON:-python3}
OUT=${OUT:-results/local}
export PYTHONIOENCODING=utf-8
mkdir -p "$OUT" data out
step() { echo; echo "== $* =="; }

step "1/8 Docker"
docker --version
if [ "${SKIP_RUN:-0}" != 1 ]; then
  if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then docker start "$CONTAINER" >/dev/null
  else docker run --name "$CONTAINER" -p 9042:9042 -e MAX_HEAP_SIZE=1G -e HEAP_NEWSIZE=256M -d "$IMAGE" >/dev/null; fi
fi

step "2/8 Warten auf Cassandra"
for i in $(seq 1 60); do
  docker exec "$CONTAINER" cqlsh -e "SELECT release_version FROM system.local" >/dev/null 2>&1 && break
  sleep 5
done
docker exec "$CONTAINER" cqlsh -e "SHOW VERSION"

step "3/8 Vorbereitung im Container (apt-get, wget, unzip)"
PREP='apt-get update -qq && apt-get -y -qq install unzip nano wget >/dev/null && mkdir -p /home/cassandra && cd /home/cassandra && (test -f ml-latest-small.zip || wget -q https://files.grouplens.org/datasets/movielens/ml-latest-small.zip) && unzip -o -q ml-latest-small.zip'
if ! docker exec "$CONTAINER" bash -c "$PREP"; then
  echo "wget im Container nicht möglich -> Download auf dem Host und docker cp"
  [ -f data/ml-latest-small.zip ] || curl -fsSL -o data/ml-latest-small.zip https://files.grouplens.org/datasets/movielens/ml-latest-small.zip
  docker exec "$CONTAINER" mkdir -p /home/cassandra
  docker cp data/ml-latest-small.zip "$CONTAINER":/home/cassandra/
  docker exec "$CONTAINER" python3 -c "import zipfile;zipfile.ZipFile('/home/cassandra/ml-latest-small.zip').extractall('/home/cassandra')"
fi
rm -rf data/ml-latest-small && docker cp "$CONTAINER":/home/cassandra/ml-latest-small data/
ls -l data/ml-latest-small

step "4/8 Python-Treiber"
"$PYTHON" -c "import cassandra; print('cassandra-driver', cassandra.__version__)"

step "5/8 Aufgabe 1"
docker exec "$CONTAINER" mkdir -p /home/cassandra/cql
docker cp cql/. "$CONTAINER":/home/cassandra/cql/
CONTAINER=$CONTAINER "$PYTHON" scripts/record_session.py cql/aufgabe1_person.cql "$OUT/aufgabe1_session.txt"
tail -8 "$OUT/aufgabe1_session.txt"

step "6/8 Aufgabe 3 a-f"
"$PYTHON" denormalize.py data/ml-latest-small out/denormalized | tee "$OUT/denormalize_output.txt"
docker cp out/denormalized "$CONTAINER":/home/cassandra/
for f in aufgabe3_schema aufgabe3_import aufgabe3_check aufgabe3_query_tables aufgabe3_query_import aufgabe3_queries; do
  echo "  $f.cql"
  CONTAINER=$CONTAINER "$PYTHON" scripts/record_session.py "cql/$f.cql" "$OUT/${f}_session.txt"
done
grep -h "rows imported" "$OUT"/aufgabe3_*import_session.txt

step "7/8 Testkette"
TEST_OUTPUT="${OUT#results/}/test_output.txt" "$PYTHON" run_tests.py > "$OUT/test_console.txt" 2>&1 || TEST_FAILED=1
tail -10 "$OUT/test_output.txt"

step "8/8 Antworten und Tracing"
"$PYTHON" answers.py | tee "$OUT/antworten.txt" | tail -14
"$PYTHON" scripts/trace_queries.py > "$OUT/tracing.txt"
[ "${TEST_FAILED:-0}" = 0 ] || { echo "Testkette FEHLGESCHLAGEN"; exit 1; }
echo; echo "FERTIG. Ergebnisse in $OUT/"

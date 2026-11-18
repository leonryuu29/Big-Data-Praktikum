# Praktikum 2 – kompletter Ablauf unter Windows mit Docker Desktop
#   1 Docker prüfen  2 Cassandra-Container  3 Vorbereitung im Container (bash, apt-get, wget, unzip)
#   4 Python-Pakete  5 Aufgabe 1  6 Aufgabe 3 a-f  7 Testkette  8 Antworten
# Aufruf: Doppelklick auf deploy.bat (Protokoll: results\local\deploy_log.txt)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
$name = "CassandraPraktikum2026"
$out = Join-Path $root "results\local"
New-Item -ItemType Directory -Force -Path $out, "data", "out" | Out-Null

function Native([string]$label, [scriptblock]$cmd) {
    # Externe Programme: stderr nicht als Abbruch werten, Erfolg über den Exit-Code prüfen
    $ErrorActionPreference = "Continue"
    & $cmd
    if ($LASTEXITCODE -ne 0) { throw "$label fehlgeschlagen (Exit-Code $LASTEXITCODE)" }
}

Write-Host "== 1/8 Python und Docker pruefen =="
$python = $null
foreach ($c in @("python", "py")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notlike "*WindowsApps*") { $python = $cmd.Source; break }
}
if (-not $python) { throw "Python nicht gefunden (Haken 'Add python.exe to PATH' bei der Installation)." }
& $python --version
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker nicht gefunden. Bitte Docker Desktop installieren: https://www.docker.com/products/docker-desktop/"
}
$ErrorActionPreference = "Continue"
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    $dd = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dd) { Write-Host "Starte Docker Desktop ..."; Start-Process $dd }
    for ($i = 0; $i -lt 60; $i++) { Start-Sleep 3; docker info *> $null; if ($LASTEXITCODE -eq 0) { break } }
}
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker Engine laeuft nicht. Docker Desktop oeffnen und auf 'Engine running' warten." }
$ErrorActionPreference = "Stop"
docker --version

Write-Host "== 2/8 Cassandra-Container (offizielles Image) =="
$ErrorActionPreference = "Continue"
$exists = docker ps -a --filter "name=^$name$" --format "{{.Names}}"
if ($exists -eq $name) {
    docker start $name | Out-Null
} else {
    Native "docker pull" { docker pull cassandra:latest }
    Native "docker run" { docker run --name $name -p 9042:9042 -e MAX_HEAP_SIZE=1G -e HEAP_NEWSIZE=256M -d cassandra:latest }
}
Write-Host "Warte auf Cassandra (beim ersten Start ca. 1 Minute) ..."
$ready = $false
for ($i = 0; $i -lt 60; $i++) {
    $v = docker exec $name cqlsh -e "SELECT release_version FROM system.local" 2>$null
    if ($LASTEXITCODE -eq 0 -and ($v -match "\d+\.\d+")) { $ready = $true; break }
    Start-Sleep 5
}
if (-not $ready) { throw "Cassandra antwortet nicht. Log: docker logs $name" }
docker exec $name cqlsh -e "SHOW VERSION"
$ErrorActionPreference = "Stop"

Write-Host "== 3/8 Vorbereitung im Container (wie im Aufgabenblatt) =="
$prep = "apt-get update -qq && apt-get -y -qq install unzip nano wget >/dev/null && mkdir -p /home/cassandra && cd /home/cassandra && " +
        "(test -f ml-latest-small.zip || wget -q https://files.grouplens.org/datasets/movielens/ml-latest-small.zip) && " +
        "unzip -o -q ml-latest-small.zip && ls -l ml-latest-small"
$ErrorActionPreference = "Continue"
docker exec $name bash -c $prep
if ($LASTEXITCODE -ne 0) {
    Write-Host "wget im Container nicht moeglich -> Download auf dem Host und docker cp"
    $zip = Join-Path $root "data\ml-latest-small.zip"
    if (-not (Test-Path $zip)) { Native "Download" { curl.exe -L -o $zip https://files.grouplens.org/datasets/movielens/ml-latest-small.zip } }
    Native "docker exec mkdir" { docker exec $name mkdir -p /home/cassandra }
    Native "docker cp zip" { docker cp $zip "${name}:/home/cassandra/ml-latest-small.zip" }
    Native "unzip im Container" { docker exec $name python3 -c "import zipfile;zipfile.ZipFile('/home/cassandra/ml-latest-small.zip').extractall('/home/cassandra')" }
}
# Host-Kopie der CSV-Dateien für Python (Denormalisierung, Integritätstests)
Native "docker cp Daten" { docker cp "${name}:/home/cassandra/ml-latest-small" "data" }
$ErrorActionPreference = "Stop"

Write-Host "== 4/8 Python-Pakete (cassandra-driver) =="
Native "pip install" { & $python -m pip install -q -r requirements.txt }
Native "Treiber" { & $python -c "import cassandra; print('cassandra-driver', cassandra.__version__)" }

Write-Host "== 5/8 Aufgabe 1 (keyspace k1, Tabelle person) =="
Native "docker cp cql" { docker cp "cql\." "${name}:/home/cassandra/cql/" }
Native "Aufgabe 1" { cmd /c "`"$python`" scripts\record_session.py cql\aufgabe1_person.cql results\local\aufgabe1_session.txt" }
Get-Content results\local\aufgabe1_session.txt | Select-Object -Last 20

Write-Host "== 6/8 Aufgabe 3 a-f (Schema, COPY, Abfragetabellen) =="
Native "Denormalisierung" { cmd /c "`"$python`" denormalize.py data\ml-latest-small out\denormalized > results\local\denormalize_output.txt 2>&1" }
Get-Content results\local\denormalize_output.txt
Native "docker cp denormalized" { docker cp "out\denormalized" "${name}:/home/cassandra/" }
foreach ($f in @("aufgabe3_schema", "aufgabe3_import", "aufgabe3_check", "aufgabe3_query_tables", "aufgabe3_query_import", "aufgabe3_queries")) {
    Write-Host "  $f.cql"
    Native $f { cmd /c "`"$python`" scripts\record_session.py cql\$f.cql results\local\${f}_session.txt" }
}

Write-Host "== 7/8 Testkette (Smoke, Unit, Integration, Lokalitaet, Integritaet) =="
$env:TEST_OUTPUT = "local\test_output.txt"
$ErrorActionPreference = "Continue"
cmd /c "`"$python`" run_tests.py > results\local\test_console.txt 2>&1"
$testExit = $LASTEXITCODE
$ErrorActionPreference = "Stop"
Get-Content results\local\test_output.txt | Select-Object -Last 12

Write-Host "== 8/8 Antworten und Tracing =="
Native "answers.py" { cmd /c "`"$python`" answers.py > results\local\antworten.txt 2>&1" }
Native "Tracing" { cmd /c "`"$python`" scripts\trace_queries.py > results\local\tracing.txt 2>&1" }
Get-Content results\local\antworten.txt | Select-Object -Last 16

if ($testExit -ne 0) { throw "Testkette FEHLGESCHLAGEN - siehe results\local\test_output.txt" }
Write-Host ""
Write-Host "FERTIG. Alle Ergebnisse in results\local\ . cqlsh oeffnen: cqlsh.bat"

# Praktikum 1 – kompletter Ablauf unter Windows mit Docker Desktop
#   1 Docker + Redis-Container  2 redis-py  3 Daten  4 Aufgabe 1  5 Struktur  6 Import  7 Antworten  8 Testkette
# Aufruf: Doppelklick auf deploy.bat (Protokoll: results\local\deploy_log.txt)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
$env:PYTHONIOENCODING = "utf-8"
$name = "RedisPraktikum2026"
New-Item -ItemType Directory -Force -Path "results\local", "data" | Out-Null

function Native([string]$label, [scriptblock]$cmd) {
    # Externe Programme: stderr nicht als Abbruch werten, Erfolg über den Exit-Code prüfen
    $ErrorActionPreference = "Continue"
    & $cmd
    if ($LASTEXITCODE -ne 0) { throw "$label fehlgeschlagen (Exit-Code $LASTEXITCODE)" }
}

Write-Host "== 1/8 Docker: Redis-Container =="
$python = $null
foreach ($c in @("python", "py")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source -notlike "*WindowsApps*") { $python = $cmd.Source; break }
}
if (-not $python) { throw "Python nicht gefunden." }
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { throw "Docker nicht gefunden (Docker Desktop installieren)." }
$ErrorActionPreference = "Continue"
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    $dd = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
    if (-not (Test-Path $dd)) { $dd = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\Docker Desktop.exe" }
    if (Test-Path $dd) { Write-Host "Starte Docker Desktop ..."; Start-Process $dd }
    for ($i = 0; $i -lt 60; $i++) { Start-Sleep 3; docker info *> $null; if ($LASTEXITCODE -eq 0) { break } }
}
docker info *> $null
if ($LASTEXITCODE -ne 0) { throw "Docker Engine laeuft nicht. Docker Desktop oeffnen und auf 'Engine running' warten." }
$exists = docker ps -a --filter "name=^$name$" --format "{{.Names}}"
if ($exists -eq $name) { docker start $name | Out-Null }
else { Native "docker run" { docker run --name $name -p 6379:6379 -d redis:latest } }
for ($i = 0; $i -lt 30; $i++) {
    $pong = docker exec $name redis-cli ping 2>$null
    if ($pong -eq "PONG") { break }
    Start-Sleep 1
}
if ($pong -ne "PONG") { throw "Redis antwortet nicht. Log: docker logs $name" }
docker exec $name redis-cli INFO server | Select-String "redis_version"
$ErrorActionPreference = "Stop"

Write-Host "== 2/8 Python-Paket redis-py =="
Native "pip install" { & $python -m pip install -q -r requirements.txt }
Native "redis-py" { & $python -c "import redis; print('redis-py', redis.__version__)" }

Write-Host "== 3/8 Daten =="
if (-not (Test-Path "data\business.json") -or -not (Test-Path "data\businessS.json")) {
    & (Join-Path $PSScriptRoot "download_data.ps1")
}
Get-ChildItem data -Filter *.json | Format-Table Name, Length

Write-Host "== 4/8 Aufgabe 1 (redis-cli, Datenbank 1) =="
Native "Aufgabe 1" { cmd /c "`"$python`" scripts\record_session.py cli\aufgabe1.redis results\local\aufgabe1_session.txt" }

Write-Host "== 5/8 Aufgabe 2: Struktur der Datei =="
Native "Struktur" { cmd /c "`"$python`" analyze_structure.py data\businessS.json > results\local\struktur.txt 2>&1" }
Get-Content results\local\struktur.txt | Select-Object -First 20

Write-Host "== 6/8 Aufgabe 2 a+b: Import von business.json =="
Native "Import" { cmd /c "`"$python`" load_data.py data\business.json --flush > results\local\import.txt 2>&1" }
Get-Content results\local\import.txt | Select-Object -Last 4

Write-Host "== 7/8 Aufgabe 2 c+d: Antworten und Autovervollstaendigung =="
Native "answers.py" { cmd /c "`"$python`" answers.py > results\local\antworten.txt 2>&1" }
Set-Content -Path "results\local\demo_input.txt" -Value "Star`n0`nThe Sti`n1`n`n" -NoNewline -Encoding ascii
Native "Demo" { cmd /c "`"$python`" autocomplete.py < results\local\demo_input.txt > results\local\autocomplete_demo.txt 2>&1" }
Get-Content results\local\antworten.txt | Select-Object -Last 24

Write-Host "== 8/8 Testkette (Smoke, Unit, Integration, Effizienz, Integritaet) =="
$env:TEST_OUTPUT = "local\test_output.txt"
$ErrorActionPreference = "Continue"
cmd /c "`"$python`" run_tests.py > results\local\test_console.txt 2>&1"
$testExit = $LASTEXITCODE
$ErrorActionPreference = "Stop"
Get-Content results\local\test_output.txt | Select-Object -Last 10
if ($testExit -ne 0) { throw "Testkette FEHLGESCHLAGEN - siehe results\local\test_output.txt" }
Write-Host ""
Write-Host "FERTIG. Ergebnisse in results\local\ . Interaktiv: redis-cli.bat und autocomplete.bat"

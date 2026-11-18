@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist results\local mkdir results\local
echo Praktikum 2 - Deployment und Tests (Protokoll: results\local\deploy_log.txt)
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Transcript -Path 'results\local\deploy_log.txt' -Force | Out-Null; try { & '.\scripts\run_praktikum2.ps1' } catch { Write-Host ('FEHLER: ' + $_) } finally { Stop-Transcript | Out-Null }"
echo.
pause

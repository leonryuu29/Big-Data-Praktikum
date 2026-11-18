@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set TEST_OUTPUT=local\test_output.txt
if not exist results\local mkdir results\local
docker start CassandraPraktikum2026 >nul 2>&1
python run_tests.py
pause

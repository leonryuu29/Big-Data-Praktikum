@echo off
chcp 65001 >nul
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
docker start RedisPraktikum2026 >nul 2>&1
python autocomplete.py
pause

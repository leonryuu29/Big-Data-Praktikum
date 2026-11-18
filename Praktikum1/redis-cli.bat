@echo off
chcp 65001 >nul
rem Aufgabe 1 interaktiv: redis-cli im Container, Datenbank 1 (die Yelp-Daten liegen in Datenbank 0)
docker start RedisPraktikum2026 >nul 2>&1
docker exec -it RedisPraktikum2026 redis-cli -n 1

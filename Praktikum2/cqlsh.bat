@echo off
chcp 65001 >nul
docker start CassandraPraktikum2026 >nul 2>&1
docker exec -it CassandraPraktikum2026 cqlsh

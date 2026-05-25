@echo off
REM Worker启动脚本 - 持续运行版

echo ============================================================
echo MyRAG ARQ Worker (Continuous Mode)
echo ============================================================
echo.

cd /d %~dp0

set PYTHONIOENCODING=utf-8
set PYTHONPATH=%~dp0

echo Redis: 192.168.137.13:6379
echo Job submitted to queue: YES
echo.
echo Starting worker...
echo Worker will process pending jobs and keep running.
echo Press Ctrl+C to stop.
echo.

python -m arq app.tasks.WorkerSettings

pause
@echo off
REM 使用系统Python启动 ARQ Worker（备选方案）

echo ============================================================
echo MyRAG ARQ Worker 启动（系统Python）
echo ============================================================

cd /d %~dp0

REM 设置环境变量
set PYTHONIOENCODING=utf-8
set PYTHONPATH=%~dp0

echo.
echo Redis: 192.168.137.13:6379
echo 启动 Worker...
echo.

REM 使用系统Python启动worker（前台运行）
python -m arq app.tasks.WorkerSettings

pause
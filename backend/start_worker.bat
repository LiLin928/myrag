@echo off
REM 启动 ARQ Worker - Windows 批处理脚本

echo ============================================================
echo MyRAG ARQ Worker 启动
echo ============================================================

cd /d %~dp0

REM 检查虚拟环境
if not exist ".venv\Scripts\python.exe" (
    echo 错误: 虚拟环境不存在，请先运行: python -m venv .venv
    exit /b 1
)

REM 设置环境变量（解决Windows asyncio问题）
set PYTHONIOENCODING=utf-8

echo.
echo Redis: 192.168.137.13:6379
echo 启动 Worker...
echo.

REM 启动worker（前台运行，可以看到输出）
.venv\Scripts\python.exe -m arq app.tasks.WorkerSettings

pause
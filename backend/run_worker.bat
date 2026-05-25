@echo off
REM MyRAG ARQ Worker 启动脚本 - Windows

echo ============================================================
echo MyRAG ARQ Worker 启动
echo ============================================================
echo.

cd /d %~dp0

REM 设置Python路径（优先使用系统Python）
set PYTHON_EXE=python
if exist ".venv\Scripts\python.exe" set PYTHON_EXE=.venv\Scripts\python.exe

REM 设置编码
set PYTHONIOENCODING=utf-8
set PYTHONPATH=%~dp0

echo 使用Python: %PYTHON_EXE%
echo.
echo 启动Worker（前台运行，按Ctrl+C停止）...
echo.

REM 启动增强版Worker脚本
%PYTHON_EXE% start_worker_enhanced.py

pause
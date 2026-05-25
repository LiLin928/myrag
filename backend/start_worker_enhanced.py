"""启动 ARQ Worker - 增强版

功能:
- 自动检查依赖
- 前台运行,显示实时日志
- 支持Windows/Linux/Mac
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Windows asyncio 支持
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def check_dependencies():
    """检查必要的依赖库"""
    print("检查依赖库...")

    missing = []

    # ARQ
    try:
        import arq
        print("  ✓ arq")
    except ImportError:
        missing.append("arq")
        print("  ✗ arq (缺失)")

    # Redis
    try:
        import redis
        print("  ✓ redis")
    except ImportError:
        missing.append("redis")
        print("  ✗ redis (缺失)")

    # DOCX 解析
    try:
        import docx
        print("  ✓ python-docx")
    except ImportError:
        missing.append("python-docx")
        print("  ✗ python-docx (缺失)")

    # PPTX 解析
    try:
        import pptx
        print("  ✓ python-pptx")
    except ImportError:
        missing.append("python-pptx")
        print("  ✗ python-pptx (缺失)")

    # Excel 解析
    try:
        import openpyxl
        print("  ✓ openpyxl")
    except ImportError:
        missing.append("openpyxl")
        print("  ✗ openpyxl (缺失)")

    # HTML 解析
    try:
        import bs4
        print("  ✓ beautifulsoup4")
    except ImportError:
        missing.append("beautifulsoup4")
        print("  ✗ beautifulsoup4 (缺失)")

    if missing:
        print(f"\n缺少依赖库: {', '.join(missing)}")
        print("\n请运行以下命令安装:")
        print(f"  pip install {' '.join(missing)}")
        print("\n或者使用系统Python:")
        print(f"  python -m pip install {' '.join(missing)}")
        return False

    print("\n所有依赖已安装 ✓")
    return True

def main():
    """启动 Worker"""
    print("=" * 60)
    print("MyRAG ARQ Worker 启动")
    print("=" * 60)
    print()

    # 检查依赖
    if not check_dependencies():
        sys.exit(1)

    print()
    print("Redis配置:")
    print(f"  Host: 192.168.137.13")
    print(f"  Port: 6379")
    print(f"  Password: lilin1992")
    print()
    print("Worker配置:")
    print(f"  Max Jobs: 10")
    print(f"  Job Timeout: 600秒 (10分钟)")
    print()
    print("=" * 60)
    print("启动中... (按 Ctrl+C 停止)")
    print("=" * 60)
    print()

    # 导入Worker配置
    try:
        from app.tasks import WorkerSettings
        from arq import run_worker

        # 启动worker
        run_worker(WorkerSettings)

    except KeyboardInterrupt:
        print("\n\nWorker已停止")
    except Exception as e:
        print(f"\n启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
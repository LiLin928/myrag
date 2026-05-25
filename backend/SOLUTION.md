# 文档解析问题 - 解决方案

## 问题诊断结果

### 根本原因
**ARQ Worker 进程未启动** - 这是文档解析卡在"等待解析"状态的根本原因。

**影响**:
- 文档状态停留在 `parsing`, Progress=0
- Redis队列中有等待任务，但无人处理
- 即使解析库已实现，也无法执行

### 已完成的代码修复

1. ✅ **实现真实的 docx 解析** (`unstructured_extractor.py`)
   - 使用 `python-docx` 库提取所有段落
   - 提取表格并转换为 Markdown 格式
   - 检测段落类型（标题、正文、列表）

2. ✅ **实现真实的 PDF 解析** (`mineru_extractor.py`)
   - 调用 MinerU API (http://192.168.137.13:8888)
   - 提取文本、表格、公式
   - 失败时返回错误信息

3. ✅ **安装解析库**
   - python-docx 1.2.0 ✓
   - python-pptx, openpyxl, beautifulsoup4 ✓

4. ✅ **创建 Worker 启动脚本**
   - `run_worker.bat` - Windows 启动脚本
   - `start_worker_enhanced.py` - 增强版Python脚本
   - 自动检查依赖和配置

5. ✅ **更新 requirements.txt**
   - 添加 Office 文档解析库

---

## 立即执行的操作

### 1. 启动 ARQ Worker

**方式A - Windows CMD (推荐)**:
```cmd
cd D:\4-MyProject\MyRAG01\myrag-app\backend
run_worker.bat
```

**方式B - 手动启动**:
```cmd
cd D:\4-MyProject\MyRAG01\myrag-app\backend
python start_worker_enhanced.py
```

### 2. 验证 Worker 启动成功

启动后应该看到:

```
============================================================
MyRAG ARQ Worker 启动
============================================================

检查依赖库...
  ✓ arq
  ✓ redis
  ✓ python-docx
  ✓ python-pptx
  ✓ openpyxl
  ✓ beautifulsoup4

所有依赖已安装 ✓

Redis配置:
  Host: 192.168.137.13
  Port: 6379
  Password: lilin1992

Worker配置:
  Max Jobs: 10
  Job Timeout: 600秒 (10分钟)

============================================================
启动中... (按 Ctrl+C 停止)
============================================================

ARQ Worker started
Job started: 197b0202b3594bb985f6a61ec8f6958d
```

### 3. 查看解析进度

访问知识库页面:
```
http://localhost:3000/knowledge/4f761b48-d7c0-4b0d-b042-a0db528bde24
```

文档状态变化:
- `parsing` → `parsed` → `indexed`

---

## 常见问题

### Q: Worker启动失败，提示缺少库

**A**: 使用系统Python安装缺失的库:
```bash
python -m pip install arq redis python-docx python-pptx openpyxl beautifulsoup4 lxml
```

### Q: Worker启动后文档仍然卡住

**A**: 检查以下几点:
1. Redis连接是否正常 (`192.168.137.13:6379`)
2. Worker终端是否有错误日志
3. 文档job_id是否在队列中

### Q: docx 解析失败

**A**: 确保:
- 文件是有效docx格式（不是.doc）
- 文件未加密或损坏
- python-docx已正确安装

### Q: MinerU API 连接失败

**A**: MinerU服务配置:
- 地址: `http://192.168.137.13:8888`
- 如不可用,系统会返回错误信息，不影响docx解析

---

## 文件清单

### 启动脚本
- `run_worker.bat` - Windows启动脚本（双击运行）
- `start_worker_enhanced.py` - Python启动脚本
- `start_worker_system.bat` - 备选启动脚本

### 解析器实现
- `app/rag/extractor/unstructured_extractor.py` - DOCX/PPTX/XLSX解析
- `app/rag/extractor/mineru_extractor.py` - PDF解析(MinerU API)
- `app/services/multimodal/mineru_client.py` - MinerU客户端

### 配置文件
- `requirements.txt` - 已添加解析库依赖
- `.env` - Redis和MinerU配置

### 说明文档
- `QUICK_START.md` - 快速启动指南
- `SOLUTION.md` - 本文档

---

## 下一步

1. ✅ 双击运行 `run_worker.bat`
2. ⏳ 等待Worker处理队列中的任务
3. ✅ 刷新知识库页面查看进度
4. ✅ 解析完成后可搜索文档内容

**预计处理时间**:
- DOCX文件: 1-3分钟
- PDF文件: 3-10分钟（取决于MinerU服务）

---

**Created**: 2026-05-22
**Author**: Claude Code Debug Session
# MyRAG Backend - 快速启动指南

## 问题诊断结果

### 根本原因
1. **ARQ Worker 进程未启动** - 文档解析任务提交到Redis后无人处理
2. **解析库未实现** - UnstructuredExtractor 只是占位代码
3. **解析库未安装** - python-docx 等库未安装

### 已完成的修复
1. ✅ 实现真实的 docx 解析逻辑（使用 python-docx）
2. ✅ 支持表格提取并转换为 Markdown
3. ✅ 创建 Worker 启动脚本
4. ✅ 更新 requirements.txt

---

## 启动步骤

### 1. 安装依赖库

在 backend 目录下运行：

```bash
# 方式1：使用 uv（推荐）
uv sync

# 方式2：使用 pip
pip install python-docx python-pptx openpyxl beautifulsoup4 lxml
```

### 2. 启动 ARQ Worker

**重要**: Worker 必须启动才能处理文档！

**Windows CMD**:
```bash
cd D:\4-MyProject\MyRAG01\myrag-app\backend
start_worker.bat
```

**PowerShell**:
```powershell
cd D:\4-MyProject\MyRAG01\myrag-app\backend
.venv\Scripts\python.exe start_worker.py
```

**Linux/Mac**:
```bash
cd myrag-app/backend
python start_worker.py
```

### 3. 验证 Worker 启动成功

启动后应该看到类似输出：

```
============================================================
MyRAG ARQ Worker
============================================================
Redis Host: 192.168.137.13
Redis Port: 6379
Max Jobs: 10
Job Timeout: 600s
============================================================

Starting worker...
ARQ Worker started
```

### 4. 检查文档解析进度

访问知识库页面，文档状态应该从 `parsing` 变为 `parsed` 或 `indexed`。

---

## 解析库功能说明

### python-docx（Word 文档）
- ✅ 提取所有段落文本
- ✅ 提取表格并转换为 Markdown
- ✅ 检测段落类型（标题、正文、列表）
- ✅ 保留样式信息

### python-pptx（PowerPoint）
- ✅ 按幻灯片提取内容
- ✅ 提取所有文本形状
- ✅ 保留幻灯片编号

### openpyxl（Excel）
- ✅ 提取所有工作表
- ✅ 转换为 Markdown 表格
- ✅ 支持多Sheet

### beautifulsoup4（HTML）
- ✅ 提取正文内容
- ✅ 移除 script/style 标签
- ✅ 按段落分割

---

## 常见问题

### Q: Worker启动失败，提示 "ModuleNotFoundError: No module named 'arq'"
**A**: 需要先安装 ARQ 和 Redis 连接库：
```bash
pip install arq redis
```

### Q: Worker启动成功，但文档仍然卡在 parsing 状态
**A**: 检查以下几点：
1. Redis 连接是否正常（192.168.137.13:6379）
2. 查看终端是否有错误日志
3. 检查文档job_id是否存在（使用 `redis-cli` 查看队列）

### Q: python-docx 解析失败
**A**: 确保：
1. 文件是有效的 docx 格式（不是旧版 .doc）
2. 文件未被加密或损坏
3. python-docx 已正确安装

---

## 下一步

1. 安装依赖库
2. 启动 ARQ Worker（保持前台运行，可以看到日志）
3. 刷新知识库页面查看解析进度
4. 解析完成后可以搜索文档内容

---

**Created**: 2026-05-22
**Author**: Claude Code Debug Session
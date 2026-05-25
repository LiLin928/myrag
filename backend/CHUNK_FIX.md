# 分块问题修复说明

## 根因诊断

**根本问题**: Extractor接收的是MinIO路径，但需要本地文件才能解析。

**影响**:
- 文档状态更新为 `indexed`，但实际解析失败
- chunk_count=0，数据库中没有分块
- Extractor无法读取MinIO对象路径

## 已完成的修复

### 1. 添加文件下载逻辑
- ✅ 从MinIO下载文件内容到临时目录
- ✅ 使用本地临时文件路径调用Extractor
- ✅ 处理完成后清理临时文件

### 2. 修复属性访问方式
- ✅ ContentBlock继承自dict，改用字典访问方式
- ✅ 支持同时处理dict和object两种格式

### 3. 添加详细进度反馈
- ✅ 下载进度："从MinIO下载文件" → "文件下载完成"
- ✅ 解析进度：显示使用的Extractor类型
- ✅ 错误处理：下载失败时返回错误信息

---

## 重启 Worker 应用修复

**步骤**:

### 1. 停止当前Worker

如果Worker正在运行，按 `Ctrl+C` 停止。

### 2. 重新启动Worker

```cmd
cd D:\4-MyProject\MyRAG01\myrag-app\backend
run_worker.bat
```

或者双击运行 `run_worker.bat`

### 3. 重新解析文档

**方式A - 删除并重新上传**:
- 删除知识库中的当前文档
- 重新上传docx文件
- 点击"解析"按钮

**方式B - 直接重新解析**:
- 在知识库页面点击"解析"按钮（如果状态允许）

---

## 预期效果

重启Worker后，解析流程：

1. **下载文件** (5-10%)
   - 从MinIO下载文件到临时目录
   - 显示文件大小

2. **解析文档** (10-30%)
   - 使用 `UnstructuredExtractor` (docx文件)
   - 提取段落和表格

3. **分块处理** (40-60%)
   - 创建分块记录到数据库
   - chunk_count > 0

4. **向量化** (70-90%)
   - 调用embedding API
   - 存储向量到数据库

5. **完成** (100%)
   - 状态更新为 `indexed`
   - vectorized_count > 0

---

## 查看分块数据

解析完成后，可以：

1. **前端查看**: 知识库详情页 → 点击文档 → 查看分块列表

2. **数据库查询**:
```sql
SELECT id, clause_id, content, clause_type, page_number
FROM document_chunks
WHERE document_id = '1ada5608-8b7c-4359-a1ec-b5a77de79688'
ORDER BY clause_id;
```

---

## 修复的文件

- `app/tasks/document_tasks.py` - 添加文件下载和清理逻辑
- 已修复的函数：`parse_knowledge_document`

---

**Created**: 2026-05-22
**Author**: Claude Code Debug Session
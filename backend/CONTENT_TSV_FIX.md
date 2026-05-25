# content_tsv 类型错误修复

## 错误诊断

**错误信息**:
```
(sqlalchemy.dialects.postgresql.asyncpg.ProgrammingError)
<class 'asyncpg.exceptions.DatatypeMismatchError'>:
column "content_tsv" is of type tsvector
```

**根本原因**:
- 数据库中 `content_tsv` 列是 `tsvector` 类型（PostgreSQL全文搜索）
- SQLAlchemy模型中定义为 `Column(Text, nullable=True)`
- 插入数据时类型冲突

**触发器机制**:
数据库已有自动填充机制：
```sql
CREATE TRIGGER trigger_update_document_chunk_tsv
BEFORE INSERT OR UPDATE ON document_chunks
FOR EACH ROW
EXECUTE FUNCTION update_document_chunk_tsv()

-- 函数定义：
NEW.content_tsv := to_tsvector('simple',
    COALESCE(NEW.content, '') || ' ' ||
    COALESCE(NEW.chunk_metadata::text, ''));
```

---

## 已完成的修复

### 1. 移除模型中的 content_tsv 定义

**修改文件**: `app/models/document.py`

**修改内容**:
```python
# 旧代码（错误）:
content_tsv = Column(Text, nullable=True)  # tsvector for fulltext search

# 新代码（正确）:
# content_tsv 由数据库触发器自动填充，不需要在模型中定义
# content_tsv = Column(Text, nullable=True)  # 移除：这会与触发器冲突
```

**效果**:
- SQLAlchemy不再尝试手动设置 `content_tsv` 的值
- 触发器会自动根据 `content` 和 `chunk_metadata` 生成 tsvector
- 类型冲突问题解决

---

## 重启 Worker 应用修复

**步骤**:

### 1. 停止当前Worker

按 `Ctrl+C` 停止正在运行的Worker

### 2. 重启Worker

```cmd
cd D:\4-MyProject\MyRAG01\myrag-app\backend
run_worker.bat
```

### 3. 重新解析文档

在知识库页面重新上传并解析docx文件

---

## 预期效果

修复后的解析流程：

1. ✅ **下载文件** - 从MinIO下载到本地
2. ✅ **解析文档** - 使用python-docx提取内容
3. ✅ **创建分块** - **成功插入到数据库**
4. ✅ **触发器工作** - 自动填充 `content_tsv` (tsvector)
5. ✅ **向量化** - 调用embedding API
6. ✅ **完成** - chunk_count > 0

---

## 验证修复

解析完成后，可以查询验证：

```sql
-- 查看分块数据
SELECT id, clause_id, content, content_length
FROM document_chunks
WHERE document_id = 'xxx'
ORDER BY created_at;

-- 查看全文搜索是否工作
SELECT id, clause_id, content_tsv
FROM document_chunks
WHERE document_id = 'xxx'
LIMIT 5;

-- 测试全文搜索
SELECT clause_id, content
FROM document_chunks
WHERE content_tsv @@ to_tsquery('simple', '关键词')
ORDER BY created_at;
```

---

## 技术要点

**为什么不需要在模型中定义 content_tsv**:

1. PostgreSQL触发器在INSERT/UPDATE前自动填充
2. 触发器使用 `to_tsvector()` 函数生成正确类型
3. SQLAlchemy的 Text 类型与 tsvector 不兼容
4. 模型中定义会尝试手动赋值，导致类型错误

**最佳实践**:
- 服务器自动生成的列，不需要在ORM模型中定义
- 特别注意 PostgreSQL 的特殊类型（tsvector, geometry等）
- 使用触发器/存储过程处理复杂类型转换

---

## 相关文件

- `app/models/document.py` - DocumentChunk模型（已修复）
- `alembic/versions/016_add_fulltext_search.py` - 全文搜索迁移脚本
- `app/tasks/document_tasks.py` - 文档解析任务（已修复MinIO下载）

---

**Created**: 2026-05-22
**Author**: Claude Code Debug Session
**Issue**: content_tsv类型不匹配导致插入失败
**Status**: ✅ 已修复
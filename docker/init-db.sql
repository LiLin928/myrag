-- 启用 PGVector 扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 创建向量索引（示例配置）
-- 后续会通过 Alembic 迁移创建详细表结构

-- 设置默认搜索路径
SET search_path TO public;

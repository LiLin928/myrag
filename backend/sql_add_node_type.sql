-- 添加 workflow_execution_logs 表缺少的 node_type 列
ALTER TABLE workflow_execution_logs ADD COLUMN IF NOT EXISTS node_type VARCHAR(32);

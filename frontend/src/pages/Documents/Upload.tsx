import { useState, useCallback } from 'react'
import { Upload, Select, Button, Card, message, Space, Typography, Alert } from 'antd'
import { InboxOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useEffect } from 'react'
import { useKnowledgeStore } from '../../stores/knowledgeStore'
import { useDocumentStore } from '../../stores/documentStore'
import { useDocumentProgress } from '../../hooks/useWebSocket'
import { DocumentProgressTracker } from '../../components/Progress'
import type { Document as DocumentModel } from '../../types/models'

const { Text } = Typography

export function DocumentUpload() {
  const navigate = useNavigate()
  const { knowledgeBases, fetchList } = useKnowledgeStore()
  const { upload, uploadProgress } = useDocumentStore()
  const [selectedKb, setSelectedKb] = useState<string>()
  const [file, setFile] = useState<File>()
  const [uploading, setUploading] = useState(false)
  const [documentId, setDocumentId] = useState<string>()
  const [jobId, setJobId] = useState<string>()

  // 获取用户 ID（从 localStorage）
  const userId = localStorage.getItem('user_id') || ''

  // WebSocket 进度追踪
  const { isConnected, subscribeDocument, getTaskState } = useDocumentProgress(userId, documentId)

  // 当前任务状态
  const taskState = jobId ? getTaskState(jobId) : null

  useEffect(() => {
    fetchList()
  }, [])

  // 上传完成后订阅进度
  const handleUploadComplete = useCallback((docId: string, job: string) => {
    setDocumentId(docId)
    setJobId(job)
    subscribeDocument(docId)
  }, [subscribeDocument])

  const handleUpload = async () => {
    if (!file || !selectedKb) {
      message.warning('请选择知识库和文件')
      return
    }
    try {
      setUploading(true)
      const result = await upload(file, selectedKb)

      // 设置 document ID 和 job ID，开始追踪进度
      const doc = result as DocumentModel
      if (doc.id && doc.job?.job_id) {
        handleUploadComplete(doc.id, doc.job.job_id)
      }

      // 不立即跳转，等待处理完成
      // message.success('上传成功，开始处理...')
    } catch {
      message.error('上传失败')
      setUploading(false)
    }
  }

  // 处理完成后跳转
  useEffect(() => {
    if (taskState?.status === 'completed') {
      message.success('文档处理完成')
      // 3秒后跳转
      setTimeout(() => {
        navigate('/documents')
      }, 3000)
    }
    if (taskState?.status === 'failed') {
      message.error(`处理失败: ${taskState.error}`)
      setUploading(false)
    }
  }, [taskState?.status, taskState?.error, navigate])

  // WebSocket 连接状态提示
  const wsStatusIndicator = isConnected ? (
    <Text type="success">WebSocket 已连接</Text>
  ) : (
    <Text type="warning">WebSocket 未连接</Text>
  )

  return (
    <Card title="上传文档" extra={wsStatusIndicator}>
      {/* 知识库选择 */}
      <div style={{ marginBottom: 16 }}>
        <label style={{ marginRight: 8 }}>选择知识库：</label>
        <Select
          style={{ width: 200 }}
          placeholder="选择知识库"
          value={selectedKb}
          onChange={setSelectedKb}
          options={knowledgeBases.map((kb) => ({ value: kb.id, label: kb.name }))}
        />
      </div>

      {/* 文件上传区域 */}
      <Upload.Dragger
        beforeUpload={(file) => {
          setFile(file)
          return false
        }}
        maxCount={1}
        accept=".txt,.md,.pdf,.docx,.xlsx,.pptx"
        disabled={uploading || taskState?.status === 'running'}
      >
        <p className="ant-upload-drag-icon">
          <InboxOutlined />
        </p>
        <p className="ant-upload-text">点击或拖拽文件到此区域上传</p>
        <p className="ant-upload-hint">支持 txt, md, pdf, docx, xlsx, pptx 格式</p>
      </Upload.Dragger>

      {/* 文件上传进度 */}
      {uploading && uploadProgress > 0 && !taskState && (
        <div style={{ marginTop: 16 }}>
          <Text type="secondary">文件上传进度：</Text>
          <div>{uploadProgress}%</div>
        </div>
      )}

      {/* 文档处理进度 */}
      {taskState && taskState.status !== 'idle' && (
        <div style={{ marginTop: 16 }}>
          <Alert
            type={taskState.status === 'running' ? 'info' : taskState.status === 'completed' ? 'success' : 'error'}
            message={
              taskState.status === 'completed' ? '文档处理完成' :
              taskState.status === 'failed' ? '文档处理失败' :
              '正在处理文档...'
            }
            icon={
              taskState.status === 'completed' ? <CheckCircleOutlined /> :
              taskState.status === 'failed' ? <CloseCircleOutlined /> :
              undefined
            }
            showIcon
          />
          <DocumentProgressTracker
            status={{
              status: taskState.status,
              stage: taskState.stage,
              progress: taskState.progress,
              message: taskState.message,
              error: taskState.error,
            }}
            showDetails
          />
        </div>
      )}

      {/* 操作按钮 */}
      <div style={{ marginTop: 16 }}>
        <Space>
          <Button
            onClick={() => navigate('/documents')}
            disabled={taskState?.status === 'running'}
          >
            取消
          </Button>
          <Button
            type="primary"
            onClick={handleUpload}
            disabled={!file || !selectedKb || uploading || taskState?.status === 'running'}
            loading={uploading && !taskState}
          >
            上传
          </Button>
        </Space>
      </div>
    </Card>
  )
}
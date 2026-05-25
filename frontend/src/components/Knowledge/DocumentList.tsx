import { useEffect, useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Table, Button, Space, Progress, Tag, Popconfirm, message, Upload, Spin } from 'antd'
import { UploadOutlined, PlayCircleOutlined, DeleteOutlined, ReloadOutlined, LoadingOutlined, EyeOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd'
import { useKnowledgeStore } from '../../stores/knowledgeStore'
import { KnowledgeDocument } from '../../types/models'

interface DocumentListProps {
  knowledgeId: string
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function getStatusColor(status: KnowledgeDocument['status']): string {
  const colorMap: Record<KnowledgeDocument['status'], string> = {
    pending: 'default',
    parsing: 'processing',
    parsed: 'cyan',
    indexing: 'processing',
    indexed: 'success',
    vectorizing: 'processing',
    vectorized: 'success',
    completed: 'success',
    compiled: 'success',
    failed: 'error',
  }
  return colorMap[status] || 'default'
}

function getStatusText(status: KnowledgeDocument['status']): string {
  const textMap: Record<KnowledgeDocument['status'], string> = {
    pending: '待处理',
    parsing: '解析中',
    parsed: '已解析',
    indexing: '索引中',
    indexed: '已完成',
    vectorizing: '向量化中',
    vectorized: '已向量化',
    completed: '已完成',
    compiled: '已编译',
    failed: '失败',
  }
  return textMap[status] || status
}

// 判断是否是处理中的状态（需要轮询）
function isProcessingStatus(status: KnowledgeDocument['status']): boolean {
  return ['parsing', 'parsed', 'indexing', 'vectorizing'].includes(status)
}

export function DocumentList({ knowledgeId }: DocumentListProps) {
  const navigate = useNavigate()
  const { currentDocuments, loading, fetchDocuments, uploadDocument, parseDocument, deleteDocument } = useKnowledgeStore()
  const [polling, setPolling] = useState(false)
  const pollingRef = useRef<number | null>(null)

  // 初始加载
  useEffect(() => {
    if (knowledgeId) {
      fetchDocuments(knowledgeId)
    }
  }, [knowledgeId, fetchDocuments])

  // 自动轮询处理中的文档
  useEffect(() => {
    const hasProcessing = currentDocuments.some(doc => isProcessingStatus(doc.status))

    if (hasProcessing && !pollingRef.current) {
      setPolling(true)
      // 每 3 秒刷新一次
      pollingRef.current = window.setInterval(() => {
        fetchDocuments(knowledgeId)
      }, 3000)
    } else if (!hasProcessing && pollingRef.current) {
      // 没有处理中的文档时停止轮询
      clearInterval(pollingRef.current)
      pollingRef.current = null
      setPolling(false)
    }

    return () => {
      if (pollingRef.current) {
        clearInterval(pollingRef.current)
        pollingRef.current = null
      }
    }
  }, [currentDocuments, knowledgeId, fetchDocuments])

  const handleUpload = async (file: File) => {
    try {
      await uploadDocument(knowledgeId, file)
      message.success('文件上传成功')
      // 上传后刷新列表
      fetchDocuments(knowledgeId)
    } catch (error: any) {
      message.error(error.message || '上传失败')
    }
    return false
  }

  const uploadProps: UploadProps = {
    beforeUpload: handleUpload,
    showUploadList: false,
    multiple: true,
  }

  const handleParse = async (documentId: string) => {
    try {
      await parseDocument(knowledgeId, documentId)
      message.success('已开始解析文档')
      // 解析开始后刷新列表
      fetchDocuments(knowledgeId)
    } catch (error: any) {
      message.error(error.message || '解析失败')
    }
  }

  const handleDelete = async (documentId: string) => {
    try {
      await deleteDocument(knowledgeId, documentId)
      message.success('文档已删除')
    } catch (error: any) {
      message.error(error.message || '删除失败')
    }
  }

  const handleRefresh = () => {
    fetchDocuments(knowledgeId)
  }

  const columns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      ellipsis: true,
    },
    {
      title: '类型',
      dataIndex: 'file_type',
      key: 'file_type',
      width: 100,
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      width: 100,
      render: (size: number) => formatFileSize(size),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: KnowledgeDocument['status']) => (
        <Tag color={getStatusColor(status)}>{getStatusText(status)}</Tag>
      ),
    },
    {
      title: '进度',
      dataIndex: 'processing_progress',
      key: 'processing_progress',
      width: 150,
      render: (_: number, record: KnowledgeDocument) => {
        if (record.status === 'pending' || record.status === 'failed') {
          return '-'
        }
        return (
          <Progress
            percent={record.processing_progress || 0}
            size="small"
            status={record.status === 'parsing' || record.status === 'indexing' ? 'active' : 'success'}
          />
        )
      },
    },
    {
      title: '分块数',
      dataIndex: 'chunk_count',
      key: 'chunk_count',
      width: 80,
      render: (count: number) => count || '-',
    },
    {
      title: '向量数',
      dataIndex: 'vectorized_count',
      key: 'vectorized_count',
      width: 80,
      render: (count: number) => count || '-',
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 160,
      render: (date: string) => new Date(date).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      render: (_: any, record: KnowledgeDocument) => (
        <Space size="small" direction="vertical" style={{ width: '100%' }}>
          {/* 查看分块按钮 - 显示在已完成状态 */}
          {(record.status === 'indexed' || record.status === 'completed' || record.status === 'vectorized') && (
            <Button
              type="link"
              size="small"
              icon={<EyeOutlined />}
              onClick={() => navigate(`/knowledge/${knowledgeId}/documents/${record.id}/chunks`)}
              style={{ padding: '0 4px' }}
            >
              查看分块
            </Button>
          )}
          {/* 解析按钮 */}
          {record.status === 'pending' && (
            <Button
              type="link"
              size="small"
              icon={<PlayCircleOutlined />}
              onClick={() => handleParse(record.id)}
              style={{ padding: '0 4px' }}
            >
              解析
            </Button>
          )}
          {/* 重新解析按钮 */}
          {(record.status === 'indexed' || record.status === 'failed') && (
            <Button
              type="link"
              size="small"
              icon={<ReloadOutlined />}
              onClick={() => handleParse(record.id)}
              style={{ padding: '0 4px' }}
            >
              重新解析
            </Button>
          )}
          {/* 删除按钮 */}
          <Popconfirm
            title="确认删除"
            description="确定要删除此文档吗？"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" size="small" danger icon={<DeleteOutlined />} style={{ padding: '0 4px' }}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
        <Upload {...uploadProps}>
          <Button icon={<UploadOutlined />}>上传文档</Button>
        </Upload>
        <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
          刷新
        </Button>
        {polling && (
          <Spin indicator={<LoadingOutlined spin />} tip="自动更新中...">
            <span style={{ marginLeft: 8 }}>自动更新中...</span>
          </Spin>
        )}
      </div>
      <Table
        columns={columns}
        dataSource={currentDocuments}
        rowKey="id"
        loading={loading}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
      />
    </div>
  )
}
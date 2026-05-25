import { useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Descriptions, List, Button, Tag, Spin } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { useDocumentStore } from '../../stores/documentStore'

const statusColors: Record<string, string> = {
  pending: 'default',
  processing: 'processing',
  completed: 'success',
  failed: 'error',
}

export function DocumentDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { currentDocument, chunks, loading, fetchOne, fetchChunks } = useDocumentStore()

  useEffect(() => {
    if (id) {
      fetchOne(id)
      fetchChunks(id)
    }
  }, [id])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  if (!currentDocument) return <div>文档不存在</div>

  return (
    <Card>
      <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/documents')} style={{ marginBottom: 16 }}>
        返回
      </Button>
      <Descriptions title={currentDocument.filename} bordered column={2}>
        <Descriptions.Item label="状态">
          <Tag color={statusColors[currentDocument.status]}>{currentDocument.status}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="类型">{currentDocument.file_type}</Descriptions.Item>
        <Descriptions.Item label="大小">
          {(currentDocument.file_size / 1024).toFixed(2)} KB
        </Descriptions.Item>
        <Descriptions.Item label="创建时间">
          {new Date(currentDocument.created_at).toLocaleString()}
        </Descriptions.Item>
      </Descriptions>
      {chunks.length > 0 && (
        <Card title="文档分块" style={{ marginTop: 16 }}>
          <List
            dataSource={chunks}
            renderItem={(chunk) => (
              <List.Item>
                <List.Item.Meta
                  title={`分块 ${chunk.chunk_index + 1}`}
                  description={chunk.content.slice(0, 200) + (chunk.content.length > 200 ? '...' : '')}
                />
              </List.Item>
            )}
          />
        </Card>
      )}
    </Card>
  )
}
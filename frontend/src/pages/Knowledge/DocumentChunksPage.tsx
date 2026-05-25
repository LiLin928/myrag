import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Spin, Result, List, Pagination, Select, Space, Tag, Typography, Popconfirm, message } from 'antd'
import { ArrowLeftOutlined, EditOutlined, SyncOutlined, DeleteOutlined, ReloadOutlined } from '@ant-design/icons'
import { useKnowledgeStore } from '../../stores/knowledgeStore'
import { DocumentMetadataPanel, MetadataEditorModal } from '../../components/Metadata'
import { ChunkDetail, MetadataResponse } from '../../types/models'
import { knowledgeApi } from '../../api/knowledge'
import { chunkMetadataApi } from '../../api/metadata'

const { Paragraph } = Typography

export function DocumentChunksPage() {
  const { knowledgeId, documentId } = useParams()
  const navigate = useNavigate()
  const { currentDocuments, fetchDocuments } = useKnowledgeStore()

  const [chunks, setChunks] = useState<ChunkDetail[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [loading, setLoading] = useState(false)
  const [document, setDocument] = useState<any>(null)

  const [sectionFilter, setSectionFilter] = useState<string>()
  const [embeddingFilter, setEmbeddingFilter] = useState<boolean>()

  const [editingChunk, setEditingChunk] = useState<ChunkDetail | null>(null)
  const [editingMetadata, setEditingMetadata] = useState<MetadataResponse | null>(null)
  const [sections, setSections] = useState<string[]>([])

  // 加载文档信息
  useEffect(() => {
    if (knowledgeId) {
      fetchDocuments(knowledgeId).then(() => {
        const doc = currentDocuments.find(d => d.id === documentId)
        setDocument(doc)
      })
    }
  }, [knowledgeId, documentId])

  // 加载分块
  useEffect(() => {
    if (knowledgeId && documentId) {
      setLoading(true)
      knowledgeApi.listChunks(knowledgeId, documentId, page, pageSize, {
        section_filter: sectionFilter,
        has_embedding: embeddingFilter,
      })
        .then(response => {
          setChunks(response.data.chunks)
          setTotal(response.data.total)
          // 提取章节列表
          const uniqueSections = new Set(
            response.data.chunks
              .map(c => c.clause_title)
              .filter(Boolean) as string[]
          )
          setSections(Array.from(uniqueSections))
        })
        .catch(() => {
          message.error('加载分块失败')
        })
        .finally(() => setLoading(false))
    }
  }, [knowledgeId, documentId, page, pageSize, sectionFilter, embeddingFilter])

  const handlePageChange = (p: number, ps: number) => {
    setPage(p)
    setPageSize(ps)
  }

  const handleRefresh = () => {
    setPage(1)
  }

  const handleEditChunkMetadata = async (chunk: ChunkDetail) => {
    try {
      const metadata = await chunkMetadataApi.get(chunk.id)
      setEditingChunk(chunk)
      setEditingMetadata(metadata.data)
    } catch (error) {
      message.error('获取元数据失败')
    }
  }

  const handleSaveChunkMetadata = async (metadata: Record<string, string>) => {
    if (!editingChunk) return
    await chunkMetadataApi.update(editingChunk.id, { metadata })
    message.success('保存成功')
    setEditingChunk(null)
    handleRefresh()
  }

  const handleRevectorize = async (_chunkId: string) => {
    message.info('重新向量化功能待实现')
  }

  const handleDeleteChunk = async (_chunkId: string) => {
    message.info('删除分块功能待实现')
  }

  if (!knowledgeId || !documentId) {
    return <Result status="404" title="缺少参数" />
  }

  if (loading && chunks.length === 0) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  }

  return (
    <div style={{ padding: 24 }}>
      {/* 返回按钮 */}
      <Button
        icon={<ArrowLeftOutlined />}
        onClick={() => navigate(`/knowledge/${knowledgeId}`)}
        style={{ marginBottom: 16 }}
      >
        返回文档列表
      </Button>

      {/* 文档元数据面板 */}
      {document && (
        <DocumentMetadataPanel
          knowledgeId={knowledgeId}
          documentId={documentId}
          filename={document.filename}
        />
      )}

      {/* 分块列表 */}
      <Card
        title={`分块列表 (共 ${total} 条)`}
        style={{ marginTop: 16 }}
        extra={
          <Button icon={<ReloadOutlined />} onClick={handleRefresh} loading={loading}>
            刷新
          </Button>
        }
      >
        {/* 过滤器 */}
        <Space style={{ marginBottom: 16 }}>
          <Select
            placeholder="章节过滤"
            allowClear
            style={{ width: 200 }}
            value={sectionFilter}
            onChange={setSectionFilter}
            options={sections.map(s => ({ value: s, label: s }))}
          />
          <Select
            placeholder="向量状态"
            allowClear
            style={{ width: 120 }}
            value={embeddingFilter === undefined ? undefined : embeddingFilter ? 'yes' : 'no'}
            onChange={(v) => setEmbeddingFilter(v === 'yes' ? true : v === 'no' ? false : undefined)}
            options={[
              { value: 'yes', label: '已向量' },
              { value: 'no', label: '未向量' },
            ]}
          />
        </Space>

        {/* 分块卡片列表 */}
        <List
          dataSource={chunks}
          renderItem={(chunk) => (
            <List.Item
              actions={[
                <Button
                  key="edit"
                  size="small"
                  icon={<EditOutlined />}
                  onClick={() => handleEditChunkMetadata(chunk)}
                >
                  编辑元数据
                </Button>,
                <Button
                  key="revectorize"
                  size="small"
                  icon={<SyncOutlined />}
                  onClick={() => handleRevectorize(chunk.id)}
                >
                  重新向量化
                </Button>,
                <Popconfirm
                  key="delete"
                  title="确认删除？"
                  onConfirm={() => handleDeleteChunk(chunk.id)}
                >
                  <Button size="small" danger icon={<DeleteOutlined />}>
                    删除
                  </Button>
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                title={`#${chunk.page_number} ${chunk.clause_title || chunk.clause_id}`}
                description={
                  <Paragraph
                    ellipsis={{ rows: 2 }}
                    style={{ maxWidth: 400, marginBottom: 0 }}
                  >
                    {chunk.content}
                  </Paragraph>
                }
              />
              {/* 元数据显示 */}
              <Space direction="vertical" size="small">
                <Typography.Text type="secondary">
                  继承: {Object.entries(chunk.metadata.inherited).slice(0, 2).map(([k, v]) => `${k}=${v}`).join(', ') || '无'}
                </Typography.Text>
                <Typography.Text>
                  自有: {Object.entries(chunk.metadata.own).map(([k, v]) => `${k}=${v}`).join(', ') || '无'}
                </Typography.Text>
                {chunk.has_embedding ? (
                  <Tag color="success">已向量</Tag>
                ) : (
                  <Tag color="warning">未向量</Tag>
                )}
              </Space>
            </List.Item>
          )}
        />

        {/* 分页 */}
        {total > pageSize && (
          <Pagination
            current={page}
            pageSize={pageSize}
            total={total}
            showSizeChanger
            showQuickJumper
            onChange={handlePageChange}
            onShowSizeChange={handlePageChange}
            style={{ marginTop: 16, textAlign: 'center' }}
          />
        )}
      </Card>

      {/* 分块元数据编辑弹窗 */}
      {editingChunk && editingMetadata && (
        <MetadataEditorModal
          visible={true}
          title="编辑分块元数据"
          metadata={editingMetadata}
          mode="chunk"
          chunkId={editingChunk.id}
          onSave={handleSaveChunkMetadata}
          onCancel={() => {
            setEditingChunk(null)
            setEditingMetadata(null)
          }}
        />
      )}
    </div>
  )
}
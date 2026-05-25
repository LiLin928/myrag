import { useEffect, useState } from 'react'
import { List, Pagination, Select, Space, Spin, Empty, Checkbox, Typography, Card, Button } from 'antd'
import { useChunkStore } from '../../stores/chunkStore'
import { ChunkCard } from './ChunkCard'
import { MetadataEditor } from './MetadataEditor'

const { Text } = Typography

interface ChunkListProps {
  projectId: string
  documentId: string
  onChunkSelect?: (chunkId: string) => void
}

export function ChunkList({ projectId, documentId, onChunkSelect }: ChunkListProps) {
  const {
    chunks,
    total,
    page,
    pageSize,
    loading,
    selectedChunkIds,
    fetchChunks,
    updateMetadata,
    deleteChunk,
    revectorizeChunk,
    selectChunk,
    deselectChunk,
    selectAllChunks,
    clearSelection,
    setCurrentChunk: _setCurrentChunk,
  } = useChunkStore()

  const [editingChunk, setEditingChunk] = useState<string | null>(null)
  const [sectionFilter, setSectionFilter] = useState<string>()
  const [embeddingFilter, setEmbeddingFilter] = useState<string>()

  // Fetch chunks on mount
  useEffect(() => {
    fetchChunks(projectId, documentId, page, pageSize, {
      section_filter: sectionFilter,
      has_embedding: embeddingFilter === 'true' ? true : embeddingFilter === 'false' ? false : undefined,
    })
  }, [projectId, documentId, page, pageSize, sectionFilter, embeddingFilter])

  // Get unique sections for filter
  const sections = [...new Set(chunks.map(c => c.metadata.section_title).filter(Boolean))]

  // Handle page change
  const handlePageChange = (newPage: number, newPageSize: number) => {
    fetchChunks(projectId, documentId, newPage, newPageSize)
  }

  // Handle metadata edit
  const handleEditMetadata = (chunkId: string) => {
    setEditingChunk(chunkId)
  }

  const handleSaveMetadata = async (metadata: Record<string, unknown>) => {
    if (editingChunk) {
      await updateMetadata(editingChunk, metadata as any)
      setEditingChunk(null)
    }
  }

  // Handle delete
  const handleDelete = async (chunkId: string) => {
    await deleteChunk(chunkId)
    // Refresh list
    fetchChunks(projectId, documentId, page, pageSize)
  }

  // Handle revectorize
  const handleRevectorize = async (chunkId: string) => {
    try {
      const result = await revectorizeChunk(chunkId)
      console.log('Revectorize job started:', result.job_id)
    } catch (error) {
      console.error('Revectorize failed:', error)
    }
  }

  // Handle selection
  const handleSelect = (chunkId: string) => {
    if (selectedChunkIds.includes(chunkId)) {
      deselectChunk(chunkId)
    } else {
      selectChunk(chunkId)
    }
    onChunkSelect?.(chunkId)
  }

  // Find editing chunk
  const editingChunkData = editingChunk ? chunks.find(c => c.id === editingChunk) : null

  if (loading) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  }

  return (
    <div>
      {/* Filters */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space size="middle">
          <Text strong>过滤:</Text>

          <Select
            placeholder="章节"
            allowClear
            style={{ width: 150 }}
            value={sectionFilter}
            onChange={setSectionFilter}
            options={sections.map(s => ({ value: s, label: s }))}
          />

          <Select
            placeholder="向量状态"
            allowClear
            style={{ width: 120 }}
            value={embeddingFilter}
            onChange={setEmbeddingFilter}
            options={[
              { value: 'true', label: '已向量' },
              { value: 'false', label: '未向量' },
            ]}
          />

          <Text type="secondary">
            共 {total} 条分块
          </Text>
        </Space>
      </Card>

      {/* Selection actions */}
      {selectedChunkIds.length > 0 && (
        <Card size="small" style={{ marginBottom: 16 }}>
          <Space>
            <Text>已选择 {selectedChunkIds.length} 条</Text>
            <Checkbox
              checked={selectedChunkIds.length === chunks.length}
              indeterminate={selectedChunkIds.length > 0 && selectedChunkIds.length < chunks.length}
              onChange={(e) => e.target.checked ? selectAllChunks() : clearSelection()}
            >
              全选
            </Checkbox>
            <Button size="small" onClick={clearSelection}>取消选择</Button>
          </Space>
        </Card>
      )}

      {/* Chunk list */}
      {chunks.length === 0 ? (
        <Empty description="暂无分块数据" />
      ) : (
        <List
          dataSource={chunks}
          renderItem={(chunk) => (
            <ChunkCard
              key={chunk.id}
              chunk={chunk}
              selected={selectedChunkIds.includes(chunk.id)}
              onSelect={handleSelect}
              onEditMetadata={() => handleEditMetadata(chunk.id)}
              onDelete={() => handleDelete(chunk.id)}
              onRevectorize={() => handleRevectorize(chunk.id)}
            />
          )}
        />
      )}

      {/* Pagination */}
      {total > pageSize && (
        <div style={{ textAlign: 'center', marginTop: 16 }}>
          <Pagination
            current={page}
            pageSize={pageSize}
            total={total}
            showSizeChanger
            showQuickJumper
            onChange={handlePageChange}
            onShowSizeChange={handlePageChange}
          />
        </div>
      )}

      {/* Metadata editor modal */}
      {editingChunkData && (
        <MetadataEditor
          visible={true}
          chunk={editingChunkData}
          onSave={handleSaveMetadata}
          onCancel={() => setEditingChunk(null)}
        />
      )}
    </div>
  )
}
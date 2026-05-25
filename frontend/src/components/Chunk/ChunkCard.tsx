import React from 'react'
import { Card, Tag, Space, Button, Typography, Popconfirm } from 'antd'
import {
  FileTextOutlined,
  TableOutlined,
  FontSizeOutlined,
  CheckCircleOutlined,
  EditOutlined,
  DeleteOutlined,
  CloudOutlined,
} from '@ant-design/icons'

import { Chunk } from '../../stores/chunkStore'

const { Text, Paragraph } = Typography

interface ChunkCardProps {
  chunk: Chunk
  onEditMetadata?: (chunk: Chunk) => void
  onDelete?: (chunk: Chunk) => void
  onRevectorize?: (chunk: Chunk) => void
  selected?: boolean
  onSelect?: (chunkId: string) => void
}

const CHUNK_TYPE_ICONS: Record<string, React.ReactNode> = {
  header: <FontSizeOutlined />,
  paragraph: <FileTextOutlined />,
  table: <TableOutlined />,
  footer: <FileTextOutlined />,
}

export function ChunkCard({
  chunk,
  onEditMetadata,
  onDelete,
  onRevectorize,
  selected,
  onSelect,
}: ChunkCardProps) {
  const chunkType = chunk.clause_type || chunk.metadata.position_type || 'paragraph'
  const icon = CHUNK_TYPE_ICONS[chunkType] || <FileTextOutlined />

  // Truncate content for preview
  const previewContent = chunk.content.length > 200
    ? chunk.content.slice(0, 200) + '...'
    : chunk.content

  return (
    <Card
      size="small"
      hoverable
      onClick={() => onSelect?.(chunk.id)}
      style={{
        marginBottom: 12,
        borderLeft: selected ? '3px solid #1890ff' : undefined,
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <Space size="small">
          <Tag icon={icon} color={chunkType === 'header' ? 'blue' : chunkType === 'table' ? 'cyan' : 'default'}>
            {chunkType}
          </Tag>
          <Tag>{chunk.page_number}页</Tag>
          {chunk.has_embedding ? (
            <Tag icon={<CheckCircleOutlined />} color="success">已向量</Tag>
          ) : (
            <Tag color="warning">未向量</Tag>
          )}
        </Space>

        <Text type="secondary" style={{ fontSize: 12 }}>
          {chunk.content_length} 字符
        </Text>
      </div>

      {/* Section title */}
      {chunk.metadata.section_title && (
        <Text type="secondary" style={{ marginBottom: 4, display: 'block' }}>
          章节: {chunk.metadata.section_title}
        </Text>
      )}

      {/* Content preview */}
      <Paragraph
        ellipsis={{ rows: 2, expandable: true }}
        style={{ marginBottom: 8, fontSize: 13 }}
      >
        {previewContent}
      </Paragraph>

      {/* User tags */}
      {chunk.metadata.user_tags?.length > 0 && (
        <Space size="small" style={{ marginBottom: 8 }}>
          {chunk.metadata.user_tags.map(tag => (
            <Tag key={tag} color="blue">{tag}</Tag>
          ))}
        </Space>
      )}

      {/* Actions */}
      <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
        <Space size="small">
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={(e) => {
              e.stopPropagation()
              onEditMetadata?.(chunk)
            }}
          >
            编辑
          </Button>

          {!chunk.has_embedding && (
            <Button
              size="small"
              icon={<CloudOutlined />}
              onClick={(e) => {
                e.stopPropagation()
                onRevectorize?.(chunk)
              }}
            >
              向量化
            </Button>
          )}

          <Popconfirm
            title="确定删除此分块？"
            onConfirm={() => onDelete?.(chunk)}
            onCancel={(e) => e?.stopPropagation()}
          >
            <Button
              size="small"
              danger
              icon={<DeleteOutlined />}
              onClick={(e) => e.stopPropagation()}
            />
          </Popconfirm>
        </Space>
      </div>
    </Card>
  )
}

interface ChunkDetailPanelProps {
  chunk: Chunk
  onUpdateContent?: (chunkId: string, content: string) => void
  onClose?: () => void
}

export function ChunkDetailPanel({ chunk, onUpdateContent: _onUpdateContent, onClose }: ChunkDetailPanelProps) {
  return (
    <Card
      title={`分块详情 - ${chunk.clause_id}`}
      extra={onClose && <Button size="small" onClick={onClose}>关闭</Button>}
    >
      {/* Metadata info */}
      <Space direction="vertical" style={{ width: '100%', marginBottom: 16 }}>
        <Text strong>基本信息</Text>
        <div>
          <Text type="secondary">类型: </Text>
          <Tag>{chunk.clause_type || 'paragraph'}</Tag>
        </div>
        <div>
          <Text type="secondary">页码: </Text>
          <Text>{chunk.page_number}</Text>
        </div>
        <div>
          <Text type="secondary">字符数: </Text>
          <Text>{chunk.content_length}</Text>
        </div>
        {chunk.metadata.section_title && (
          <div>
            <Text type="secondary">章节: </Text>
            <Text>{chunk.metadata.section_title}</Text>
          </div>
        )}
      </Space>

      {/* Full content */}
      <Text strong style={{ marginBottom: 8, display: 'block' }}>完整内容</Text>
      <Paragraph style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 12, borderRadius: 4 }}>
        {chunk.content}
      </Paragraph>

      {/* User metadata */}
      <Text strong style={{ marginBottom: 8, display: 'block' }}>用户标签</Text>
      <Space size="small">
        {chunk.metadata.user_tags?.map(tag => (
          <Tag key={tag} color="blue">{tag}</Tag>
        )) || <Text type="secondary">无标签</Text>}
      </Space>
    </Card>
  )
}
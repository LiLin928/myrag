import React from 'react'
import { Card, Typography, Tag, Space, Tooltip } from 'antd'
import {
  FileTextOutlined,
  TableOutlined,
  FontSizeOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'

import { SearchTestResult } from '../../stores/searchStore'

const { Text, Paragraph } = Typography

interface SearchResultCardProps {
  result: SearchTestResult
  rank: number
  onClick?: (result: SearchTestResult) => void
}

const CHUNK_TYPE_ICONS: Record<string, React.ReactNode> = {
  header: <FontSizeOutlined />,
  paragraph: <FileTextOutlined />,
  table: <TableOutlined />,
}

export function SearchResultCard({ result, rank, onClick }: SearchResultCardProps) {
  const chunkType = result.clause_type || (result.metadata.position_type as string) || 'paragraph'
  const userTags = (result.metadata.user_tags as string[]) || []
  const icon = CHUNK_TYPE_ICONS[chunkType] || <FileTextOutlined />

  // Score color based on similarity
  const scoreColor = result.score >= 0.8 ? 'success' : result.score >= 0.6 ? 'processing' : result.score >= 0.4 ? 'warning' : 'default'

  return (
    <Card
      size="small"
      hoverable
      onClick={() => onClick?.(result)}
      style={{ marginBottom: 12 }}
    >
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <Space size="small">
          <Tag color="blue">#{rank}</Tag>
          <Tag icon={icon}>{chunkType}</Tag>
          <Tag>{result.page_number}页</Tag>
          <Tag color={scoreColor}>
            相似度: {typeof result.score === 'number' ? result.score.toFixed(3) : result.score}
          </Tag>
          <Tag color="cyan">{result.search_method}</Tag>
        </Space>
      </div>

      {/* Section */}
      {result.section_title && (
        <Text type="secondary" style={{ marginBottom: 4, display: 'block' }}>
          章节: {result.section_title}
        </Text>
      )}

      {/* Content preview */}
      <Paragraph
        ellipsis={{ rows: 3, expandable: true }}
        style={{ marginBottom: 8, fontSize: 13 }}
      >
        {result.content}
      </Paragraph>

      {/* Metadata tags */}
      {userTags.length > 0 && (
        <Space size="small" style={{ marginBottom: 8 }}>
          {userTags.map((tag: string) => (
            <Tag key={tag} color="blue">{tag}</Tag>
          ))}
        </Space>
      )}

      {/* Document ID */}
      <Text type="secondary" style={{ fontSize: 12 }}>
        文档: {result.document_id}
      </Text>
    </Card>
  )
}

interface PerformanceStatsProps {
  performance: {
    query_time_ms: number
    total_time_ms: number
    result_count: number
    top_scores: number[]
  }
}

export function PerformanceStats({ performance }: PerformanceStatsProps) {
  return (
    <Card size="small" title="性能统计">
      <Space direction="vertical" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Text type="secondary">查询耗时:</Text>
          <Text strong>
            <ClockCircleOutlined style={{ marginRight: 4 }} />
            {performance.query_time_ms} ms
          </Text>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Text type="secondary">总耗时:</Text>
          <Text strong>{performance.total_time_ms} ms</Text>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Text type="secondary">结果数:</Text>
          <Text strong>{performance.result_count} 条</Text>
        </div>

        <div>
          <Text type="secondary">Top 分数:</Text>
          <Space size="small" style={{ marginTop: 4 }}>
            {performance.top_scores.map((score, i) => (
              <Tooltip key={i} title={`排名第${i + 1}`}>
                <Tag color={score >= 0.8 ? 'success' : score >= 0.6 ? 'processing' : 'warning'}>
                  {typeof score === 'number' ? score.toFixed(3) : score}
                </Tag>
              </Tooltip>
            ))}
          </Space>
        </div>
      </Space>
    </Card>
  )
}

interface SearchStatsPanelProps {
  stats: {
    document_count: number
    total_chunks: number
    vectorized_chunks: number
    vectorization_rate: number
  }
}

export function SearchStatsPanel({ stats }: SearchStatsPanelProps) {
  return (
    <Card size="small" title="知识库统计">
      <Space direction="vertical" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Text type="secondary">文档数:</Text>
          <Text strong>{stats.document_count}</Text>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Text type="secondary">分块数:</Text>
          <Text strong>{stats.total_chunks}</Text>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Text type="secondary">已向量:</Text>
          <Text strong>{stats.vectorized_chunks}</Text>
        </div>

        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
          <Text type="secondary">向量率:</Text>
          <Tag color={stats.vectorization_rate >= 80 ? 'success' : stats.vectorization_rate >= 50 ? 'warning' : 'error'}>
            {stats.vectorization_rate}%
          </Tag>
        </div>
      </Space>
    </Card>
  )
}
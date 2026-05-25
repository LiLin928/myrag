import { useEffect, useState } from 'react'
import {
  Card,
  Input,
  Select,
  Button,
  Space,
  Spin,
  Empty,
  Typography,
  Row,
  Col,
  Slider,
  Tag,
  List,
} from 'antd'
import {
  SearchOutlined,
  ClearOutlined,
  HistoryOutlined,
} from '@ant-design/icons'

import { useSearchStore } from '../../stores/searchStore'
import { SearchResultCard, PerformanceStats, SearchStatsPanel } from '../../components/Search'

const { Text, Title } = Typography

interface SearchTestProps {
  projectId: string
}

export function SearchTest({ projectId }: SearchTestProps) {
  const {
    testResults,
    loading,
    lastQuery,
    searchType,
    topK,
    scoreThreshold,
    filters,
    performance,
    stats,
    filterOptions,
    queryHistory,
    testSearch,
    fetchStats,
    fetchFilterOptions,
    setSearchType,
    setTopK,
    setScoreThreshold,
    setFilters,
    clearFilters,
    clearHistory,
  } = useSearchStore()

  const [query, setQuery] = useState('')
  const [localFilters, setLocalFilters] = useState(filters)

  // Fetch stats and filter options on mount
  useEffect(() => {
    fetchStats(projectId)
    fetchFilterOptions(projectId)
  }, [projectId])

  // Handle search
  const handleSearch = () => {
    if (query.trim()) {
      setFilters(localFilters)
      testSearch(projectId, query.trim())
    }
  }

  // Handle clear filters
  const handleClearFilters = () => {
    setLocalFilters({})
    clearFilters()
  }

  // Handle history click
  const handleHistoryClick = (historyQuery: string) => {
    setQuery(historyQuery)
    testSearch(projectId, historyQuery)
  }

  return (
    <div style={{ padding: 24 }}>
      <Title level={4}>检索测试</Title>

      <Row gutter={24}>
        {/* Left: Search input and filters */}
        <Col span={8}>
          {/* Stats panel */}
          {stats && <SearchStatsPanel stats={stats} />}

          {/* Search input */}
          <Card size="small" title="查询" style={{ marginTop: 16 }}>
            <Input.Search
              placeholder="输入查询文本..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onSearch={handleSearch}
              enterButton={<SearchOutlined />}
              size="large"
              loading={loading}
            />
          </Card>

          {/* Search type */}
          <Card size="small" title="检索类型" style={{ marginTop: 16 }}>
            <Select
              value={searchType}
              onChange={setSearchType}
              style={{ width: '100%' }}
              options={[
                { value: 'hybrid', label: '混合检索（推荐）' },
                { value: 'vector', label: '向量检索' },
                { value: 'keyword', label: '关键词检索' },
              ]}
            />
          </Card>

          {/* Parameters */}
          <Card size="small" title="参数设置" style={{ marginTop: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <Text type="secondary">返回数量: {topK}</Text>
                <Slider
                  min={1}
                  max={20}
                  value={topK}
                  onChange={setTopK}
                />
              </div>

              <div>
                <Text type="secondary">相似度阈值: {scoreThreshold.toFixed(1)}</Text>
                <Slider
                  min={0}
                  max={1}
                  step={0.1}
                  value={scoreThreshold}
                  onChange={setScoreThreshold}
                />
              </div>
            </Space>
          </Card>

          {/* Filters */}
          <Card size="small" title="过滤条件" style={{ marginTop: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              {/* Document type filter */}
              <Select
                placeholder="文档类型"
                allowClear
                style={{ width: '100%' }}
                value={localFilters.document_type}
                onChange={(v) => setLocalFilters({ ...localFilters, document_type: v })}
                options={filterOptions?.document_types?.map(t => ({ value: t, label: t })) || []}
              />

              {/* Section filter */}
              <Select
                placeholder="章节"
                allowClear
                showSearch
                style={{ width: '100%' }}
                value={localFilters.section_title}
                onChange={(v) => setLocalFilters({ ...localFilters, section_title: v })}
                options={filterOptions?.sections?.map(s => ({ value: s, label: s })) || []}
              />

              {/* User tags filter */}
              <Select
                placeholder="用户标签"
                allowClear
                mode="multiple"
                style={{ width: '100%' }}
                value={localFilters.user_tags}
                onChange={(v) => setLocalFilters({ ...localFilters, user_tags: v })}
                options={filterOptions?.user_tags?.map(t => ({ value: t, label: t })) || []}
              />

              {/* Category filter */}
              <Select
                placeholder="分类"
                allowClear
                style={{ width: '100%' }}
                value={localFilters.category}
                onChange={(v) => setLocalFilters({ ...localFilters, category: v })}
                options={filterOptions?.categories?.map(c => ({ value: c, label: c })) || []}
              />

              <Button
                icon={<ClearOutlined />}
                onClick={handleClearFilters}
                style={{ width: '100%' }}
              >
                清除过滤
              </Button>
            </Space>
          </Card>

          {/* Query history */}
          {queryHistory.length > 0 && (
            <Card size="small" title={<><HistoryOutlined /> 查询历史</>} style={{ marginTop: 16 }}>
              <Space direction="vertical" style={{ width: '100%' }}>
                {queryHistory.slice(0, 5).map((h) => (
                  <Tag
                    key={h}
                    style={{ cursor: 'pointer', marginBottom: 4 }}
                    onClick={() => handleHistoryClick(h)}
                  >
                    {h.length > 20 ? h.slice(0, 20) + '...' : h}
                  </Tag>
                ))}
                <Button size="small" onClick={clearHistory}>
                  清除历史
                </Button>
              </Space>
            </Card>
          )}
        </Col>

        {/* Right: Results */}
        <Col span={16}>
          {/* Performance stats */}
          {performance && (
            <PerformanceStats performance={performance} />
          )}

          {/* Results */}
          <Card size="small" title={`检索结果 (${testResults.length})`} style={{ marginTop: 16 }}>
            {loading ? (
              <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
            ) : testResults.length === 0 ? (
              <Empty description={lastQuery ? '未找到相关结果' : '输入查询进行检索测试'} />
            ) : (
              <List
                dataSource={testResults}
                renderItem={(result, index) => (
                  <SearchResultCard
                    key={result.chunk_id}
                    result={result}
                    rank={index + 1}
                  />
                )}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}
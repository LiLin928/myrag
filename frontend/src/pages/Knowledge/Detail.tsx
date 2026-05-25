import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Spin, Descriptions, Tabs, Result, Input, Space, message, List, Typography } from 'antd'
import { ArrowLeftOutlined, SearchOutlined } from '@ant-design/icons'
import { useKnowledgeStore } from '../../stores/knowledgeStore'
import { DocumentList } from '../../components/Knowledge/DocumentList'
import { KBSettingsForm } from '../../components/Knowledge/KBSettingsForm'
import { knowledgeApi } from '../../api/knowledge'

const { Text } = Typography

interface SearchResult {
  id: string
  content: string
  score: number
  filename?: string
  source: string
  metadata: Record<string, any>
}

export function KnowledgeDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { currentKnowledge, loading, error, fetchOne } = useKnowledgeStore()
  const [activeTab, setActiveTab] = useState('documents')
  const [searchQuery, setSearchQuery] = useState('')
  const [searching, setSearching] = useState(false)
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])

  useEffect(() => {
    if (id) fetchOne(id)
  }, [id, fetchOne])

  // 搜索测试功能
  const handleSearch = async () => {
    if (!searchQuery.trim() || !id) {
      message.warning('请输入搜索内容')
      return
    }
    setSearching(true)
    setSearchResults([])
    try {
      const response = await knowledgeApi.search(id, { query: searchQuery, top_k: 10 })
      // 映射后端返回的 filename 到 source
      const results = (response.data.results || []).map((r: any) => ({
        ...r,
        source: r.filename || '未知',
      }))
      setSearchResults(results)
      message.success(`找到 ${results.length} 条相关结果`)
    } catch (error: any) {
      message.error(error.message || '检索失败')
    } finally {
      setSearching(false)
    }
  }

  if (!id) {
    return <Result status="404" title="缺少知识库ID" subTitle="请从知识库列表进入" />
  }

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  if (error) {
    return <Result status="error" title="加载失败" subTitle={error} />
  }
  if (!currentKnowledge) return <div>知识库不存在</div>

  const tabItems = [
    {
      key: 'documents',
      label: '文档管理',
      children: id ? <DocumentList knowledgeId={id} /> : null,
    },
    {
      key: 'search',
      label: '检索测试',
      children: id ? (
        <Card>
          <Space.Compact style={{ width: '100%', marginBottom: 16 }}>
            <Input
              placeholder="输入关键词测试检索效果..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onPressEnter={handleSearch}
              style={{ width: 'calc(100% - 100px)' }}
            />
            <Button
              type="primary"
              icon={<SearchOutlined />}
              loading={searching}
              onClick={handleSearch}
            >
              搜索
            </Button>
          </Space.Compact>
          <Text type="secondary" style={{ marginBottom: 16, display: 'block' }}>
            提示：输入关键词测试知识库的检索效果，将使用当前知识库的配置进行搜索
          </Text>

          {searchResults.length > 0 && (
            <List
              header={`${searchResults.length} 条搜索结果`}
              bordered
              dataSource={searchResults}
              renderItem={(item) => (
                <List.Item>
                  <List.Item.Meta
                    title={<Text>相似度: {(item.score * 100).toFixed(1)}%</Text>}
                    description={
                      <div>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          来源: {item.source || '未知'}
                        </Text>
                        <div style={{ marginTop: 8 }}>
                          {item.content.length > 200
                            ? item.content.substring(0, 200) + '...'
                            : item.content}
                        </div>
                      </div>
                    }
                  />
                </List.Item>
              )}
            />
          )}
        </Card>
      ) : null,
    },
    {
      key: 'settings',
      label: '知识库设置',
      children: id ? <KBSettingsForm knowledgeId={id} /> : null,
    },
    {
      key: 'info',
      label: '基本信息',
      children: (
        <Descriptions bordered column={2}>
          <Descriptions.Item label="ID">{currentKnowledge.id}</Descriptions.Item>
          <Descriptions.Item label="文档数">{currentKnowledge.document_count}</Descriptions.Item>
          <Descriptions.Item label="向量模型">{currentKnowledge.embedding_model}</Descriptions.Item>
          <Descriptions.Item label="检索方法">{currentKnowledge.retrieval_method}</Descriptions.Item>
          <Descriptions.Item label="创建时间">
            {new Date(currentKnowledge.created_at).toLocaleString('zh-CN')}
          </Descriptions.Item>
          <Descriptions.Item label="描述" span={2}>
            {currentKnowledge.description || '-'}
          </Descriptions.Item>
        </Descriptions>
      ),
    },
  ]

  return (
    <Card
      title={currentKnowledge.name}
      extra={
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/knowledge')}>
          返回列表
        </Button>
      }
    >
      <Tabs activeKey={activeTab} onChange={setActiveTab} items={tabItems} />
    </Card>
  )
}
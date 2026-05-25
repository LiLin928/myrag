import { Card, Form, Input, Select, Space, List, Tag, Spin, Empty, Switch, Collapse } from 'antd'
import { SearchOutlined, FileTextOutlined, DatabaseOutlined } from '@ant-design/icons'
import { useSearchStore } from '../../stores/searchStore'
import { SearchResult } from '../../api/search'

export function SearchPage() {
  const { results, loading, lastQuery, searchGlobal } = useSearchStore()
  const [form] = Form.useForm()

  const handleSearch = async (values: { query: string; top_k?: number; use_hybrid?: boolean }) => {
    if (!values.query) return
    await searchGlobal({
      query: values.query,
      top_k: values.top_k || 10,
      use_hybrid: values.use_hybrid ?? true,
    })
  }

  return (
    <div>
      <Card>
        <Form form={form} onFinish={handleSearch} layout="inline">
          <Form.Item name="query" style={{ flex: 1 }}>
            <Input.Search
              placeholder="输入搜索内容..."
              enterButton={<SearchOutlined />}
              size="large"
              loading={loading}
            />
          </Form.Item>
          <Form.Item name="top_k" initialValue={10}>
            <Select style={{ width: 100 }} options={[
              { value: 5, label: '5条' },
              { value: 10, label: '10条' },
              { value: 20, label: '20条' },
              { value: 50, label: '50条' },
            ]} />
          </Form.Item>
          <Form.Item name="use_hybrid" initialValue={true}>
            <Switch checkedChildren="混合检索" unCheckedChildren="向量检索" defaultChecked />
          </Form.Item>
        </Form>
      </Card>

      <Card title={`搜索结果: "${lastQuery}"`} style={{ marginTop: 16 }}>
        {loading && <Spin size="large" style={{ display: 'block', margin: '50px auto' }} />}
        {!loading && results.length === 0 && lastQuery === '' && (
          <Empty description="输入关键词开始搜索" style={{ padding: '50px 0' }} />
        )}
        {!loading && results.length === 0 && lastQuery !== '' && (
          <Empty description="未找到相关结果" style={{ padding: '50px 0' }} />
        )}
        {!loading && results.length > 0 && (
          <List
            dataSource={results}
            renderItem={(item: SearchResult, index: number) => (
              <List.Item key={item.id}>
                <Card size="small" style={{ width: '100%' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Space>
                      <Tag color="blue"># {index + 1}</Tag>
                      <Tag color="geekblue">相似度: {item.score.toFixed(3)}</Tag>
                      {item.document_name && (
                        <Tag icon={<FileTextOutlined />} color="green">{item.document_name}</Tag>
                      )}
                    </Space>
                    {item.metadata?.supplier && (
                      <Tag icon={<DatabaseOutlined />} color="orange">{item.metadata.supplier}</Tag>
                    )}
                  </div>
                  <div style={{
                    background: '#f5f5f5',
                    padding: 12,
                    borderRadius: 4,
                    maxHeight: 200,
                    overflow: 'auto',
                    whiteSpace: 'pre-wrap',
                  }}>
                    {item.content}
                  </div>
                  {item.metadata && Object.keys(item.metadata).length > 0 && (
                    <Collapse size="small" style={{ marginTop: 8 }}>
                      <Collapse.Panel header="元数据" key="metadata">
                        <Space direction="vertical">
                          {Object.entries(item.metadata).map(([key, value]) => (
                            <div key={key}>
                              <Tag>{key}</Tag>: {String(value)}
                            </div>
                          ))}
                        </Space>
                      </Collapse.Panel>
                    </Collapse>
                  )}
                </Card>
              </List.Item>
            )}
          />
        )}
      </Card>
    </div>
  )
}
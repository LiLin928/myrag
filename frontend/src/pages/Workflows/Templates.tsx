import { useEffect, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { Card, Row, Col, Space, Tag, Button, Input, Spin } from 'antd'
import { templateApi, WorkflowTemplate, WorkflowTemplateDetail } from '../../api/templates'
import { TemplateDetailModal } from '../../components/Workflow/TemplateDetailModal'

const categoryColors: Record<string, string> = {
  RAG: 'purple',
  approval: 'orange',
  data: 'cyan',
  dialog: 'blue',
  custom: 'default',
}

const categories = ['RAG', 'approval', 'data', 'custom']

export function WorkflowTemplates() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([])
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null)
  const [searchText, setSearchText] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState<WorkflowTemplateDetail | null>(null)
  const [modalVisible, setModalVisible] = useState(false)

  const fetchTemplates = useCallback(async () => {
    setLoading(true)
    try {
      const response = await templateApi.list(selectedCategory || undefined)
      setTemplates(response.data)
    } catch (error) {
      console.error('获取模板失败:', error)
    } finally {
      setLoading(false)
    }
  }, [selectedCategory])

  useEffect(() => {
    fetchTemplates()
  }, [fetchTemplates])

  const handleTemplateClick = useCallback(async (template: WorkflowTemplate) => {
    try {
      const response = await templateApi.get(template.id)
      setSelectedTemplate(response.data)
      setModalVisible(true)
    } catch (error) {
      console.error('获取模板详情失败:', error)
    }
  }, [])

  const handleUseTemplate = useCallback(async (templateId: string) => {
    try {
      const response = await templateApi.createWorkflowFromTemplate(templateId, {})
      setModalVisible(false)
      navigate(`/workflows/${response.data.id}`)
    } catch (error) {
      console.error('创建工作流失败:', error)
    }
  }, [navigate])

  const filteredTemplates = useMemo(
    () => templates.filter((t) => t.name.toLowerCase().includes(searchText.toLowerCase())),
    [templates, searchText]
  )

  return (
    <div style={{ display: 'flex', height: 'calc(100vh - 150px)' }}>
      {/* 左侧分类栏 */}
      <Card style={{ width: 200, marginRight: 16 }} title="分类">
        <Space direction="vertical" style={{ width: '100%' }}>
          {categories.map((cat) => (
            <Button
              key={cat}
              block
              type={selectedCategory === cat ? 'primary' : 'default'}
              onClick={() => setSelectedCategory(cat)}
            >
              {cat}
            </Button>
          ))}
          <Button
            block
            type={selectedCategory === null ? 'primary' : 'default'}
            onClick={() => setSelectedCategory(null)}
          >
            全部
          </Button>
        </Space>
      </Card>

      {/* 右侧模板列表 */}
      <div style={{ flex: 1 }}>
        <Input.Search
          placeholder="搜索模板"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          style={{ marginBottom: 16 }}
        />

        {loading ? (
          <Spin size="large" />
        ) : (
          <Row gutter={16}>
            {filteredTemplates.map((template) => (
              <Col span={6} key={template.id}>
                <Card
                  hoverable
                  onClick={() => handleTemplateClick(template)}
                  style={{ marginBottom: 16 }}
                >
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <Tag color={categoryColors[template.category]}>{template.category}</Tag>
                    <div style={{ fontWeight: 'bold' }}>{template.name}</div>
                    <div style={{ fontSize: 12, color: '#999' }}>
                      {template.description?.slice(0, 50) || '暂无描述'}
                    </div>
                    <Space>
                      {template.tags?.slice(0, 2).map((t) => (
                        <Tag key={t}>{t}</Tag>
                      ))}
                    </Space>
                    <div style={{ fontSize: 12 }}>
                      使用次数: {template.usage_count}
                    </div>
                  </Space>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </div>

      <TemplateDetailModal
        template={selectedTemplate}
        visible={modalVisible}
        onClose={() => setModalVisible(false)}
        onUse={handleUseTemplate}
      />
    </div>
  )
}
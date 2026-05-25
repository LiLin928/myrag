import { useEffect, useState } from 'react'
import { Card, Tabs, Button, Switch, Tag, Space, Popconfirm, Empty, Spin, message, Row, Col } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, StarOutlined, StarFilled } from '@ant-design/icons'
import { useModelStore } from '../../stores/modelStore'
import { ModelConfig, ModelType } from '../../api/models'

import { ModelForm } from './ModelForm'

interface ModelListProps {
  onEdit?: (model: ModelConfig) => void
  onCreate?: () => void
}

// Type filter tab items
const typeTabs = [
  { key: 'all', label: '全部' },
  { key: 'llm', label: 'LLM' },
  { key: 'embedding', label: 'Embedding' },
  { key: 'rerank', label: 'Rerank' },
]

// Type tag colors
const typeColors: Record<ModelType, string> = {
  llm: 'blue',
  embedding: 'green',
  rerank: 'orange',
}

// Type labels in Chinese
const typeLabels: Record<ModelType, string> = {
  llm: 'LLM',
  embedding: 'Embedding',
  rerank: 'Rerank',
}

// Mask API base for display
function maskApiBase(apiBase: string): string {
  try {
    const url = new URL(apiBase)
    // Show protocol and domain, mask path
    const domain = url.hostname
    const maskedPath = url.pathname.length > 1 ? '/***' : ''
    return `${url.protocol}//${domain}${maskedPath}`
  } catch {
    return apiBase
  }
}

export function ModelList({ onEdit, onCreate }: ModelListProps) {
  const { models, loading, fetchList, delete: deleteModel, setDefault, toggleActive } = useModelStore()
  const [activeTab, setActiveTab] = useState<string>('all')
  const [formModalOpen, setFormModalOpen] = useState(false)
  const [editingModel, setEditingModel] = useState<ModelConfig | null>(null)

  useEffect(() => {
    fetchList()
  }, [])

  // Filter models by type
  const filteredModels = activeTab === 'all'
    ? models
    : models.filter((m) => m.type === activeTab)

  // Handle delete
  const handleDelete = async (id: string) => {
    try {
      await deleteModel(id)
      message.success('删除成功')
    } catch (error: any) {
      message.error(error.response?.data?.message || '删除失败')
    }
  }

  // Handle set default
  const handleSetDefault = async (model: ModelConfig) => {
    try {
      await setDefault(model.type, model.id)
      message.success('已设为默认模型')
    } catch (error: any) {
      message.error(error.response?.data?.message || '设置失败')
    }
  }

  // Handle toggle active
  const handleToggleActive = async (id: string, isActive: boolean) => {
    try {
      await toggleActive(id, isActive)
      message.success(isActive ? '已启用' : '已停用')
    } catch (error: any) {
      message.error(error.response?.data?.message || '操作失败')
    }
  }

  // Handle create new model
  const handleCreate = () => {
    if (onCreate) {
      onCreate()
    } else {
      setEditingModel(null)
      setFormModalOpen(true)
    }
  }

  // Handle edit model
  const handleEdit = (model: ModelConfig) => {
    if (onEdit) {
      onEdit(model)
    } else {
      setEditingModel(model)
      setFormModalOpen(true)
    }
  }

  // Render model card
  const renderModelCard = (model: ModelConfig) => (
    <Col xs={24} sm={12} md={8} lg={6} key={model.id}>
      <Card
        hoverable
        style={{ height: '100%' }}
        styles={{ body: { padding: '16px' } }}
      >
        {/* Header: Type tag + Default star */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <Tag color={typeColors[model.type]}>{typeLabels[model.type]}</Tag>
          <Space>
            {model.is_default && (
              <StarFilled style={{ color: '#faad14', fontSize: 16 }} title="默认模型" />
            )}
            <Switch
              size="small"
              checked={model.is_active}
              onChange={(checked) => handleToggleActive(model.id, checked)}
            />
          </Space>
        </div>

        {/* Model name */}
        <h3 style={{ margin: '0 0 8px', fontSize: 16, fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {model.name}
        </h3>

        {/* Provider + model_name */}
        <div style={{ marginBottom: 8, color: '#666' }}>
          <span style={{ fontWeight: 500 }}>{model.provider}</span>
          <span style={{ margin: '0 4px' }}>/</span>
          <span>{model.model_name}</span>
        </div>

        {/* Masked API base */}
        <div style={{ marginBottom: 12, fontSize: 12, color: '#999' }}>
          {maskApiBase(model.api_base)}
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #f0f0f0', paddingTop: 12 }}>
          <Space>
            <Button
              type="text"
              size="small"
              icon={<EditOutlined />}
              onClick={() => handleEdit(model)}
            >
              编辑
            </Button>
            {!model.is_default && (
              <Button
                type="text"
                size="small"
                icon={<StarOutlined />}
                onClick={() => handleSetDefault(model)}
              >
                设为默认
              </Button>
            )}
          </Space>
          <Popconfirm
            title="确定要删除此模型吗？"
            description="删除后无法恢复"
            onConfirm={() => handleDelete(model.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
            >
              删除
            </Button>
          </Popconfirm>
        </div>
      </Card>
    </Col>
  )

  return (
    <div>
      {/* Header */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>模型配置</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          新建模型
        </Button>
      </div>

      {/* Type filter tabs */}
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={typeTabs.map((tab) => ({
          key: tab.key,
          label: tab.label,
        }))}
        style={{ marginBottom: 16 }}
      />

      {/* Model list */}
      <Spin spinning={loading}>
        {filteredModels.length === 0 ? (
          <Empty
            description={activeTab === 'all' ? '暂无模型配置' : `暂无${typeLabels[activeTab as ModelType] || ''}模型`}
            style={{ padding: '40px 0' }}
          >
            <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
              新建模型
            </Button>
          </Empty>
        ) : (
          <Row gutter={[16, 16]}>
            {filteredModels.map(renderModelCard)}
          </Row>
        )}
      </Spin>

      {/* ModelForm Modal */}
      <ModelForm
        open={formModalOpen}
        model={editingModel}
        onClose={() => {
          setFormModalOpen(false)
          setEditingModel(null)
        }}
        onSuccess={() => {
          setFormModalOpen(false)
          setEditingModel(null)
          fetchList()
        }}
      />
    </div>
  )
}

export default ModelList
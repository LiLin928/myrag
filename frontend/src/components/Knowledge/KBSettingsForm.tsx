import { useEffect, useState } from 'react'
import { Form, Input, Select, InputNumber, Slider, Switch, Button, message, Spin, Divider, Card, Typography } from 'antd'
import { SaveOutlined } from '@ant-design/icons'
import { useKnowledgeStore } from '../../stores/knowledgeStore'
import { CreateKnowledgeBaseRequest } from '../../types/models'

const { Title } = Typography

interface KBSettingsFormProps {
  knowledgeId: string
}

export function KBSettingsForm({ knowledgeId }: KBSettingsFormProps) {
  const { currentKnowledge, loading, update } = useKnowledgeStore()
  const [form] = Form.useForm()
  const [saving, setSaving] = useState(false)

  // Populate form when currentKnowledge changes
  // Note: fetchOne is called in Detail.tsx, no need to call here
  useEffect(() => {
    if (currentKnowledge) {
      form.setFieldsValue({
        // Basic info
        name: currentKnowledge.name,
        description: currentKnowledge.description,
        // Chunking settings
        chunk_strategy: currentKnowledge.chunk_strategy,
        chunk_size: currentKnowledge.chunk_size,
        chunk_overlap: currentKnowledge.chunk_overlap,
        // Retrieval settings
        embedding_model: currentKnowledge.embedding_model,
        retrieval_method: currentKnowledge.retrieval_method,
        retrieval_top_k: currentKnowledge.retrieval_top_k,
        similarity_threshold: currentKnowledge.similarity_threshold,
        // Hybrid weights
        vector_weight: currentKnowledge.vector_weight,
        keyword_weight: currentKnowledge.keyword_weight,
        // Rerank settings
        rerank_enabled: currentKnowledge.rerank_enabled,
        rerank_model: currentKnowledge.rerank_model || 'bge-reranker-v2-m3',
        rerank_top_n: currentKnowledge.rerank_top_n,
      })
    }
  }, [currentKnowledge, form])

  // Watch form values for conditional rendering
  const retrievalMethod = Form.useWatch('retrieval_method', form)
  const rerankEnabled = Form.useWatch('rerank_enabled', form)

  const handleSave = async (values: CreateKnowledgeBaseRequest) => {
    setSaving(true)
    try {
      await update(knowledgeId, values)
      message.success('设置已保存')
    } catch (error: any) {
      message.error(error.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  if (loading && !currentKnowledge) {
    return (
      <div style={{ textAlign: 'center', padding: '40px 0' }}>
        <Spin tip="加载中..." />
      </div>
    )
  }

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSave}
    >
      {/* Basic Information */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Title level={5} style={{ marginBottom: 16 }}>基本信息</Title>
        <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
          <Input placeholder="知识库名称" />
        </Form.Item>
        <Form.Item name="description" label="描述">
          <Input.TextArea rows={3} placeholder="知识库描述（可选）" />
        </Form.Item>
      </Card>

      {/* Chunking Settings */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Title level={5} style={{ marginBottom: 16 }}>分块设置</Title>
        <Form.Item name="chunk_strategy" label="分块策略" tooltip="选择文档分块的策略">
          <Select options={[
            { value: 'auto', label: '自动（推荐）' },
            { value: 'structured', label: '结构化' },
            { value: 'semantic', label: '语义' },
            { value: 'fixed', label: '固定大小' },
          ]} />
        </Form.Item>
        <Form.Item name="chunk_size" label="分块大小" tooltip="每个分块的最大字符数">
          <InputNumber min={100} max={2000} addonAfter="字符" style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="chunk_overlap" label="重叠大小" tooltip="相邻分块之间的重叠字符数">
          <InputNumber min={0} max={500} addonAfter="字符" style={{ width: '100%' }} />
        </Form.Item>
      </Card>

      {/* Retrieval Settings */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Title level={5} style={{ marginBottom: 16 }}>检索设置</Title>
        <Form.Item name="embedding_model" label="向量模型" tooltip="用于生成文档向量的模型">
          <Select options={[
            { value: 'text-embedding-3-small', label: 'OpenAI text-embedding-3-small（推荐）' },
            { value: 'text-embedding-3-large', label: 'OpenAI text-embedding-3-large' },
            { value: 'bge-large-zh', label: 'BGE Large Chinese' },
          ]} />
        </Form.Item>
        <Form.Item name="retrieval_method" label="检索方法" tooltip="选择检索文档的方式">
          <Select options={[
            { value: 'vector', label: '向量检索' },
            { value: 'keyword', label: '关键词检索' },
            { value: 'hybrid', label: '混合检索（推荐）' },
          ]} />
        </Form.Item>
        <Form.Item name="retrieval_top_k" label="返回数量" tooltip="检索返回的文档数量">
          <InputNumber min={1} max={100} addonAfter="条" style={{ width: '100%' }} />
        </Form.Item>
        <Form.Item name="similarity_threshold" label="相似度阈值" tooltip="低于此阈值的文档将被过滤">
          <Slider min={0} max={1} step={0.1} marks={{ 0: '0', 0.5: '0.5', 1: '1' }} />
        </Form.Item>

        {/* Hybrid weights - only show when retrieval_method is 'hybrid' */}
        {retrievalMethod === 'hybrid' && (
          <>
            <Divider style={{ margin: '12px 0' }} />
            <Form.Item name="vector_weight" label="向量权重" tooltip="向量检索结果的权重">
              <Slider min={0} max={1} step={0.1} marks={{ 0: '0', 0.5: '0.5', 1: '1' }} />
            </Form.Item>
            <Form.Item name="keyword_weight" label="关键词权重" tooltip="关键词检索结果的权重">
              <Slider min={0} max={1} step={0.1} marks={{ 0: '0', 0.5: '0.5', 1: '1' }} />
            </Form.Item>
          </>
        )}
      </Card>

      {/* Rerank Settings */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Title level={5} style={{ marginBottom: 16 }}>Rerank 设置</Title>
        <Form.Item name="rerank_enabled" label="启用 Rerank" valuePropName="checked" tooltip="启用后对检索结果进行重排序">
          <Switch checkedChildren="开" unCheckedChildren="关" />
        </Form.Item>

        {/* Rerank model and top_n - only show when rerank_enabled is true */}
        {rerankEnabled && (
          <>
            <Form.Item name="rerank_model" label="Rerank 模型" tooltip="用于重排序的模型">
              <Select options={[
                { value: 'bge-reranker-v2-m3', label: 'BGE Reranker v2' },
                { value: 'cohere-rerank', label: 'Cohere Rerank' },
              ]} />
            </Form.Item>
            <Form.Item name="rerank_top_n" label="Rerank 返回数量" tooltip="Rerank 后返回的文档数量">
              <InputNumber min={1} max={50} addonAfter="条" style={{ width: '100%' }} />
            </Form.Item>
          </>
        )}
      </Card>

      {/* Save Button */}
      <Form.Item style={{ marginBottom: 0 }}>
        <Button
          type="primary"
          htmlType="submit"
          icon={<SaveOutlined />}
          loading={saving}
          block
        >
          保存设置
        </Button>
      </Form.Item>
    </Form>
  )
}
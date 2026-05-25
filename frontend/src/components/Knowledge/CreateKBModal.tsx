import { useState, useEffect } from 'react'
import { Modal, Form, Input, Select, InputNumber, Slider, Switch, Steps, Button, Space, Spin, Alert } from 'antd'
import { useKnowledgeStore } from '../../stores/knowledgeStore'
import { modelApi, ModelConfig } from '../../api/models'
import { CreateKnowledgeBaseRequest } from '../../types/models'

interface CreateKBModalProps {
  open: boolean
  onClose: () => void
}

export function CreateKBModal({ open, onClose }: CreateKBModalProps) {
  const { create } = useKnowledgeStore()
  const [currentStep, setCurrentStep] = useState(0)
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [embeddingModels, setEmbeddingModels] = useState<{ value: string; label: string; model: ModelConfig }[]>([])
  const [rerankModels, setRerankModels] = useState<{ value: string; label: string; model: ModelConfig }[]>([])
  const [modelsLoading, setModelsLoading] = useState(false)
  const [hasEmbeddingModel, setHasEmbeddingModel] = useState(true)

  // 加载模型列表
  useEffect(() => {
    if (open) {
      setModelsLoading(true)
      Promise.all([
        modelApi.list('embedding', true),
        modelApi.list('rerank', true),
      ])
        .then(([embeddingRes, rerankRes]) => {
          // 处理 embedding 模型
          const embOpts = (embeddingRes.items || []).map(m => ({
            value: m.id,
            label: `${m.name} (${m.model_name})`,
            model: m,
          }))
          setEmbeddingModels(embOpts)
          setHasEmbeddingModel(embOpts.length > 0)
          if (embOpts.length > 0) {
            const defaultEmb = embeddingRes.items.find(m => m.is_default)
            form.setFieldValue('embedding_model', defaultEmb?.id || embOpts[0].value)
          }

          // 处理 rerank 模型
          const rerankOpts = (rerankRes.items || []).map(m => ({
            value: m.id,
            label: `${m.name} (${m.model_name})`,
            model: m,
          }))
          setRerankModels(rerankOpts)
          if (rerankOpts.length > 0) {
            const defaultRerank = rerankRes.items.find(m => m.is_default)
            form.setFieldValue('rerank_model', defaultRerank?.id || rerankOpts[0].value)
          }
        })
        .catch(err => console.error('加载模型失败:', err))
        .finally(() => setModelsLoading(false))
    }
  }, [open])

  const handleFinish = async (values: CreateKnowledgeBaseRequest) => {
    setLoading(true)
    try {
      // 确保数值字段正确
      const payload = {
        ...values,
        similarity_threshold: values.similarity_threshold ?? 0.5,
        vector_weight: values.vector_weight ?? 0.7,
        keyword_weight: values.keyword_weight ?? 0.3,
        rerank_enabled: values.rerank_enabled ?? false,
        rerank_model: values.rerank_enabled ? values.rerank_model : null,
      }
      console.log('创建知识库 payload:', payload)
      await create(payload as CreateKnowledgeBaseRequest)
      Modal.success({ content: '知识库创建成功' })
      form.resetFields()
      setCurrentStep(0)
      onClose()
    } catch (error: any) {
      console.error('创建失败:', error)
      Modal.error({ content: error.response?.data?.detail || error.message || '创建失败' })
    } finally {
      setLoading(false)
    }
  }

  const handleNext = async () => {
    try {
      // 根据当前步骤验证不同字段
      if (currentStep === 0) {
        await form.validateFields(['name', 'description'])
      } else if (currentStep === 1) {
        await form.validateFields(['chunk_strategy', 'chunk_size', 'chunk_overlap'])
      } else if (currentStep === 2) {
        await form.validateFields(['embedding_model', 'retrieval_method', 'retrieval_top_k'])
        // 如果启用了 rerank，需要验证 rerank_model
        if (form.getFieldValue('rerank_enabled')) {
          await form.validateFields(['rerank_model'])
        }
      }
      setCurrentStep(currentStep + 1)
    } catch (error: any) {
      console.error('验证失败:', error)
    }
  }

  const handlePrev = () => {
    setCurrentStep(currentStep - 1)
  }

  const retrievalMethod = Form.useWatch('retrieval_method', form)
  const rerankEnabled = Form.useWatch('rerank_enabled', form)

  const stepTitles = ['基本信息', '分块设置', '向量与检索']

  return (
    <Modal
      title="创建知识库"
      open={open}
      onCancel={onClose}
      footer={null}
      width={600}
    >
      <Steps current={currentStep} style={{ marginBottom: 24 }}>
        {stepTitles.map((title) => (
          <Steps.Step key={title} title={title} />
        ))}
      </Steps>

      <Form form={form} layout="vertical" onFinish={handleFinish}>
        {/* 所有步骤的表单字段都要渲染，只显示当前步骤的内容 */}
        <div style={{ display: currentStep === 0 ? 'block' : 'none' }}>
          <Form.Item name="name" label="名称" rules={[{ required: true, message: '请输入名称' }]}>
            <Input placeholder="知识库名称" />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input.TextArea rows={3} placeholder="知识库描述（可选）" />
          </Form.Item>
        </div>

        <div style={{ display: currentStep === 1 ? 'block' : 'none' }}>
          <Form.Item name="chunk_strategy" label="分块策略" initialValue="auto">
            <Select options={[
              { value: 'auto', label: '自动（推荐）' },
              { value: 'structured', label: '结构化' },
              { value: 'semantic', label: '语义' },
              { value: 'fixed', label: '固定大小' },
            ]} />
          </Form.Item>
          <Form.Item name="chunk_size" label="分块大小" initialValue={800}>
            <InputNumber min={100} max={2000} addonAfter="字符" />
          </Form.Item>
          <Form.Item name="chunk_overlap" label="重叠大小" initialValue={100}>
            <InputNumber min={0} max={500} addonAfter="字符" />
          </Form.Item>
        </div>

        <div style={{ display: currentStep === 2 ? 'block' : 'none' }}>
          {modelsLoading ? (
            <Spin tip="加载模型列表..." />
          ) : !hasEmbeddingModel ? (
            <Alert
              type="warning"
              message="请先配置向量模型"
              description="您尚未配置任何向量模型，请前往「模型设置」页面添加向量模型后再创建知识库。"
              showIcon
            />
          ) : (
            <>
              <Form.Item
                name="embedding_model"
                label="向量模型"
                rules={[{ required: true, message: '请选择向量模型' }]}
              >
                <Select
                  options={embeddingModels}
                  placeholder="选择向量模型"
                />
              </Form.Item>
              <Form.Item name="retrieval_method" label="检索方法" initialValue="hybrid">
                <Select options={[
                  { value: 'vector', label: '向量检索' },
                  { value: 'keyword', label: '关键词检索' },
                  { value: 'hybrid', label: '混合检索（推荐）' },
                ]} />
              </Form.Item>
              <Form.Item name="retrieval_top_k" label="返回数量" initialValue={10}>
                <InputNumber min={1} max={100} addonAfter="条" />
              </Form.Item>
              <Form.Item name="similarity_threshold" label="相似度阈值" initialValue={0.5}>
                <Slider min={0} max={1} step={0.1} marks={{ 0: '0', 0.5: '0.5', 1: '1' }} />
              </Form.Item>

              {retrievalMethod === 'hybrid' && (
                <>
                  <Form.Item name="vector_weight" label="向量权重" initialValue={0.7}>
                    <Slider min={0} max={1} step={0.1} marks={{ 0: '0', 0.7: '0.7', 1: '1' }} />
                  </Form.Item>
                  <Form.Item name="keyword_weight" label="关键词权重" initialValue={0.3}>
                    <Slider min={0} max={1} step={0.1} marks={{ 0: '0', 0.3: '0.3', 1: '1' }} />
                  </Form.Item>
                </>
              )}

              <Form.Item name="rerank_enabled" label="启用 Rerank" initialValue={false}>
                <Switch />
              </Form.Item>

              {rerankEnabled && (
                <Form.Item name="rerank_model" label="Rerank 模型">
                  <Select
                    options={rerankModels}
                    placeholder={rerankModels.length === 0 ? '请先在模型设置中配置Rerank模型' : '选择Rerank模型'}
                  />
                </Form.Item>
              )}
            </>
          )}
        </div>

        <Space style={{ width: '100%', justifyContent: 'space-between', marginTop: 24 }}>
          <Button onClick={onClose}>取消</Button>
          <Space>
            {currentStep > 0 && <Button onClick={handlePrev}>上一步</Button>}
            {currentStep < stepTitles.length - 1 && (
              <Button type="primary" onClick={handleNext}>下一步</Button>
            )}
            {currentStep === stepTitles.length - 1 && hasEmbeddingModel && (
              <Button type="primary" htmlType="submit" loading={loading}>创建</Button>
            )}
          </Space>
        </Space>
      </Form>
    </Modal>
  )
}
import { useEffect, useState } from 'react'
import { Modal, Form, Input, Select, Switch, InputNumber, Steps, Button, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import { useChatStore } from '../../stores/chatStore'
import { useKnowledgeStore } from '../../stores/knowledgeStore'
import { systemPromptsApi } from '../../api/systemPrompts'
import { workflowApi } from '../../api/workflows'
import type { SystemPromptTemplate, Workflow, ConversationConfig } from '../../types/models'

interface CreateModalProps {
  open: boolean
  onClose: () => void
}

interface FormValues {
  // Step 1
  mode: 'model' | 'workflow'
  title?: string
  // Step 2A - Model mode
  model?: string
  knowledge_base_ids?: string[]
  kb_config_enabled?: boolean
  top_k?: number
  threshold?: number
  search_type?: 'vector' | 'keyword' | 'hybrid'
  temperature?: number
  max_tokens?: number
  // Step 2B - Workflow mode
  workflow_id?: string
  // Step 3
  system_prompt_template_id?: string
  custom_prompt_enabled?: boolean
  custom_system_prompt?: string
  greeting_enabled?: boolean
  greeting_content?: string
}

export function CreateModal({ open, onClose }: CreateModalProps) {
  const navigate = useNavigate()
  const { create } = useChatStore()
  const { knowledgeBases, fetchList: fetchKnowledgeBases } = useKnowledgeStore()
  const [form] = Form.useForm<FormValues>()
  const [currentStep, setCurrentStep] = useState(0)
  const [loading, setLoading] = useState(false)
  const [templates, setTemplates] = useState<SystemPromptTemplate[]>([])
  const [workflows, setWorkflows] = useState<Workflow[]>([])

  // Watch mode field to determine which step 2 to show
  const mode = Form.useWatch('mode', form)

  useEffect(() => {
    if (open) {
      fetchKnowledgeBases()
      loadTemplates()
      loadWorkflows()
    }
  }, [open])

  const loadTemplates = async () => {
    try {
      const response = await systemPromptsApi.list()
      setTemplates(response.data)
    } catch {
      // Ignore errors
    }
  }

  const loadWorkflows = async () => {
    try {
      const response = await workflowApi.list()
      setWorkflows(response.data.filter(w => w.status === 'published'))
    } catch {
      // Ignore errors
    }
  }

  const handleNext = async () => {
    try {
      await form.validateFields()
      setCurrentStep(currentStep + 1)
    } catch {
      // Validation failed
    }
  }

  const handlePrev = () => {
    setCurrentStep(currentStep - 1)
  }

  const handleFinish = async () => {
    try {
      await form.validateFields()
      setLoading(true)
      const values = form.getFieldsValue()

      // Build config for model mode
      let config: ConversationConfig | undefined
      if (values.mode === 'model') {
        config = {
          knowledge_base_ids: values.knowledge_base_ids || [],
          knowledge_base_config: values.kb_config_enabled
            ? {
                top_k: values.top_k || 5,
                threshold: values.threshold || 0.7,
                search_type: values.search_type || 'vector',
              }
            : null,
          tools_enabled: false,
          tool_ids: [],
          skills_enabled: false,
          skill_ids: [],
          temperature: values.temperature ?? 0.7,
          max_tokens: values.max_tokens || 4096,
        }
      }

      const conv = await create({
        title: values.title,
        mode: values.mode,
        model: values.mode === 'model' ? values.model : undefined,
        config,
        workflow_id: values.mode === 'workflow' ? values.workflow_id : undefined,
        system_prompt_template_id: values.system_prompt_template_id,
        custom_system_prompt: values.custom_prompt_enabled ? values.custom_system_prompt : undefined,
        greeting_enabled: values.greeting_enabled,
        greeting_content: values.greeting_enabled ? values.greeting_content : undefined,
      })

      message.success('创建成功')
      form.resetFields()
      setCurrentStep(0)
      onClose()
      navigate(`/chat/${conv.id}`)
    } catch {
      message.error('创建失败')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    form.resetFields()
    setCurrentStep(0)
    onClose()
  }

  const steps = [
    { title: '选择模式' },
    { title: '配置' },
    { title: '系统提示词' },
  ]

  return (
    <Modal
      title="创建新对话"
      open={open}
      onCancel={handleClose}
      width={600}
      footer={null}
      destroyOnClose
    >
      <Steps current={currentStep} items={steps} style={{ marginBottom: 24 }} />

      <Form
        form={form}
        layout="vertical"
        initialValues={{
          mode: 'model',
          model: 'gpt-4o-mini',
          top_k: 5,
          threshold: 0.7,
          search_type: 'vector',
          temperature: 0.7,
          max_tokens: 4096,
          kb_config_enabled: false,
          custom_prompt_enabled: false,
          greeting_enabled: false,
        }}
      >
        {/* Step 1: 选择模式 */}
        <div style={{ display: currentStep === 0 ? 'block' : 'none' }}>
          <Form.Item
            name="mode"
            label="模式"
            rules={[{ required: true, message: '请选择模式' }]}
          >
            <Select
              options={[
                { value: 'model', label: '模型模式 - 使用 LLM 进行对话' },
                { value: 'workflow', label: '工作流模式 - 执行预定义工作流' },
              ]}
            />
          </Form.Item>
          <Form.Item name="title" label="标题">
            <Input placeholder="可选，不填则自动生成" />
          </Form.Item>
        </div>

        {/* Step 2A: 模型模式配置 */}
        <div style={{ display: currentStep === 1 && mode === 'model' ? 'block' : 'none' }}>
          <Form.Item
            name="model"
            label="模型"
            rules={[{ required: mode === 'model', message: '请选择模型' }]}
          >
            <Select
              options={[
                { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
                { value: 'gpt-4o', label: 'GPT-4o' },
                { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6' },
              ]}
            />
          </Form.Item>

          <Form.Item name="knowledge_base_ids" label="知识库">
            <Select
              mode="multiple"
              placeholder="选择知识库（可选）"
              options={knowledgeBases.map(kb => ({
                value: kb.id,
                label: kb.name,
              }))}
              allowClear
            />
          </Form.Item>

          <Form.Item name="kb_config_enabled" label="知识库检索配置" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item shouldUpdate={(prev, curr) => prev.kb_config_enabled !== curr.kb_config_enabled}>
            {({ getFieldValue }) =>
              getFieldValue('kb_config_enabled') ? (
                <>
                  <Form.Item name="search_type" label="搜索类型">
                    <Select
                      options={[
                        { value: 'vector', label: '向量检索' },
                        { value: 'keyword', label: '关键词检索' },
                        { value: 'hybrid', label: '混合检索' },
                      ]}
                    />
                  </Form.Item>
                  <Form.Item name="top_k" label="返回数量 (Top K)">
                    <InputNumber min={1} max={20} style={{ width: '100%' }} />
                  </Form.Item>
                  <Form.Item name="threshold" label="相似度阈值">
                    <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
                  </Form.Item>
                </>
              ) : null
            }
          </Form.Item>

          <Form.Item name="temperature" label="温度 (Temperature)">
            <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="max_tokens" label="最大输出令牌数 (Max Tokens)">
            <InputNumber min={256} max={32768} step={256} style={{ width: '100%' }} />
          </Form.Item>
        </div>

        {/* Step 2B: 工作流模式配置 */}
        <div style={{ display: currentStep === 1 && mode === 'workflow' ? 'block' : 'none' }}>
          <Form.Item
            name="workflow_id"
            label="工作流"
            rules={[{ required: mode === 'workflow', message: '请选择工作流' }]}
          >
            <Select
              placeholder="选择工作流"
              options={workflows.map(w => ({
                value: w.id,
                label: w.name,
              }))}
            />
          </Form.Item>
        </div>

        {/* Step 3: 系统提示词设置 */}
        <div style={{ display: currentStep === 2 ? 'block' : 'none' }}>
          <Form.Item name="system_prompt_template_id" label="系统提示词模板">
            <Select
              placeholder="选择模板（可选）"
              options={templates.map(t => ({
                value: t.id,
                label: t.name,
              }))}
              allowClear
            />
          </Form.Item>

          <Form.Item name="custom_prompt_enabled" label="自定义提示词" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item shouldUpdate={(prev, curr) => prev.custom_prompt_enabled !== curr.custom_prompt_enabled}>
            {({ getFieldValue }) =>
              getFieldValue('custom_prompt_enabled') ? (
                <Form.Item name="custom_system_prompt" label="自定义系统提示词">
                  <Input.TextArea rows={4} placeholder="输入自定义系统提示词" />
                </Form.Item>
              ) : null
            }
          </Form.Item>

          <Form.Item name="greeting_enabled" label="开场白" valuePropName="checked">
            <Switch checkedChildren="启用" unCheckedChildren="禁用" />
          </Form.Item>

          <Form.Item shouldUpdate={(prev, curr) => prev.greeting_enabled !== curr.greeting_enabled}>
            {({ getFieldValue }) =>
              getFieldValue('greeting_enabled') ? (
                <Form.Item name="greeting_content" label="开场白内容">
                  <Input.TextArea rows={3} placeholder="输入开场白内容，将在对话开始时自动发送" />
                </Form.Item>
              ) : null
            }
          </Form.Item>
        </div>
      </Form>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 24 }}>
        {currentStep > 0 && (
          <Button onClick={handlePrev}>上一步</Button>
        )}
        {currentStep < 2 ? (
          <Button type="primary" onClick={handleNext}>
            下一步
          </Button>
        ) : (
          <Button type="primary" loading={loading} onClick={handleFinish}>
            创建
          </Button>
        )}
      </div>
    </Modal>
  )
}
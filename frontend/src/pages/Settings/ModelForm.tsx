import { useEffect } from 'react'
import { Modal, Form, Input, Select, InputNumber, Divider, message } from 'antd'
import { useModelStore } from '../../stores/modelStore'
import { ModelConfig, CreateModelRequest, UpdateModelRequest } from '../../api/models'

interface ModelFormProps {
  open: boolean
  model?: ModelConfig | null
  onClose: () => void
  onSuccess: () => void
}

// Provider options
const providerOptions = [
  { value: 'OpenAI', label: 'OpenAI' },
  { value: 'Azure', label: 'Azure OpenAI' },
  { value: 'Anthropic', label: 'Anthropic' },
  { value: 'Custom', label: 'Custom' },
]

// Model type options
const typeOptions = [
  { value: 'llm', label: 'LLM' },
  { value: 'embedding', label: 'Embedding' },
  { value: 'rerank', label: 'Rerank' },
]

// Mask API key for display (show last 4 chars if available)
function maskApiKey(apiKey: string): string {
  if (!apiKey) return ''
  if (apiKey.length <= 4) return '****'
  return `${apiKey.slice(0, 4)}****`
}

export function ModelForm({ open, model, onClose, onSuccess }: ModelFormProps) {
  const [form] = Form.useForm()
  const { create, update } = useModelStore()
  const isEditing = !!model

  // Watch the type field for dynamic fields
  const modelType = Form.useWatch('type', form)

  // Reset form and set initial values when modal opens/closes or model changes
  useEffect(() => {
    if (open) {
      if (model) {
        // Editing: pre-fill all fields
        form.setFieldsValue({
          name: model.name,
          type: model.type,
          provider: model.provider,
          api_base: model.api_base,
          api_key: maskApiKey(model.api_key),
          model_name: model.model_name,
          timeout: model.timeout || 30,
          // Dynamic fields based on type
          context_length: model.context_length,
          max_tokens: model.max_tokens,
          temperature: model.temperature,
          dimension: model.dimension,
          batch_size: model.batch_size,
          top_k: model.top_k,
        })
      } else {
        // Creating: reset to defaults
        form.resetFields()
        form.setFieldsValue({
          type: 'llm',
          provider: 'OpenAI',
          timeout: 30,
        })
      }
    }
  }, [open, model, form])

  // Handle form submission
  const handleSubmit = async (values: any) => {
    try {
      // Process api_key: if it contains "***", it means user didn't change it
      const apiKey = values.api_key
      const shouldSubmitApiKey = !isEditing || (apiKey && !apiKey.includes('****'))

      // Build request data
      const data: CreateModelRequest | UpdateModelRequest = {
        name: values.name,
        provider: values.provider,
        api_base: values.api_base,
        model_name: values.model_name,
        timeout: values.timeout || 30,
      }

      // Only include api_key if it was changed or is a new model
      if (shouldSubmitApiKey && apiKey) {
        data.api_key = apiKey
      }

      // Add type for create only
      if (!isEditing) {
        (data as CreateModelRequest).type = values.type
      }

      // Add dynamic fields based on type
      if (values.type === 'llm') {
        if (values.context_length !== undefined) data.context_length = values.context_length
        if (values.max_tokens !== undefined) data.max_tokens = values.max_tokens
        if (values.temperature !== undefined) data.temperature = values.temperature
      } else if (values.type === 'embedding') {
        if (values.dimension !== undefined) data.dimension = values.dimension
        if (values.batch_size !== undefined) data.batch_size = values.batch_size
      } else if (values.type === 'rerank') {
        if (values.top_k !== undefined) data.top_k = values.top_k
        if (values.batch_size !== undefined) data.batch_size = values.batch_size
      }

      if (isEditing && model) {
        await update(model.id, data as UpdateModelRequest)
        message.success('模型更新成功')
      } else {
        await create(data as CreateModelRequest)
        message.success('模型创建成功')
      }

      form.resetFields()
      onSuccess()
    } catch (error: any) {
      message.error(error.response?.data?.message || (isEditing ? '更新失败' : '创建失败'))
    }
  }

  // Handle modal close
  const handleClose = () => {
    form.resetFields()
    onClose()
  }

  return (
    <Modal
      title={isEditing ? '编辑模型' : '新建模型'}
      open={open}
      onCancel={handleClose}
      onOk={() => form.submit()}
      okText={isEditing ? '保存' : '创建'}
      cancelText="取消"
      width={600}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        onFinish={handleSubmit}
        initialValues={{
          type: 'llm',
          provider: 'OpenAI',
          timeout: 30,
        }}
      >
        {/* Basic Information Section */}
        <Divider orientation="left" plain style={{ margin: '12px 0' }}>
          基本配置
        </Divider>

        <Form.Item
          name="name"
          label="模型名称"
          rules={[
            { required: true, message: '请输入模型名称' },
            { max: 100, message: '名称最多100个字符' },
          ]}
        >
          <Input placeholder="给模型起一个名称" maxLength={100} />
        </Form.Item>

        <Form.Item
          name="type"
          label="模型类型"
          rules={[{ required: true, message: '请选择模型类型' }]}
        >
          <Select
            options={typeOptions}
            placeholder="选择模型类型"
            disabled={isEditing}
          />
        </Form.Item>

        <Form.Item
          name="provider"
          label="提供商"
          rules={[{ required: true, message: '请选择提供商' }]}
        >
          <Select options={providerOptions} placeholder="选择提供商" />
        </Form.Item>

        <Form.Item
          name="api_base"
          label="API Base URL"
          rules={[
            { required: true, message: '请输入API Base URL' },
            { type: 'url', message: '请输入有效的URL' },
          ]}
        >
          <Input placeholder="https://api.openai.com/v1" />
        </Form.Item>

        <Form.Item
          name="api_key"
          label="API Key"
          rules={isEditing ? [] : [{ required: true, message: '请输入API Key' }]}
          extra={isEditing ? '留空或显示为 **** 表示保持原值不变' : undefined}
        >
          <Input.Password placeholder={isEditing ? '留空保持原值' : '输入API Key'} />
        </Form.Item>

        <Form.Item
          name="model_name"
          label="模型标识"
          rules={[{ required: true, message: '请输入模型标识' }]}
        >
          <Input placeholder="gpt-4, text-embedding-ada-002, 等" />
        </Form.Item>

        <Form.Item
          name="timeout"
          label="超时时间(秒)"
          rules={[{ required: true, message: '请输入超时时间' }]}
        >
          <InputNumber min={1} max={600} style={{ width: '100%' }} />
        </Form.Item>

        {/* Dynamic Fields Based on Type */}
        {modelType === 'llm' && (
          <>
            <Divider orientation="left" plain style={{ margin: '12px 0' }}>
              LLM 配置
            </Divider>

            <Form.Item
              name="context_length"
              label="上下文长度"
              extra="模型支持的最大上下文token数"
            >
              <InputNumber min={1} style={{ width: '100%' }} placeholder="如: 8192" />
            </Form.Item>

            <Form.Item
              name="max_tokens"
              label="最大输出Token"
              extra="模型输出的最大token数"
            >
              <InputNumber min={1} style={{ width: '100%' }} placeholder="如: 4096" />
            </Form.Item>

            <Form.Item
              name="temperature"
              label="温度 (0-100)"
              extra="控制输出的随机性，0表示确定性输出"
              rules={[
                { type: 'number', min: 0, max: 100, message: '温度范围0-100' },
              ]}
            >
              <InputNumber min={0} max={100} precision={0} style={{ width: '100%' }} />
            </Form.Item>
          </>
        )}

        {modelType === 'embedding' && (
          <>
            <Divider orientation="left" plain style={{ margin: '12px 0' }}>
              Embedding 配置
            </Divider>

            <Form.Item
              name="dimension"
              label="向量维度"
              extra="Embedding向量的维度"
            >
              <InputNumber min={1} style={{ width: '100%' }} placeholder="如: 1536" />
            </Form.Item>

            <Form.Item
              name="batch_size"
              label="批处理大小"
              extra="批量Embedding时的批次大小"
            >
              <InputNumber min={1} style={{ width: '100%' }} placeholder="如: 100" />
            </Form.Item>
          </>
        )}

        {modelType === 'rerank' && (
          <>
            <Divider orientation="left" plain style={{ margin: '12px 0' }}>
              Rerank 配置
            </Divider>

            <Form.Item
              name="top_k"
              label="Top K"
              extra="Rerank返回的top结果数量"
            >
              <InputNumber min={1} style={{ width: '100%' }} placeholder="如: 10" />
            </Form.Item>

            <Form.Item
              name="batch_size"
              label="批处理大小"
              extra="批量Rerank时的批次大小"
            >
              <InputNumber min={1} style={{ width: '100%' }} placeholder="如: 100" />
            </Form.Item>
          </>
        )}
      </Form>
    </Modal>
  )
}

export default ModelForm
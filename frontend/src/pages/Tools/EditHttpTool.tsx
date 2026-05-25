import { useEffect } from 'react'
import { Form, Input, Select, Switch, Button, Space, message, Divider, InputNumber } from 'antd'
import { useToolStore } from '../../stores/toolStore'
import { Tool, CreateToolRequest, HttpToolConfig } from '../../types/models'

interface EditHttpToolProps {
  tool: Tool | null
  onClose: () => void
}

export function EditHttpTool({ tool, onClose }: EditHttpToolProps) {
  const [form] = Form.useForm()
  const { create, update, fetchList } = useToolStore()

  useEffect(() => {
    if (tool) {
      form.setFieldsValue({
        name: tool.name,
        description: tool.description,
        is_public: tool.is_public,
        url: tool.config?.url || '',
        method: tool.config?.method || 'GET',
        headers: tool.config?.headers ? JSON.stringify(tool.config.headers, null, 2) : '',
        body_template: tool.config?.body_template ? JSON.stringify(tool.config.body_template, null, 2) : '',
        timeout: tool.config?.timeout || 30000,
        input_schema: tool.input_schema ? JSON.stringify(tool.input_schema, null, 2) : '',
      })
    } else {
      form.resetFields()
      form.setFieldsValue({
        method: 'GET',
        timeout: 30000,
        is_public: false,
      })
    }
  }, [tool, form])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()

      let bodyTemplate = {}
      if (values.body_template) {
        try {
          bodyTemplate = JSON.parse(values.body_template)
        } catch {
          message.error('请求体模板格式错误，请检查 JSON 格式')
          return
        }
      }

      let headers = {}
      if (values.headers) {
        try {
          headers = JSON.parse(values.headers)
        } catch {
          message.error('请求头格式错误，请检查 JSON 格式')
          return
        }
      }

      let inputSchema = null
      if (values.input_schema) {
        try {
          inputSchema = JSON.parse(values.input_schema)
        } catch {
          message.error('输入参数 Schema 格式错误，请检查 JSON 格式')
          return
        }
      }

      const config: HttpToolConfig = {
        url: values.url,
        method: values.method,
        headers,
        body_template: bodyTemplate,
        timeout: values.timeout,
      }

      const data: CreateToolRequest = {
        name: values.name,
        description: values.description,
        config,
        input_schema: inputSchema,
        is_public: values.is_public,
      }

      if (tool) {
        await update(tool.id, data)
        message.success('更新成功')
      } else {
        await create(data)
        message.success('创建成功')
      }

      fetchList()
      onClose()
    } catch {
      message.error(tool ? '更新失败' : '创建失败')
    }
  }

  return (
    <Form
      form={form}
      layout="vertical"
      onFinish={handleSubmit}
    >
      <Form.Item
        name="name"
        label="工具名称"
        rules={[{ required: true, message: '请输入工具名称' }]}
      >
        <Input placeholder="例如: weather_api" />
      </Form.Item>

      <Form.Item
        name="description"
        label="描述"
      >
        <Input.TextArea rows={2} placeholder="工具功能描述" />
      </Form.Item>

      <Form.Item
        name="is_public"
        label="公开"
        valuePropName="checked"
      >
        <Switch checkedChildren="公开" unCheckedChildren="私有" />
      </Form.Item>

      <Divider>HTTP 配置</Divider>

      <Form.Item
        name="method"
        label="请求方法"
        rules={[{ required: true }]}
      >
        <Select
          options={[
            { value: 'GET', label: 'GET' },
            { value: 'POST', label: 'POST' },
            { value: 'PUT', label: 'PUT' },
            { value: 'PATCH', label: 'PATCH' },
            { value: 'DELETE', label: 'DELETE' },
          ]}
        />
      </Form.Item>

      <Form.Item
        name="url"
        label="请求 URL"
        rules={[{ required: true, message: '请输入 URL' }]}
        extra="支持模板变量，如: https://api.example.com/weather?city={{city}}"
      >
        <Input placeholder="https://api.example.com/endpoint?param={{param}}" />
      </Form.Item>

      <Form.Item
        name="headers"
        label="请求头 (JSON)"
      >
        <Input.TextArea
          rows={3}
          placeholder='{"Content-Type": "application/json"}'
        />
      </Form.Item>

      <Form.Item
        name="body_template"
        label="请求体模板 (JSON)"
      >
        <Input.TextArea
          rows={4}
          placeholder='{"key": "{{input.key}}"}'
        />
      </Form.Item>

      <Form.Item
        name="timeout"
        label="超时时间 (毫秒)"
      >
        <InputNumber min={1000} max={300000} style={{ width: '100%' }} />
      </Form.Item>

      <Divider>输入参数配置</Divider>

      <Form.Item
        name="input_schema"
        label="输入参数 Schema (JSON)"
        extra={'定义工具需要的输入参数，格式遵循 JSON Schema。示例: {"type":"object","properties":{"city":{"type":"string","title":"城市"}},"required":["city"]}'}
      >
        <Input.TextArea
          rows={6}
          placeholder={'{"type":"object","properties":{"city":{"type":"string","title":"城市","description":"查询的城市名称"}},"required":["city"]}'}
        />
      </Form.Item>

      <Form.Item>
        <Space>
          <Button type="primary" htmlType="submit">
            {tool ? '更新' : '创建'}
          </Button>
          <Button onClick={onClose}>取消</Button>
        </Space>
      </Form.Item>
    </Form>
  )
}
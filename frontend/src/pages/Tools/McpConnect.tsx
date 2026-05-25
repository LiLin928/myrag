import { useEffect, useState } from 'react'
import { Form, Input, Select, Button, Space, message, Divider, Switch, Collapse } from 'antd'
import { mcpApi, McpConnection } from '../../api/mcp'

interface TestResult {
  success: boolean
  available_tools?: number
  error?: string
}

interface SyncResult {
  success: boolean
  count?: number
  error?: string
}

const { TextArea } = Input

interface McpConnectProps {
  connection: McpConnection | null
  onClose: () => void
  onSync?: () => void
}

export function McpConnect({ connection, onClose, onSync }: McpConnectProps) {
  const [form] = Form.useForm()
  const [testing, setTesting] = useState(false)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    if (connection) {
      form.setFieldsValue({
        name: connection.name,
        description: connection.description,
        transport_type: connection.transport_type,
        connection_url: connection.connection_url,
        command: connection.command,
        args: connection.args?.join('\n'),
        env_vars: connection.env_vars
          ? Object.entries(connection.env_vars).map(([k, v]) => `${k}=${v}`).join('\n')
          : '',
        is_public: connection.is_public,
      })
    } else {
      form.resetFields()
    }
  }, [connection, form])

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()

      const args = values.args?.split('\n').filter(Boolean)
      const env_vars: Record<string, string> = {}
      values.env_vars?.split('\n').filter(Boolean).forEach((line: string) => {
        const [key, ...rest] = line.split('=')
        if (key) {
          env_vars[key] = rest.join('=')
        }
      })

      const data = {
        name: values.name,
        description: values.description,
        transport_type: values.transport_type,
        connection_url: values.connection_url,
        command: values.command,
        args,
        env_vars,
        is_public: values.is_public,
      }

      if (connection) {
        await mcpApi.updateConnection(connection.id, data)
        message.success('更新成功')
      } else {
        await mcpApi.createConnection(data)
        message.success('创建成功')
      }

      onClose()
      onSync?.()
    } catch {
      message.error('保存失败')
    }
  }

  const handleTest = async () => {
    if (!connection) return
    setTesting(true)
    try {
      const result = await mcpApi.testConnection(connection.id)
      const data = result.data as TestResult
      if (data.success) {
        message.success(`连接成功，可用工具: ${data.available_tools}`)
      } else {
        message.error(`连接失败: ${data.error}`)
      }
    } catch {
      message.error('测试失败')
    }
    setTesting(false)
  }

  const handleSync = async () => {
    if (!connection) return
    setSyncing(true)
    try {
      const result = await mcpApi.syncTools(connection.id)
      const data = result.data as SyncResult
      if (data.success) {
        message.success(`同步成功，已注册 ${data.count} 个工具`)
      } else {
        message.error(`同步失败: ${data.error}`)
      }
    } catch {
      message.error('同步失败')
    }
    setSyncing(false)
  }

  return (
    <Form form={form} layout="vertical">
      <Form.Item name="name" label="连接名称" rules={[{ required: true }]}>
        <Input placeholder="唯一名称" />
      </Form.Item>

      <Form.Item name="description" label="描述">
        <TextArea rows={2} placeholder="MCP Server 描述" />
      </Form.Item>

      <Form.Item name="transport_type" label="传输类型">
        <Select
          options={[
            { value: 'sse', label: 'SSE (HTTP Server-Sent Events)' },
            { value: 'websocket', label: 'WebSocket' },
            { value: 'stdio', label: 'Stdio (本地进程)' },
          ]}
        />
      </Form.Item>

      <Form.Item name="is_public" label="公开" valuePropName="checked">
        <Switch />
      </Form.Item>

      <Divider>连接配置</Divider>

      <Form.Item
        name="connection_url"
        label="连接 URL"
        rules={[{ required: true, message: 'SSE/WebSocket 需要填写 URL' }]}
      >
        <Input placeholder="http://localhost:8080/mcp" />
      </Form.Item>

      <Collapse>
        <Collapse.Panel header="Stdio 配置（可选）" key="stdio">
          <Form.Item name="command" label="启动命令">
            <Input placeholder="uvx mcp-server-xxx 或 python server.py" />
          </Form.Item>
          <Form.Item name="args" label="启动参数">
            <TextArea rows={3} placeholder="每行一个参数" />
          </Form.Item>
          <Form.Item name="env_vars" label="环境变量">
            <TextArea rows={3} placeholder="KEY=value 格式，每行一个" />
          </Form.Item>
        </Collapse.Panel>
      </Collapse>

      <Divider />

      <Space style={{ width: '100%', justifyContent: 'space-between' }}>
        {connection && (
          <Space>
            <Button onClick={handleTest} loading={testing}>
              测试连接
            </Button>
            <Button onClick={handleSync} loading={syncing}>
              同步工具
            </Button>
          </Space>
        )}
        <Space>
          <Button onClick={onClose}>取消</Button>
          <Button type="primary" onClick={handleSubmit}>
            {connection ? '更新' : '创建'}
          </Button>
        </Space>
      </Space>
    </Form>
  )
}
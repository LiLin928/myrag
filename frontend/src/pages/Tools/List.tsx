import { useEffect, useState } from 'react'
import { Card, Button, Space, Tag, Popconfirm, message, Row, Col, Input, Select, Modal, Form, InputNumber, Switch, Typography } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined, ApiOutlined, SyncOutlined, LinkOutlined } from '@ant-design/icons'
import { useToolStore } from '../../stores/toolStore'
import { Tool } from '../../types/models'
import { EditHttpTool } from './EditHttpTool'
import { McpConnect } from './McpConnect'
import { mcpApi, McpConnection } from '../../api/mcp'

export function ToolList() {
  const { tools, fetchList, delete: deleteTool, toggleEnable, test } = useToolStore()
  const [filter, setFilter] = useState<'all' | 'http' | 'mcp'>('all')
  const [search, setSearch] = useState('')
  const [editModalOpen, setEditModalOpen] = useState(false)
  const [editingTool, setEditingTool] = useState<Tool | null>(null)

  // MCP Connection state
  const [mcpConnections, setMcpConnections] = useState<McpConnection[]>([])
  const [mcpModalOpen, setMcpModalOpen] = useState(false)
  const [editingConnection, setEditingConnection] = useState<McpConnection | null>(null)

  // Test Modal state
  const [testModalOpen, setTestModalOpen] = useState(false)
  const [testingTool, setTestingTool] = useState<Tool | null>(null)
  const [testForm] = Form.useForm()
  const [testResult, setTestResult] = useState<any>(null)
  const [testLoading, setTestLoading] = useState(false)

  useEffect(() => {
    fetchList(filter === 'all' ? undefined : filter)
  }, [fetchList, filter])

  // Load MCP connections
  useEffect(() => {
    mcpApi.listConnections().then((res) => setMcpConnections(res.data)).catch((error) => {
      console.error('Failed to load MCP connections:', error)
    })
  }, [])

  const filteredTools = tools.filter((t) =>
    t.name.toLowerCase().includes(search.toLowerCase())
  )

  const httpTools = filteredTools.filter((t) => t.tool_type === 'http')
  const mcpTools = filteredTools.filter((t) => t.tool_type === 'mcp')

  const handleDelete = async (id: string) => {
    try {
      await deleteTool(id)
      message.success('删除成功')
    } catch {
      message.error('删除失败')
    }
  }

  const handleToggle = async (id: string, enabled: boolean) => {
    try {
      await toggleEnable(id, enabled)
      message.success(enabled ? '已启用' : '已禁用')
    } catch {
      message.error('操作失败')
    }
  }

  const handleTest = (tool: Tool) => {
    setTestingTool(tool)
    setTestResult(null)
    // 如果有 input_schema，打开对话框让用户输入参数
    if (tool.input_schema && tool.input_schema.properties && Object.keys(tool.input_schema.properties).length > 0) {
      testForm.resetFields()
      setTestModalOpen(true)
    } else {
      // 没有 input_schema，直接测试
      executeTest(tool.id, {})
    }
  }

  const executeTest = async (toolId: string, input_data: Record<string, any>) => {
    setTestLoading(true)
    try {
      const result = await test(toolId, input_data)
      setTestResult(result)
      if (!testModalOpen) {
        // 如果没有打开测试对话框，直接显示结果
        if (result.success) {
          message.success('测试成功')
        } else {
          message.error(`测试失败: ${result.error || '未知错误'}`)
        }
      }
    } catch (error: any) {
      setTestResult({ success: false, error: error.message || '请求失败' })
      if (!testModalOpen) {
        message.error('测试失败')
      }
    } finally {
      setTestLoading(false)
    }
  }

  const handleTestSubmit = async () => {
    if (!testingTool) return
    try {
      const values = await testForm.validateFields()
      await executeTest(testingTool.id, values)
    } catch {
      // 表单验证失败
    }
  }

  const handleTestModalClose = () => {
    setTestModalOpen(false)
    setTestingTool(null)
    setTestResult(null)
  }

  // 根据 input_schema 渲染表单字段
  const renderInputFields = () => {
    if (!testingTool?.input_schema?.properties) return null

    const properties = testingTool.input_schema.properties
    const required = testingTool.input_schema.required || []

    return Object.entries(properties).map(([key, schema]: [string, any]) => (
      <Form.Item
        key={key}
        name={key}
        label={schema.title || key}
        rules={required.includes(key) ? [{ required: true, message: `请输入${schema.title || key}` }] : []}
      >
        {schema.type === 'string' ? (
          <Input placeholder={schema.description || `请输入${schema.title || key}`} />
        ) : schema.type === 'number' ? (
          <InputNumber style={{ width: '100%' }} placeholder={schema.description} />
        ) : schema.type === 'boolean' ? (
          <Switch />
        ) : (
          <Input placeholder={schema.description} />
        )}
      </Form.Item>
    ))
  }

  const handleEdit = (tool: Tool) => {
    setEditingTool(tool)
    setEditModalOpen(true)
  }

  const handleCreate = () => {
    setEditingTool(null)
    setEditModalOpen(true)
  }

  // MCP Connection handlers
  const handleCreateMcpConnection = () => {
    setEditingConnection(null)
    setMcpModalOpen(true)
  }

  const handleEditMcpConnection = (connection: McpConnection) => {
    setEditingConnection(connection)
    setMcpModalOpen(true)
  }

  const handleDeleteMcpConnection = async (id: string) => {
    try {
      await mcpApi.deleteConnection(id)
      setMcpConnections((prev) => prev.filter((c) => c.id !== id))
      message.success('删除成功')
    } catch {
      message.error('删除失败')
    }
  }

  const handleSyncMcpConnection = async (id: string) => {
    try {
      const result = await mcpApi.syncTools(id)
      const data = result.data
      // Validate response before type assertion
      if (typeof data === 'object' && data !== null && 'success' in data) {
        const syncData = data as { success: boolean; count?: number; error?: string }
        if (syncData.success) {
          message.success(`同步成功，已注册 ${syncData.count ?? 0} 个工具`)
          // Refresh tools list
          fetchList(filter === 'all' ? undefined : filter)
        } else {
          message.error(`同步失败: ${syncData.error ?? '未知错误'}`)
        }
      } else {
        message.error('同步失败: 响应格式无效')
      }
    } catch {
      message.error('同步失败')
    }
  }

  const handleMcpModalClose = () => {
    setMcpModalOpen(false)
    setEditingConnection(null)
  }

  const handleMcpModalSync = () => {
    // Reload connections list after create/update
    mcpApi.listConnections().then((res) => setMcpConnections(res.data))
  }

  const ToolCard = ({ tool }: { tool: Tool }) => (
    <Card
      style={{ marginBottom: 16 }}
      size="small"
      title={
        <Space>
          <ApiOutlined />
          <span>{tool.name}</span>
          {tool.is_public ? <Tag color="blue">公开</Tag> : <Tag>私有</Tag>}
        </Space>
      }
      extra={
        <Space>
          <Button
            size="small"
            icon={<PlayCircleOutlined />}
            onClick={() => handleTest(tool)}
          >
            测试
          </Button>
          <Button
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(tool)}
          />
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(tool.id)}>
            <Button size="small" icon={<DeleteOutlined />} danger />
          </Popconfirm>
        </Space>
      }
    >
      <p style={{ marginBottom: 8, color: '#666' }}>{tool.description || '无描述'}</p>
      {tool.tool_type === 'http' && (
        <p style={{ fontSize: 12, color: '#999' }}>
          URL: {tool.config?.url || '-'}
        </p>
      )}
      <Space>
        <Tag color={tool.is_enabled ? 'green' : 'red'}>
          {tool.is_enabled ? '已启用' : '已禁用'}
        </Tag>
        <Button
          size="small"
          type="link"
          onClick={() => handleToggle(tool.id, !tool.is_enabled)}
        >
          {tool.is_enabled ? '禁用' : '启用'}
        </Button>
      </Space>
    </Card>
  )

  return (
    <div>
      <div style={{ marginBottom: 24, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>工具管理</h2>
        <Space>
          <Input.Search
            placeholder="搜索工具"
            style={{ width: 200 }}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <Select
            value={filter}
            style={{ width: 120 }}
            onChange={setFilter}
            options={[
              { value: 'all', label: '全部' },
              { value: 'http', label: 'HTTP' },
              { value: 'mcp', label: 'MCP' },
            ]}
          />
          <Button icon={<LinkOutlined />} onClick={handleCreateMcpConnection}>
            添加 MCP 连接
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            创建 HTTP 工具
          </Button>
        </Space>
      </div>

      <Row gutter={24}>
        <Col span={12}>
          <h3 style={{ marginBottom: 16 }}>HTTP 工具</h3>
          {httpTools.length === 0 ? (
            <Card size="small">
              <p style={{ textAlign: 'center', color: '#999' }}>暂无 HTTP 工具</p>
            </Card>
          ) : (
            httpTools.map((tool) => <ToolCard key={tool.id} tool={tool} />)
          )}
        </Col>
        <Col span={12}>
          <h3 style={{ marginBottom: 16 }}>MCP 工具</h3>
          {/* MCP Connections list */}
          {mcpConnections.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              {mcpConnections.map((conn) => (
                <Card
                  key={conn.id}
                  size="small"
                  style={{ marginBottom: 8 }}
                  title={
                    <Space>
                      <LinkOutlined />
                      <span>{conn.name}</span>
                      <Tag color={conn.is_enabled ? 'green' : 'red'}>
                        {conn.is_enabled ? '已启用' : '已禁用'}
                      </Tag>
                      <Tag color={conn.sync_status === 'success' ? 'green' : conn.sync_status === 'failed' ? 'red' : 'blue'}>
                        {conn.sync_status === 'success' ? '已同步' : conn.sync_status === 'failed' ? '同步失败' : '待同步'}
                      </Tag>
                    </Space>
                  }
                  extra={
                    <Space>
                      <Button
                        size="small"
                        icon={<SyncOutlined />}
                        onClick={() => handleSyncMcpConnection(conn.id)}
                      >
                        同步
                      </Button>
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        onClick={() => handleEditMcpConnection(conn)}
                      />
                      <Popconfirm
                        title="确认删除此连接？"
                        onConfirm={() => handleDeleteMcpConnection(conn.id)}
                      >
                        <Button size="small" icon={<DeleteOutlined />} danger />
                      </Popconfirm>
                    </Space>
                  }
                >
                  <p style={{ marginBottom: 4, color: '#666', fontSize: 12 }}>
                    {conn.description || '无描述'}
                  </p>
                  <p style={{ marginBottom: 0, fontSize: 12, color: '#999' }}>
                    类型: {conn.transport_type.toUpperCase()} |
                    {conn.connection_url && ` URL: ${conn.connection_url}`}
                    {conn.command && ` 命令: ${conn.command}`}
                  </p>
                </Card>
              ))}
            </div>
          )}
          {/* MCP Tools list */}
          {mcpTools.length === 0 ? (
            <Card size="small">
              <p style={{ textAlign: 'center', color: '#999' }}>暂无 MCP 工具</p>
            </Card>
          ) : (
            mcpTools.map((tool) => <ToolCard key={tool.id} tool={tool} />)
          )}
        </Col>
      </Row>

      <Modal
        title={editingTool ? '编辑 HTTP 工具' : '创建 HTTP 工具'}
        open={editModalOpen}
        onCancel={() => setEditModalOpen(false)}
        footer={null}
        width={700}
      >
        <EditHttpTool
          tool={editingTool}
          onClose={() => setEditModalOpen(false)}
        />
      </Modal>

      {/* MCP Connection Modal */}
      <Modal
        title={editingConnection ? '编辑 MCP 连接' : '添加 MCP 连接'}
        open={mcpModalOpen}
        onCancel={handleMcpModalClose}
        footer={null}
        width={600}
      >
        <McpConnect
          connection={editingConnection}
          onClose={handleMcpModalClose}
          onSync={handleMcpModalSync}
        />
      </Modal>

      {/* Test Tool Modal */}
      <Modal
        title={`测试工具: ${testingTool?.name || ''}`}
        open={testModalOpen}
        onCancel={handleTestModalClose}
        onOk={handleTestSubmit}
        okText="执行测试"
        cancelText="关闭"
        confirmLoading={testLoading}
        width={600}
      >
        <Form form={testForm} layout="vertical">
          {renderInputFields()}
        </Form>
        {testResult && (
          <div style={{ marginTop: 16 }}>
            <Typography.Title level={5}>测试结果</Typography.Title>
            <pre style={{
              background: testResult.success ? '#f6ffed' : '#fff2f0',
              padding: 12,
              borderRadius: 4,
              maxHeight: 300,
              overflow: 'auto'
            }}>
              {JSON.stringify(testResult, null, 2)}
            </pre>
          </div>
        )}
      </Modal>
    </div>
  )
}
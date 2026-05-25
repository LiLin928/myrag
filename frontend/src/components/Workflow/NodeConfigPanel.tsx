import { useState, useEffect, useCallback, useMemo, createContext, useContext } from 'react'
import {
  Form,
  Input,
  Select,
  Slider,
  InputNumber,
  Collapse,
  Button,
  Space,
  Divider,
  Alert,
  Switch,
  Checkbox,
  message,
} from 'antd'
import { PlusOutlined, DeleteOutlined } from '@ant-design/icons'
import type { Node, Edge } from 'reactflow'
import type { CommonNodeConfig } from '../../types/workflowConfig'
import type { Tool, KnowledgeBase } from '../../types/models'
import { toolApi } from '../../api/tools'
import { modelApi, ModelConfig } from '../../api/models'
import { knowledgeApi } from '../../api/knowledge'

const { TextArea } = Input

// 上游输出参数 Context
const UpstreamOutputsContext = createContext<{ name: string; path: string }[]>([])

// 节点类型名称映射
const nodeTypeNames: Record<string, string> = {
  start: '开始',
  end: '结束',
  llm: '大模型',
  rag: '知识检索',
  code: '代码',
  condition: '条件',
  http: 'HTTP',
  human: '人工',
  tool: '工具',
}

// 获取上游节点（通过边连接的前置节点）
function getUpstreamNodes(currentNodeId: string, nodes: Node[], edges: Edge[]): Node[] {
  const upstreamIds = edges
    .filter((e) => e.target === currentNodeId)
    .map((e) => e.source)
  return nodes.filter((n) => upstreamIds.includes(n.id))
}

// 获取节点的输出参数列表
function getNodeOutputParams(node: Node): { name: string; path: string }[] {
  const nodeType = node.type
  const nodeName = node.data?.name || nodeTypeNames[nodeType || ''] || node.id

  // 所有节点默认有 result 输出参数（除开始节点外）
  const defaultOutputs = [{ name: `${nodeName}.result`, path: `${node.id}.result` }]

  // 根据节点类型添加特定输出参数
  if (nodeType === 'start') {
    // 开始节点的输出参数来自用户定义的输入变量
    const inputVars = node.data?.input_variables || []
    return inputVars.map((v: any) => ({
      name: `${nodeName}.${v.name}`,
      path: `${node.id}.${v.name}`,
    }))
  }

  if (nodeType === 'llm') {
    return [
      { name: `${nodeName}.result`, path: `${node.id}.result` },
      { name: `${nodeName}.content`, path: `${node.id}.content` },
    ]
  }

  if (nodeType === 'rag') {
    return [
      { name: `${nodeName}.result`, path: `${node.id}.result` },
      { name: `${nodeName}.documents`, path: `${node.id}.documents` },
      { name: `${nodeName}.context`, path: `${node.id}.context` },
    ]
  }

  if (nodeType === 'http') {
    return [
      { name: `${nodeName}.result`, path: `${node.id}.result` },
      { name: `${nodeName}.response`, path: `${node.id}.response` },
    ]
  }

  if (nodeType === 'code') {
    return [
      { name: `${nodeName}.result`, path: `${node.id}.result` },
      { name: `${nodeName}.output`, path: `${node.id}.output` },
    ]
  }

  return defaultOutputs
}

interface NodeConfigPanelProps {
  selectedNode: Node | null
  nodes: Node[]
  edges: Edge[]
  onConfigChange: (config: Record<string, unknown>) => void
}

export function NodeConfigPanel({ selectedNode, nodes, edges, onConfigChange }: NodeConfigPanelProps) {
  const [form] = Form.useForm()
  const [hasChanges, setHasChanges] = useState(false)
  const [initialData, setInitialData] = useState<Record<string, unknown>>({})

  // 获取上游节点及其输出参数
  const upstreamOutputs = useMemo(() => {
    if (!selectedNode) return []
    const upstreamNodes = getUpstreamNodes(selectedNode.id, nodes, edges)
    return upstreamNodes.flatMap((n) => getNodeOutputParams(n))
  }, [selectedNode, nodes, edges])

  // Initialize form when node selection changes
  useEffect(() => {
    if (selectedNode) {
      const data = selectedNode.data || {}
      form.setFieldsValue(data)
      setInitialData(data)
      setHasChanges(false)
    }
  }, [selectedNode, form])

  // Handle form value changes
  const handleValuesChange = useCallback(
    (_changedValues: Partial<CommonNodeConfig>, allValues: Record<string, unknown>) => {
      setHasChanges(true)
    },
    []
  )

  const handleSave = useCallback(() => {
    const values = form.getFieldsValue()
    onConfigChange(values)
    setHasChanges(false)
    setInitialData(values)
    message.success('节点配置已保存')
  }, [form, onConfigChange])

  const handleReset = useCallback(() => {
    form.setFieldsValue(initialData)
    setHasChanges(false)
  }, [form, initialData])

  if (!selectedNode) {
    return <Alert message="请选择一个节点进行配置" type="info" />
  }

  const nodeType = selectedNode.type

  return (
    <UpstreamOutputsContext.Provider value={upstreamOutputs}>
      <Form
        form={form}
        layout="vertical"
        onValuesChange={handleValuesChange}
        initialValues={selectedNode.data || {}}
      >
        {/* Common Configuration Section - 默认折叠 */}
        <Collapse style={{ marginBottom: 16 }}>
          <Collapse.Panel header="基本配置（可选）" key="common">
            <Form.Item name="name" label="节点名称">
              <Input placeholder="输入节点名称" />
            </Form.Item>
            <Form.Item name="description" label="描述">
              <TextArea rows={2} placeholder="节点描述" />
            </Form.Item>
          </Collapse.Panel>
        </Collapse>

        {/* Advanced Settings - 高级配置 */}
        <Collapse style={{ marginBottom: 16 }}>
          <Collapse.Panel header="高级设置" key="advanced">
            <Form.Item name="timeout" label="超时时间(秒)">
              <InputNumber min={1} max={600} placeholder="300" />
            </Form.Item>
            <Form.Item name="retry_count" label="重试次数">
              <InputNumber min={0} max={5} placeholder="0" />
            </Form.Item>
            <Form.Item name="retry_delay" label="重试间隔(秒)">
              <InputNumber min={0.1} max={10} step={0.1} placeholder="1" />
            </Form.Item>
            <Form.Item name="error_handling" label="错误处理策略">
              <Select
                options={[
                  { value: 'abort', label: '中止流程' },
                  { value: 'skip', label: '跳过继续' },
                  { value: 'fallback', label: '使用默认值' },
                ]}
                placeholder="中止流程"
              />
            </Form.Item>
          </Collapse.Panel>
        </Collapse>

      {/* Node Type Specific Configuration */}
      {nodeType === 'llm' && <LLMConfigSection />}
      {nodeType === 'rag' && <RAGConfigSection />}
      {nodeType === 'code' && <CodeConfigSection />}
      {nodeType === 'http' && <HTTPConfigSection />}
      {nodeType === 'condition' && <ConditionConfigSection />}
      {nodeType === 'human' && <HumanConfigSection />}
      {nodeType === 'tool' && <ToolConfigSection />}
      {nodeType === 'start' && <StartConfigSection />}
      {nodeType === 'end' && <EndConfigSection />}

      {/* 保存按钮区域 */}
      <Divider />
      <Space>
        <Button type="primary" onClick={handleSave} disabled={!hasChanges}>
          保存配置
        </Button>
        <Button onClick={handleReset} disabled={!hasChanges}>
          重置
        </Button>
      </Space>
    </Form>
    </UpstreamOutputsContext.Provider>
  )
}

// ============================================================================
// 输入参数选择组件 - 从上游节点输出参数中选择
// ============================================================================

function InputParamSelector({ label, placeholder }: { label: string; placeholder?: string }) {
  const upstreamOutputs = useContext(UpstreamOutputsContext)

  return (
    <Form.Item name={label} label={label}>
      <Select
        placeholder={placeholder || '选择输入参数'}
        showSearch
        optionFilterProp="label"
        options={upstreamOutputs.map((p) => ({
          value: `\${${p.path}}`,
          label: p.name,
        }))}
        allowClear
      />
    </Form.Item>
  )
}

// ============================================================================
// 输入变量编辑器 - 支持选择上游节点输出或手动输入
// ============================================================================

function InputVariablesEditorWithSelector() {
  const upstreamOutputs = useContext(UpstreamOutputsContext)

  return (
    <Form.List name="input_variables">
      {(fields, { add, remove }) => (
        <>
          {fields.map(({ key, name, ...restField }) => (
            <div key={key} style={{ marginBottom: 8, padding: 8, background: '#fafafa', borderRadius: 4 }}>
              <Space style={{ display: 'flex', marginBottom: 4 }} align="baseline">
                <Form.Item {...restField} name={[name, 'name']} style={{ flex: 1, marginBottom: 0 }}>
                  <Input placeholder="变量名" />
                </Form.Item>
                <Form.Item {...restField} name={[name, 'source']} style={{ flex: 1, marginBottom: 0 }}>
                  <Select
                    placeholder="选择来源"
                    showSearch
                    optionFilterProp="label"
                    options={upstreamOutputs.map((p) => ({
                      value: `\${${p.path}}`,
                      label: p.name,
                    }))}
                    allowClear
                  />
                </Form.Item>
                <Button type="text" danger icon={<DeleteOutlined />} onClick={() => remove(name)} />
              </Space>
            </div>
          ))}
          <Button type="dashed" onClick={() => add({ name: '', source: '' })} block icon={<PlusOutlined />}>
            添加输入变量
          </Button>
        </>
      )}
    </Form.List>
  )
}

// ============================================================================
// LLM Node Configuration Section (大模型配置)
// ============================================================================

function LLMConfigSection() {
  const upstreamOutputs = useContext(UpstreamOutputsContext)
  const [models, setModels] = useState<ModelConfig[]>([])
  const [tools, setTools] = useState<Tool[]>([])
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [loadingModels, setLoadingModels] = useState(false)
  const [loadingTools, setLoadingTools] = useState(false)
  const [loadingKnowledge, setLoadingKnowledge] = useState(false)
  const form = Form.useFormInstance()

  // 加载大模型列表
  useEffect(() => {
    let isMounted = true
    setLoadingModels(true)
    modelApi.list('llm', true)
      .then((res) => {
        if (isMounted) {
          setModels(res.items || [])
        }
      })
      .catch((error) => {
        if (isMounted) {
          console.error('Failed to load models:', error)
          setModels([])
        }
      })
      .finally(() => {
        if (isMounted) {
          setLoadingModels(false)
        }
      })
    return () => { isMounted = false }
  }, [])

  // 加载工具列表
  useEffect(() => {
    let isMounted = true
    setLoadingTools(true)
    toolApi.available()
      .then((res) => {
        if (isMounted) {
          setTools(res.data || [])
        }
      })
      .catch((error) => {
        if (isMounted) {
          console.error('Failed to load tools:', error)
          setTools([])
        }
      })
      .finally(() => {
        if (isMounted) {
          setLoadingTools(false)
        }
      })
    return () => { isMounted = false }
  }, [])

  // 加载知识库列表
  useEffect(() => {
    let isMounted = true
    setLoadingKnowledge(true)
    knowledgeApi.list()
      .then((res) => {
        if (isMounted) {
          setKnowledgeBases(res.data?.items || [])
        }
      })
      .catch((error) => {
        if (isMounted) {
          console.error('Failed to load knowledge bases:', error)
          setKnowledgeBases([])
        }
      })
      .finally(() => {
        if (isMounted) {
          setLoadingKnowledge(false)
        }
      })
    return () => { isMounted = false }
  }, [])

  return (
    <Collapse defaultActiveKey={['llm']} style={{ marginBottom: 16 }}>
      <Collapse.Panel header="大模型配置" key="llm">
        <Form.Item name="model_id" label="大模型">
          <Select
            loading={loadingModels}
            placeholder="选择大模型"
            showSearch
            optionFilterProp="label"
            onChange={(value) => {
              const model = models.find(m => m.id === value)
              if (model) {
                form.setFieldValue('model_name', model.name)
                form.setFieldValue('model_provider', model.provider)
              }
            }}
            options={models.map((m) => ({
              value: m.id,
              label: `${m.name} (${m.provider}/${m.model_name})`,
            }))}
          />
        </Form.Item>

        <Divider>输入参数</Divider>

        {upstreamOutputs.length > 0 ? (
          <InputVariablesEditorWithSelector />
        ) : (
          <Alert message="请先连接上游节点以选择输入参数" type="info" style={{ marginBottom: 16 }} />
        )}

        <Divider>提示词配置</Divider>

        <Form.Item name="system_prompt" label="系统提示词">
          <TextArea rows={4} placeholder="设置系统角色和行为，可使用 ${变量名} 引用输入参数" />
        </Form.Item>

        <Form.Item name="user_prompt" label="用户提示词">
          <TextArea rows={4} placeholder="用户输入的提示词，可使用 ${变量名} 引用输入参数" />
        </Form.Item>

        <Divider>知识检索配置</Divider>

        <Form.Item name="enable_rag" label="启用知识检索" valuePropName="checked">
          <Switch />
        </Form.Item>

        <Form.Item noStyle shouldUpdate={(prev, cur) => prev.enable_rag !== cur.enable_rag}>
          {({ getFieldValue }) => {
            return getFieldValue('enable_rag') ? (
              <>
                <Form.Item name="knowledge_base_id" label="知识库">
                  <Select
                    loading={loadingKnowledge}
                    placeholder="选择知识库"
                    showSearch
                    optionFilterProp="label"
                    options={knowledgeBases.map((kb) => ({
                      value: kb.id,
                      label: kb.name,
                    }))}
                  />
                </Form.Item>

                <Form.Item name="rag_top_k" label="检索数量 (Top K)">
                  <InputNumber min={1} max={20} placeholder="5" />
                </Form.Item>

                <Form.Item name="rag_score_threshold" label="相似度阈值">
                  <Slider min={0} max={1} step={0.1} marks={{ 0: '0', 0.5: '0.5', 1: '1' }} />
                </Form.Item>
              </>
            ) : null
          }}
        </Form.Item>

        <Divider>模型参数</Divider>

        <Form.Item name="temperature" label="温度">
          <Slider min={0} max={1} step={0.1} marks={{ 0: '精确', 0.5: '适中', 1: '随机' }} />
        </Form.Item>

        <Form.Item name="max_tokens" label="最大输出长度">
          <InputNumber min={1} max={8000} placeholder="1024" />
        </Form.Item>

        <Form.Item name="top_p" label="Top P">
          <Slider min={0} max={1} step={0.1} marks={{ 0: '0', 0.5: '0.5', 1: '1' }} />
        </Form.Item>

        <Divider>工具配置</Divider>

        <Form.Item name="enable_tools" label="启用工具" valuePropName="checked">
          <Switch />
        </Form.Item>

        <Form.Item noStyle shouldUpdate={(prev, cur) => prev.enable_tools !== cur.enable_tools}>
          {({ getFieldValue }) => {
            return getFieldValue('enable_tools') ? (
              <Form.Item name="selected_tools" label="选择工具">
                <Checkbox.Group
                  options={tools.map((t) => ({
                    label: t.name,
                    value: t.id,
                  }))}
                />
              </Form.Item>
            ) : null
          }}
        </Form.Item>

        <Divider>输出变量映射</Divider>
        <OutputVariablesEditor />
      </Collapse.Panel>
    </Collapse>
  )
}

// ============================================================================
// RAG Node Configuration Section (知识检索配置)
// ============================================================================

function RAGConfigSection() {
  const upstreamOutputs = useContext(UpstreamOutputsContext)
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    let isMounted = true
    setLoading(true)
    knowledgeApi.list()
      .then((res) => {
        if (isMounted) {
          setKnowledgeBases(res.data?.items || [])
        }
      })
      .catch((error) => {
        if (isMounted) {
          console.error('Failed to load knowledge bases:', error)
          setKnowledgeBases([])
        }
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false)
        }
      })
    return () => { isMounted = false }
  }, [])

  return (
    <Collapse defaultActiveKey={['rag']} style={{ marginBottom: 16 }}>
      <Collapse.Panel header="知识检索配置" key="rag">
        <Divider>输入参数</Divider>

        {upstreamOutputs.length > 0 ? (
          <>
            <Form.Item name="query_source" label="查询文本来源">
              <Select
                placeholder="选择查询参数来源"
                showSearch
                optionFilterProp="label"
                options={upstreamOutputs.map((p) => ({
                  value: `\${${p.path}}`,
                  label: p.name,
                }))}
                allowClear
              />
            </Form.Item>
          </>
        ) : (
          <Alert message="请先连接上游节点以选择输入参数" type="info" style={{ marginBottom: 16 }} />
        )}

        <Divider>知识库配置</Divider>

        <Form.Item name="knowledge_base_id" label="知识库">
          <Select
            loading={loading}
            placeholder="选择知识库"
            showSearch
            optionFilterProp="label"
            onChange={(value) => {
              const kb = knowledgeBases.find(k => k.id === value)
              if (kb) {
                form.setFieldValue('knowledge_base_name', kb.name)
              }
            }}
            options={knowledgeBases.map((kb) => ({
              value: kb.id,
              label: kb.name,
            }))}
          />
        </Form.Item>

        <Form.Item name="top_k" label="返回数量 (Top K)">
          <InputNumber min={1} max={20} placeholder="5" />
        </Form.Item>

        <Form.Item name="score_threshold" label="相似度阈值">
          <Slider min={0} max={1} step={0.1} marks={{ 0: '0', 0.5: '0.5', 1: '1' }} />
        </Form.Item>

        <Form.Item name="search_type" label="搜索类型">
          <Select
            options={[
              { value: 'similarity', label: '向量相似度' },
              { value: 'hybrid', label: '混合检索' },
              { value: 'keyword', label: '关键词检索' },
            ]}
            placeholder="向量相似度"
          />
        </Form.Item>

        <Form.Item name="rerank" label="结果重排序" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Divider>输出变量映射</Divider>
        <OutputVariablesEditor />
      </Collapse.Panel>
    </Collapse>
  )
}

// ============================================================================
// Code Node Configuration Section
// ============================================================================

function CodeConfigSection() {
  return (
    <Collapse defaultActiveKey={['code']} style={{ marginBottom: 16 }}>
      <Collapse.Panel header="代码配置" key="code">
        <Form.Item name="language" label="编程语言">
          <Select
            options={[
              { value: 'python', label: 'Python' },
              { value: 'javascript', label: 'JavaScript' },
              { value: 'typescript', label: 'TypeScript' },
            ]}
            placeholder="Python"
          />
        </Form.Item>
        <Form.Item name="code" label="代码">
          <TextArea
            rows={12}
            placeholder="编写代码处理输入数据，使用 input 变量获取输入"
            style={{ fontFamily: 'monospace' }}
          />
        </Form.Item>
        <Divider>输入变量</Divider>
        <InputVariablesEditor />
        <Divider>输出变量</Divider>
        <OutputVariablesEditor />
      </Collapse.Panel>
    </Collapse>
  )
}

// ============================================================================
// HTTP Node Configuration Section
// ============================================================================

function HTTPConfigSection() {
  return (
    <Collapse defaultActiveKey={['http']} style={{ marginBottom: 16 }}>
      <Collapse.Panel header="HTTP 配置" key="http">
        <Form.Item name="url" label="URL">
          <Input placeholder="请求地址，可使用 ${变量名}" />
        </Form.Item>
        <Form.Item name="method" label="方法">
          <Select
            options={[
              { value: 'GET', label: 'GET' },
              { value: 'POST', label: 'POST' },
              { value: 'PUT', label: 'PUT' },
              { value: 'PATCH', label: 'PATCH' },
              { value: 'DELETE', label: 'DELETE' },
            ]}
            placeholder="GET"
          />
        </Form.Item>
        <Form.Item name="headers" label="请求头">
          <TextArea
            rows={4}
            placeholder="JSON 格式，例如: { 'Authorization': 'Bearer ${token}' }"
          />
        </Form.Item>
        <Form.Item name="body" label="请求体">
          <TextArea
            rows={6}
            placeholder="JSON 格式，可使用变量引用"
          />
        </Form.Item>
        <Form.Item name="timeout_seconds" label="超时(秒)">
          <InputNumber min={1} max={120} placeholder="30" />
        </Form.Item>
        <Divider>输出变量映射</Divider>
        <OutputVariablesEditor />
      </Collapse.Panel>
    </Collapse>
  )
}

// ============================================================================
// Tool Node Configuration Section
// ============================================================================

function ToolConfigSection() {
  const [tools, setTools] = useState<Tool[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedTool, setSelectedTool] = useState<Tool | null>(null)
  const form = Form.useFormInstance()

  // Load available tools
  useEffect(() => {
    let isMounted = true
    setLoading(true)
    toolApi
      .available()
      .then((res) => {
        if (isMounted) {
          setTools(res.data || [])
        }
      })
      .catch((error) => {
        if (isMounted) {
          console.error('Failed to load tools:', error)
          setTools([])
        }
      })
      .finally(() => {
        if (isMounted) {
          setLoading(false)
        }
      })
    return () => {
      isMounted = false
    }
  }, [])

  // Handle tool selection change
  const handleToolChange = (toolId: string) => {
    const tool = tools.find((t) => t.id === toolId)
    setSelectedTool(tool || null)

    // Reset tool_inputs when tool changes
    form.setFieldValue('tool_inputs', {})
  }

  // Get input fields from tool's input_schema
  const getInputFields = () => {
    if (!selectedTool?.input_schema?.properties) {
      return []
    }
    const properties = selectedTool.input_schema.properties
    const required = selectedTool.input_schema.required || []

    return Object.entries(properties).map(([key, schema]: [string, any]) => ({
      name: key,
      label: schema.title || key,
      type: schema.type || 'string',
      description: schema.description || '',
      required: required.includes(key),
      enum: schema.enum,
    }))
  }

  const inputFields = getInputFields()

  return (
    <Collapse defaultActiveKey={['tool']} style={{ marginBottom: 16 }}>
      <Collapse.Panel header="工具配置" key="tool">
        <Form.Item name="tool_id" label="选择工具">
          <Select
            loading={loading}
            placeholder="选择要执行的工具"
            showSearch
            optionFilterProp="label"
            onChange={handleToolChange}
            options={tools.map((tool) => ({
              value: tool.id,
              label: tool.name,
            }))}
          />
        </Form.Item>

        {selectedTool && (
          <>
            <Alert
              message={selectedTool.name}
              description={selectedTool.description || '暂无描述'}
              type="info"
              showIcon
              style={{ marginBottom: 16 }}
            />

            {inputFields.length > 0 && (
              <>
                <Divider>工具输入参数</Divider>
                {inputFields.map((field) => (
                  <Form.Item
                    key={field.name}
                    name={['tool_inputs', field.name]}
                    label={field.label}
                    required={field.required}
                    help={field.description}
                  >
                    {field.enum ? (
                      <Select
                        placeholder={`选择 ${field.label}`}
                        options={field.enum.map((v: string) => ({
                          value: v,
                          label: v,
                        }))}
                      />
                    ) : field.type === 'number' || field.type === 'integer' ? (
                      <InputNumber
                        placeholder={`输入 ${field.label}`}
                        style={{ width: '100%' }}
                      />
                    ) : field.type === 'boolean' ? (
                      <Select
                        placeholder={`选择 ${field.label}`}
                        options={[
                          { value: true, label: '是' },
                          { value: false, label: '否' },
                        ]}
                      />
                    ) : (
                      <Input placeholder={`输入 ${field.label}`} />
                    )}
                  </Form.Item>
                ))}
              </>
            )}

            <Divider>输出变量配置</Divider>
            <Form.Item name="output_variable_name" label="输出变量名">
              <Input placeholder="tool_result" />
            </Form.Item>
          </>
        )}
      </Collapse.Panel>
    </Collapse>
  )
}

// ============================================================================
// Condition Node Configuration Section
// ============================================================================

function ConditionConfigSection() {
  return (
    <Collapse defaultActiveKey={['condition']} style={{ marginBottom: 16 }}>
      <Collapse.Panel header="条件配置" key="condition">
        <Form.List name="conditions">
          {(fields, { add, remove }) => (
            <>
              {fields.map(({ key, name, ...restField }) => (
                <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                  <Form.Item
                    {...restField}
                    name={[name, 'expression']}
                    rules={[{ required: true, message: '请输入条件表达式' }]}
                    style={{ flex: 1 }}
                  >
                    <Input placeholder="例如: ${result} == 'success'" />
                  </Form.Item>
                  <Form.Item
                    {...restField}
                    name={[name, 'target_node']}
                    style={{ width: 150 }}
                  >
                    <Input placeholder="目标节点 ID" />
                  </Form.Item>
                  <Button type="text" danger icon={<DeleteOutlined />} onClick={() => remove(name)} />
                </Space>
              ))}
              <Button type="dashed" onClick={() => add()} block icon={<PlusOutlined />}>
                添加条件分支
              </Button>
            </>
          )}
        </Form.List>
        <Form.Item name="default_branch" label="默认分支" style={{ marginTop: 16 }}>
          <Input placeholder="无条件匹配时执行的节点 ID" />
        </Form.Item>
      </Collapse.Panel>
    </Collapse>
  )
}

// ============================================================================
// Human Node Configuration Section
// ============================================================================

function HumanConfigSection() {
  return (
    <Collapse defaultActiveKey={['human']} style={{ marginBottom: 16 }}>
      <Collapse.Panel header="人工审批配置" key="human">
        <Form.Item name="title" label="标题">
          <Input placeholder="审批标题" />
        </Form.Item>
        <Form.Item name="description" label="说明">
          <TextArea rows={3} placeholder="向审批人展示的说明" />
        </Form.Item>
        <Form.Item name="timeout_hours" label="超时时间(小时)">
          <InputNumber min={0} max={168} placeholder="24" />
        </Form.Item>
        <Form.Item name="timeout_action" label="超时处理">
          <Select
            options={[
              { value: 'approve', label: '自动通过' },
              { value: 'reject', label: '自动拒绝' },
              { value: 'notify', label: '发送通知' },
            ]}
            placeholder="自动拒绝"
          />
        </Form.Item>
        <Divider>操作选项</Divider>
        <Form.List name="action_options">
          {(fields, { add, remove }) => (
            <>
              {fields.map(({ key, name, ...restField }) => (
                <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                  <Form.Item {...restField} name={[name, 'label']} style={{ flex: 1 }}>
                    <Input placeholder="选项名称" />
                  </Form.Item>
                  <Form.Item {...restField} name={[name, 'value']} style={{ width: 100 }}>
                    <Input placeholder="值" />
                  </Form.Item>
                  <Button type="text" danger icon={<DeleteOutlined />} onClick={() => remove(name)} />
                </Space>
              ))}
              <Button type="dashed" onClick={() => add({ label: '', value: '' })} block icon={<PlusOutlined />}>
                添加操作选项
              </Button>
            </>
          )}
        </Form.List>
        <Divider>输出变量映射</Divider>
        <OutputVariablesEditor />
      </Collapse.Panel>
    </Collapse>
  )
}

// ============================================================================
// Start Node Configuration Section
// ============================================================================

function StartConfigSection() {
  return (
    <Collapse defaultActiveKey={['start']} style={{ marginBottom: 16 }}>
      <Collapse.Panel header="输入变量定义" key="start">
        <Form.List name="input_variables">
          {(fields, { add, remove }) => (
            <>
              {fields.map(({ key, name, ...restField }) => (
                <div key={key} style={{ marginBottom: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
                  <Space style={{ display: 'flex', marginBottom: 8 }} align="baseline">
                    <Form.Item {...restField} name={[name, 'name']} rules={[{ required: true }]}>
                      <Input placeholder="变量名" style={{ width: 120 }} />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'type']}>
                      <Select
                        options={[
                          { value: 'string', label: '字符串' },
                          { value: 'number', label: '数字' },
                          { value: 'boolean', label: '布尔值' },
                          { value: 'object', label: '对象' },
                          { value: 'array', label: '数组' },
                          { value: 'file', label: '文件' },
                        ]}
                        style={{ width: 100 }}
                        placeholder="类型"
                      />
                    </Form.Item>
                    <Form.Item {...restField} name={[name, 'required']} valuePropName="checked">
                      <Switch size="small" />
                    </Form.Item>
                    <Button type="text" danger icon={<DeleteOutlined />} onClick={() => remove(name)} />
                  </Space>
                  <Form.Item {...restField} name={[name, 'description']}>
                    <Input placeholder="变量描述" />
                  </Form.Item>
                  <Form.Item {...restField} name={[name, 'default']}>
                    <Input placeholder="默认值" />
                  </Form.Item>
                </div>
              ))}
              <Button type="dashed" onClick={() => add({ name: '', type: 'string', required: false })} block icon={<PlusOutlined />}>
                添加输入变量
              </Button>
            </>
          )}
        </Form.List>
      </Collapse.Panel>
    </Collapse>
  )
}

// ============================================================================
// End Node Configuration Section
// ============================================================================

function EndConfigSection() {
  const upstreamOutputs = useContext(UpstreamOutputsContext)

  return (
    <Collapse defaultActiveKey={['end']} style={{ marginBottom: 16 }}>
      <Collapse.Panel header="输出变量定义" key="end">
        {upstreamOutputs.length > 0 ? (
          <Form.List name="output_variables">
            {(fields, { add, remove }) => (
              <>
                {fields.map(({ key, name, ...restField }) => (
                  <div key={key} style={{ marginBottom: 8, padding: 8, background: '#fafafa', borderRadius: 4 }}>
                    <Space style={{ display: 'flex', marginBottom: 4 }} align="baseline">
                      <Form.Item
                        {...restField}
                        name={[name, 'name']}
                        rules={[{ required: true, message: '请输入变量名' }]}
                        style={{ flex: 1, marginBottom: 0 }}
                      >
                        <Input placeholder="输出变量名" />
                      </Form.Item>
                      <Form.Item
                        {...restField}
                        name={[name, 'source']}
                        style={{ flex: 1, marginBottom: 0 }}
                      >
                        <Select
                          placeholder="选择来源"
                          showSearch
                          optionFilterProp="label"
                          options={upstreamOutputs.map((p) => ({
                            value: `\${${p.path}}`,
                            label: p.name,
                          }))}
                          allowClear
                        />
                      </Form.Item>
                      <Button type="text" danger icon={<DeleteOutlined />} onClick={() => remove(name)} />
                    </Space>
                  </div>
                ))}
                <Button type="dashed" onClick={() => add({ name: '', source: '' })} block icon={<PlusOutlined />}>
                  添加输出变量
                </Button>
              </>
            )}
          </Form.List>
        ) : (
          <Alert message="请先连接上游节点以选择输出参数" type="info" style={{ marginBottom: 16 }} />
        )}
      </Collapse.Panel>
    </Collapse>
  )
}

// ============================================================================
// Output Variables Editor Component
// ============================================================================

function OutputVariablesEditor() {
  return (
    <Form.List name="output_variables">
      {(fields, { add, remove }) => (
        <>
          {fields.map(({ key, name, ...restField }) => (
            <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
              <Form.Item
                {...restField}
                name={[name, 'name']}
                rules={[{ required: true, message: '请输入变量名' }]}
                style={{ flex: 1 }}
              >
                <Input placeholder="变量名" />
              </Form.Item>
              <Form.Item
                {...restField}
                name={[name, 'path']}
                style={{ flex: 1 }}
              >
                <Input placeholder="输出路径 (如: content)" />
              </Form.Item>
              <Button type="text" danger icon={<DeleteOutlined />} onClick={() => remove(name)} />
            </Space>
          ))}
          <Button type="dashed" onClick={() => add({ name: '', path: '' })} block icon={<PlusOutlined />}>
            添加输出变量
          </Button>
        </>
      )}
    </Form.List>
  )
}

// ============================================================================
// Input Variables Editor Component
// ============================================================================

function InputVariablesEditor() {
  return (
    <Form.List name="input_variables">
      {(fields, { add, remove }) => (
        <>
          {fields.map(({ key, name, ...restField }) => (
            <Space key={key} style={{ display: 'flex', marginBottom: 8 }} align="baseline">
              <Form.Item
                {...restField}
                name={[name, 'name']}
                rules={[{ required: true, message: '请输入变量名' }]}
                style={{ flex: 1 }}
              >
                <Input placeholder="参数名" />
              </Form.Item>
              <Form.Item
                {...restField}
                name={[name, 'source']}
                style={{ flex: 1 }}
              >
                <Input placeholder="来源变量 ${节点.output.字段}" />
              </Form.Item>
              <Button type="text" danger icon={<DeleteOutlined />} onClick={() => remove(name)} />
            </Space>
          ))}
          <Button type="dashed" onClick={() => add({ name: '', source: '' })} block icon={<PlusOutlined />}>
            添加输入变量
          </Button>
        </>
      )}
    </Form.List>
  )
}
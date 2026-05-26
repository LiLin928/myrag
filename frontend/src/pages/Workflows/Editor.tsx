import { useEffect, useCallback, useState, useRef, useMemo, useContext, createContext } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import ReactFlow, {
  Node,
  Controls,
  Background,
  MiniMap,
  addEdge,
  Connection,
  NodeTypes,
  Handle,
  Position,
  applyNodeChanges,
  applyEdgeChanges,
  OnNodesChange,
  OnEdgesChange,
  MarkerType,
  Edge,
  EdgeProps,
  getBezierPath,
  EdgeTypes,
  useReactFlow,
  ReactFlowProvider,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Card, Button, Space, Form, Input, message, Drawer, Modal, Spin, Typography } from 'antd'
import { SaveOutlined, PlayCircleOutlined, ArrowLeftOutlined, SendOutlined } from '@ant-design/icons'
import { useWorkflowStore } from '../../stores/workflowStore'
import { NodeConfigPanel } from '../../components/Workflow/NodeConfigPanel'
import { workflowApi } from '../../api/workflows'

const { TextArea } = Input
const { Text } = Typography

// 删除回调 Context
const DeleteNodeContext = createContext<(id: string) => void>(() => {})

// 删除按钮组件
function DeleteButton({ id }: { id: string }) {
  const onDelete = useContext(DeleteNodeContext)
  return (
    <button
      onClick={(e) => {
        e.stopPropagation()
        onDelete(id)
      }}
      style={{
        position: 'absolute',
        top: -8,
        right: -8,
        width: 20,
        height: 20,
        borderRadius: '50%',
        background: '#ff4d4f',
        border: 'none',
        cursor: 'pointer',
        fontSize: 12,
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 10,
      }}
      title="删除节点"
    >
      ×
    </button>
  )
}

// 自定义节点组件 - 使用正确的 NodeProps 类型
interface CustomNodeProps {
  id: string
  data?: any
  selected?: boolean
}

function StartNode({ id }: CustomNodeProps) {
  return (
    <div style={{
      position: 'relative',
      padding: '10px 20px',
      background: '#52c41a',
      borderRadius: '50%',
      color: '#fff',
      fontWeight: 'bold',
    }}>
      开始
      <Handle type="source" position={Position.Right} />
      <DeleteButton id={id} />
    </div>
  )
}

function EndNode({ id }: CustomNodeProps) {
  return (
    <div style={{
      position: 'relative',
      padding: '10px 20px',
      background: '#ff4d4f',
      borderRadius: '50%',
      color: '#fff',
      fontWeight: 'bold',
    }}>
      结束
      <Handle type="target" position={Position.Left} />
      <DeleteButton id={id} />
    </div>
  )
}

function LLMNode({ data, id }: CustomNodeProps) {
  const displayName = data?.model_name || '未配置'
  return (
    <div style={{
      position: 'relative',
      padding: '12px',
      background: '#1890ff',
      borderRadius: '8px',
      color: '#fff',
      minWidth: '120px',
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: 4 }}>大模型</div>
      <div style={{ fontSize: 12 }}>{displayName}</div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <DeleteButton id={id} />
    </div>
  )
}

function RAGNode({ data, id }: CustomNodeProps) {
  const displayName = data?.knowledge_base_name || '未配置'
  return (
    <div style={{
      position: 'relative',
      padding: '12px',
      background: '#722ed1',
      borderRadius: '8px',
      color: '#fff',
      minWidth: '120px',
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: 4 }}>知识检索</div>
      <div style={{ fontSize: 12 }}>{displayName}</div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <DeleteButton id={id} />
    </div>
  )
}

function CodeNode({ id }: CustomNodeProps) {
  return (
    <div style={{
      position: 'relative',
      padding: '12px',
      background: '#13c2c2',
      borderRadius: '8px',
      color: '#fff',
      minWidth: '120px',
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: 4 }}>代码</div>
      <div style={{ fontSize: 12 }}>Python</div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <DeleteButton id={id} />
    </div>
  )
}

function ConditionNode({ data, id }: CustomNodeProps) {
  return (
    <div style={{
      position: 'relative',
      padding: '12px',
      background: '#faad14',
      borderRadius: '8px',
      color: '#fff',
      minWidth: '120px',
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: 4 }}>条件</div>
      <div style={{ fontSize: 12 }}>{data?.condition || '表达式'}</div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} id="true" style={{ top: 20 }} />
      <Handle type="source" position={Position.Right} id="false" style={{ top: 50 }} />
      <DeleteButton id={id} />
    </div>
  )
}

function HttpNode({ data, id }: CustomNodeProps) {
  return (
    <div style={{
      position: 'relative',
      padding: '12px',
      background: '#eb2f96',
      borderRadius: '8px',
      color: '#fff',
      minWidth: '120px',
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: 4 }}>HTTP</div>
      <div style={{ fontSize: 12 }}>{data?.url || '请求'}</div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <DeleteButton id={id} />
    </div>
  )
}

function HumanNode({ id }: CustomNodeProps) {
  return (
    <div style={{
      position: 'relative',
      padding: '12px',
      background: '#fa8c16',
      borderRadius: '8px',
      color: '#fff',
      minWidth: '120px',
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: 4 }}>人工</div>
      <div style={{ fontSize: 12 }}>审批节点</div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <DeleteButton id={id} />
    </div>
  )
}

function ToolNode({ data, id }: CustomNodeProps) {
  return (
    <div style={{
      position: 'relative',
      padding: '12px',
      background: '#874aaf',
      borderRadius: '8px',
      color: '#fff',
      minWidth: '120px',
    }}>
      <div style={{ fontWeight: 'bold', marginBottom: 4 }}>工具</div>
      <div style={{ fontSize: 12 }}>{data?.tool_name || '选择工具'}</div>
      <Handle type="target" position={Position.Left} />
      <Handle type="source" position={Position.Right} />
      <DeleteButton id={id} />
    </div>
  )
}

// 创建动态节点类型（在 ReactFlowProvider 内部）
function createNodeTypes(deleteNode: (id: string) => void): NodeTypes {
  return {
    start: (props: any) => <DeleteNodeContext.Provider value={deleteNode}><StartNode {...props} /></DeleteNodeContext.Provider>,
    end: (props: any) => <DeleteNodeContext.Provider value={deleteNode}><EndNode {...props} /></DeleteNodeContext.Provider>,
    llm: (props: any) => <DeleteNodeContext.Provider value={deleteNode}><LLMNode {...props} /></DeleteNodeContext.Provider>,
    rag: (props: any) => <DeleteNodeContext.Provider value={deleteNode}><RAGNode {...props} /></DeleteNodeContext.Provider>,
    code: (props: any) => <DeleteNodeContext.Provider value={deleteNode}><CodeNode {...props} /></DeleteNodeContext.Provider>,
    condition: (props: any) => <DeleteNodeContext.Provider value={deleteNode}><ConditionNode {...props} /></DeleteNodeContext.Provider>,
    http: (props: any) => <DeleteNodeContext.Provider value={deleteNode}><HttpNode {...props} /></DeleteNodeContext.Provider>,
    human: (props: any) => <DeleteNodeContext.Provider value={deleteNode}><HumanNode {...props} /></DeleteNodeContext.Provider>,
    tool: (props: any) => <DeleteNodeContext.Provider value={deleteNode}><ToolNode {...props} /></DeleteNodeContext.Provider>,
  }
}

// 自定义边组件 - 带删除按钮
function DeletableEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  style,
  markerEnd,
}: EdgeProps) {
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
  })

  const onEdgeClick = (evt: React.MouseEvent, edgeId: string) => {
    evt.stopPropagation()
    // 触发删除事件
    const deleteEvent = new CustomEvent('edge-delete', { detail: { id: edgeId } })
    window.dispatchEvent(deleteEvent)
  }

  return (
    <>
      <path
        id={id}
        style={style}
        className="react-flow__edge-path"
        d={edgePath}
        markerEnd={markerEnd}
      />
      <g transform={`translate(${labelX}, ${labelY})`}>
        <circle
          r={10}
          fill="#ff4d4f"
          stroke="#fff"
          strokeWidth={2}
          style={{ cursor: 'pointer' }}
          onClick={(e) => onEdgeClick(e, id)}
        />
        <text
          x={0}
          y={0}
          textAnchor="middle"
          dominantBaseline="middle"
          style={{ fontSize: 12, fill: '#fff', fontWeight: 'bold', cursor: 'pointer' }}
          onClick={(e) => onEdgeClick(e, id)}
        >
          ×
        </text>
      </g>
    </>
  )
}

const edgeTypes: EdgeTypes = {
  default: DeletableEdge,
}

const nodeTemplates = [
  { type: 'start', label: '开始', color: '#52c41a' },
  { type: 'end', label: '结束', color: '#ff4d4f' },
  { type: 'llm', label: '大模型', color: '#1890ff' },
  { type: 'rag', label: '知识检索', color: '#722ed1' },
  { type: 'code', label: '代码', color: '#13c2c2' },
  { type: 'condition', label: '条件', color: '#faad14' },
  { type: 'http', label: 'HTTP', color: '#eb2f96' },
  { type: 'human', label: '人工', color: '#fa8c16' },
  { type: 'tool', label: '工具', color: '#874aaf' },
]

// 默认边选项 - 使用自定义可删除边
const defaultEdgeOptions = {
  type: 'default',
  animated: true,
  style: { stroke: '#1890ff', strokeWidth: 2 },
  markerEnd: { type: MarkerType.ArrowClosed, color: '#1890ff' },
}

export function WorkflowEditor() {
  const { id } = useParams()
  const navigate = useNavigate()
  const {
    currentWorkflow,
    nodes,
    edges,
    loading,
    fetchOne,
    create,
    update,
    setNodes,
    setEdges,
    addNode,
    setCurrent,
  } = useWorkflowStore()
  const [form] = Form.useForm()
  const [saving, setSaving] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)

  // 测试对话框状态
  const [testModalOpen, setTestModalOpen] = useState(false)
  const [testInput, setTestInput] = useState('')
  const [testExecuting, setTestExecuting] = useState(false)
  const [testResult, setTestResult] = useState<string | null>(null)
  const [testError, setTestError] = useState<string | null>(null)

  // 计算 isNew 和 ref
  const isNew = id === 'new'
  const workflowIdRef = useRef<string>(id || 'new')

  // 当 id 变化时更新 ref
  useEffect(() => {
    workflowIdRef.current = id || 'new'
  }, [id])

  // 如果 id 为 undefined，重定向到列表页
  useEffect(() => {
    if (id === undefined) {
      navigate('/workflows', { replace: true })
    }
  }, [id, navigate])

  // 监听边删除事件
  useEffect(() => {
    const handleEdgeDelete = (e: CustomEvent) => {
      const edgeId = e.detail.id
      setEdges(edges.filter((edge: Edge) => edge.id !== edgeId) as any)
    }
    window.addEventListener('edge-delete', handleEdgeDelete as EventListener)
    return () => {
      window.removeEventListener('edge-delete', handleEdgeDelete as EventListener)
    }
  }, [edges, setEdges])

  // 根据路由参数初始化工作流
  useEffect(() => {
    console.log('Init useEffect, id:', id, 'isNew:', isNew)
    if (id && id !== 'new') {
      fetchOne(id)
    } else if (id === 'new') {
      // 新建工作流：清空当前工作流数据和表单
      console.log('Initializing default nodes for new workflow')
      setCurrent(null)
      form.resetFields()
      setNodes([
        { id: 'start-1', type: 'start', position: { x: 50, y: 250 }, data: {} },
        { id: 'end-1', type: 'end', position: { x: 600, y: 250 }, data: {} },
      ])
      setEdges([
        { id: 'e-start-end', source: 'start-1', target: 'end-1', ...defaultEdgeOptions },
      ])
    }
  }, [id])

  // 如果 id 为 undefined，显示加载状态（在所有 hooks 之后）
  if (id === undefined) {
    return <div style={{ textAlign: 'center', padding: 100 }}>跳转中...</div>
  } // 只依赖 id，避免其他依赖导致的重复执行

  useEffect(() => {
    if (currentWorkflow) {
      form.setFieldsValue({
        name: currentWorkflow.name,
        description: currentWorkflow.description,
        status: currentWorkflow.status,
      })
    }
  }, [currentWorkflow])

  // 删除节点函数 - 使用 getState() 避免依赖变化
  const deleteNode = useCallback((nodeId: string) => {
    const { nodes, edges, setNodes, setEdges } = useWorkflowStore.getState()
    // 删除节点及其相关的边
    setNodes(nodes.filter((n) => n.id !== nodeId) as any)
    setEdges(edges.filter((e) => e.source !== nodeId && e.target !== nodeId) as any)
    message.success('节点已删除')
  }, []) // 空依赖，函数引用稳定

  // 动态创建 nodeTypes（包含删除回调）
  const nodeTypes = useMemo(() => createNodeTypes(deleteNode), [deleteNode])

  // 处理节点变化（拖拽、删除等）
  const onNodesChange: OnNodesChange = useCallback(
    (changes) => setNodes(applyNodeChanges(changes, nodes as Node[]) as any),
    [nodes, setNodes]
  )

  // 处理边变化（删除等）
  const onEdgesChange: OnEdgesChange = useCallback(
    (changes) => setEdges(applyEdgeChanges(changes, edges) as any),
    [edges, setEdges]
  )

  // 处理新增连接
  const onConnect = useCallback(
    (params: Connection) => setEdges(addEdge({ ...params, ...defaultEdgeOptions }, edges) as any),
    [edges, setEdges]
  )

  const onNodeClick = useCallback(
    (_: any, node: Node) => {
      setSelectedNode(node)
      setDrawerOpen(true)
    },
    []
  )

  const handleConfigChange = useCallback(
    (config: Record<string, unknown>) => {
      if (!selectedNode) return
      setNodes(
        nodes.map((n) =>
          n.id === selectedNode.id ? { ...n, data: config } : n
        ) as any
      )
    },
    [selectedNode, nodes, setNodes]
  )

  const handleSave = async () => {
    try {
      const values = await form.validateFields()
      setSaving(true)

      if (isNew) {
        console.log('Creating new workflow with:', { name: values.name, description: values.description, definition: { nodes, edges } })
        const workflow = await create({
          name: values.name,
          description: values.description,
          definition: { nodes, edges },
        })
        console.log('Created workflow:', workflow)
        if (!workflow || !workflow.id) {
          message.error('创建失败：未获取到工作流 ID')
          console.error('Invalid workflow response:', workflow)
          return
        }
        message.success('创建成功')
        // 立即更新 ref，避免 navigate 后的竞态条件
        workflowIdRef.current = workflow.id
        navigate(`/workflows/${workflow.id}`)
      } else {
        const currentId = workflowIdRef.current
        console.log('Updating workflow, currentId:', currentId, 'isNew:', isNew, 'id:', id)
        if (!currentId || currentId === 'new') {
          message.error('工作流 ID 无效')
          return
        }
        await update(currentId, {
          name: values.name,
          description: values.description,
          definition: { nodes, edges },
        })
        message.success('保存成功')
      }
    } catch (error: any) {
      console.error('Save error:', error)
      message.error(error.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  // 打开测试对话框
  const handleOpenTest = () => {
    setTestModalOpen(true)
    setTestInput('')
    setTestResult(null)
    setTestError(null)
  }

  // 执行工作流测试
  const handleTestExecute = async () => {
    const currentId = workflowIdRef.current
    if (!currentId || isNew || currentId === 'new') {
      message.warning('请先保存工作流后再执行测试')
      return
    }
    setTestExecuting(true)
    setTestError(null)
    setTestResult(null)

    try {
      // 先保存当前配置
      const values = form.getFieldsValue()
      await update(currentId, {
        name: values.name,
        description: values.description,
        definition: { nodes, edges },
      })

      // 执行工作流 - 直接传递 query 变量，而不是嵌套在 input 中
      const response = await workflowApi.execute(currentId, { query: testInput })

      // 显示执行结果
      setTestResult(JSON.stringify(response.data, null, 2))
    } catch (error: any) {
      setTestError(error.response?.data?.detail || error.message || '执行失败')
    } finally {
      setTestExecuting(false)
    }
  }

  if (!isNew && loading) {
    return <div style={{ textAlign: 'center', padding: 100 }}>加载中...</div>
  }

  return (
    <div style={{ height: 'calc(100vh - 150px)', display: 'flex', flexDirection: 'column' }}>
      <Card style={{ marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/workflows')}>
            返回
          </Button>
          <Form form={form} layout="inline" style={{ display: 'inline-flex' }}>
            <Form.Item name="name" rules={[{ required: true, message: '请输入名称' }]}>
              <Input placeholder="工作流名称" style={{ width: 200 }} />
            </Form.Item>
            <Form.Item name="description">
              <Input placeholder="描述" style={{ width: 300 }} />
            </Form.Item>
          </Form>
          <Button type="primary" icon={<SaveOutlined />} onClick={handleSave} loading={saving}>
            保存
          </Button>
          {isNew && <span style={{ color: '#999', marginLeft: 8 }}>保存后可执行</span>}
          {!isNew && (
            <Button icon={<PlayCircleOutlined />} onClick={handleOpenTest}>
              测试
            </Button>
          )}
        </Space>
      </Card>

      <div style={{ display: 'flex', flex: 1 }}>
        <Card style={{ width: 200, marginRight: 16 }} title="节点类型">
          <Space direction="vertical" style={{ width: '100%' }}>
            {nodeTemplates.map((t) => (
              <Button
                key={t.type}
                block
                style={{ background: t.color, color: '#fff' }}
                onClick={() => {
                  const currentNodes = useWorkflowStore.getState().nodes
                  const maxX = currentNodes.reduce((max, n) => Math.max(max, n.position.x), 0)
                  const newNode: Node = {
                    id: `${t.type}-${Date.now()}`,
                    type: t.type,
                    position: { x: maxX + 150, y: 200 + Math.random() * 100 },
                    data: {},
                  }
                  addNode(newNode as any)
                }}
              >
                {t.label}
              </Button>
            ))}
          </Space>
        </Card>

        <div style={{ flex: 1, background: '#f5f5f5', borderRadius: 8 }}>
          <ReactFlowProvider>
            <FlowCanvas
              nodes={nodes}
              edges={edges}
              onNodesChange={onNodesChange}
              onEdgesChange={onEdgesChange}
              onConnect={onConnect}
              onNodeClick={onNodeClick}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              defaultEdgeOptions={defaultEdgeOptions}
            />
          </ReactFlowProvider>
        </div>
      </div>

      <Drawer
        title="节点配置"
        open={drawerOpen}
        onClose={() => {
          setDrawerOpen(false)
          setSelectedNode(null)
        }}
        width={500}
        destroyOnClose
      >
        <NodeConfigPanel
          selectedNode={selectedNode}
          nodes={nodes as Node[]}
          edges={edges}
          onConfigChange={handleConfigChange}
        />
      </Drawer>

      {/* 测试对话框 */}
      <Modal
        title="工作流测试"
        open={testModalOpen}
        onCancel={() => setTestModalOpen(false)}
        footer={null}
        width={600}
      >
        <div style={{ marginBottom: 16 }}>
          <Text>输入测试数据：</Text>
          <TextArea
            rows={4}
            value={testInput}
            onChange={(e) => setTestInput(e.target.value)}
            placeholder="输入测试内容..."
            style={{ marginTop: 8 }}
          />
        </div>
        <Button
          type="primary"
          icon={<SendOutlined />}
          onClick={handleTestExecute}
          loading={testExecuting}
          disabled={!testInput.trim()}
        >
          发送执行
        </Button>

        {testExecuting && (
          <div style={{ marginTop: 16, textAlign: 'center' }}>
            <Spin tip="正在执行工作流..." />
          </div>
        )}

        {testError && (
          <div style={{ marginTop: 16, padding: 12, background: '#fff2f0', borderRadius: 4, border: '1px solid #ffccc7' }}>
            <Text type="danger">执行错误: {testError}</Text>
          </div>
        )}

        {testResult && (
          <div style={{ marginTop: 16, padding: 12, background: '#f6ffed', borderRadius: 4, border: '1px solid #b7eb8f' }}>
            <Text strong>执行结果：</Text>
            <pre style={{ marginTop: 8, whiteSpace: 'pre-wrap', fontSize: 12 }}>{testResult}</pre>
          </div>
        )}
      </Modal>
    </div>
  )
}

// 内部画布组件 - 使用 useReactFlow
function FlowCanvas({
  nodes,
  edges,
  onNodesChange,
  onEdgesChange,
  onConnect,
  onNodeClick,
  nodeTypes,
  edgeTypes,
  defaultEdgeOptions,
}: {
  nodes: Node[]
  edges: Edge[]
  onNodesChange: OnNodesChange
  onEdgesChange: OnEdgesChange
  onConnect: (params: Connection) => void
  onNodeClick: (_: any, node: Node) => void
  nodeTypes: NodeTypes
  edgeTypes: EdgeTypes
  defaultEdgeOptions: any
}) {
  const { fitView } = useReactFlow()

  // 当 nodes 变化时自动调整视图
  useEffect(() => {
    if (nodes.length > 0) {
      // 延迟执行 fitView，确保节点已渲染
      setTimeout(() => fitView({ padding: 0.2 }), 50)
    }
  }, [nodes.length, fitView])

  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      onNodesChange={onNodesChange}
      onEdgesChange={onEdgesChange}
      onConnect={onConnect}
      onNodeClick={onNodeClick}
      nodeTypes={nodeTypes}
      edgeTypes={edgeTypes}
      defaultEdgeOptions={defaultEdgeOptions}
      nodesDraggable={true}
      nodesConnectable={true}
      elementsSelectable={true}
      selectNodesOnDrag={false}
      panOnDrag={[1, 2]}
      panOnScroll={true}
      deleteKeyCode="Delete"
      fitView
    >
      <Background />
      <Controls />
      <MiniMap />
    </ReactFlow>
  )
}
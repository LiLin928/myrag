import { useEffect, useCallback, useState, useRef } from 'react'
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
import { Card, Button, Space, Form, Input, message, Drawer } from 'antd'
import { SaveOutlined, PlayCircleOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { useWorkflowStore } from '../../stores/workflowStore'
import { NodeConfigPanel } from '../../components/Workflow/NodeConfigPanel'

// 自定义节点组件 - 横向布局
function StartNode({ data: _data }: { data: any }) {
  return (
    <div style={{
      padding: '10px 20px',
      background: '#52c41a',
      borderRadius: '50%',
      color: '#fff',
      fontWeight: 'bold',
    }}>
      开始
      <Handle type="source" position={Position.Right} />
    </div>
  )
}

function EndNode({ data: _data }: { data: any }) {
  return (
    <div style={{
      padding: '10px 20px',
      background: '#ff4d4f',
      borderRadius: '50%',
      color: '#fff',
      fontWeight: 'bold',
    }}>
      结束
      <Handle type="target" position={Position.Left} />
    </div>
  )
}

function LLMNode({ data }: { data: any }) {
  const displayName = data?.model_name || '未配置'
  return (
    <div style={{
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
    </div>
  )
}

function RAGNode({ data }: { data: any }) {
  const displayName = data?.knowledge_base_name || '未配置'
  return (
    <div style={{
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
    </div>
  )
}

function CodeNode({ data: _data }: { data: any }) {
  return (
    <div style={{
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
    </div>
  )
}

function ConditionNode({ data }: { data: any }) {
  return (
    <div style={{
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
    </div>
  )
}

function HttpNode({ data }: { data: any }) {
  return (
    <div style={{
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
    </div>
  )
}

function HumanNode({ data: _data }: { data: any }) {
  return (
    <div style={{
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
    </div>
  )
}

function ToolNode({ data }: { data: any }) {
  return (
    <div style={{
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
    </div>
  )
}

const nodeTypes: NodeTypes = {
  start: StartNode,
  end: EndNode,
  llm: LLMNode,
  rag: RAGNode,
  code: CodeNode,
  condition: ConditionNode,
  http: HttpNode,
  human: HumanNode,
  tool: ToolNode,
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
  } = useWorkflowStore()
  const [form] = Form.useForm()
  const [saving, setSaving] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedNode, setSelectedNode] = useState<Node | null>(null)

  const isNew = id === 'new'
  const initialized = useRef(false)

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

  // 只在首次加载时初始化
  useEffect(() => {
    if (initialized.current) return
    initialized.current = true

    if (!isNew && id) {
      fetchOne(id)
    } else {
      // 新建工作流初始化默认节点 - 横向布局
      setNodes([
        { id: 'start-1', type: 'start', position: { x: 50, y: 250 }, data: {} },
        { id: 'end-1', type: 'end', position: { x: 600, y: 250 }, data: {} },
      ])
      setEdges([
        { id: 'e-start-end', source: 'start-1', target: 'end-1', ...defaultEdgeOptions },
      ])
    }
  }, [id, isNew, fetchOne, setNodes, setEdges])

  useEffect(() => {
    if (currentWorkflow) {
      form.setFieldsValue({
        name: currentWorkflow.name,
        description: currentWorkflow.description,
        status: currentWorkflow.status,
      })
    }
  }, [currentWorkflow])

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
        const workflow = await create({
          name: values.name,
          description: values.description,
          definition: { nodes, edges },
        })
        message.success('创建成功')
        navigate(`/workflows/${workflow.id}`)
      } else {
        await update(id!, {
          name: values.name,
          description: values.description,
          definition: { nodes, edges },
        })
        message.success('保存成功')
      }
    } catch (error: any) {
      message.error(error.message || '保存失败')
    } finally {
      setSaving(false)
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
            <Button icon={<PlayCircleOutlined />} onClick={() => navigate(`/workflows/${id}/execute`)}>
              执行
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
      >
        <NodeConfigPanel
          selectedNode={selectedNode}
          nodes={nodes as Node[]}
          edges={edges}
          onConfigChange={handleConfigChange}
        />
      </Drawer>
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
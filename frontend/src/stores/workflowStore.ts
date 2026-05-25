import { create } from 'zustand'
import { Workflow, WorkflowNode, WorkflowEdge } from '../types/models'
import { workflowApi, CreateWorkflowRequest, WorkflowExecution } from '../api/workflows'

export interface ProgressEvent {
  type: string
  execution_id: string
  workflow_id?: string
  timestamp: string
  node_id?: string
  node_name?: string
  node_type?: string
  input_data?: Record<string, unknown>
  output_data?: Record<string, unknown>
  error_message?: string
  duration_ms?: number
  progress_percent?: number
  total_nodes?: number
  completed_nodes?: number
  final_output?: Record<string, unknown>
  reason?: string
}

interface WorkflowState {
  workflows: Workflow[]
  currentWorkflow: Workflow | null
  executions: WorkflowExecution[]
  currentExecution: WorkflowExecution | null
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
  loading: boolean
  executing: boolean
  progressEvents: ProgressEvent[]
  currentProgress: number
  completedNodes: number
  totalNodes: number
  fetchList: () => Promise<void>
  fetchOne: (id: string) => Promise<void>
  create: (data: CreateWorkflowRequest) => Promise<Workflow>
  update: (id: string, data: Partial<CreateWorkflowRequest>) => Promise<void>
  delete: (id: string) => Promise<void>
  execute: (id: string, input?: Record<string, any>) => Promise<WorkflowExecution>
  fetchExecutions: (id: string) => Promise<void>
  setNodes: (nodes: WorkflowNode[]) => void
  setEdges: (edges: WorkflowEdge[]) => void
  addNode: (node: WorkflowNode) => void
  removeNode: (nodeId: string) => void
  addEdge: (edge: WorkflowEdge) => void
  removeEdge: (edgeId: string) => void
  updateNodeData: (nodeId: string, data: Record<string, any>) => void
  setCurrent: (workflow: Workflow | null) => void
  setProgressEvent: (event: ProgressEvent) => void
  clearProgressEvents: () => void
  setCurrentExecution: (execution: WorkflowExecution | null) => void
  setExecuting: (executing: boolean) => void
}

export const useWorkflowStore = create<WorkflowState>((set, get) => ({
  workflows: [],
  currentWorkflow: null,
  executions: [],
  currentExecution: null,
  nodes: [],
  edges: [],
  loading: false,
  executing: false,
  progressEvents: [],
  currentProgress: 0,
  completedNodes: 0,
  totalNodes: 0,

  fetchList: async () => {
    set({ loading: true })
    try {
      const response = await workflowApi.list()
      set({ workflows: response.data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchOne: async (id) => {
    set({ loading: true })
    try {
      const response = await workflowApi.get(id)
      const workflow = response.data
      set({
        currentWorkflow: workflow,
        nodes: workflow.definition?.nodes || [],
        edges: workflow.definition?.edges || [],
        loading: false,
      })
    } catch {
      set({ loading: false })
    }
  },

  create: async (data) => {
    const response = await workflowApi.create(data)
    const workflow = response.data
    set({ workflows: [...get().workflows, workflow] })
    return workflow
  },

  update: async (id, data) => {
    const response = await workflowApi.update(id, {
      ...data,
      definition: { nodes: get().nodes, edges: get().edges },
    })
    set({
      workflows: get().workflows.map((w) => (w.id === id ? response.data : w)),
      currentWorkflow: response.data,
    })
  },

  delete: async (id) => {
    await workflowApi.delete(id)
    set({
      workflows: get().workflows.filter((w) => w.id !== id),
      currentWorkflow: null,
    })
  },

  execute: async (id, input) => {
    set({ executing: true })
    try {
      const response = await workflowApi.execute(id, { input })
      set({ currentExecution: response.data, executing: false })
      return response.data
    } catch {
      set({ executing: false })
      throw new Error('执行失败')
    }
  },

  fetchExecutions: async (id) => {
    try {
      const response = await workflowApi.getExecutions(id)
      set({ executions: response.data })
    } catch {}
  },

  setNodes: (nodes) => set({ nodes }),
  setEdges: (edges) => set({ edges }),

  addNode: (node) => set({ nodes: [...get().nodes, node] }),

  removeNode: (nodeId) => {
    set({
      nodes: get().nodes.filter((n) => n.id !== nodeId),
      edges: get().edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
    })
  },

  addEdge: (edge) => set({ edges: [...get().edges, edge] }),

  removeEdge: (edgeId) => set({ edges: get().edges.filter((e) => e.id !== edgeId) }),

  updateNodeData: (nodeId, data) => {
    set({
      nodes: get().nodes.map((n) =>
        n.id === nodeId ? { ...n, data: { ...n.data, ...data } } : n
      ),
    })
  },

  setCurrent: (workflow) => set({
    currentWorkflow: workflow,
    nodes: workflow?.definition?.nodes || [],
    edges: workflow?.definition?.edges || [],
  }),

  setProgressEvent: (event) => {
    set((state) => {
      const updates: Partial<WorkflowState> = {
        progressEvents: [...state.progressEvents, event],
      }

      if (
        event.type === 'execution_progress' ||
        event.type === 'execution_start'
      ) {
        if (event.progress_percent !== undefined) {
          updates.currentProgress = event.progress_percent
        }
        if (event.completed_nodes !== undefined) {
          updates.completedNodes = event.completed_nodes
        }
        if (event.total_nodes !== undefined) {
          updates.totalNodes = event.total_nodes
        }
      }

      return updates
    })
  },

  clearProgressEvents: () => set({
    progressEvents: [],
    currentProgress: 0,
    completedNodes: 0,
    totalNodes: 0,
  }),

  setCurrentExecution: (execution) => set({ currentExecution: execution }),

  setExecuting: (executing) => set({ executing }),
}))
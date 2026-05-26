import { apiClient } from './client'
import { Workflow, WorkflowDefinition } from '../types/models'

export interface CreateWorkflowRequest {
  name: string
  description?: string
  definition?: WorkflowDefinition
}

export interface UpdateWorkflowRequest {
  name?: string
  description?: string
  definition?: WorkflowDefinition
  status?: 'draft' | 'published' | 'archived'
}

export interface ExecuteWorkflowRequest {
  input?: Record<string, any>
  query?: string  // 直接传递查询字符串，用于 RAG 检索
}

export interface WorkflowExecution {
  id: string
  workflow_id: string
  status: 'running' | 'completed' | 'failed' | 'paused'
  input: Record<string, any>
  output?: Record<string, unknown>
  created_at: string
  completed_at?: string
  error_message?: string
  current_node?: string
}

export interface ExecutionHistoryItem {
  id: string
  workflow_id: string
  workflow_name: string
  status: string
  started_at: string | null
  completed_at: string | null
  duration_ms: number | null
  triggered_by: string
  error_summary: string | null
}

export interface ExecutionHistoryResponse {
  items: ExecutionHistoryItem[]
  total: number
  page: number
  page_size: number
}

export interface ExecutionHistoryParams {
  workflow_id?: string
  status?: string
  start_date?: string
  end_date?: string
  page?: number
  page_size?: number
}

export const workflowApi = {
  list: () => apiClient.get<Workflow[]>('/workflows'),

  get: (id: string) => apiClient.get<Workflow>(`/workflows/${id}`),

  create: (data: CreateWorkflowRequest) => apiClient.post<Workflow>('/workflows', data),

  update: (id: string, data: UpdateWorkflowRequest) =>
    apiClient.put<Workflow>(`/workflows/${id}`, data),

  delete: (id: string) => apiClient.delete(`/workflows/${id}`),

  execute: (id: string, data: ExecuteWorkflowRequest) =>
    apiClient.post<WorkflowExecution>(`/workflows/${id}/execute`, data),

  getExecutions: (id: string) =>
    apiClient.get<WorkflowExecution[]>(`/workflows/${id}/executions`),

  getExecution: (workflowId: string, executionId: string) =>
    apiClient.get<WorkflowExecution>(`/workflows/${workflowId}/executions/${executionId}`),

  listExecutions: (params: ExecutionHistoryParams) =>
    apiClient.get<ExecutionHistoryResponse>('/workflows/executions', { params }),

  deleteExecution: (executionId: string) =>
    apiClient.delete(`/workflows/executions/${executionId}`),

  rerunExecution: (executionId: string) =>
    apiClient.post<{ execution_id: string; message: string }>(`/workflows/executions/${executionId}/rerun`),
}
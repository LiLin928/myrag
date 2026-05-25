import { apiClient } from './client'
import { WorkflowDefinition } from '../types/models'

export interface WorkflowTemplate {
  id: string
  name: string
  category: string
  description: string
  tags: string[]
  is_builtin: boolean
  usage_count: number
}

export interface WorkflowTemplateDetail extends WorkflowTemplate {
  definition: WorkflowDefinition
  default_input_variables: Record<string, unknown>
}

export interface CreateTemplateRequest {
  name: string
  category: string
  description?: string
  definition: WorkflowDefinition
  default_input_variables?: Record<string, unknown>
  tags?: string[]
}

export interface CreateWorkflowFromTemplateRequest {
  name?: string
}

export const templateApi = {
  list: (category?: string) =>
    apiClient.get<WorkflowTemplate[]>('/workflow-templates/', { params: { category } }),

  get: (id: string) =>
    apiClient.get<WorkflowTemplateDetail>(`/workflow-templates/${id}/`),

  create: (data: CreateTemplateRequest) =>
    apiClient.post<{ id: string; name: string; category: string }>('/workflow-templates/', data),

  createWorkflowFromTemplate: (templateId: string, data: CreateWorkflowFromTemplateRequest) =>
    apiClient.post<{ id: string; name: string; template_name: string }>(
      `/workflow-templates/${templateId}/create-workflow/`,
      data
    ),

  update: (id: string, data: Partial<CreateTemplateRequest>) =>
    apiClient.put<{ id: string; message: string }>(`/workflow-templates/${id}/`, data),

  delete: (id: string) =>
    apiClient.delete<{ message: string }>(`/workflow-templates/${id}/`),
}
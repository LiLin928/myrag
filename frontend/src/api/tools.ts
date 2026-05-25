import { apiClient } from './client'
import { Tool, CreateToolRequest } from '../types/models'

export const toolApi = {
  list: (toolType?: 'http' | 'mcp') =>
    apiClient.get<Tool[]>(`/tools/${toolType ? `?tool_type=${toolType}` : ''}`),

  get: (id: string) => apiClient.get<Tool>(`/tools/${id}`),

  create: (data: CreateToolRequest) => apiClient.post<Tool>('/tools/', data),

  update: (id: string, data: Partial<CreateToolRequest>) =>
    apiClient.put<Tool>(`/tools/${id}`, data),

  delete: (id: string) => apiClient.delete(`/tools/${id}`),

  toggleEnable: (id: string, is_enabled: boolean) =>
    apiClient.patch(`/tools/${id}/enable`, { is_enabled }),

  test: (id: string, input_data: Record<string, any> = {}) =>
    apiClient.post(`/tools/${id}/test`, input_data),

  available: () => apiClient.get<Tool[]>('/tools/available'),
}
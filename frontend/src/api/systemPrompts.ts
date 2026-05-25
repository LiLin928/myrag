import { apiClient } from './client'
import { SystemPromptTemplate } from '../types/models'

export const systemPromptsApi = {
  list: (params?: { category?: string; is_public?: boolean }) =>
    apiClient.get<SystemPromptTemplate[]>('/system-prompts', { params }),

  get: (id: string) =>
    apiClient.get<SystemPromptTemplate>(`/system-prompts/${id}`),

  create: (data: {
    name: string
    description?: string
    content: string
    category?: string
    is_public?: boolean
  }) =>
    apiClient.post<SystemPromptTemplate>('/system-prompts', data),

  update: (id: string, data: Partial<{
    name: string
    description: string
    content: string
    category: string
    is_public: boolean
  }>) =>
    apiClient.put<SystemPromptTemplate>(`/system-prompts/${id}`, data),

  delete: (id: string) =>
    apiClient.delete(`/system-prompts/${id}`),

  getCategories: () =>
    apiClient.get<{ category: string; count: number }[]>('/system-prompts/categories'),
}
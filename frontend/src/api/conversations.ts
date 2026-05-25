import { apiClient } from './client'
import { Conversation, Message, ConversationConfig, ConfigUpdateRequest, CreateConversationRequest } from '../types/models'

export const conversationApi = {
  list: (projectId?: string) =>
    apiClient.get<Conversation[]>('/conversations/', { project_id: projectId }),

  get: (id: string) =>
    apiClient.get<Conversation>(`/conversations/${id}/`),

  create: (data: CreateConversationRequest) =>
    apiClient.post<Conversation>('/conversations/', data),

  delete: (id: string) =>
    apiClient.delete(`/conversations/${id}/`),

  getMessages: (id: string) =>
    apiClient.get<Message[]>(`/conversations/${id}/messages/`),

  sendMessage: (id: string, message: string) =>
    apiClient.post<{ response: string }>(`/conversations/${id}/messages/`, { message }),

  // 新增：更新配置
  updateConfig: (id: string, data: ConfigUpdateRequest) =>
    apiClient.put(`/conversations/${id}/config`, data),

  // 新增：获取配置
  getConfig: (id: string) =>
    apiClient.get<{
      id: string
      mode: string
      model: string
      config: ConversationConfig | null
      workflow_id: string | null
      system_prompt_template_id: string | null
      system_prompt_template_content: string | null
      custom_system_prompt: string | null
      greeting_enabled: boolean
      greeting_content: string | null
      greeting_sent: boolean
    }>(`/conversations/${id}/config`),

  // 新增：发送开场白
  sendGreeting: (id: string) =>
    apiClient.post(`/conversations/${id}/send-greeting`),

  // 新增：获取配置历史
  getConfigHistory: (id: string, limit?: number) =>
    apiClient.get(`/conversations/${id}/config-history`, { params: { limit } }),
}
import { apiClient } from './client'

// Types
export interface Agent {
  id: string
  user_id: string
  name: string
  description?: string
  model_id: string
  model_name?: string
  system_prompt?: string
  use_knowledge: boolean
  use_tools: boolean
  use_skills: boolean
  search_type: string
  top_k: number
  score_threshold: number
  knowledge_bindings: KnowledgeBinding[]
  tool_bindings: string[]
  skill_bindings: string[]
  created_at: string
  updated_at: string
}

export interface KnowledgeBinding {
  id: string
  knowledge_base_id: string
  knowledge_base_name?: string
  search_type: string
  top_k: number
  score_threshold: number
  priority: number
}

export interface CreateAgentRequest {
  name: string
  description?: string
  model_id: string
  system_prompt?: string
  use_knowledge?: boolean
  use_tools?: boolean
  use_skills?: boolean
  knowledge_bindings?: Array<{
    knowledge_base_id: string
    search_type?: string
    top_k?: number
    score_threshold?: number
  }>
  tool_bindings?: string[]
  skill_bindings?: string[]
}

export interface ChatRequest {
  message: string
  use_knowledge?: boolean
  use_tools?: boolean
}

export interface ChatResponse {
  session_id: string
  response: string
  sources: Array<{ doc_name: string; chunk: string; score: number }>
  tool_calls: Array<{ tool: string; args: any; result?: string }>
  created_at: string
}

export interface Session {
  id: string
  agent_id: string
  thread_id: string
  title?: string
  message_count: number
  created_at: string
  updated_at: string
}

// API
export const agentApi = {
  list: () => apiClient.get<Agent[]>('/agents/'),

  get: (id: string) => apiClient.get<Agent>(`/agents/${id}/`),

  create: (data: CreateAgentRequest) => apiClient.post<Agent>('/agents/', data),

  update: (id: string, data: Partial<CreateAgentRequest>) =>
    apiClient.put<Agent>(`/agents/${id}/`, data),

  delete: (id: string) => apiClient.delete(`/agents/${id}/`),

  // Chat
  chat: (agentId: string, data: ChatRequest) =>
    apiClient.post<ChatResponse>(`/agents/${agentId}/chat/`, data),

  continueChat: (agentId: string, sessionId: string, data: ChatRequest) =>
    apiClient.post<ChatResponse>(`/agents/${agentId}/sessions/${sessionId}/chat/`, data),

  // Sessions
  listSessions: (agentId: string) =>
    apiClient.get<Session[]>(`/agents/${agentId}/sessions/`),

  getSession: (agentId: string, sessionId: string) =>
    apiClient.get<Session>(`/agents/${agentId}/sessions/${sessionId}/`),

  deleteSession: (agentId: string, sessionId: string) =>
    apiClient.delete(`/agents/${agentId}/sessions/${sessionId}/`),

  // All sessions history (user level)
  listAllSessions: (params?: {
    agent_id?: string
    start_date?: string
    end_date?: string
    page?: number
    page_size?: number
  }) => apiClient.get<Session[]>('/agent-sessions/history/', { params }),

  getSessionDetail: (sessionId: string) =>
    apiClient.get<Session>(`/agent-sessions/history/${sessionId}/`),

  deleteSessionById: (sessionId: string) =>
    apiClient.delete(`/agent-sessions/history/${sessionId}/`),
}
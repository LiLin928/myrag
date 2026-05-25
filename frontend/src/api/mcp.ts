import { apiClient } from './client'

export interface McpConnection {
  id: string
  name: string
  description: string
  transport_type: 'stdio' | 'sse' | 'websocket'
  connection_url?: string
  command?: string
  args?: string[]
  env_vars?: Record<string, string>
  is_enabled: boolean
  is_public: boolean
  sync_status: 'pending' | 'success' | 'failed'
  sync_error?: string
  last_sync_at?: string
}

export interface CreateMcpConnectionRequest {
  name: string
  description?: string
  transport_type?: 'stdio' | 'sse' | 'websocket'
  connection_url?: string
  command?: string
  args?: string[]
  env_vars?: Record<string, string>
  is_public?: boolean
}

export const mcpApi = {
  listConnections: () => apiClient.get<McpConnection[]>('/mcp/connections'),

  getConnection: (id: string) => apiClient.get<McpConnection>(`/mcp/connections/${id}`),

  createConnection: (data: CreateMcpConnectionRequest) =>
    apiClient.post<McpConnection>('/mcp/connections', data),

  updateConnection: (id: string, data: Partial<CreateMcpConnectionRequest>) =>
    apiClient.put<McpConnection>(`/mcp/connections/${id}`, data),

  deleteConnection: (id: string) => apiClient.delete(`/mcp/connections/${id}`),

  syncTools: (id: string) => apiClient.post(`/mcp/connections/${id}/sync`),

  getConnectionTools: (id: string) => apiClient.get(`/mcp/connections/${id}/tools`),

  testConnection: (id: string) => apiClient.post(`/mcp/connections/${id}/test`),
}
import { apiClient } from './client'

// Types
export type ModelType = 'llm' | 'embedding' | 'rerank'

export interface ModelConfig {
  id: string
  name: string
  type: ModelType
  provider: string
  api_base: string
  api_key: string // 脱敏显示
  model_name: string
  context_length?: number
  max_tokens?: number
  temperature?: number
  dimension?: number
  batch_size?: number
  top_k?: number
  timeout: number
  extra_config?: Record<string, any>
  is_active: boolean
  is_default: boolean
  created_by: string
  created_at: string
  updated_at: string
}

export interface CreateModelRequest {
  name: string
  type: ModelType
  provider: string
  api_base: string
  api_key: string
  model_name: string
  context_length?: number
  max_tokens?: number
  temperature?: number
  dimension?: number
  batch_size?: number
  top_k?: number
  timeout?: number
  extra_config?: Record<string, any>
}

export interface UpdateModelRequest {
  name?: string
  provider?: string
  api_base?: string
  api_key?: string
  model_name?: string
  context_length?: number
  max_tokens?: number
  temperature?: number
  dimension?: number
  batch_size?: number
  top_k?: number
  timeout?: number
  extra_config?: Record<string, any>
  is_active?: boolean
}

export interface ModelListResponse {
  items: ModelConfig[]
  total: number
}

// API client
export const modelApi = {
  /**
   * Get list of model configs
   * @param type - Filter by model type (llm, embedding, rerank)
   * @param isActive - Filter by active status
   */
  list: async (type?: ModelType, isActive?: boolean): Promise<ModelListResponse> => {
    const params: Record<string, any> = {}
    if (type) params.type = type
    if (isActive !== undefined) params.is_active = isActive
    const response = await apiClient.get<ModelListResponse>('/models/', params)
    return response.data
  },

  /**
   * Get a single model config by ID
   * @param id - Model config ID
   */
  get: async (id: string): Promise<ModelConfig> => {
    const response = await apiClient.get<ModelConfig>(`/models/${id}`)
    return response.data
  },

  /**
   * Create a new model config
   * @param data - Model config data
   */
  create: async (data: CreateModelRequest): Promise<ModelConfig> => {
    const response = await apiClient.post<ModelConfig>('/models/', data)
    return response.data
  },

  /**
   * Update an existing model config
   * @param id - Model config ID
   * @param data - Updated model config data
   */
  update: async (id: string, data: UpdateModelRequest): Promise<ModelConfig> => {
    const response = await apiClient.put<ModelConfig>(`/models/${id}`, data)
    return response.data
  },

  /**
   * Delete a model config
   * @param id - Model config ID
   */
  delete: async (id: string): Promise<{ deleted: string }> => {
    const response = await apiClient.delete<{ deleted: string }>(`/models/${id}`)
    return response.data
  },

  /**
   * Get the default model for a given type
   * @param type - Model type (llm, embedding, rerank)
   */
  getDefault: async (type: ModelType): Promise<ModelConfig> => {
    const response = await apiClient.get<ModelConfig>(`/models/default/${type}`)
    return response.data
  },

  /**
   * Set the default model for a given type
   * @param type - Model type (llm, embedding, rerank)
   * @param modelId - Model config ID to set as default
   */
  setDefault: async (type: ModelType, modelId: string): Promise<ModelConfig> => {
    const response = await apiClient.put<ModelConfig>(`/models/default/${type}`, {
      model_id: modelId,
    })
    return response.data
  },

  /**
   * Toggle model active status
   * @param id - Model config ID
   * @param isActive - New active status
   */
  toggleActive: async (id: string, isActive: boolean): Promise<ModelConfig> => {
    const response = await apiClient.put<ModelConfig>(`/models/${id}/active`, {
      is_active: isActive,
    })
    return response.data
  },
}

export default modelApi
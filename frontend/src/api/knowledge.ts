import { apiClient } from './client'
import { KnowledgeBase, CreateKnowledgeBaseRequest, KnowledgeDocument, ParseResponse, ChunkListResponse, ChunkDetail } from '../types/models'

export interface KnowledgeListResponse {
  items: KnowledgeBase[]
  total: number
}

export interface SearchResult {
  id: string
  content: string
  score: number
  source: string
  metadata: Record<string, any>
}

export interface SearchResponse {
  results: SearchResult[]
  total: number
  query: string
}

export const knowledgeApi = {
  // ========== 知识库管理 ==========

  list: () =>
    apiClient.get<KnowledgeListResponse>('/knowledge'),

  get: (id: string) =>
    apiClient.get<KnowledgeBase>(`/knowledge/${id}`),

  create: (data: CreateKnowledgeBaseRequest) =>
    apiClient.post<KnowledgeBase>('/knowledge', data),

  update: (id: string, data: Partial<CreateKnowledgeBaseRequest>) =>
    apiClient.put<KnowledgeBase>(`/knowledge/${id}`, data),

  delete: (id: string) =>
    apiClient.delete(`/knowledge/${id}`),

  // ========== 检索测试 ==========

  search: (knowledgeId: string, params: { query: string; top_k?: number }) =>
    apiClient.post<SearchResponse>(`/knowledge/${knowledgeId}/search`, params),

  // ========== 文档管理 ==========

  listDocuments: (knowledgeId: string) =>
    apiClient.get<KnowledgeDocument[]>(`/knowledge/${knowledgeId}/documents`),

  uploadDocument: (knowledgeId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    // 使用 apiClient.upload 方法上传文件
    return apiClient.upload<KnowledgeDocument>(
      `/knowledge/${knowledgeId}/documents/upload`,
      file
    )
  },

  parseDocument: (knowledgeId: string, documentId: string) =>
    apiClient.post<ParseResponse>(
      `/knowledge/${knowledgeId}/documents/${documentId}/parse`
    ),

  deleteDocument: (knowledgeId: string, documentId: string) =>
    apiClient.delete(`/knowledge/${knowledgeId}/documents/${documentId}`),

  // ========== 分块管理 ==========

  listChunks: (knowledgeId: string, documentId: string, page = 1, pageSize = 20, filters?: {
    section_filter?: string
    has_embedding?: boolean
  }) =>
    apiClient.get<ChunkListResponse>(
      `/knowledge/${knowledgeId}/documents/${documentId}/chunks`,
      { page, page_size: pageSize, ...filters }
    ),

  getChunk: (chunkId: string) =>
    apiClient.get<ChunkDetail>(`/knowledge/chunks/${chunkId}`),
}
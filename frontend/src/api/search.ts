import { apiClient } from './client'

export interface SearchResult {
  id: string
  content: string
  score: number
  metadata: Record<string, any>
  document_id?: string
  document_name?: string
}

export interface SearchRequest {
  query: string
  top_k?: number
  score_threshold?: number
  use_hybrid?: boolean
  supplier?: string
  clause_type?: string
  document_type?: string
  section?: string
}

export const searchApi = {
  searchInProject: (projectId: string, request: SearchRequest) =>
    apiClient.post<{
      query: string
      project_id: string
      filters?: Record<string, string>
      search_type: string
      results_count: number
      results: SearchResult[]
    }>(`/search/projects/${projectId}`, request),

  searchBySupplier: (projectId: string, supplier: string, request: SearchRequest) =>
    apiClient.post<{
      query: string
      project_id: string
      supplier: string
      results_count: number
      results: SearchResult[]
    }>(`/search/projects/${projectId}/supplier/${supplier}`, request),

  searchByClauseType: (projectId: string, clauseType: string, request: SearchRequest) =>
    apiClient.post<{
      query: string
      project_id: string
      clause_type: string
      results_count: number
      results: SearchResult[]
    }>(`/search/projects/${projectId}/clause-type/${clauseType}`, request),

  globalSearch: (request: SearchRequest) =>
    apiClient.post<{
      query: string
      results_count: number
      results: SearchResult[]
    }>('/search/global', request),

  searchInDocument: (documentId: string, request: SearchRequest) =>
    apiClient.post<{
      query: string
      document_id: string
      results_count: number
      results: SearchResult[]
    }>(`/search/documents/${documentId}`, request),
}
import { apiClient } from './client'
import { Document, DocumentChunk } from '../types/models'

export const documentApi = {
  list: (knowledgeBaseId?: string) =>
    apiClient.get<Document[]>('/documents/', { knowledge_base_id: knowledgeBaseId }),

  get: (id: string) =>
    apiClient.get<Document>(`/documents/${id}/`),

  upload: (file: File, knowledgeBaseId: string, onProgress?: (percent: number) => void) =>
    apiClient.upload<Document>(`/documents/upload/?knowledge_base_id=${knowledgeBaseId}`, file, onProgress),

  delete: (id: string) =>
    apiClient.delete(`/documents/${id}/`),

  getChunks: (id: string) =>
    apiClient.get<DocumentChunk[]>(`/documents/${id}/chunks/`),
}
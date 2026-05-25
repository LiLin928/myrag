import { apiClient } from './client'
import { MetadataFieldsResponse, MetadataResponse, MetadataUpdateRequest, MetadataPatchRequest } from '../types/models'

export const metadataApi = {
  // 获取系统预定义字段
  getFields: (type?: 'document' | 'chunk') =>
    apiClient.get<MetadataFieldsResponse>('/metadata/fields', type ? { type } : {}),
}

export const documentMetadataApi = {
  // 获取文档元数据
  get: (knowledgeId: string, documentId: string) =>
    apiClient.get<MetadataResponse>(`/knowledge/${knowledgeId}/documents/${documentId}/metadata`),

  // 全量更新
  update: (knowledgeId: string, documentId: string, data: MetadataUpdateRequest) =>
    apiClient.put<MetadataResponse>(`/knowledge/${knowledgeId}/documents/${documentId}/metadata`, data),

  // 增量更新
  patch: (knowledgeId: string, documentId: string, data: MetadataPatchRequest) =>
    apiClient.patch<MetadataResponse>(`/knowledge/${knowledgeId}/documents/${documentId}/metadata`, data),

  // 删除字段
  deleteField: (knowledgeId: string, documentId: string, fieldName: string) =>
    apiClient.delete(`/knowledge/${knowledgeId}/documents/${documentId}/metadata/${fieldName}`),
}

export const chunkMetadataApi = {
  // 获取分块元数据（含继承）
  get: (chunkId: string) =>
    apiClient.get<MetadataResponse>(`/knowledge/chunks/${chunkId}/metadata`),

  // 全量更新
  update: (chunkId: string, data: MetadataUpdateRequest) =>
    apiClient.put<MetadataResponse>(`/knowledge/chunks/${chunkId}/metadata`, data),

  // 增量更新
  patch: (chunkId: string, data: MetadataPatchRequest) =>
    apiClient.patch<MetadataResponse>(`/knowledge/chunks/${chunkId}/metadata`, data),

  // 删除字段
  deleteField: (chunkId: string, fieldName: string) =>
    apiClient.delete(`/knowledge/chunks/${chunkId}/metadata/${fieldName}`),
}
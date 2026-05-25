import { create } from 'zustand'
import { MetadataResponse, MetadataFieldDefinition } from '../types/models'
import { metadataApi, documentMetadataApi, chunkMetadataApi } from '../api/metadata'

interface MetadataState {
  // 字段定义
  fields: MetadataFieldDefinition[]
  fieldsLoading: boolean

  // 当前文档元数据
  currentDocumentMetadata: MetadataResponse | null
  metadataLoading: boolean

  // Actions
  fetchFields: (type?: 'document' | 'chunk') => Promise<void>
  fetchDocumentMetadata: (knowledgeId: string, documentId: string) => Promise<void>
  updateDocumentMetadata: (knowledgeId: string, documentId: string, metadata: Record<string, string>) => Promise<void>
  patchDocumentMetadata: (knowledgeId: string, documentId: string, name: string, value: string) => Promise<void>
  deleteDocumentMetadataField: (knowledgeId: string, documentId: string, fieldName: string) => Promise<void>

  fetchChunkMetadata: (chunkId: string) => Promise<MetadataResponse>
  patchChunkMetadata: (chunkId: string, name: string, value: string) => Promise<MetadataResponse>
  deleteChunkMetadataField: (chunkId: string, fieldName: string) => Promise<void>

  clearCurrentMetadata: () => void
}

export const useMetadataStore = create<MetadataState>((set, get) => ({
  fields: [],
  fieldsLoading: false,
  currentDocumentMetadata: null,
  metadataLoading: false,

  fetchFields: async (type) => {
    set({ fieldsLoading: true })
    try {
      const response = await metadataApi.getFields(type)
      set({ fields: response.data.fields, fieldsLoading: false })
    } catch (error) {
      set({ fieldsLoading: false })
      console.error('Failed to fetch metadata fields:', error)
    }
  },

  fetchDocumentMetadata: async (knowledgeId, documentId) => {
    set({ metadataLoading: true })
    try {
      const response = await documentMetadataApi.get(knowledgeId, documentId)
      set({ currentDocumentMetadata: response.data, metadataLoading: false })
    } catch (error) {
      set({ metadataLoading: false, currentDocumentMetadata: null })
      console.error('Failed to fetch document metadata:', error)
    }
  },

  updateDocumentMetadata: async (knowledgeId, documentId, metadata) => {
    try {
      const response = await documentMetadataApi.update(knowledgeId, documentId, { metadata })
      set({ currentDocumentMetadata: response.data })
    } catch (error) {
      console.error('Failed to update document metadata:', error)
      throw error
    }
  },

  patchDocumentMetadata: async (knowledgeId, documentId, name, value) => {
    try {
      const response = await documentMetadataApi.patch(knowledgeId, documentId, { name, value })
      set({ currentDocumentMetadata: response.data })
    } catch (error) {
      console.error('Failed to patch document metadata:', error)
      throw error
    }
  },

  deleteDocumentMetadataField: async (knowledgeId, documentId, fieldName) => {
    try {
      await documentMetadataApi.deleteField(knowledgeId, documentId, fieldName)
      // 更新本地状态
      const current = get().currentDocumentMetadata
      if (current) {
        const newOwn = { ...current.own }
        delete newOwn[fieldName]
        const newMerged = { ...current.merged }
        delete newMerged[fieldName]
        set({
          currentDocumentMetadata: {
            inherited: current.inherited,
            own: newOwn,
            merged: newMerged,
          }
        })
      }
    } catch (error) {
      console.error('Failed to delete document metadata field:', error)
      throw error
    }
  },

  fetchChunkMetadata: async (chunkId) => {
    try {
      const response = await chunkMetadataApi.get(chunkId)
      return response.data
    } catch (error) {
      console.error('Failed to fetch chunk metadata:', error)
      throw error
    }
  },

  patchChunkMetadata: async (chunkId, name, value) => {
    try {
      const response = await chunkMetadataApi.patch(chunkId, { name, value })
      return response.data
    } catch (error) {
      console.error('Failed to patch chunk metadata:', error)
      throw error
    }
  },

  deleteChunkMetadataField: async (chunkId, fieldName) => {
    try {
      await chunkMetadataApi.deleteField(chunkId, fieldName)
    } catch (error) {
      console.error('Failed to delete chunk metadata field:', error)
      throw error
    }
  },

  clearCurrentMetadata: () => {
    set({ currentDocumentMetadata: null })
  },
}))
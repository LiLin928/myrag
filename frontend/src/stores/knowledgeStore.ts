import { create } from 'zustand'
import { KnowledgeBase, CreateKnowledgeBaseRequest, KnowledgeDocument } from '../types/models'
import { knowledgeApi } from '../api/knowledge'

interface KnowledgeState {
  knowledgeBases: KnowledgeBase[]
  currentKnowledge: KnowledgeBase | null
  currentDocuments: KnowledgeDocument[]
  loading: boolean
  error: string | null
  fetchList: () => Promise<void>
  fetchOne: (id: string) => Promise<void>
  create: (data: CreateKnowledgeBaseRequest) => Promise<KnowledgeBase>
  update: (id: string, data: Partial<CreateKnowledgeBaseRequest>) => Promise<void>
  delete: (id: string) => Promise<void>
  setCurrent: (kb: KnowledgeBase | null) => void
  // ========== 文档方法 ==========
  fetchDocuments: (knowledgeId: string) => Promise<void>
  uploadDocument: (knowledgeId: string, file: File) => Promise<KnowledgeDocument>
  parseDocument: (knowledgeId: string, documentId: string) => Promise<void>
  deleteDocument: (knowledgeId: string, documentId: string) => Promise<void>
}

export const useKnowledgeStore = create<KnowledgeState>((set, get) => ({
  knowledgeBases: [],
  currentKnowledge: null,
  currentDocuments: [],
  loading: false,
  error: null,

  fetchList: async () => {
    set({ loading: true, error: null })
    try {
      const response = await knowledgeApi.list()
      const data = response.data.items || []
      set({ knowledgeBases: data, loading: false })
    } catch (error: any) {
      set({ error: error.message, loading: false, knowledgeBases: [] })
    }
  },

  fetchOne: async (id: string) => {
    set({ loading: true, error: null })
    try {
      const response = await knowledgeApi.get(id)
      set({ currentKnowledge: response.data, loading: false })
    } catch (error: any) {
      set({ error: error.message, loading: false })
    }
  },

  create: async (data) => {
    set({ loading: true, error: null })
    try {
      const response = await knowledgeApi.create(data)
      const kb = response.data
      set({ knowledgeBases: [...get().knowledgeBases, kb], loading: false })
      return kb
    } catch (error: any) {
      set({ error: error.message, loading: false })
      throw error
    }
  },

  update: async (id, data) => {
    set({ loading: true, error: null })
    try {
      const response = await knowledgeApi.update(id, data)
      set({
        knowledgeBases: get().knowledgeBases.map((kb) =>
          kb.id === id ? response.data : kb
        ),
        currentKnowledge: response.data,
        loading: false,
      })
    } catch (error: any) {
      set({ error: error.message, loading: false })
      throw error
    }
  },

  delete: async (id) => {
    set({ loading: true, error: null })
    try {
      await knowledgeApi.delete(id)
      set({
        knowledgeBases: get().knowledgeBases.filter((kb) => kb.id !== id),
        currentKnowledge: null,
        loading: false,
      })
    } catch (error: any) {
      set({ error: error.message, loading: false })
      throw error
    }
  },

  setCurrent: (kb) => set({ currentKnowledge: kb }),

  // ========== 文档方法 ==========

  fetchDocuments: async (knowledgeId: string) => {
    try {
      const response = await knowledgeApi.listDocuments(knowledgeId)
      set({ currentDocuments: response.data })
    } catch (error: any) {
      set({ error: error.message, currentDocuments: [] })
    }
  },

  uploadDocument: async (knowledgeId: string, file: File) => {
    set({ loading: true, error: null })
    try {
      const response = await knowledgeApi.uploadDocument(knowledgeId, file)
      set({
        currentDocuments: [...get().currentDocuments, response.data],
        loading: false,
      })
      return response.data
    } catch (error: any) {
      set({ error: error.message, loading: false })
      throw error
    }
  },

  parseDocument: async (knowledgeId: string, documentId: string) => {
    try {
      await knowledgeApi.parseDocument(knowledgeId, documentId)
      // WebSocket will update progress, this just triggers parsing
    } catch (error: any) {
      set({ error: error.message })
      throw error
    }
  },

  deleteDocument: async (knowledgeId: string, documentId: string) => {
    set({ loading: true, error: null })
    try {
      await knowledgeApi.deleteDocument(knowledgeId, documentId)
      set({
        currentDocuments: get().currentDocuments.filter(d => d.id !== documentId),
        loading: false,
      })
    } catch (error: any) {
      set({ error: error.message, loading: false })
      throw error
    }
  },
}))
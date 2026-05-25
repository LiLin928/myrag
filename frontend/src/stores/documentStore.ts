import { create } from 'zustand'
import { Document, DocumentChunk } from '../types/models'
import { documentApi } from '../api/documents'

interface DocumentState {
  documents: Document[]
  currentDocument: Document | null
  chunks: DocumentChunk[]
  uploadProgress: number
  loading: boolean
  fetchList: (knowledgeBaseId?: string) => Promise<void>
  fetchOne: (id: string) => Promise<void>
  fetchChunks: (id: string) => Promise<void>
  upload: (file: File, knowledgeBaseId: string) => Promise<Document>
  delete: (id: string) => Promise<void>
}

export const useDocumentStore = create<DocumentState>((set, get) => ({
  documents: [],
  currentDocument: null,
  chunks: [],
  uploadProgress: 0,
  loading: false,

  fetchList: async (knowledgeBaseId) => {
    set({ loading: true })
    try {
      const response = await documentApi.list(knowledgeBaseId)
      set({ documents: response.data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchOne: async (id) => {
    set({ loading: true })
    try {
      const response = await documentApi.get(id)
      set({ currentDocument: response.data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchChunks: async (id) => {
    try {
      const response = await documentApi.getChunks(id)
      set({ chunks: response.data })
    } catch {}
  },

  upload: async (file, knowledgeBaseId) => {
    set({ uploadProgress: 0 })
    const response = await documentApi.upload(file, knowledgeBaseId, (percent) => {
      set({ uploadProgress: percent })
    })
    set({ documents: [...get().documents, response.data] })
    return response.data
  },

  delete: async (id) => {
    await documentApi.delete(id)
    set({ documents: get().documents.filter((d) => d.id !== id) })
  },
}))
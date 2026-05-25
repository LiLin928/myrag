import { create } from 'zustand'
import { apiClient } from '../api/client'

export interface ChunkMetadata {
  document_type?: string
  source_filename?: string
  section_title?: string
  section_level?: number
  position_type?: string
  user_tags: string[]
  category?: string
  note?: string
  custom_fields: Record<string, unknown>
}

export interface Chunk {
  id: string
  document_id: string
  clause_id: string
  clause_type?: string
  clause_title?: string
  content: string
  page_number: number
  content_length: number
  metadata: ChunkMetadata
  has_embedding: boolean
  created_at: string
  updated_at?: string
}

export interface ChunkListResponse {
  total: number
  page: number
  page_size: number
  chunks: Chunk[]
}

interface ChunkState {
  chunks: Chunk[]
  currentChunk: Chunk | null
  total: number
  page: number
  pageSize: number
  loading: boolean
  selectedChunkIds: string[]

  // Actions
  fetchChunks: (projectId: string, documentId: string, page?: number, pageSize?: number, filters?: Record<string, unknown>) => Promise<void>
  fetchChunkDetail: (chunkId: string) => Promise<void>
  updateMetadata: (chunkId: string, metadata: Partial<ChunkMetadata>) => Promise<void>
  updateContent: (chunkId: string, content: string) => Promise<void>
  deleteChunk: (chunkId: string) => Promise<void>
  revectorizeChunk: (chunkId: string) => Promise<{ job_id: string }>
  selectChunk: (chunkId: string) => void
  deselectChunk: (chunkId: string) => void
  selectAllChunks: () => void
  clearSelection: () => void
  setCurrentChunk: (chunk: Chunk | null) => void
}

export const useChunkStore = create<ChunkState>((set, get) => ({
  chunks: [],
  currentChunk: null,
  total: 0,
  page: 1,
  pageSize: 20,
  loading: false,
  selectedChunkIds: [],

  fetchChunks: async (projectId, documentId, page = 1, pageSize = 20, filters = {}) => {
    set({ loading: true, page, pageSize })
    try {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      })

      // Add filters
      if (filters.section_filter) {
        params.append('section_filter', filters.section_filter as string)
      }
      if (filters.has_embedding !== undefined) {
        params.append('has_embedding', String(filters.has_embedding))
      }

      const response = await apiClient.get<ChunkListResponse>(
        `/api/knowledge/projects/${projectId}/documents/${documentId}/chunks?${params}`
      )

      set({
        chunks: response.data.chunks,
        total: response.data.total,
        loading: false,
      })
    } catch (error) {
      console.error('Failed to fetch chunks:', error)
      set({ loading: false })
    }
  },

  fetchChunkDetail: async (chunkId) => {
    set({ loading: true })
    try {
      const response = await apiClient.get<Chunk>(
        `/api/knowledge/chunks/${chunkId}`
      )
      set({ currentChunk: response.data, loading: false })
    } catch (error) {
      console.error('Failed to fetch chunk detail:', error)
      set({ loading: false })
    }
  },

  updateMetadata: async (chunkId, metadata) => {
    try {
      const response = await apiClient.put<{ id: string; metadata: ChunkMetadata }>(
        `/api/knowledge/chunks/${chunkId}/metadata`,
        { metadata }
      )

      // Update local state
      const chunks = get().chunks.map(c =>
        c.id === chunkId ? { ...c, metadata: response.data.metadata } : c
      )
      set({ chunks })

      if (get().currentChunk?.id === chunkId) {
        set({ currentChunk: { ...get().currentChunk!, metadata: response.data.metadata } })
      }
    } catch (error) {
      console.error('Failed to update metadata:', error)
      throw error
    }
  },

  updateContent: async (chunkId, content) => {
    try {
      const response = await apiClient.put<{
        id: string
        content_length: number
        needs_revectorization: boolean
      }>(
        `/api/knowledge/chunks/${chunkId}/content`,
        { content }
      )

      // Update local state
      const chunks = get().chunks.map(c =>
        c.id === chunkId
          ? { ...c, content, content_length: response.data.content_length, has_embedding: false }
          : c
      )
      set({ chunks })

      if (get().currentChunk?.id === chunkId) {
        set({
          currentChunk: {
            ...get().currentChunk!,
            content,
            content_length: response.data.content_length,
            has_embedding: false,
          }
        })
      }
    } catch (error) {
      console.error('Failed to update content:', error)
      throw error
    }
  },

  deleteChunk: async (chunkId) => {
    try {
      await apiClient.delete(`/api/knowledge/chunks/${chunkId}`)

      // Remove from local state
      const chunks = get().chunks.filter(c => c.id !== chunkId)
      const selectedChunkIds = get().selectedChunkIds.filter(id => id !== chunkId)
      set({ chunks, selectedChunkIds, total: get().total - 1 })

      if (get().currentChunk?.id === chunkId) {
        set({ currentChunk: null })
      }
    } catch (error) {
      console.error('Failed to delete chunk:', error)
      throw error
    }
  },

  revectorizeChunk: async (chunkId) => {
    try {
      const response = await apiClient.post<{ chunk_id: string; job_id: string; status: string }>(
        `/api/knowledge/chunks/${chunkId}/revectorize`
      )
      return { job_id: response.data.job_id }
    } catch (error) {
      console.error('Failed to revectorize chunk:', error)
      throw error
    }
  },

  selectChunk: (chunkId) => {
    set({ selectedChunkIds: [...get().selectedChunkIds, chunkId] })
  },

  deselectChunk: (chunkId) => {
    set({ selectedChunkIds: get().selectedChunkIds.filter(id => id !== chunkId) })
  },

  selectAllChunks: () => {
    set({ selectedChunkIds: get().chunks.map(c => c.id) })
  },

  clearSelection: () => {
    set({ selectedChunkIds: [] })
  },

  setCurrentChunk: (chunk) => {
    set({ currentChunk: chunk })
  },
}))
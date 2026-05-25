import { create } from 'zustand'
import { SystemPromptTemplate } from '../types/models'
import { systemPromptsApi } from '../api/systemPrompts'

interface SystemPromptState {
  templates: SystemPromptTemplate[]
  categories: { category: string; count: number }[]
  loading: boolean
  saving: boolean

  fetchList: (params?: { category?: string; is_public?: boolean }) => Promise<void>
  fetchCategories: () => Promise<void>
  create: (data: {
    name: string
    description?: string
    content: string
    category?: string
    is_public?: boolean
  }) => Promise<SystemPromptTemplate>
  update: (id: string, data: Partial<{
    name: string
    description: string
    content: string
    category: string
    is_public: boolean
  }>) => Promise<void>
  delete: (id: string) => Promise<void>
}

export const useSystemPromptStore = create<SystemPromptState>((set, get) => ({
  templates: [],
  categories: [],
  loading: false,
  saving: false,

  fetchList: async (params) => {
    set({ loading: true })
    try {
      const response = await systemPromptsApi.list(params)
      set({ templates: response.data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchCategories: async () => {
    try {
      const response = await systemPromptsApi.getCategories()
      set({ categories: response.data })
    } catch {
      set({ categories: [] })
    }
  },

  create: async (data) => {
    set({ saving: true })
    try {
      const response = await systemPromptsApi.create(data)
      set({
        templates: [...get().templates, response.data],
        saving: false,
      })
      return response.data
    } catch (error) {
      set({ saving: false })
      throw error
    }
  },

  update: async (id, data) => {
    set({ saving: true })
    try {
      const response = await systemPromptsApi.update(id, data)
      set({
        templates: get().templates.map((t) => (t.id === id ? response.data : t)),
        saving: false,
      })
    } catch (error) {
      set({ saving: false })
      throw error
    }
  },

  delete: async (id) => {
    try {
      await systemPromptsApi.delete(id)
      set({ templates: get().templates.filter((t) => t.id !== id) })
    } catch (error) {
      throw error
    }
  },
}))
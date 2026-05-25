import { create } from 'zustand'
import { Tool, CreateToolRequest } from '../types/models'
import { toolApi } from '../api/tools'

interface ToolState {
  tools: Tool[]
  currentTool: Tool | null
  loading: boolean
  fetchList: (toolType?: 'http' | 'mcp') => Promise<void>
  fetchOne: (id: string) => Promise<void>
  create: (data: CreateToolRequest) => Promise<Tool>
  update: (id: string, data: Partial<CreateToolRequest>) => Promise<void>
  delete: (id: string) => Promise<void>
  toggleEnable: (id: string, is_enabled: boolean) => Promise<void>
  test: (id: string, input_data?: Record<string, any>) => Promise<any>
  setCurrent: (tool: Tool | null) => void
}

export const useToolStore = create<ToolState>((set, get) => ({
  tools: [],
  currentTool: null,
  loading: false,

  fetchList: async (toolType) => {
    set({ loading: true })
    try {
      const response = await toolApi.list(toolType)
      set({ tools: response.data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchOne: async (id) => {
    set({ loading: true })
    try {
      const response = await toolApi.get(id)
      set({ currentTool: response.data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  create: async (data) => {
    const response = await toolApi.create(data)
    set({ tools: [...get().tools, response.data] })
    return response.data
  },

  update: async (id, data) => {
    const response = await toolApi.update(id, data)
    set({
      tools: get().tools.map((t) => (t.id === id ? response.data : t)),
      currentTool: response.data,
    })
  },

  delete: async (id) => {
    await toolApi.delete(id)
    set({ tools: get().tools.filter((t) => t.id !== id) })
  },

  toggleEnable: async (id, is_enabled) => {
    await toolApi.toggleEnable(id, is_enabled)
    set({
      tools: get().tools.map((t) =>
        t.id === id ? { ...t, is_enabled } : t
      ),
    })
  },

  test: async (id, input_data) => {
    const response = await toolApi.test(id, input_data)
    return response.data
  },

  setCurrent: (tool) => set({ currentTool: tool }),
}))
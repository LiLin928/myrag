import { create } from 'zustand'
import { ModelConfig, modelApi, CreateModelRequest, UpdateModelRequest, ModelType } from '../api/models'

interface ModelState {
  models: ModelConfig[]
  loading: boolean
  error: string | null
  currentFilter: ModelType | null
  fetchList: (type?: ModelType, isActive?: boolean) => Promise<void>
  create: (data: CreateModelRequest) => Promise<ModelConfig>
  update: (id: string, data: UpdateModelRequest) => Promise<ModelConfig>
  delete: (id: string) => Promise<void>
  setDefault: (type: ModelType, modelId: string) => Promise<void>
  toggleActive: (id: string, isActive: boolean) => Promise<void>
  clear: () => void
}

export const useModelStore = create<ModelState>((set, get) => ({
  models: [],
  loading: false,
  error: null,
  currentFilter: null,

  fetchList: async (type?: ModelType, isActive?: boolean) => {
    set({ loading: true, error: null, currentFilter: type ?? null })
    try {
      const response = await modelApi.list(type, isActive)
      set({ models: response.items || [], loading: false })
    } catch (error: any) {
      set({ error: error.message, loading: false, models: [] })
    }
  },

  create: async (data: CreateModelRequest) => {
    const model = await modelApi.create(data)
    set({ models: [...get().models, model] })
    return model
  },

  update: async (id: string, data: UpdateModelRequest) => {
    const model = await modelApi.update(id, data)
    set({
      models: get().models.map((m) => (m.id === id ? model : m)),
    })
    return model
  },

  delete: async (id: string) => {
    await modelApi.delete(id)
    set({
      models: get().models.filter((m) => m.id !== id),
    })
  },

  setDefault: async (type: ModelType, modelId: string) => {
    await modelApi.setDefault(type, modelId)
    // Update the list: set is_default for all models of this type
    set({
      models: get().models.map((m) =>
        m.type === type ? { ...m, is_default: m.id === modelId } : m
      ),
    })
  },

  toggleActive: async (id: string, isActive: boolean) => {
    const model = await modelApi.toggleActive(id, isActive)
    set({
      models: get().models.map((m) => (m.id === id ? model : m)),
    })
  },

  clear: () => {
    set({ models: [], loading: false, error: null, currentFilter: null })
  },
}))
import { create } from 'zustand'
import { User, CreateUserRequest, UpdateUserRequest } from '../api/users'
import { userApi } from '../api/users'

interface UserState {
  users: User[]
  currentUser: User | null
  total: number
  loading: boolean
  fetchList: (skip?: number, limit?: number) => Promise<void>
  fetchOne: (id: string) => Promise<void>
  create: (data: CreateUserRequest) => Promise<User>
  update: (id: string, data: UpdateUserRequest) => Promise<void>
  activate: (id: string) => Promise<void>
  deactivate: (id: string) => Promise<void>
}

export const useUserStore = create<UserState>((set, get) => ({
  users: [],
  currentUser: null,
  total: 0,
  loading: false,

  fetchList: async (skip = 0, limit = 20) => {
    set({ loading: true })
    try {
      const response = await userApi.list(skip, limit)
      set({ users: response.data.items, total: response.data.total, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchOne: async (id) => {
    set({ loading: true })
    try {
      const response = await userApi.get(id)
      set({ currentUser: response.data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  create: async (data) => {
    const response = await userApi.create(data)
    set({ users: [...get().users, response.data], total: get().total + 1 })
    return response.data
  },

  update: async (id, data) => {
    const response = await userApi.update(id, data)
    set({
      users: get().users.map((u) => (u.id === id ? response.data : u)),
      currentUser: response.data,
    })
  },

  activate: async (id) => {
    await userApi.activate(id)
    set({
      users: get().users.map((u) => (u.id === id ? { ...u, is_active: true } : u)),
    })
  },

  deactivate: async (id) => {
    await userApi.deactivate(id)
    set({
      users: get().users.map((u) => (u.id === id ? { ...u, is_active: false } : u)),
    })
  },
}))
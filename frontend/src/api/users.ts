import { apiClient } from './client'

export interface User {
  id: string
  username: string
  email: string
  full_name?: string
  avatar_url?: string
  is_active: boolean
  is_superuser: boolean
  created_at?: string
}

export interface CreateUserRequest {
  username: string
  email: string
  password: string
  full_name?: string
}

export interface UpdateUserRequest {
  full_name?: string
  avatar_url?: string
}

export const userApi = {
  list: (skip?: number, limit?: number) =>
    apiClient.get<{ items: User[]; total: number }>('/users/', { skip, limit }),

  get: (id: string) =>
    apiClient.get<User>(`/users/${id}/`),

  create: (data: CreateUserRequest) =>
    apiClient.post<User>('/users/', data),

  update: (id: string, data: UpdateUserRequest) =>
    apiClient.put<User>(`/users/${id}/`, data),

  activate: (id: string) =>
    apiClient.post<void>(`/users/${id}/activate/`),

  deactivate: (id: string) =>
    apiClient.post<void>(`/users/${id}/deactivate/`),
}
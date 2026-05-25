import { apiClient } from './client'
import { User } from '../types/models'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  refresh_token: string
  user: User
}

export interface RegisterRequest {
  email: string
  username: string
  password: string
}

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<LoginResponse>('/auth/login', data),

  register: (data: RegisterRequest) =>
    apiClient.post<User>('/auth/register', data),

  logout: () =>
    apiClient.post<void>('/auth/logout'),

  getCurrentUser: () =>
    apiClient.get<User>('/auth/me'),

  refreshToken: (refreshToken: string) =>
    apiClient.post<LoginResponse>('/auth/refresh', { refresh_token: refreshToken }),
}
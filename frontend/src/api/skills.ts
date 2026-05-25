import { apiClient } from './client'
import { Skill, SkillFile, SkillVersion } from '../types/models'

export interface CreateSkillRequest {
  internal_name: string
  display_name?: string
  description?: string
  is_public?: boolean
  entry_command?: string
}

export interface CreateSkillFileRequest {
  file_path: string
  content: string
  is_entry?: boolean
}

export interface GenerateSkillRequest {
  requirement: string
  skill_name?: string
}

export const skillApi = {
  list: () => apiClient.get<Skill[]>('/skills/'),

  get: (id: string) => apiClient.get<Skill>(`/skills/${id}/`),

  create: (data: CreateSkillRequest) => apiClient.post<Skill>('/skills/', data),

  update: (id: string, data: Partial<CreateSkillRequest>) =>
    apiClient.put<Skill>(`/skills/${id}/`, data),

  delete: (id: string) => apiClient.delete(`/skills/${id}/`),

  generate: (data: GenerateSkillRequest) =>
    apiClient.post<{ success: boolean; code: string; name: string; description: string }>('/skills/generate/', data),

  createVersion: (id: string, code: string) =>
    apiClient.post<Skill>(`/skills/${id}/version/`, { code }),

  // ========== 文件管理 ==========

  listFiles: (skillId: string) =>
    apiClient.get<SkillFile[]>(`/skills/${skillId}/files`),

  createFile: (skillId: string, data: CreateSkillFileRequest) =>
    apiClient.post<SkillFile>(`/skills/${skillId}/files`, data),

  getFile: (skillId: string, filePath: string) =>
    apiClient.get<{ id: string; file_path: string; content: string; file_type: string }>(
      `/skills/${skillId}/files/${encodeURIComponent(filePath)}`
    ),

  updateFile: (skillId: string, filePath: string, content: string) =>
    apiClient.put<SkillFile>(`/skills/${skillId}/files/${encodeURIComponent(filePath)}`, { content }),

  deleteFile: (skillId: string, filePath: string) =>
    apiClient.delete(`/skills/${skillId}/files/${encodeURIComponent(filePath)}`),

  uploadFiles: (skillId: string, files: File[]) => {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    return apiClient.post<{ uploaded: Array<{ path: string; size: number }>; count: number }>(
      `/skills/${skillId}/files/upload`,
      formData
    )
  },

  // ========== 版本管理 ==========

  listVersions: (skillId: string) =>
    apiClient.get<SkillVersion[]>(`/skills/${skillId}/versions`),

  getVersion: (skillId: string, versionNumber: number) =>
    apiClient.get<SkillVersion>(`/skills/${skillId}/versions/${versionNumber}`),

  rollback: (skillId: string, versionNumber: number) =>
    apiClient.post(`/skills/${skillId}/rollback/${versionNumber}`),
}
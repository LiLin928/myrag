import { create } from 'zustand'
import { Skill, SkillFile, SkillVersion } from '../types/models'
import { skillApi, CreateSkillRequest, CreateSkillFileRequest, GenerateSkillRequest } from '../api/skills'

interface SkillState {
  skills: Skill[]
  currentSkill: Skill | null
  currentFiles: SkillFile[]
  currentVersions: SkillVersion[]
  selectedFilePath: string | null
  fileContent: string | null
  generatedCode: string | null
  generatedName: string | null
  generatedDescription: string | null
  loading: boolean
  generating: boolean
  saving: boolean

  // 技能方法
  fetchList: () => Promise<void>
  fetchOne: (id: string) => Promise<void>
  create: (data: CreateSkillRequest) => Promise<Skill>
  update: (id: string, data: Partial<CreateSkillRequest>) => Promise<void>
  delete: (id: string) => Promise<void>

  // 文件方法
  fetchFiles: (skillId: string) => Promise<void>
  fetchFileContent: (skillId: string, filePath: string) => Promise<void>
  createFile: (skillId: string, data: CreateSkillFileRequest) => Promise<SkillFile>
  updateFile: (skillId: string, filePath: string, content: string) => Promise<void>
  deleteFile: (skillId: string, filePath: string) => Promise<void>
  uploadFiles: (skillId: string, files: File[]) => Promise<void>
  selectFile: (filePath: string | null) => void

  // 版本方法
  fetchVersions: (skillId: string) => Promise<void>
  rollback: (skillId: string, versionNumber: number) => Promise<void>

  // 生成方法
  generate: (data: GenerateSkillRequest) => Promise<{ name: string; code: string; description: string }>
  createVersion: (id: string, code: string) => Promise<Skill>
  clearGenerated: () => void
}

export const useSkillStore = create<SkillState>((set, get) => ({
  skills: [],
  currentSkill: null,
  currentFiles: [],
  currentVersions: [],
  selectedFilePath: null,
  fileContent: null,
  generatedCode: null,
  generatedName: null,
  generatedDescription: null,
  loading: false,
  generating: false,
  saving: false,

  // 技能方法
  fetchList: async () => {
    set({ loading: true })
    try {
      const response = await skillApi.list()
      set({ skills: response.data, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  fetchOne: async (id) => {
    set({ loading: true })
    try {
      const response = await skillApi.get(id)
      set({ currentSkill: response.data, loading: false })
      if (response.data.files) {
        set({ currentFiles: response.data.files })
      }
    } catch {
      set({ loading: false })
    }
  },

  create: async (data) => {
    const response = await skillApi.create(data)
    set({ skills: [...get().skills, response.data] })
    return response.data
  },

  update: async (id, data) => {
    const response = await skillApi.update(id, data)
    set({
      skills: get().skills.map((s) => (s.id === id ? response.data : s)),
      currentSkill: response.data,
    })
  },

  delete: async (id) => {
    await skillApi.delete(id)
    set({ skills: get().skills.filter((s) => s.id !== id) })
  },

  // ========== 文件方法 ==========

  fetchFiles: async (skillId) => {
    try {
      const response = await skillApi.listFiles(skillId)
      set({ currentFiles: response.data })
    } catch {
      set({ currentFiles: [] })
    }
  },

  fetchFileContent: async (skillId, filePath) => {
    set({ loading: true })
    try {
      const response = await skillApi.getFile(skillId, filePath)
      set({ fileContent: response.data.content, selectedFilePath: filePath, loading: false })
    } catch {
      set({ fileContent: null, loading: false })
    }
  },

  createFile: async (skillId, data) => {
    const response = await skillApi.createFile(skillId, data)
    set({ currentFiles: [...get().currentFiles, response.data] })
    return response.data
  },

  updateFile: async (skillId, filePath, content) => {
    set({ saving: true })
    try {
      await skillApi.updateFile(skillId, filePath, content)
      await get().fetchFiles(skillId)
      set({ saving: false })
    } catch {
      set({ saving: false })
      throw new Error('保存失败')
    }
  },

  deleteFile: async (skillId, filePath) => {
    await skillApi.deleteFile(skillId, filePath)
    set({
      currentFiles: get().currentFiles.filter((f) => f.file_path !== filePath),
      selectedFilePath: get().selectedFilePath === filePath ? null : get().selectedFilePath,
      fileContent: get().selectedFilePath === filePath ? null : get().fileContent,
    })
  },

  uploadFiles: async (skillId, files) => {
    await skillApi.uploadFiles(skillId, files)
    await get().fetchFiles(skillId)
  },

  selectFile: (filePath) => {
    set({ selectedFilePath: filePath })
  },

  // ========== 版本方法 ==========

  fetchVersions: async (skillId) => {
    try {
      const response = await skillApi.listVersions(skillId)
      set({ currentVersions: response.data })
    } catch {
      set({ currentVersions: [] })
    }
  },

  rollback: async (skillId, versionNumber) => {
    await skillApi.rollback(skillId, versionNumber)
    await get().fetchOne(skillId)
    await get().fetchFiles(skillId)
  },

  // 生成方法
  generate: async (data) => {
    set({ generating: true })
    try {
      const response = await skillApi.generate(data)
      set({
        generatedCode: response.data.code,
        generatedName: response.data.name,
        generatedDescription: response.data.description,
        generating: false,
      })
      return { name: response.data.name, code: response.data.code, description: response.data.description }
    } catch {
      set({ generating: false })
      throw new Error('生成失败')
    }
  },

  createVersion: async (id, code) => {
    const response = await skillApi.createVersion(id, code)
    return response.data
  },

  clearGenerated: () => set({ generatedCode: null, generatedName: null, generatedDescription: null }),
}))
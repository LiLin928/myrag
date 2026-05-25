import { create } from 'zustand'
import { Agent, ChatResponse, Session } from '../api/agents'
import { agentApi } from '../api/agents'

interface AgentState {
  currentAgent: Agent | null
  sessions: Session[]
  currentSessionId: string | null
  chatHistory: Array<{ role: string; content: string; sources?: any[] }>
  loading: boolean
  saving: boolean

  // Actions
  fetchAgent: (id: string) => Promise<void>
  createAgent: (data: any) => Promise<Agent>
  updateAgent: (id: string, data: any) => Promise<void>
  deleteAgent: (id: string) => Promise<void>

  fetchSessions: (agentId: string) => Promise<void>
  setCurrentSession: (sessionId: string | null) => void

  chat: (agentId: string, message: string) => Promise<ChatResponse>
  clearChatHistory: () => void
}

export const useAgentStore = create<AgentState>((set, get) => ({
  currentAgent: null,
  sessions: [],
  currentSessionId: null,
  chatHistory: [],
  loading: false,
  saving: false,

  fetchAgent: async (id: string) => {
    set({ loading: true })
    try {
      const res = await agentApi.get(id)
      set({ currentAgent: res.data, loading: false })
    } catch (e) {
      set({ loading: false })
      throw e
    }
  },

  createAgent: async (data: any) => {
    set({ saving: true })
    try {
      const res = await agentApi.create(data)
      set({ saving: false })
      return res.data
    } catch (e) {
      set({ saving: false })
      throw e
    }
  },

  updateAgent: async (id: string, data: any) => {
    set({ saving: true })
    try {
      const res = await agentApi.update(id, data)
      set({ currentAgent: res.data, saving: false })
    } catch (e) {
      set({ saving: false })
      throw e
    }
  },

  deleteAgent: async (id: string) => {
    await agentApi.delete(id)
    set({ currentAgent: null })
  },

  fetchSessions: async (agentId: string) => {
    const res = await agentApi.listSessions(agentId)
    set({ sessions: res.data })
  },

  setCurrentSession: (sessionId: string | null) => {
    set({ currentSessionId: sessionId })
  },

  chat: async (agentId: string, message: string) => {
    const state = get()
    const sessionId = state.currentSessionId

    let res: ChatResponse
    if (sessionId) {
      const response = await agentApi.continueChat(agentId, sessionId, { message })
      res = response.data
    } else {
      const response = await agentApi.chat(agentId, { message })
      res = response.data
    }

    set({
      currentSessionId: res.session_id,
      chatHistory: [
        ...state.chatHistory,
        { role: 'user', content: message },
        { role: 'assistant', content: res.response, sources: res.sources },
      ],
    })

    return res
  },

  clearChatHistory: () => {
    set({ chatHistory: [], currentSessionId: null })
  },
}))
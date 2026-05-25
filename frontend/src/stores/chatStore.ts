import { create } from 'zustand'
import { Conversation, Message, CreateConversationRequest } from '../types/models'
import { conversationApi } from '../api/conversations'

interface ChatState {
  conversations: Conversation[]
  currentConversation: Conversation | null
  messages: Message[]
  threadId: string | null
  sending: boolean
  fetchList: () => Promise<void>
  fetchOne: (id: string) => Promise<void>
  fetchMessages: (id: string) => Promise<void>
  create: (data: CreateConversationRequest) => Promise<Conversation>
  delete: (id: string) => Promise<void>
  sendMessage: (message: string) => Promise<string>
  setCurrent: (conv: Conversation | null) => void
  clearMessages: () => void
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  currentConversation: null,
  messages: [],
  threadId: null,
  sending: false,

  fetchList: async () => {
    try {
      const response = await conversationApi.list()
      set({ conversations: response.data })
    } catch {}
  },

  fetchOne: async (id) => {
    try {
      const response = await conversationApi.get(id)
      set({ currentConversation: response.data, threadId: response.data.thread_id })
    } catch {}
  },

  fetchMessages: async (id) => {
    try {
      const response = await conversationApi.getMessages(id)
      set({ messages: response.data })
    } catch {}
  },

  create: async (data) => {
    const response = await conversationApi.create(data)
    const conv = response.data
    set({
      conversations: [...get().conversations, conv],
      currentConversation: conv,
      threadId: conv.thread_id,
      messages: [],
    })
    return conv
  },

  delete: async (id) => {
    await conversationApi.delete(id)
    set({
      conversations: get().conversations.filter((c) => c.id !== id),
      currentConversation: null,
      messages: [],
    })
  },

  sendMessage: async (message) => {
    const conv = get().currentConversation
    if (!conv) throw new Error('No conversation selected')

    set({ sending: true })
    try {
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        role: 'user',
        content: message,
        tokens: 0,
        created_at: new Date().toISOString(),
      }
      set({ messages: [...get().messages, userMessage] })

      const response = await conversationApi.sendMessage(conv.id, message)
      const assistantMessage: Message = {
        id: `assistant-${Date.now()}`,
        role: 'assistant',
        content: response.data.response,
        tokens: 0,
        created_at: new Date().toISOString(),
      }
      set({ messages: [...get().messages, assistantMessage] })
      return response.data.response
    } finally {
      set({ sending: false })
    }
  },

  setCurrent: (conv) => set({
    currentConversation: conv,
    threadId: conv?.thread_id,
    messages: [],
  }),

  clearMessages: () => set({ messages: [] }),
}))
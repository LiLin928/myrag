import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { User } from '../types/models'

interface AuthState {
  user: User | null
  accessToken: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  setUser: (user: User) => void
  setTokens: (accessToken: string, refreshToken: string) => void
  logout: () => void
  checkAuth: () => boolean
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      setUser: (user) => set({ user, isAuthenticated: true }),

      setTokens: (accessToken, refreshToken) => {
        // 同时保存到 localStorage 的 access_token key（供 API client 使用）
        localStorage.setItem('access_token', accessToken)
        set({ accessToken, refreshToken, isAuthenticated: true })
      },

      logout: () => {
        // 清除 localStorage 的 access_token
        localStorage.removeItem('access_token')
        set({
          user: null,
          accessToken: null,
          refreshToken: null,
          isAuthenticated: false,
        })
      },

      checkAuth: () => {
        const state = get()
        return !!state.accessToken && !!state.user
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
      onRehydrateStorage: () => (state) => {
        // 页面刷新后恢复状态，并同步 access_token 到 localStorage
        if (state?.accessToken) {
          localStorage.setItem('access_token', state.accessToken)
          if (state?.user) {
            state.isAuthenticated = true
          }
        }
      },
    }
  )
)
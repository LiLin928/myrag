import { useAuthStore } from '../stores/authStore'
import { authApi, LoginRequest, RegisterRequest } from '../api/auth'

export function useAuth() {
  const { user, isAuthenticated, setUser, setTokens, logout } = useAuthStore()

  const login = async (data: LoginRequest) => {
    const response = await authApi.login(data)
    const { access_token, refresh_token } = response.data
    setTokens(access_token, refresh_token)

    // 登录成功后获取用户信息
    const userResponse = await authApi.getCurrentUser()
    setUser(userResponse.data)
    return userResponse.data
  }

  const register = async (data: RegisterRequest) => {
    const response = await authApi.register(data)
    return response.data
  }

  const checkAuth = async () => {
    if (!isAuthenticated) return false
    try {
      const response = await authApi.getCurrentUser()
      setUser(response.data)
      return true
    } catch {
      logout()
      return false
    }
  }

  return {
    user,
    isAuthenticated,
    login,
    register,
    logout,
    checkAuth,
  }
}
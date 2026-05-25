import axios, { AxiosInstance, AxiosError } from 'axios'
import { ApiError } from '../types/api'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1'

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    this.client.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token')
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    this.client.interceptors.response.use(
      (response) => response,
      (error: AxiosError<ApiError>) => {
        if (error.response?.status === 401) {
          localStorage.removeItem('access_token')
          window.location.href = '/login'
        }
        return Promise.reject(error)
      }
    )
  }

  get<T>(url: string, params?: any) {
    return this.client.get<T>(url, { params })
  }

  post<T>(url: string, data?: any) {
    return this.client.post<T>(url, data)
  }

  put<T>(url: string, data?: any) {
    return this.client.put<T>(url, data)
  }

  delete<T>(url: string) {
    return this.client.delete<T>(url)
  }

  patch<T>(url: string, data?: any) {
    return this.client.patch<T>(url, data)
  }

  upload<T>(url: string, file: File, onProgress?: (percent: number) => void) {
    const formData = new FormData()
    formData.append('file', file)
    return this.client.post<T>(url, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (e) => {
        if (e.total && onProgress) {
          onProgress(Math.round((e.loaded * 100) / e.total))
        }
      },
    })
  }
}

export const apiClient = new ApiClient()
export interface ApiResponse<T> {
  data: T
  message?: string
}

export interface PaginationParams {
  page?: number
  size?: number
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  size: number
}

export interface ApiError {
  code: string
  message: string
  details?: Record<string, string>
}
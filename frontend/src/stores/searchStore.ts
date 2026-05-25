import { create } from 'zustand'
import { SearchResult, SearchRequest } from '../api/search'
import { searchApi } from '../api/search'
import { apiClient } from '../api/client'

export interface SearchTestResult {
  chunk_id: string
  document_id: string
  content: string
  score: number
  clause_type?: string
  section_title?: string
  page_number: number
  metadata: Record<string, unknown>
  search_method: string
}

export interface SearchTestResponse {
  query: string
  search_type: string
  filters?: Record<string, unknown>
  results: SearchTestResult[]
  performance: {
    query_time_ms: number
    total_time_ms: number
    result_count: number
    top_scores: number[]
  }
}

export interface SearchStats {
  project_id: string
  document_count: number
  total_chunks: number
  vectorized_chunks: number
  vectorization_rate: number
}

export interface FilterOptions {
  document_types: string[]
  sections: string[]
  user_tags: string[]
  categories: string[]
}

export interface SearchTestFilters {
  document_type?: string
  section_title?: string
  user_tags?: string[]
  category?: string
  position_type?: string
}

interface SearchState {
  results: SearchResult[]
  testResults: SearchTestResult[]
  loading: boolean
  lastQuery: string
  searchType: 'vector' | 'hybrid' | 'keyword'
  topK: number
  scoreThreshold: number
  filters: SearchTestFilters
  performance: SearchTestResponse['performance'] | null
  stats: SearchStats | null
  filterOptions: FilterOptions | null
  queryHistory: string[]

  // Original actions
  searchGlobal: (request: SearchRequest) => Promise<void>
  searchInProject: (projectId: string, request: SearchRequest) => Promise<void>
  searchInDocument: (documentId: string, request: SearchRequest) => Promise<void>

  // New actions for knowledge search
  testSearch: (projectId: string, query: string) => Promise<void>
  fetchStats: (projectId: string) => Promise<void>
  fetchFilterOptions: (projectId: string) => Promise<void>
  setSearchType: (type: 'vector' | 'hybrid' | 'keyword') => void
  setTopK: (k: number) => void
  setScoreThreshold: (threshold: number) => void
  setFilters: (filters: SearchTestFilters) => void
  clearFilters: () => void
  addToHistory: (query: string) => void
  clearHistory: () => void
}

export const useSearchStore = create<SearchState>((set, get) => ({
  results: [],
  testResults: [],
  loading: false,
  lastQuery: '',
  searchType: 'hybrid',
  topK: 5,
  scoreThreshold: 0.5,
  filters: {},
  performance: null,
  stats: null,
  filterOptions: null,
  queryHistory: [],

  // Original actions
  searchGlobal: async (request) => {
    set({ loading: true, lastQuery: request.query })
    try {
      const response = await searchApi.globalSearch(request)
      set({ results: response.data.results, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  searchInProject: async (projectId, request) => {
    set({ loading: true, lastQuery: request.query })
    try {
      const response = await searchApi.searchInProject(projectId, request)
      set({ results: response.data.results, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  searchInDocument: async (documentId, request) => {
    set({ loading: true, lastQuery: request.query })
    try {
      const response = await searchApi.searchInDocument(documentId, request)
      set({ results: response.data.results, loading: false })
    } catch {
      set({ loading: false })
    }
  },

  // New actions
  testSearch: async (projectId, query) => {
    set({ loading: true, lastQuery: query })
    const state = get()

    try {
      const response = await apiClient.post<SearchTestResponse>(
        `/api/knowledge/projects/${projectId}/test-search`,
        {
          query,
          top_k: state.topK,
          score_threshold: state.scoreThreshold,
          search_type: state.searchType,
          filters: state.filters,
        }
      )

      set({
        testResults: response.data.results,
        performance: response.data.performance,
        loading: false,
      })

      // Add to history
      if (query && !state.queryHistory.includes(query)) {
        set({ queryHistory: [query, ...state.queryHistory.slice(0, 9)] })
      }
    } catch (error) {
      console.error('Search test failed:', error)
      set({ loading: false })
    }
  },

  fetchStats: async (projectId) => {
    try {
      const response = await apiClient.get<SearchStats>(
        `/api/knowledge/projects/${projectId}/search-stats`
      )
      set({ stats: response.data })
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  },

  fetchFilterOptions: async (projectId) => {
    try {
      const response = await apiClient.get<FilterOptions>(
        `/api/knowledge/projects/${projectId}/filter-options`
      )
      set({ filterOptions: response.data })
    } catch (error) {
      console.error('Failed to fetch filter options:', error)
    }
  },

  setSearchType: (type) => set({ searchType: type }),
  setTopK: (k) => set({ topK: k }),
  setScoreThreshold: (threshold) => set({ scoreThreshold: threshold }),
  setFilters: (filters) => set({ filters }),
  clearFilters: () => set({ filters: {} }),
  addToHistory: (query) => {
    const state = get()
    if (query && !state.queryHistory.includes(query)) {
      set({ queryHistory: [query, ...state.queryHistory.slice(0, 9)] })
    }
  },
  clearHistory: () => set({ queryHistory: [] }),
}))
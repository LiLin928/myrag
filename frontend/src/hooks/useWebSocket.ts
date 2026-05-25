import { useEffect, useRef, useCallback, useState } from 'react'

export interface TaskProgressEvent {
  type: 'task_progress'
  job_id: string
  stage: 'parsing' | 'chunking' | 'vectorizing' | 'storing' | 'completed'
  progress: number
  message?: string
  extra?: Record<string, unknown>
  timestamp: string
}

export interface TaskCompleteEvent {
  type: 'task_complete'
  job_id: string
  result: Record<string, unknown>
  timestamp: string
}

export interface TaskFailedEvent {
  type: 'task_failed'
  job_id: string
  error: string
  error_details?: Record<string, unknown>
  timestamp: string
}

export type WebSocketEvent = TaskProgressEvent | TaskCompleteEvent | TaskFailedEvent

export interface TaskState {
  status: 'idle' | 'running' | 'completed' | 'failed'
  stage: string
  progress: number
  message?: string
  result?: Record<string, unknown>
  error?: string
}

interface UseWebSocketOptions {
  userId: string
  onProgress?: (event: TaskProgressEvent) => void
  onComplete?: (event: TaskCompleteEvent) => void
  onFailed?: (event: TaskFailedEvent) => void
  autoConnect?: boolean
}

export function useWebSocket(options: UseWebSocketOptions) {
  const { userId, onProgress, onComplete, onFailed, autoConnect = true } = options

  const socketRef = useRef<WebSocket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [taskStates, setTaskStates] = useState<Record<string, TaskState>>({})
  const reconnectTimeoutRef = useRef<number | null>(null)

  const connect = useCallback(() => {
    const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
    const wsUrl = `${WS_URL}/ws/${userId}`

    socketRef.current = new WebSocket(wsUrl)

    socketRef.current.onopen = () => {
      console.log('WebSocket connected')
      setIsConnected(true)
      // Clear reconnect timeout
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
        reconnectTimeoutRef.current = null
      }
    }

    socketRef.current.onmessage = (event) => {
      try {
        const data: WebSocketEvent = JSON.parse(event.data)

        switch (data.type) {
          case 'task_progress':
            setTaskStates(prev => ({
              ...prev,
              [data.job_id]: {
                status: 'running',
                stage: data.stage,
                progress: data.progress,
                message: data.message,
              }
            }))
            onProgress?.(data)
            break

          case 'task_complete':
            setTaskStates(prev => ({
              ...prev,
              [data.job_id]: {
                status: 'completed',
                stage: 'completed',
                progress: 100,
                result: data.result,
              }
            }))
            onComplete?.(data)
            break

          case 'task_failed':
            setTaskStates(prev => ({
              ...prev,
              [data.job_id]: {
                status: 'failed',
                stage: 'failed',
                progress: 0,
                error: data.error,
              }
            }))
            onFailed?.(data)
            break
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    socketRef.current.onclose = () => {
      console.log('WebSocket disconnected')
      setIsConnected(false)

      // Auto reconnect after 3 seconds
      reconnectTimeoutRef.current = window.setTimeout(() => {
        if (autoConnect) {
          connect()
        }
      }, 3000)
    }

    socketRef.current.onerror = (error) => {
      console.error('WebSocket error:', error)
    }
  }, [userId, onProgress, onComplete, onFailed, autoConnect])

  const disconnect = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current)
    }
    socketRef.current?.close()
    socketRef.current = null
    setIsConnected(false)
  }, [])

  const subscribeChannel = useCallback((channel: string) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        event: 'subscribe',
        channel,
      }))
    }
  }, [])

  const unsubscribeChannel = useCallback((channel: string) => {
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({
        event: 'unsubscribe',
        channel,
      }))
    }
  }, [])

  const getTaskState = useCallback((jobId: string): TaskState => {
    return taskStates[jobId] || { status: 'idle', stage: '', progress: 0 }
  }, [taskStates])

  const clearTaskState = useCallback((jobId: string) => {
    setTaskStates(prev => {
      const newState = { ...prev }
      delete newState[jobId]
      return newState
    })
  }, [])

  useEffect(() => {
    if (autoConnect && userId) {
      connect()
    }

    return () => {
      disconnect()
    }
  }, [autoConnect, userId, connect, disconnect])

  return {
    isConnected,
    taskStates,
    connect,
    disconnect,
    subscribeChannel,
    unsubscribeChannel,
    getTaskState,
    clearTaskState,
  }
}

export function useDocumentProgress(userId: string, documentId?: string) {
  const channelRef = useRef<string | null>(null)

  const {
    isConnected,
    getTaskState,
    clearTaskState,
    subscribeChannel,
    unsubscribeChannel,
  } = useWebSocket({
    userId,
    autoConnect: true,
  })

  const subscribeDocument = useCallback((docId: string) => {
    const channel = `doc_processing_${docId}`
    channelRef.current = channel
    subscribeChannel(channel)
  }, [subscribeChannel])

  const unsubscribeDocument = useCallback(() => {
    if (channelRef.current) {
      unsubscribeChannel(channelRef.current)
      channelRef.current = null
    }
  }, [unsubscribeChannel])

  useEffect(() => {
    if (documentId && isConnected) {
      subscribeDocument(documentId)
    }

    return () => {
      unsubscribeDocument()
    }
  }, [documentId, isConnected, subscribeDocument, unsubscribeDocument])

  return {
    isConnected,
    subscribeDocument,
    unsubscribeDocument,
    getTaskState,
    clearTaskState,
  }
}
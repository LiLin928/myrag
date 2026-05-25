import { useEffect, useRef, useCallback } from 'react'
import { useWorkflowStore } from '../stores/workflowStore'

interface ProgressEvent {
  type: string
  execution_id: string
  workflow_id?: string
  timestamp: string
  node_id?: string
  node_name?: string
  node_type?: string
  input_data?: Record<string, unknown>
  output_data?: Record<string, unknown>
  error_message?: string
  duration_ms?: number
  progress_percent?: number
  total_nodes?: number
  completed_nodes?: number
  final_output?: Record<string, unknown>
  reason?: string
}

export function useWorkflowProgress(executionId: string | null) {
  const wsRef = useRef<WebSocket | null>(null)
  const {
    setProgressEvent,
    setCurrentExecution,
    setExecuting,
  } = useWorkflowStore()

  // Disconnect function - defined first as it's used by handleProgressEvent
  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close()
      wsRef.current = null
    }
  }, [])

  // Handle progress events - defined before connect
  const handleProgressEvent = useCallback((event: ProgressEvent) => {
    setProgressEvent(event)

    switch (event.type) {
      case 'execution_start':
        setExecuting(true)
        break

      case 'execution_complete':
        setExecuting(false)
        setCurrentExecution({
          id: event.execution_id,
          workflow_id: event.workflow_id || '',
          status: 'completed',
          input: {},
          output: event.final_output || {},
          created_at: event.timestamp,
          completed_at: event.timestamp,
        })
        disconnect()
        break

      case 'execution_error':
        setExecuting(false)
        setCurrentExecution({
          id: event.execution_id,
          workflow_id: event.workflow_id || '',
          status: 'failed',
          input: {},
          output: {},
          created_at: event.timestamp,
          error_message: event.error_message,
        })
        disconnect()
        break

      case 'execution_interrupted':
        setExecuting(false)
        setCurrentExecution({
          id: event.execution_id,
          workflow_id: event.workflow_id || '',
          status: 'paused',
          input: {},
          output: {},
          created_at: event.timestamp,
          current_node: event.node_id,
        })
        disconnect()
        break
    }
  }, [setProgressEvent, setCurrentExecution, setExecuting, disconnect])

  // Connect function - uses handleProgressEvent
  const connect = useCallback(() => {
    if (!executionId) return

    const wsUrl = `ws://localhost:8000/ws/workflows/executions/${executionId}/progress`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = () => {
      console.log('WebSocket connected for execution:', executionId)
    }

    ws.onmessage = (event) => {
      try {
        const data: ProgressEvent = JSON.parse(event.data)
        handleProgressEvent(data)
      } catch (e) {
        // 心跳消息 pong
        if (event.data === 'pong') return
        console.error('Failed to parse WebSocket message:', e)
      }
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onclose = () => {
      console.log('WebSocket disconnected')
      wsRef.current = null
    }
  }, [executionId, handleProgressEvent])

  const sendPing = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send('ping')
    }
  }, [])

  useEffect(() => {
    if (executionId) {
      connect()

      // 心跳定时器
      const pingInterval = setInterval(sendPing, 30000)

      return () => {
        clearInterval(pingInterval)
        disconnect()
      }
    }
  }, [executionId, connect, disconnect, sendPing])

  return {
    disconnect,
    reconnect: connect,
  }
}
import React, { useMemo } from 'react'
import {
  List,
  Timeline,
  Typography,
  Tag,
  Collapse,
  Space,
  Empty,
  Tooltip,
  Card,
} from 'antd'
import {
  PlayCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  DatabaseOutlined,
  CloudOutlined,
  ApiOutlined,
  SearchOutlined,
  BranchesOutlined,
  CodeOutlined,
  ArrowRightOutlined,
} from '@ant-design/icons'
import { useWorkflowStore, ProgressEvent } from '../../stores/workflowStore'

const { Text, Paragraph } = Typography
const { Panel } = Collapse

// Event type configurations for icons and colors
const EVENT_CONFIG: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  execution_start: {
    icon: <PlayCircleOutlined />,
    color: 'blue',
    label: '开始执行',
  },
  execution_progress: {
    icon: <LoadingOutlined />,
    color: 'processing',
    label: '执行中',
  },
  execution_complete: {
    icon: <CheckCircleOutlined />,
    color: 'success',
    label: '执行完成',
  },
  execution_error: {
    icon: <CloseCircleOutlined />,
    color: 'error',
    label: '执行错误',
  },
  node_start: {
    icon: <ArrowRightOutlined />,
    color: 'cyan',
    label: '节点开始',
  },
  node_complete: {
    icon: <CheckCircleOutlined />,
    color: 'green',
    label: '节点完成',
  },
  node_error: {
    icon: <CloseCircleOutlined />,
    color: 'error',
    label: '节点错误',
  },
}

// Node type configurations
const NODE_TYPE_CONFIG: Record<string, { icon: React.ReactNode; color: string }> = {
  start: { icon: <PlayCircleOutlined />, color: 'green' },
  end: { icon: <CheckCircleOutlined />, color: 'blue' },
  llm: { icon: <CloudOutlined />, color: 'purple' },
  retrieval: { icon: <SearchOutlined />, color: 'cyan' },
  knowledge: { icon: <DatabaseOutlined />, color: 'geekblue' },
  code: { icon: <CodeOutlined />, color: 'magenta' },
  condition: { icon: <BranchesOutlined />, color: 'orange' },
  api: { icon: <ApiOutlined />, color: 'gold' },
  document: { icon: <FileTextOutlined />, color: 'lime' },
  default: { icon: <ClockCircleOutlined />, color: 'default' },
}

// Format timestamp to readable string
function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp)
  return date.toLocaleString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  })
}

// Format duration in milliseconds to readable string
function formatDuration(durationMs?: number): string {
  if (!durationMs) return ''

  if (durationMs < 1000) {
    return `${durationMs}ms`
  } else if (durationMs < 60000) {
    return `${(durationMs / 1000).toFixed(2)}s`
  } else {
    const minutes = Math.floor(durationMs / 60000)
    const seconds = Math.round((durationMs % 60000) / 1000)
    return `${minutes}m ${seconds}s`
  }
}

// Format JSON data for display
function formatJsonData(data?: Record<string, unknown>): string {
  if (!data) return ''
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

interface ExecutionLogItemProps {
  event: ProgressEvent
}

const ExecutionLogItem = React.memo(function ExecutionLogItem({ event }: ExecutionLogItemProps) {
  const eventConfig = EVENT_CONFIG[event.type] || {
    icon: <ClockCircleOutlined />,
    color: 'default',
    label: event.type,
  }

  const nodeConfig = event.node_type
    ? NODE_TYPE_CONFIG[event.node_type] || NODE_TYPE_CONFIG.default
    : null

  const hasDetails = event.input_data || event.output_data || event.error_message

  return (
    <Timeline.Item
      dot={
        event.type === 'execution_progress' ? (
          <LoadingOutlined spin style={{ fontSize: 16 }} />
        ) : (
          React.cloneElement(eventConfig.icon as React.ReactElement, {
            style: { fontSize: 16 },
          })
        )
      }
      color={eventConfig.color === 'error' ? 'red' : eventConfig.color === 'success' ? 'green' : eventConfig.color}
    >
      <div style={{ marginBottom: 4 }}>
        <Space size="small">
          <Tag color={eventConfig.color}>{eventConfig.label}</Tag>
          {event.node_name && (
            <Tag icon={nodeConfig?.icon} color={nodeConfig?.color}>
              {event.node_name}
            </Tag>
          )}
          <Text type="secondary" style={{ fontSize: 12 }}>
            {formatTimestamp(event.timestamp)}
          </Text>
          {event.duration_ms !== undefined && event.duration_ms > 0 && (
            <Tooltip title="执行耗时">
              <Tag icon={<ClockCircleOutlined />} color="default">
                {formatDuration(event.duration_ms)}
              </Tag>
            </Tooltip>
          )}
        </Space>
      </div>

      {event.progress_percent !== undefined && (
        <div style={{ marginBottom: 8, marginTop: 4 }}>
          <Text type="secondary">
            进度: {event.completed_nodes || 0}/{event.total_nodes || 0} 节点 ({event.progress_percent}%)
          </Text>
        </div>
      )}

      {event.error_message && (
        <Paragraph
          type="danger"
          style={{ marginTop: 4, marginBottom: 8, fontSize: 12 }}
          ellipsis={{ rows: 2, expandable: true }}
        >
          错误: {event.error_message}
        </Paragraph>
      )}

      {event.reason && (
        <Text type="secondary" style={{ fontSize: 12 }}>
          {event.reason}
        </Text>
      )}

      {hasDetails && (
        <Collapse
          ghost
          size="small"
          style={{ marginTop: 8 }}
        >
          <Panel header="详细信息" key="details">
            {event.input_data && Object.keys(event.input_data).length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <Text strong style={{ fontSize: 12 }}>输入数据:</Text>
                <Paragraph
                  code
                  style={{
                    marginTop: 4,
                    marginBottom: 0,
                    fontSize: 11,
                    backgroundColor: '#f5f5f5',
                    padding: 8,
                    borderRadius: 4,
                    maxHeight: 150,
                    overflow: 'auto',
                  }}
                >
                  <pre style={{ margin: 0 }}>{formatJsonData(event.input_data)}</pre>
                </Paragraph>
              </div>
            )}
            {event.output_data && Object.keys(event.output_data).length > 0 && (
              <div style={{ marginBottom: 8 }}>
                <Text strong style={{ fontSize: 12 }}>输出数据:</Text>
                <Paragraph
                  code
                  style={{
                    marginTop: 4,
                    marginBottom: 0,
                    fontSize: 11,
                    backgroundColor: '#f5f5f5',
                    padding: 8,
                    borderRadius: 4,
                    maxHeight: 150,
                    overflow: 'auto',
                  }}
                >
                  <pre style={{ margin: 0 }}>{formatJsonData(event.output_data)}</pre>
                </Paragraph>
              </div>
            )}
          </Panel>
        </Collapse>
      )}
    </Timeline.Item>
  )
})

interface ExecutionLogPanelProps {
  /** Maximum number of events to display */
  maxEvents?: number
  /** Whether to show in compact mode */
  compact?: boolean
  /** Custom height for scrollable area */
  height?: number | string
}

export function ExecutionLogPanel({
  maxEvents = 100,
  compact = false,
  height = 400,
}: ExecutionLogPanelProps) {
  const { progressEvents } = useWorkflowStore()

  // Limit displayed events
  const displayedEvents = useMemo(() => {
    const events = progressEvents.slice(-maxEvents)
    return events
  }, [progressEvents, maxEvents])

  if (displayedEvents.length === 0) {
    return (
      <Card size="small" style={{ height: '100%' }}>
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无执行日志"
          style={{ margin: '20px 0' }}
        />
      </Card>
    )
  }

  if (compact) {
    return (
      <List
        size="small"
        dataSource={displayedEvents}
        renderItem={(event) => {
          const eventConfig = EVENT_CONFIG[event.type] || {
            icon: <ClockCircleOutlined />,
            color: 'default',
            label: event.type,
          }

          return (
            <List.Item style={{ padding: '4px 8px' }}>
              <Space size="small">
                {eventConfig.icon}
                <Tag color={eventConfig.color} style={{ margin: 0 }}>
                  {event.node_name || eventConfig.label}
                </Tag>
                <Text type="secondary" style={{ fontSize: 11 }}>
                  {formatTimestamp(event.timestamp)}
                </Text>
                {event.duration_ms !== undefined && event.duration_ms > 0 && (
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {formatDuration(event.duration_ms)}
                  </Text>
                )}
              </Space>
            </List.Item>
          )
        }}
        style={{
          maxHeight: height,
          overflow: 'auto',
        }}
      />
    )
  }

  return (
    <Card
      size="small"
      title={
        <Space>
          <ClockCircleOutlined />
          <span>执行日志</span>
          <Tag color="blue">{displayedEvents.length}</Tag>
        </Space>
      }
      bodyStyle={{
        padding: '12px 16px',
        maxHeight: height,
        overflow: 'auto',
      }}
    >
      <Timeline>
        {displayedEvents.map((event, index) => (
          <ExecutionLogItem key={`${event.execution_id}-${index}`} event={event} />
        ))}
      </Timeline>
    </Card>
  )
}

export default ExecutionLogPanel
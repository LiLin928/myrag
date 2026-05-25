import React from 'react'
import { Progress, Tag, Space, Typography } from 'antd'
import {
  FileTextOutlined,
  ScissorOutlined,
  CloudOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
} from '@ant-design/icons'

const { Text } = Typography

export type ProcessingStage = 'parsing' | 'chunking' | 'vectorizing' | 'storing' | 'completed'

export interface ProcessingStatus {
  status: 'idle' | 'running' | 'completed' | 'failed'
  stage: ProcessingStage | string
  progress: number
  message?: string
  error?: string
}

interface StageInfo {
  key: ProcessingStage | string
  label: string
  icon: React.ReactNode
  color: string
}

const STAGES: StageInfo[] = [
  { key: 'parsing', label: '解析', icon: <FileTextOutlined />, color: 'blue' },
  { key: 'chunking', label: '分块', icon: <ScissorOutlined />, color: 'cyan' },
  { key: 'vectorizing', label: '向量化', icon: <CloudOutlined />, color: 'purple' },
  { key: 'storing', label: '存储', icon: <DatabaseOutlined />, color: 'green' },
]

interface DocumentProgressTrackerProps {
  status: ProcessingStatus
  showDetails?: boolean
  compact?: boolean
}

export function DocumentProgressTracker({
  status,
  showDetails = false,
  compact = false,
}: DocumentProgressTrackerProps) {
  const currentStage = STAGES.find(s => s.key === status.stage)

  if (compact) {
    return (
      <Space size="small">
        {status.status === 'running' && (
          <>
            <LoadingOutlined spin />
            <Text type="secondary">{currentStage?.label || status.stage}</Text>
            <Progress
              percent={status.progress}
              size="small"
              style={{ width: 100 }}
              showInfo={false}
            />
            <Text type="secondary">{status.progress}%</Text>
          </>
        )}
        {status.status === 'completed' && (
          <>
            <CheckCircleOutlined style={{ color: '#52c41a' }} />
            <Text type="success">完成</Text>
          </>
        )}
        {status.status === 'failed' && (
          <>
            <CloseCircleOutlined style={{ color: '#ff4d4f' }} />
            <Text type="danger">失败</Text>
          </>
        )}
      </Space>
    )
  }

  return (
    <div style={{ padding: 16 }}>
      {/* 阶段指示器 */}
      <div style={{ marginBottom: 16 }}>
        <Space size="middle">
          {STAGES.map(stage => {
            const isActive = stage.key === status.stage
            const isCompleted = STAGES.findIndex(s => s.key === status.stage) > STAGES.findIndex(s => s.key === stage.key)

            return (
              <Tag
                key={stage.key}
                color={isCompleted ? 'success' : isActive ? stage.color : 'default'}
                icon={isActive && status.status === 'running' ? <LoadingOutlined spin /> : stage.icon}
              >
                {stage.label}
                {isCompleted && ' ✓'}
              </Tag>
            )
          })}

          {/* 最终状态 */}
          {status.status === 'completed' && (
            <Tag color="success" icon={<CheckCircleOutlined />}>
              完成 ✓
            </Tag>
          )}
          {status.status === 'failed' && (
            <Tag color="error" icon={<CloseCircleOutlined />}>
              失败
            </Tag>
          )}
        </Space>
      </div>

      {/* 进度条 */}
      {status.status === 'running' && (
        <Progress
          percent={status.progress}
          status="active"
          strokeColor={{
            '0%': '#108ee9',
            '100%': '#87d068',
          }}
        />
      )}

      {/* 消息显示 */}
      {status.message && showDetails && (
        <Text type="secondary" style={{ marginTop: 8, display: 'block' }}>
          {status.message}
        </Text>
      )}

      {/* 错误显示 */}
      {status.error && (
        <Text type="danger" style={{ marginTop: 8, display: 'block' }}>
          错误: {status.error}
        </Text>
      )}
    </div>
  )
}

interface ProgressListProps {
  documents: Array<{
    id: string
    filename: string
    status: ProcessingStatus
  }>
}

export function ProgressList({ documents }: ProgressListProps) {
  return (
    <div>
      {documents.map(doc => (
        <div
          key={doc.id}
          style={{
            padding: 12,
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text strong>{doc.filename}</Text>
            <DocumentProgressTracker status={doc.status} compact />
          </div>
        </div>
      ))}
    </div>
  )
}
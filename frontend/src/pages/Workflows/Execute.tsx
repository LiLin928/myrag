import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Card, Button, Form, Input, Space, Progress, message, Descriptions, Tag, Spin, Row, Col, Statistic, Alert } from 'antd'
import { ArrowLeftOutlined, PlayCircleOutlined, ReloadOutlined, ClearOutlined, CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { useWorkflowStore } from '../../stores/workflowStore'
import { useWorkflowProgress } from '../../hooks/useWorkflowProgress'
import { ExecutionLogPanel } from '../../components/Workflow/ExecutionLogPanel'

const statusColors: Record<string, string> = {
  running: 'processing',
  completed: 'success',
  failed: 'error',
  paused: 'warning',
}

export function WorkflowExecute() {
  const { id } = useParams()
  const navigate = useNavigate()
  const {
    currentWorkflow,
    currentExecution,
    executing,
    fetchOne,
    execute,
    currentProgress,
    completedNodes,
    totalNodes,
    progressEvents,
    clearProgressEvents,
    setCurrentExecution,
  } = useWorkflowStore()
  const [form] = Form.useForm()
  const [executionId, setExecutionId] = useState<string | null>(null)

  // Connect WebSocket when executionId changes
  const { disconnect } = useWorkflowProgress(executionId)

  useEffect(() => {
    if (id) fetchOne(id)
  }, [id, fetchOne])

  // Reset state when component unmounts
  useEffect(() => {
    return () => {
      disconnect()
      clearProgressEvents()
    }
  }, [disconnect, clearProgressEvents])

  const handleExecute = async () => {
    try {
      // Clear previous execution state
      clearProgressEvents()
      setCurrentExecution(null)
      setExecutionId(null)

      const values = form.getFieldsValue()
      let parsedInput = undefined
      if (values.input) {
        try {
          parsedInput = JSON.parse(values.input)
        } catch {
          message.error('输入参数 JSON 格式无效')
          return
        }
      }

      const result = await execute(id!, parsedInput)

      // Set executionId to trigger WebSocket connection
      setExecutionId(result.id)
      message.success('执行已启动')
    } catch (error: unknown) {
      const msg = error instanceof Error ? error.message : '执行失败'
      message.error(msg)
    }
  }

  const handleReset = () => {
    disconnect()
    clearProgressEvents()
    setCurrentExecution(null)
    setExecutionId(null)
    form.resetFields()
  }

  // Determine progress status
  const getProgressStatus = () => {
    if (currentExecution?.status === 'failed') return 'exception'
    if (currentExecution?.status === 'completed') return 'success'
    if (executing) return 'active'
    return 'normal'
  }

  if (!currentWorkflow) {
    return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />
  }

  return (
    <div style={{ padding: 0 }}>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/workflows/${id}`)}>
          返回编辑
        </Button>
        <Button
          icon={<ClearOutlined />}
          onClick={handleReset}
          disabled={!executionId && progressEvents.length === 0}
        >
          重置
        </Button>
      </Space>

      <Row gutter={16}>
        {/* Left Column: Controls and Status */}
        <Col span={10}>
          <Card size="small">
            <Descriptions title={currentWorkflow.name} bordered column={1} size="small">
              <Descriptions.Item label="状态">
                <Tag color={statusColors[currentWorkflow.status] || 'default'}>{currentWorkflow.status}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="描述">{currentWorkflow.description || '-'}</Descriptions.Item>
            </Descriptions>
          </Card>

          <Card title="执行配置" size="small" style={{ marginTop: 16 }}>
            <Form form={form} layout="vertical">
              <Form.Item name="input" label="输入参数 (JSON)">
                <Input.TextArea rows={4} placeholder='{"key": "value"}' />
              </Form.Item>
              <Form.Item>
                <Space>
                  <Button
                    type="primary"
                    icon={<PlayCircleOutlined />}
                    onClick={handleExecute}
                    loading={executing}
                  >
                    执行工作流
                  </Button>
                  <Button
                    icon={<ReloadOutlined />}
                    onClick={handleReset}
                    disabled={!executionId && progressEvents.length === 0}
                  >
                    重置
                  </Button>
                </Space>
              </Form.Item>
            </Form>
          </Card>

          {/* Progress Section */}
          {(executing || progressEvents.length > 0) && (
            <Card title="执行进度" size="small" style={{ marginTop: 16 }}>
              <Progress
                percent={currentProgress}
                status={getProgressStatus()}
                strokeColor={{
                  '0%': '#108ee9',
                  '100%': '#87d068',
                }}
              />
              <Row gutter={16} style={{ marginTop: 16 }}>
                <Col span={8}>
                  <Statistic
                    title="已完成节点"
                    value={completedNodes}
                    suffix={`/ ${totalNodes}`}
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="进度"
                    value={currentProgress}
                    suffix="%"
                  />
                </Col>
                <Col span={8}>
                  <Statistic
                    title="日志事件"
                    value={progressEvents.length}
                  />
                </Col>
              </Row>

              {/* Execution Status Alert */}
              {currentExecution && (
                <Alert
                  style={{ marginTop: 16 }}
                  type={currentExecution.status === 'completed' ? 'success' :
                        currentExecution.status === 'failed' ? 'error' : 'info'}
                  message={
                    currentExecution.status === 'completed' ? '执行完成' :
                    currentExecution.status === 'failed' ? '执行失败' : '执行中'
                  }
                  description={
                    currentExecution.status === 'completed' ? (
                      <Space>
                        <CheckCircleOutlined />
                        <span>工作流已成功执行完成</span>
                      </Space>
                    ) : currentExecution.status === 'failed' ? (
                      <Space>
                        <CloseCircleOutlined />
                        <span>{currentExecution.error_message || '执行过程中发生错误'}</span>
                      </Space>
                    ) : (
                      '正在执行工作流...'
                    )
                  }
                  showIcon
                />
              )}
            </Card>
          )}

          {/* Final Result */}
          {currentExecution?.status === 'completed' && currentExecution.output && (
            <Card title="执行结果" size="small" style={{ marginTop: 16 }}>
              <Descriptions bordered column={1} size="small">
                <Descriptions.Item label="状态">
                  <Tag icon={<CheckCircleOutlined />} color="success">
                    执行成功
                  </Tag>
                </Descriptions.Item>
                {currentExecution.completed_at && (
                  <Descriptions.Item label="完成时间">
                    {new Date(currentExecution.completed_at).toLocaleString()}
                  </Descriptions.Item>
                )}
                <Descriptions.Item label="输出结果">
                  <pre style={{
                    background: '#f5f5f5',
                    padding: 8,
                    borderRadius: 4,
                    maxHeight: 200,
                    overflow: 'auto',
                    fontSize: 12,
                  }}>
                    {JSON.stringify(currentExecution.output, null, 2)}
                  </pre>
                </Descriptions.Item>
              </Descriptions>
            </Card>
          )}
        </Col>

        {/* Right Column: Execution Logs */}
        <Col span={14}>
          <ExecutionLogPanel height={600} />
        </Col>
      </Row>
    </div>
  )
}
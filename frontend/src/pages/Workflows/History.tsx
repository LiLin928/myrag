import { useEffect, useState, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Card,
  Table,
  Tag,
  Space,
  Button,
  Select,
  DatePicker,
  Pagination,
  message,
  Popconfirm,
} from 'antd'
import {
  EyeOutlined,
  ReloadOutlined,
  DeleteOutlined,
} from '@ant-design/icons'
import dayjs from 'dayjs'
import { workflowApi, ExecutionHistoryItem, ExecutionHistoryParams } from '../../api/workflows'

const statusColors: Record<string, string> = {
  running: 'processing',
  completed: 'success',
  failed: 'error',
  paused: 'warning',
  pending: 'default',
}

export function WorkflowHistory() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [data, setData] = useState<ExecutionHistoryItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [filters, setFilters] = useState<ExecutionHistoryParams>({})

  const fetchHistory = useCallback(async () => {
    setLoading(true)
    try {
      const response = await workflowApi.listExecutions({
        ...filters,
        page,
        page_size: pageSize,
      })
      setData(response.data.items)
      setTotal(response.data.total)
    } catch (error) {
      message.error('获取执行历史失败')
    } finally {
      setLoading(false)
    }
  }, [filters, page, pageSize])

  useEffect(() => {
    fetchHistory()
  }, [fetchHistory])

  const handleView = useCallback((item: ExecutionHistoryItem) => {
    navigate(`/workflows/${item.workflow_id}/execute?execution_id=${item.id}`)
  }, [navigate])

  const handleRerun = useCallback(async (item: ExecutionHistoryItem) => {
    try {
      const response = await workflowApi.rerunExecution(item.id)
      message.success('已创建新执行')
      navigate(`/workflows/${item.workflow_id}/execute?execution_id=${response.data.execution_id}`)
    } catch (error) {
      message.error('重新执行失败')
    }
  }, [navigate])

  const handleDelete = useCallback(async (id: string) => {
    try {
      await workflowApi.deleteExecution(id)
      message.success('已删除')
      fetchHistory()
    } catch (error) {
      message.error('删除失败')
    }
  }, [fetchHistory])

  const columns = useMemo(() => [
    {
      title: '工作流',
      dataIndex: 'workflow_name',
      key: 'workflow_name',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => <Tag color={statusColors[status]}>{status}</Tag>,
    },
    {
      title: '开始时间',
      dataIndex: 'started_at',
      key: 'started_at',
      render: (time: string | null) => time ? dayjs(time).format('YYYY-MM-DD HH:mm:ss') : '-',
    },
    {
      title: '耗时',
      dataIndex: 'duration_ms',
      key: 'duration_ms',
      render: (ms: number | null) => ms ? `${(ms / 1000).toFixed(1)}s` : '-',
    },
    {
      title: '触发人',
      dataIndex: 'triggered_by',
      key: 'triggered_by',
    },
    {
      title: '错误摘要',
      dataIndex: 'error_summary',
      key: 'error_summary',
      render: (err: string | null) => err || '-',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: unknown, record: ExecutionHistoryItem) => (
        <Space>
          <Button size="small" icon={<EyeOutlined />} onClick={() => handleView(record)}>
            查看
          </Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => handleRerun(record)}>
            重跑
          </Button>
          <Popconfirm
            title="确认删除?"
            onConfirm={() => handleDelete(record.id)}
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ], [handleView, handleRerun, handleDelete])

  return (
    <Card title="执行历史">
      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="状态筛选"
          allowClear
          style={{ width: 120 }}
          onChange={(v) => setFilters(prev => ({ ...prev, status: v }))}
          options={[
            { value: 'completed', label: '已完成' },
            { value: 'failed', label: '失败' },
            { value: 'running', label: '运行中' },
            { value: 'paused', label: '暂停' },
          ]}
        />
        <DatePicker.RangePicker
          onChange={(dates) => setFilters(prev => ({
            ...prev,
            start_date: dates?.[0]?.toISOString(),
            end_date: dates?.[1]?.toISOString(),
          }))}
        />
      </Space>

      <Table
        columns={columns}
        dataSource={data}
        loading={loading}
        rowKey="id"
        pagination={false}
      />

      <Pagination
        current={page}
        pageSize={pageSize}
        total={total}
        onChange={(p, ps) => {
          setPage(p)
          setPageSize(ps)
        }}
        style={{ marginTop: 16, textAlign: 'right' }}
        showSizeChanger
        showTotal={(t) => `共 ${t} 条`}
      />
    </Card>
  )
}
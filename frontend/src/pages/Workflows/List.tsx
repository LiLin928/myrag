import { useEffect } from 'react'
import { Table, Button, Space, Tag, Popconfirm, message } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, PlayCircleOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useWorkflowStore } from '../../stores/workflowStore'
import { Workflow } from '../../types/models'

const statusColors: Record<string, string> = {
  draft: 'default',
  published: 'success',
  archived: 'warning',
}

export function WorkflowList() {
  const navigate = useNavigate()
  const { workflows, loading, fetchList, delete: deleteWorkflow } = useWorkflowStore()

  useEffect(() => {
    fetchList()
  }, [])

  const handleDelete = async (id: string) => {
    try {
      await deleteWorkflow(id)
      message.success('删除成功')
    } catch {
      message.error('删除失败')
    }
  }

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: Workflow) => (
        <a onClick={() => navigate(`/workflows/${record.id}`)}>{name}</a>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (desc: string) => desc || '-',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={statusColors[status]}>{status}</Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (date: string) => new Date(date).toLocaleString(),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Workflow) => (
        <Space>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/workflows/${record.id}`)} />
          <Button icon={<PlayCircleOutlined />} onClick={() => navigate(`/workflows/${record.id}/execute`)} />
          <Popconfirm title="确认删除？" onConfirm={() => handleDelete(record.id)}>
            <Button icon={<DeleteOutlined />} danger />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>工作流管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/workflows/new')}>
          创建工作流
        </Button>
      </div>
      <Table dataSource={workflows} columns={columns} rowKey="id" loading={loading} />
    </div>
  )
}
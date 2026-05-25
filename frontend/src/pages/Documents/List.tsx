import { useEffect } from 'react'
import { Table, Button, Space, Tag, Popconfirm, message } from 'antd'
import { UploadOutlined, DeleteOutlined, EyeOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useDocumentStore } from '../../stores/documentStore'
import { Document } from '../../types/models'

const statusColors: Record<string, string> = {
  pending: 'default',
  processing: 'processing',
  completed: 'success',
  failed: 'error',
}

export function DocumentList() {
  const navigate = useNavigate()
  const { documents, loading, fetchList, delete: deleteDoc } = useDocumentStore()

  useEffect(() => {
    fetchList()
  }, [])

  const handleDelete = async (id: string) => {
    try {
      await deleteDoc(id)
      message.success('删除成功')
    } catch {
      message.error('删除失败')
    }
  }

  const columns = [
    {
      title: '文件名',
      dataIndex: 'filename',
      key: 'filename',
      render: (name: string, record: Document) => (
        <a onClick={() => navigate(`/documents/${record.id}`)}>{name}</a>
      ),
    },
    {
      title: '类型',
      dataIndex: 'file_type',
      key: 'file_type',
    },
    {
      title: '大小',
      dataIndex: 'file_size',
      key: 'file_size',
      render: (size: number) => `${(size / 1024).toFixed(2)} KB`,
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
      render: (_: any, record: Document) => (
        <Space>
          <Button icon={<EyeOutlined />} onClick={() => navigate(`/documents/${record.id}`)} />
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
        <h2>文档管理</h2>
        <Button type="primary" icon={<UploadOutlined />} onClick={() => navigate('/documents/upload')}>
          上传文档
        </Button>
      </div>
      <Table dataSource={documents} columns={columns} rowKey="id" loading={loading} />
    </div>
  )
}
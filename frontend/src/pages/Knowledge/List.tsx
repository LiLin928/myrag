import { useEffect, useState } from 'react'
import { Table, Button, Space, Popconfirm, message, Tag } from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useKnowledgeStore } from '../../stores/knowledgeStore'
import { KnowledgeBase } from '../../types/models'
import { CreateKBModal } from '../../components/Knowledge/CreateKBModal'

export function KnowledgeList() {
  const navigate = useNavigate()
  const { knowledgeBases, loading, fetchList, delete: deleteKb } = useKnowledgeStore()
  const [modalOpen, setModalOpen] = useState(false)

  useEffect(() => {
    fetchList()
  }, [])

  const handleDelete = async (id: string) => {
    try {
      await deleteKb(id)
      message.success('删除成功')
    } catch (error: any) {
      message.error('删除失败')
    }
  }

  const getRetrievalMethodTag = (method: string) => {
    const colors: Record<string, string> = { vector: 'blue', keyword: 'green', hybrid: 'purple' }
    return <Tag color={colors[method] || 'default'}>{method || 'vector'}</Tag>
  }

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      render: (name: string, record: KnowledgeBase) => (
        <a onClick={() => navigate(`/knowledge/${record.id}`)}>{name}</a>
      ),
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      render: (desc: string) => desc || '-',
    },
    {
      title: '向量模型',
      dataIndex: 'embedding_model',
      key: 'embedding_model',
      width: 150,
      render: (model: string) => model || '-',
    },
    {
      title: '检索方法',
      dataIndex: 'retrieval_method',
      key: 'retrieval_method',
      width: 100,
      render: getRetrievalMethodTag,
    },
    {
      title: '文档数',
      dataIndex: 'document_count',
      key: 'document_count',
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
      render: (_: any, record: KnowledgeBase) => (
        <Space>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/knowledge/${record.id}`)} />
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
        <h2>知识库管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          创建知识库
        </Button>
      </div>
      <Table
        dataSource={knowledgeBases}
        columns={columns}
        rowKey="id"
        loading={loading}
      />
      <CreateKBModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  )
}
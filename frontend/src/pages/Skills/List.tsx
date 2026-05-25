import { useEffect } from 'react'
import { Table, Button, Space, Tag, Popconfirm, message } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined, RobotOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useSkillStore } from '../../stores/skillStore'
import { Skill } from '../../types/models'

const statusColors: Record<string, string> = {
  draft: 'default',
  published: 'success',
  archived: 'warning',
}

export function SkillList() {
  const navigate = useNavigate()
  const { skills, loading, fetchList, delete: deleteSkill } = useSkillStore()

  useEffect(() => {
    fetchList()
  }, [])

  const handleDelete = async (id: string) => {
    try {
      await deleteSkill(id)
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
      render: (name: string, record: Skill) => (
        <a onClick={() => navigate(`/skills/${record.id}`)}>{name}</a>
      ),
    },
    {
      title: '版本',
      dataIndex: 'version',
      key: 'version',
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
      title: 'LLM 生成',
      dataIndex: 'generated_by_llm',
      key: 'generated_by_llm',
      render: (val: boolean) => val ? <Tag color="blue">AI</Tag> : null,
    },
    {
      title: '执行次数',
      dataIndex: 'execution_count',
      key: 'execution_count',
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: Skill) => (
        <Space>
          <Button icon={<EditOutlined />} onClick={() => navigate(`/skills/${record.id}`)} />
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
        <h2>技能管理</h2>
        <Space>
          <Button icon={<RobotOutlined />} onClick={() => navigate('/skills/generate')}>
            AI 生成技能
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => navigate('/skills/new')}>
            创建技能
          </Button>
        </Space>
      </div>
      <Table dataSource={skills} columns={columns} rowKey="id" loading={loading} />
    </div>
  )
}
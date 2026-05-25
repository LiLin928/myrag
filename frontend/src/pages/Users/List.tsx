import { useEffect, useState } from 'react'
import { Table, Button, Space, Tag, Popconfirm, message, Modal, Form, Input } from 'antd'
import { PlusOutlined, UserOutlined } from '@ant-design/icons'
import { useUserStore } from '../../stores/userStore'
import { User } from '../../api/users'

export function UserList() {
  const { users, loading, fetchList, create, activate, deactivate } = useUserStore()
  const [modalOpen, setModalOpen] = useState(false)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchList()
  }, [])

  const handleCreate = async (values: { username: string; email: string; password: string; full_name?: string }) => {
    try {
      await create({
        username: values.username,
        email: values.email,
        password: values.password,
        full_name: values.full_name,
      })
      message.success('创建成功')
      setModalOpen(false)
      form.resetFields()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '创建失败')
    }
  }

  const handleActivate = async (id: string) => {
    try {
      await activate(id)
      message.success('已激活')
    } catch {
      message.error('操作失败')
    }
  }

  const handleDeactivate = async (id: string) => {
    try {
      await deactivate(id)
      message.success('已停用')
    } catch {
      message.error('操作失败')
    }
  }

  const columns = [
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
      render: (name: string, record: User) => (
        <Space>
          <Tag icon={<UserOutlined />} color="blue">{name}</Tag>
          {record.is_superuser && <Tag color="gold">超级管理员</Tag>}
        </Space>
      ),
    },
    {
      title: '邮箱',
      dataIndex: 'email',
      key: 'email',
    },
    {
      title: '姓名',
      dataIndex: 'full_name',
      key: 'full_name',
      render: (name: string) => name || '-',
    },
    {
      title: '状态',
      dataIndex: 'is_active',
      key: 'is_active',
      render: (active: boolean) => (
        <Tag color={active ? 'success' : 'error'}>{active ? '正常' : '停用'}</Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      render: (_: any, record: User) => (
        <Space>
          {record.is_active ? (
            <Popconfirm title="确认停用？" onConfirm={() => handleDeactivate(record.id)}>
              <Button size="small" danger>停用</Button>
            </Popconfirm>
          ) : (
            <Button size="small" onClick={() => handleActivate(record.id)}>激活</Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>用户管理</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setModalOpen(true)}>
          创建用户
        </Button>
      </div>
      <Table dataSource={users} columns={columns} rowKey="id" loading={loading} />

      <Modal
        title="创建用户"
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        onOk={() => form.submit()}
      >
        <Form form={form} onFinish={handleCreate} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, type: 'email' }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="full_name" label="姓名">
            <Input />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
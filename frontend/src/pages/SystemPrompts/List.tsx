import { useEffect, useState } from 'react'
import { Table, Button, Space, Tag, Popconfirm, message, Modal, Form, Input, Select } from 'antd'
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons'
import { useSystemPromptStore } from '../../stores/systemPromptStore'
import { SystemPromptTemplate } from '../../types/models'
import dayjs from 'dayjs'

export function SystemPromptList() {
  const { templates, categories, loading, saving, fetchList, fetchCategories, create, update, delete: deleteTemplate } = useSystemPromptStore()
  const [modalOpen, setModalOpen] = useState(false)
  const [editingTemplate, setEditingTemplate] = useState<SystemPromptTemplate | null>(null)
  const [form] = Form.useForm()

  useEffect(() => {
    fetchList()
    fetchCategories()
  }, [])

  const handleCreate = () => {
    setEditingTemplate(null)
    form.resetFields()
    setModalOpen(true)
  }

  const handleEdit = (template: SystemPromptTemplate) => {
    setEditingTemplate(template)
    form.setFieldsValue({
      name: template.name,
      description: template.description || '',
      content: template.content,
      category: template.category || undefined,
      is_public: template.is_public,
    })
    setModalOpen(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await deleteTemplate(id)
      message.success('删除成功')
    } catch {
      message.error('删除失败')
    }
  }

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields()
      if (editingTemplate) {
        await update(editingTemplate.id, values)
        message.success('更新成功')
      } else {
        await create(values)
        message.success('创建成功')
      }
      setModalOpen(false)
      form.resetFields()
    } catch (error) {
      if (error instanceof Error) {
        message.error(error.message)
      }
    }
  }

  const handleModalClose = () => {
    setModalOpen(false)
    setEditingTemplate(null)
    form.resetFields()
  }

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      width: 200,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      width: 250,
      render: (text: string | null) => text || '-',
    },
    {
      title: '分类',
      dataIndex: 'category',
      key: 'category',
      width: 120,
      render: (category: string | null) => category ? <Tag>{category}</Tag> : '-',
    },
    {
      title: '公开',
      dataIndex: 'is_public',
      key: 'is_public',
      width: 80,
      render: (isPublic: boolean) => (
        <Tag color={isPublic ? 'blue' : 'default'}>
          {isPublic ? '公开' : '私有'}
        </Tag>
      ),
    },
    {
      title: '默认',
      dataIndex: 'is_default',
      key: 'is_default',
      width: 80,
      render: (isDefault: boolean) => (
        <Tag color={isDefault ? 'green' : 'default'}>
          {isDefault ? '默认' : '否'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (date: string) => dayjs(date).format('YYYY-MM-DD HH:mm:ss'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 150,
      render: (_: unknown, record: SystemPromptTemplate) => (
        <Space>
          <Button
            icon={<EditOutlined />}
            size="small"
            disabled={record.is_default}
            onClick={() => handleEdit(record)}
          />
          <Popconfirm
            title="确认删除此模板？"
            onConfirm={() => handleDelete(record.id)}
            disabled={record.is_default}
          >
            <Button
              icon={<DeleteOutlined />}
              size="small"
              danger
              disabled={record.is_default}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>系统提示词模板</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
          创建模板
        </Button>
      </div>

      <Table
        dataSource={templates}
        columns={columns}
        rowKey="id"
        loading={loading}
        pagination={{
          showSizeChanger: true,
          showQuickJumper: true,
          showTotal: (total) => `共 ${total} 条`,
        }}
      />

      <Modal
        title={editingTemplate ? '编辑模板' : '创建模板'}
        open={modalOpen}
        onOk={handleSubmit}
        onCancel={handleModalClose}
        confirmLoading={saving}
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          initialValues={{ is_public: false }}
        >
          <Form.Item
            name="name"
            label="名称"
            rules={[{ required: true, message: '请输入模板名称' }]}
          >
            <Input placeholder="请输入模板名称" />
          </Form.Item>

          <Form.Item
            name="description"
            label="描述"
          >
            <Input.TextArea rows={2} placeholder="请输入模板描述（可选）" />
          </Form.Item>

          <Form.Item
            name="content"
            label="内容"
            rules={[{ required: true, message: '请输入模板内容' }]}
          >
            <Input.TextArea rows={8} placeholder="请输入系统提示词内容" />
          </Form.Item>

          <Form.Item
            name="category"
            label="分类"
          >
            <Select
              placeholder="选择分类（可选）"
              allowClear
              showSearch
              options={categories.map((c) => ({ label: c.category, value: c.category }))}
            />
          </Form.Item>

          <Form.Item
            name="is_public"
            label="公开"
            valuePropName="checked"
          >
            <Select
              options={[
                { label: '私有', value: false },
                { label: '公开', value: true },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
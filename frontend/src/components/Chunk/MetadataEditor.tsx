import { useState, useEffect } from 'react'
import { Modal, Form, Input, Tag, Space, Button, Divider, Typography } from 'antd'
import { PlusOutlined, CloseOutlined } from '@ant-design/icons'

import { Chunk, ChunkMetadata } from '../../stores/chunkStore'

const { Text } = Typography

interface MetadataEditorProps {
  visible: boolean
  chunk: Chunk
  onSave: (metadata: Partial<ChunkMetadata>) => Promise<void>
  onCancel: () => void
}

export function MetadataEditor({ visible, chunk, onSave, onCancel }: MetadataEditorProps) {
  const [form] = Form.useForm()
  const [loading, setLoading] = useState(false)
  const [userTags, setUserTags] = useState<string[]>([])
  const [newTag, setNewTag] = useState('')
  const [customFields, setCustomFields] = useState<Record<string, string>>({})
  const [newFieldName, setNewFieldName] = useState('')
  const [newFieldValue, setNewFieldValue] = useState('')

  // Initialize form with existing metadata
  useEffect(() => {
    if (visible && chunk) {
      setUserTags(chunk.metadata.user_tags || [])
      setCustomFields((chunk.metadata.custom_fields as Record<string, string>) || {})
      form.setFieldsValue({
        category: chunk.metadata.category,
        note: chunk.metadata.note,
      })
    }
  }, [visible, chunk])

  // Add tag
  const handleAddTag = () => {
    if (newTag && !userTags.includes(newTag)) {
      setUserTags([...userTags, newTag])
      setNewTag('')
    }
  }

  // Remove tag
  const handleRemoveTag = (tag: string) => {
    setUserTags(userTags.filter(t => t !== tag))
  }

  // Add custom field
  const handleAddField = () => {
    if (newFieldName && newFieldValue) {
      setCustomFields({ ...customFields, [newFieldName]: newFieldValue })
      setNewFieldName('')
      setNewFieldValue('')
    }
  }

  // Remove custom field
  const handleRemoveField = (fieldName: string) => {
    const newFields = { ...customFields }
    delete newFields[fieldName]
    setCustomFields(newFields)
  }

  // Handle save
  const handleSave = async () => {
    setLoading(true)
    try {
      const values = await form.validateFields()

      const metadata: Partial<ChunkMetadata> = {
        user_tags: userTags,
        category: values.category,
        note: values.note,
        custom_fields: customFields,
      }

      await onSave(metadata)
      setLoading(false)
    } catch (error) {
      setLoading(false)
      console.error('Save failed:', error)
    }
  }

  return (
    <Modal
      title="编辑分块元数据"
      open={visible}
      onOk={handleSave}
      onCancel={onCancel}
      confirmLoading={loading}
      width={600}
      destroyOnClose
    >
      <Form form={form} layout="vertical">
        {/* Document basic info (readonly) */}
        <Divider orientation="left">文档基础信息（只读）</Divider>

        <Space size="small" wrap style={{ marginBottom: 16 }}>
          <Tag color="blue">类型: {chunk.metadata.document_type || '未知'}</Tag>
          <Tag color="cyan">文件: {chunk.metadata.source_filename || chunk.document_id}</Tag>
          <Tag>页码: {chunk.page_number}</Tag>
          {chunk.metadata.section_title && (
            <Tag color="purple">章节: {chunk.metadata.section_title}</Tag>
          )}
          {chunk.has_embedding ? (
            <Tag color="success">已向量化</Tag>
          ) : (
            <Tag color="warning">未向量化</Tag>
          )}
        </Space>

        {/* User tags */}
        <Divider orientation="left">用户标签</Divider>

        <div style={{ marginBottom: 16 }}>
          <Space size="small" wrap>
            {userTags.map(tag => (
              <Tag
                key={tag}
                closable
                onClose={() => handleRemoveTag(tag)}
                closeIcon={<CloseOutlined />}
              >
                {tag}
              </Tag>
            ))}
          </Space>

          <Space.Compact style={{ marginTop: 8, width: '100%' }}>
            <Input
              placeholder="输入新标签"
              value={newTag}
              onChange={(e) => setNewTag(e.target.value)}
              onPressEnter={handleAddTag}
            />
            <Button icon={<PlusOutlined />} onClick={handleAddTag}>
              添加
            </Button>
          </Space.Compact>
        </div>

        {/* Category and note */}
        <Divider orientation="left">分类与备注</Divider>

        <Form.Item name="category" label="分类">
          <Input placeholder="例如：核心内容、参考资料" />
        </Form.Item>

        <Form.Item name="note" label="备注">
          <Input.TextArea rows={3} placeholder="添加备注信息" />
        </Form.Item>

        {/* Custom fields */}
        <Divider orientation="left">自定义字段</Divider>

        <div style={{ marginBottom: 16 }}>
          {Object.entries(customFields).map(([key, value]) => (
            <div key={key} style={{ marginBottom: 8 }}>
              <Space.Compact style={{ width: '100%' }}>
                <Input
                  style={{ width: '30%' }}
                  addonBefore={<Tag>{key}</Tag>}
                  value={value}
                  onChange={(e) => setCustomFields({ ...customFields, [key]: e.target.value })}
                />
                <Button
                  danger
                  icon={<CloseOutlined />}
                  onClick={() => handleRemoveField(key)}
                />
              </Space.Compact>
            </div>
          ))}

          {Object.keys(customFields).length === 0 && (
            <Text type="secondary">暂无自定义字段</Text>
          )}

          <Space.Compact style={{ marginTop: 8, width: '100%' }}>
            <Input
              style={{ width: '30%' }}
              placeholder="字段名"
              value={newFieldName}
              onChange={(e) => setNewFieldName(e.target.value)}
            />
            <Input
              style={{ width: '50%' }}
              placeholder="字段值"
              value={newFieldValue}
              onChange={(e) => setNewFieldValue(e.target.value)}
            />
            <Button icon={<PlusOutlined />} onClick={handleAddField}>
              添加
            </Button>
          </Space.Compact>
        </div>
      </Form>
    </Modal>
  )
}
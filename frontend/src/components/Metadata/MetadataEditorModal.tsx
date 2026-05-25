import { Modal, Button, Divider, Typography, Space, message, Input } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { MetadataResponse } from '../../types/models'
import { MetadataFieldEditor } from './MetadataFieldEditor'
import { useMetadataStore } from '../../stores/metadataStore'

interface MetadataEditorModalProps {
  visible: boolean
  title: string
  metadata: MetadataResponse
  mode: 'document' | 'chunk'
  knowledgeId?: string
  documentId?: string
  chunkId?: string
  onSave: (metadata: Record<string, string>) => Promise<void>
  onCancel: () => void
}

export function MetadataEditorModal({
  visible,
  title,
  metadata,
  mode: _mode,
  knowledgeId: _knowledgeId,
  documentId: _documentId,
  chunkId: _chunkId,
  onSave,
  onCancel,
}: MetadataEditorModalProps) {
  const { fields: _fields } = useMetadataStore()
  const [ownFields, setOwnFields] = useState<{ name: string; value: string }[]>([])
  const [newFieldName, setNewFieldName] = useState('')
  const [newFieldValue, setNewFieldValue] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (visible && metadata) {
      setOwnFields(
        Object.entries(metadata.own).map(([name, value]) => ({ name, value }))
      )
    }
  }, [visible, metadata])

  const inheritedFields = Object.entries(metadata?.inherited || {})

  const handleAddField = () => {
    if (!newFieldName) {
      message.error('请输入字段名')
      return
    }
    if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(newFieldName)) {
      message.error('字段名格式错误')
      return
    }
    if (inheritedFields.some(([n]) => n === newFieldName)) {
      message.error('字段名与继承字段冲突')
      return
    }
    if (ownFields.some(f => f.name === newFieldName)) {
      message.error('字段名已存在')
      return
    }

    setOwnFields([...ownFields, { name: newFieldName, value: newFieldValue }])
    setNewFieldName('')
    setNewFieldValue('')
  }

  const handleUpdateField = (index: number, value: string) => {
    const updated = [...ownFields]
    updated[index].value = value
    setOwnFields(updated)
  }

  const handleDeleteField = (index: number) => {
    setOwnFields(ownFields.filter((_, i) => i !== index))
  }

  const handleSave = async () => {
    setLoading(true)
    try {
      const metadataObj = ownFields.reduce((acc, f) => {
        acc[f.name] = f.value
        return acc
      }, {} as Record<string, string>)

      await onSave(metadataObj)
      message.success('保存成功')
      onCancel()
    } catch (error: any) {
      message.error(error.response?.data?.detail || '保存失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal
      title={title}
      open={visible}
      onCancel={onCancel}
      footer={[
        <Button key="cancel" onClick={onCancel}>
          取消
        </Button>,
        <Button key="save" type="primary" loading={loading} onClick={handleSave}>
          保存
        </Button>,
      ]}
      width={600}
    >
      {inheritedFields.length > 0 && (
        <>
          <Typography.Text type="secondary">继承的元数据（只读）</Typography.Text>
          <Divider style={{ margin: '8px 0' }} />
          {inheritedFields.map(([name, value]) => (
            <MetadataFieldEditor
              key={name}
              name={name}
              value={value}
              readonly
            />
          ))}
        </>
      )}

      <Typography.Text>自有元数据（可编辑）</Typography.Text>
      <Divider style={{ margin: '8px 0' }} />

      {ownFields.map((field, index) => (
        <MetadataFieldEditor
          key={field.name}
          name={field.name}
          value={field.value}
          onValueChange={(v) => handleUpdateField(index, v)}
          onDelete={() => handleDeleteField(index)}
        />
      ))}

      <Space.Compact style={{ width: '100%', marginTop: 8 }}>
        <Input
          style={{ width: 150 }}
          placeholder="新字段名"
          value={newFieldName}
          onChange={(e) => setNewFieldName(e.target.value)}
        />
        <Input
          style={{ flex: 1 }}
          placeholder="值"
          value={newFieldValue}
          onChange={(e) => setNewFieldValue(e.target.value)}
        />
        <Button
          type="dashed"
          icon={<PlusOutlined />}
          onClick={handleAddField}
        >
          添加
        </Button>
      </Space.Compact>

      <Typography.Text type="secondary" style={{ fontSize: 12, marginTop: 16 }}>
        字段名规则：英文开头，仅支持英文、数字、下划线
      </Typography.Text>
    </Modal>
  )
}
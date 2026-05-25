import { Input, Button, Space, Typography, Tooltip } from 'antd'
import { DeleteOutlined } from '@ant-design/icons'
import { useState } from 'react'

interface MetadataFieldEditorProps {
  name: string
  value: string
  readonly?: boolean
  isNew?: boolean
  onNameChange?: (name: string) => void
  onValueChange?: (value: string) => void
  onDelete?: () => void
}

export function MetadataFieldEditor({
  name,
  value,
  readonly = false,
  isNew = false,
  onNameChange,
  onValueChange,
  onDelete,
}: MetadataFieldEditorProps) {
  const [localName, setLocalName] = useState(name)
  const [nameError, setNameError] = useState<string | null>(null)

  const validateName = (n: string) => {
    if (!n) return '字段名不能为空'
    if (!/^[a-zA-Z][a-zA-Z0-9_]*$/.test(n)) {
      return '仅支持英文开头的字母数字下划线'
    }
    if (n.length > 50) return '字段名不能超过50字符'
    return null
  }

  const handleNameChange = (n: string) => {
    setLocalName(n)
    setNameError(validateName(n))
    onNameChange?.(n)
  }

  if (readonly) {
    return (
      <Space style={{ width: '100%', marginBottom: 8 }}>
        <Typography.Text type="secondary" style={{ width: 150 }}>
          {name}
        </Typography.Text>
        <Typography.Text type="secondary" style={{ flex: 1 }}>
          {value}
        </Typography.Text>
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          (继承)
        </Typography.Text>
      </Space>
    )
  }

  return (
    <Space.Compact style={{ width: '100%', marginBottom: 8 }}>
      {isNew ? (
        <Tooltip title={nameError || '字段名'} open={!!nameError}>
          <Input
            style={{ width: 150 }}
            placeholder="字段名 (英文)"
            value={localName}
            onChange={(e) => handleNameChange(e.target.value)}
            status={nameError ? 'error' : undefined}
          />
        </Tooltip>
      ) : (
        <Input
          style={{ width: 150 }}
          value={name}
          disabled
        />
      )}
      <Input
        style={{ flex: 1 }}
        value={value}
        onChange={(e) => onValueChange?.(e.target.value)}
        placeholder="值"
        maxLength={500}
      />
      {onDelete && (
        <Button
          icon={<DeleteOutlined />}
          onClick={onDelete}
          danger
        />
      )}
    </Space.Compact>
  )
}
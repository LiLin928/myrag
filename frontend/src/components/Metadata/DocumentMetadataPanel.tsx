import { Card, Button, Descriptions, Tag, Spin, Typography } from 'antd'
import { EditOutlined } from '@ant-design/icons'
import { useState, useEffect } from 'react'
import { useMetadataStore } from '../../stores/metadataStore'
import { MetadataEditorModal } from './MetadataEditorModal'

interface DocumentMetadataPanelProps {
  knowledgeId: string
  documentId: string
  filename: string
}

export function DocumentMetadataPanel({
  knowledgeId,
  documentId,
  filename,
}: DocumentMetadataPanelProps) {
  const { fields, fetchFields, currentDocumentMetadata, fetchDocumentMetadata } = useMetadataStore()
  const [editing, setEditing] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchFields('document')
    fetchDocumentMetadata(knowledgeId, documentId).finally(() => setLoading(false))
  }, [knowledgeId, documentId])

  const handleSave = async (metadata: Record<string, string>) => {
    const { updateDocumentMetadata } = useMetadataStore.getState()
    await updateDocumentMetadata(knowledgeId, documentId, metadata)
    // Refresh metadata after save
    await fetchDocumentMetadata(knowledgeId, documentId)
  }

  if (loading) {
    return <Spin />
  }

  const metadata = currentDocumentMetadata || { inherited: {}, own: {}, merged: {} }
  const mergedEntries = Object.entries(metadata.merged)

  const getFieldDisplayName = (name: string) => {
    const field = fields.find(f => f.name === name)
    return field?.display_name || name
  }

  const isReadonlyField = (name: string) => {
    const field = fields.find(f => f.name === name)
    return field?.readonly || false
  }

  return (
    <Card
      title={`文档: ${filename}`}
      size="small"
      extra={
        <Button
          icon={<EditOutlined />}
          onClick={() => setEditing(true)}
        >
          编辑元数据
        </Button>
      }
    >
      <Descriptions column={2} size="small">
        {mergedEntries.length === 0 && (
          <Descriptions.Item>
            <Typography.Text type="secondary">无元数据</Typography.Text>
          </Descriptions.Item>
        )}
        {mergedEntries.map(([name, value]) => (
          <Descriptions.Item
            key={name}
            label={getFieldDisplayName(name)}
          >
            <Typography.Text>{value}</Typography.Text>
            {isReadonlyField(name) && (
              <Tag color="default" style={{ marginLeft: 4 }}>
                只读
              </Tag>
            )}
          </Descriptions.Item>
        ))}
      </Descriptions>

      {editing && (
        <MetadataEditorModal
          visible={editing}
          title="编辑文档元数据"
          metadata={metadata}
          mode="document"
          knowledgeId={knowledgeId}
          documentId={documentId}
          onSave={handleSave}
          onCancel={() => setEditing(false)}
        />
      )}
    </Card>
  )
}
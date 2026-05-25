import { Modal, Descriptions, Button, Space, Tag } from 'antd'
import { WorkflowTemplateDetail } from '../../api/templates'

interface TemplateDetailModalProps {
  template: WorkflowTemplateDetail | null
  visible: boolean
  onClose: () => void
  onUse: (templateId: string) => void
}

export function TemplateDetailModal({ template, visible, onClose, onUse }: TemplateDetailModalProps) {
  if (!template) return null

  return (
    <Modal
      title={template.name}
      open={visible}
      onCancel={onClose}
      footer={[
        <Button key="cancel" onClick={onClose}>
          取消
        </Button>,
        <Button key="use" type="primary" onClick={() => onUse(template.id)}>
          使用此模板
        </Button>,
      ]}
      width={800}
    >
      <Descriptions bordered column={2}>
        <Descriptions.Item label="分类">
          <Tag color="blue">{template.category}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="标签">
          <Space>
            {template.tags?.map((t) => <Tag key={t}>{t}</Tag>)}
          </Space>
        </Descriptions.Item>
        <Descriptions.Item label="描述" span={2}>
          {template.description}
        </Descriptions.Item>
        <Descriptions.Item label="使用次数">
          {template.usage_count} 次
        </Descriptions.Item>
        <Descriptions.Item label="类型">
          {template.is_builtin ? '内置' : '自定义'}
        </Descriptions.Item>
      </Descriptions>

      <div style={{ marginTop: 16, textAlign: 'center' }}>
        <Button onClick={() => alert('预览功能待实现')}>查看工作流图预览</Button>
      </div>
    </Modal>
  )
}
import { useState } from 'react'
import { Modal, Form, Select, Input, Button, message } from 'antd'
import { apiClient } from '../../api/client'

interface PublishModalProps {
  visible: boolean
  agentId: string
  onClose: () => void
}

export function PublishModal({ visible, agentId, onClose }: PublishModalProps) {
  const [form] = Form.useForm()
  const [publishType, setPublishType] = useState('embed')
  const [publishResult, setPublishResult] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const handlePublish = async () => {
    setLoading(true)
    try {
      const values = await form.validateFields()
      const res = await apiClient.post(`/agent-publish/${agentId}/`, {
        publish_type: publishType,
        config: values,
      })

      setPublishResult(res.data)
      message.success('发布成功')
    } catch (e: any) {
      message.error(e.message || '发布失败')
    } finally {
      setLoading(false)
    }
  }

  const handleClose = () => {
    form.resetFields()
    setPublishResult(null)
    onClose()
  }

  return (
    <Modal
      title="发布智能体"
      open={visible}
      onCancel={handleClose}
      footer={null}
      width={600}
    >
      {!publishResult ? (
        <Form form={form} layout="vertical">
          <Form.Item label="发布类型">
            <Select
              value={publishType}
              onChange={setPublishType}
              options={[
                { value: 'embed', label: '嵌入代码' },
                { value: 'link', label: '公开链接' },
                { value: 'api', label: 'API 访问' },
              ]}
            />
          </Form.Item>

          {publishType === 'embed' && (
            <>
              <Form.Item label="主题色" name="theme_color">
                <Input placeholder="#1890ff" />
              </Form.Item>
              <Form.Item label="窗口标题" name="window_title">
                <Input placeholder="智能助手" />
              </Form.Item>
              <Form.Item label="位置" name="position">
                <Select
                  options={[
                    { value: 'bottom-right', label: '右下角' },
                    { value: 'bottom-left', label: '左下角' },
                  ]}
                />
              </Form.Item>
            </>
          )}

          <Button type="primary" loading={loading} onClick={handlePublish}>
            发布
          </Button>
        </Form>
      ) : (
        <div>
          {publishType === 'embed' && (
            <div>
              <h4>嵌入代码</h4>
              <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
                {publishResult.embed_code}
              </pre>
            </div>
          )}

          {publishType === 'link' && (
            <div>
              <h4>公开链接</h4>
              <a href={publishResult.link_url} target="_blank" rel="noopener noreferrer">
                {publishResult.link_url}
              </a>
            </div>
          )}

          {publishType === 'api' && (
            <div>
              <h4>API Key</h4>
              <Input.Password value={publishResult.api_key} />
            </div>
          )}

          <Button onClick={handleClose} style={{ marginTop: 16 }}>
            关闭
          </Button>
        </div>
      )}
    </Modal>
  )
}
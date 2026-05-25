import { useEffect, useState } from 'react'
import { List, Button, Popconfirm, message, Empty } from 'antd'
import { PlusOutlined, MessageOutlined, DeleteOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { useChatStore } from '../../stores/chatStore'
import { CreateModal } from './CreateModal'

export function ChatList() {
  const navigate = useNavigate()
  const { conversations, fetchList, delete: deleteConv } = useChatStore()
  const [createModalOpen, setCreateModalOpen] = useState(false)

  useEffect(() => {
    fetchList()
  }, [])

  const handleDelete = async (id: string) => {
    try {
      await deleteConv(id)
      message.success('删除成功')
    } catch {
      message.error('删除失败')
    }
  }

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>对话</h2>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateModalOpen(true)}>
          新对话
        </Button>
      </div>
      {conversations.length === 0 ? (
        <Empty description="暂无对话，点击上方按钮创建" style={{ marginTop: 100 }} />
      ) : (
        <List
          dataSource={conversations}
          renderItem={(conv) => (
            <List.Item
              actions={[
                <Popconfirm title="确认删除？" onConfirm={() => handleDelete(conv.id)}>
                  <Button icon={<DeleteOutlined />} danger size="small" />
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                avatar={<MessageOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
                title={<a onClick={() => navigate(`/chat/${conv.id}`)}>{conv.title || '新对话'}</a>}
                description={`${conv.message_count} 条消息 · ${conv.model} · ${new Date(conv.updated_at).toLocaleString()}`}
              />
            </List.Item>
          )}
        />
      )}
      <CreateModal open={createModalOpen} onClose={() => setCreateModalOpen(false)} />
    </div>
  )
}
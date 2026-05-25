import { useState } from 'react'
import { List, Input, Button, message } from 'antd'
import { SendOutlined } from '@ant-design/icons'

interface ChatWindowProps {
  history: Array<{ role: string; content: string; sources?: any[] }>
  onSend: (message: string) => Promise<void>
  sessionId: string | null
  sessions: any[]
  onSwitchSession: (sessionId: string | null) => void
}

export function ChatWindow({ history, onSend, sessionId, sessions, onSwitchSession }: ChatWindowProps) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSend = async () => {
    if (!input.trim()) return

    setLoading(true)
    try {
      await onSend(input.trim())
      setInput('')
    } catch (e: any) {
      message.error(e.message || '发送失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column', background: '#fff', borderRadius: 8 }}>
      {/* 会话切换栏 */}
      <div style={{ padding: 8, borderBottom: '1px solid #f0f0f0' }}>
        <Button
          size="small"
          onClick={() => onSwitchSession(null)}
          type={!sessionId ? 'primary' : 'default'}
        >
          新对话
        </Button>
        {sessions.length > 0 && (
          <List
            size="small"
            dataSource={sessions.slice(0, 5)}
            renderItem={(session: any) => (
              <List.Item
                onClick={() => onSwitchSession(session.id)}
                style={{
                  cursor: 'pointer',
                  background: sessionId === session.id ? '#e6f7ff' : 'transparent',
                }}
              >
                {session.title || `会话 ${session.id}`}
              </List.Item>
            )}
          />
        )}
      </div>

      {/* 消息列表 */}
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {history.map((msg, index) => (
          <div
            key={index}
            style={{
              marginBottom: 12,
              textAlign: msg.role === 'user' ? 'right' : 'left',
            }}
          >
            <div
              style={{
                display: 'inline-block',
                padding: '8px 12px',
                borderRadius: 8,
                background: msg.role === 'user' ? '#1890ff' : '#f0f0f0',
                color: msg.role === 'user' ? '#fff' : '#000',
                maxWidth: '70%',
              }}
            >
              {msg.content}
            </div>
            {msg.sources && msg.sources.length > 0 && (
              <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                引用来源: {msg.sources.map((s: any) => s.doc_name).join(', ')}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 输入区域 */}
      <div style={{ padding: 16, borderTop: '1px solid #f0f0f0' }}>
        <Input.TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="输入消息..."
          rows={3}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
        />
        <Button
          type="primary"
          icon={<SendOutlined />}
          loading={loading}
          onClick={handleSend}
          style={{ marginTop: 8 }}
        >
          发送
        </Button>
      </div>
    </div>
  )
}
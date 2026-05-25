import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Input, Button, Spin, List, Avatar, Tag } from 'antd'
import { SendOutlined, ArrowLeftOutlined, UserOutlined, RobotOutlined, SettingOutlined } from '@ant-design/icons'
import { useChatStore } from '../../stores/chatStore'
import { Message } from '../../types/models'
import { conversationApi } from '../../api/conversations'
import { ConfigPanel } from '../../components/Chat/ConfigPanel'

export function ConversationView() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { currentConversation, messages, sending, fetchOne, fetchMessages, sendMessage } = useChatStore()
  const [input, setInput] = useState('')
  const [configPanelOpen, setConfigPanelOpen] = useState(false)
  const [greetingSent, setGreetingSent] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (id) {
      fetchOne(id)
      fetchMessages(id)
    }
  }, [id])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Send greeting if enabled and not already sent
  useEffect(() => {
    if (currentConversation?.greeting_enabled && !greetingSent && !currentConversation.greeting_sent) {
      conversationApi.sendGreeting(currentConversation.id).then(() => {
        setGreetingSent(true)
        fetchMessages(currentConversation.id)
      }).catch(() => {})
    }
  }, [currentConversation, greetingSent, fetchMessages])

  const handleSend = async () => {
    if (!input.trim() || sending) return
    const message = input.trim()
    setInput('')
    await sendMessage(message)
  }

  const roleIcons: Record<string, React.ReactNode> = {
    user: <UserOutlined />,
    assistant: <RobotOutlined />,
    tool: <RobotOutlined />,
    system: <RobotOutlined />,
  }

  const roleColors: Record<string, string> = {
    user: '#1890ff',
    assistant: '#52c41a',
    tool: '#faad14',
    system: '#8c8c8c',
  }

  const roleLabels: Record<string, string> = {
    user: '用户',
    assistant: '助手',
    tool: '工具',
    system: '系统',
  }

  return (
    <div style={{
      height: 'calc(100vh - 150px)',
      display: 'flex',
      flexDirection: 'column',
      background: '#fff',
      borderRadius: 8,
    }}>
      <div style={{
        padding: '16px 24px',
        borderBottom: '1px solid #f0f0f0',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
      }}>
        <h3 style={{ margin: 0 }}>{currentConversation?.title || '对话'}</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <Button icon={<SettingOutlined />} onClick={() => setConfigPanelOpen(true)}>
            设置
          </Button>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/chat')}>
            返回
          </Button>
        </div>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {messages.length === 0 && !sending && (
          <div style={{ textAlign: 'center', padding: '100px', color: '#999' }}>
            开始对话吧...
          </div>
        )}
        <List
          dataSource={messages}
          renderItem={(msg: Message) => (
            <List.Item style={{ border: 'none', padding: '8px 0' }}>
              <div style={{ display: 'flex', gap: '12px', width: '100%', maxWidth: '800px' }}>
                <Avatar
                  style={{ background: roleColors[msg.role] }}
                  icon={roleIcons[msg.role]}
                />
                <div style={{ flex: 1 }}>
                  <div>
                    <Tag color={roleColors[msg.role]}>{roleLabels[msg.role]}</Tag>
                    <span style={{ fontSize: 12, color: '#999', marginLeft: 8 }}>
                      {new Date(msg.created_at).toLocaleString()}
                    </span>
                  </div>
                  <div style={{ marginTop: 8, whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
                    {msg.content}
                  </div>
                </div>
              </div>
            </List.Item>
          )}
        />
        {sending && (
          <div style={{ textAlign: 'center', padding: 16 }}>
            <Spin tip="思考中..." />
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div style={{
        padding: 16,
        borderTop: '1px solid #f0f0f0',
        display: 'flex',
        gap: 8,
      }}>
        <Input.TextArea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onPressEnter={(e) => {
            if (!e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder="输入消息... (Enter 发送，Shift+Enter 换行)"
          autoSize={{ minRows: 2, maxRows: 4 }}
          style={{ flex: 1 }}
          disabled={sending}
        />
        <Button type="primary" icon={<SendOutlined />} onClick={handleSend} loading={sending}>
          发送
        </Button>
      </div>

      {/* Configuration Panel */}
      {currentConversation && (
        <ConfigPanel
          conversationId={currentConversation.id}
          open={configPanelOpen}
          onClose={() => setConfigPanelOpen(false)}
          onUpdate={() => {
            fetchOne(currentConversation.id)
          }}
        />
      )}
    </div>
  )
}
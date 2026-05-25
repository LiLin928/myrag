import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Row, Col, Button, Space, Spin, message } from 'antd'
import { SaveOutlined, RocketOutlined } from '@ant-design/icons'

import { useAgentStore } from '../../stores/agentStore'
import { ConfigPanel } from '../../components/Agents/ConfigPanel'
import { ChatWindow } from '../../components/Agents/ChatWindow'
import { PublishModal } from '../../components/Agents/PublishModal'

export function AgentEditor() {
  const { id } = useParams()
  const navigate = useNavigate()
  const isNew = id === 'new'

  const {
    currentAgent,
    loading,
    saving,
    fetchAgent,
    createAgent,
    updateAgent,
    chatHistory,
    chat,
    clearChatHistory,
  } = useAgentStore()

  const [publishModalVisible, setPublishModalVisible] = useState(false)
  const [config, setConfig] = useState<any>({
    name: '',
    description: '',
    model_id: '',
    system_prompt: '',
    use_knowledge: false,
    use_tools: false,
    use_skills: false,
    knowledge_bindings: [],
    tool_bindings: [],
    skill_bindings: [],
  })

  useEffect(() => {
    if (!isNew && id) {
      fetchAgent(id)
    } else {
      clearChatHistory()
    }
  }, [id])

  useEffect(() => {
    if (currentAgent) {
      setConfig({
        name: currentAgent.name,
        description: currentAgent.description,
        model_id: currentAgent.model_id,
        system_prompt: currentAgent.system_prompt,
        use_knowledge: currentAgent.use_knowledge,
        use_tools: currentAgent.use_tools,
        use_skills: currentAgent.use_skills,
        knowledge_bindings: currentAgent.knowledge_bindings,
        tool_bindings: currentAgent.tool_bindings,
        skill_bindings: currentAgent.skill_bindings,
      })
    }
  }, [currentAgent])

  const handleSave = async () => {
    try {
      if (isNew) {
        const agent = await createAgent(config)
        message.success('创建成功')
        navigate(`/agents/${agent.id}`)
      } else {
        await updateAgent(id!, config)
        message.success('保存成功')
      }
    } catch (e: any) {
      message.error(e.message || '保存失败')
    }
  }

  const handlePublish = () => {
    setPublishModalVisible(true)
  }

  const handleChat = async (msg: string) => {
    if (!currentAgent && isNew) {
      message.warning('请先保存智能体配置')
      return
    }
    await chat(currentAgent?.id || '', msg)
  }

  if (loading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  return (
    <div style={{ height: 'calc(100vh - 64px)', padding: 16 }}>
      {/* 顶部栏 */}
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <h2>{isNew ? '新建智能体' : config.name}</h2>
        <Space>
          <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
            保存
          </Button>
          {!isNew && (
            <Button icon={<RocketOutlined />} onClick={handlePublish}>
              发布
            </Button>
          )}
        </Space>
      </div>

      {/* 主内容区 */}
      <Row gutter={16} style={{ height: 'calc(100% - 60px)' }}>
        <Col span={10}>
          <ConfigPanel
            config={config}
            onChange={setConfig}
          />
        </Col>
        <Col span={14}>
          <ChatWindow
            history={chatHistory}
            onSend={handleChat}
            sessionId={useAgentStore.getState().currentSessionId}
            sessions={useAgentStore.getState().sessions}
            onSwitchSession={(sid) => useAgentStore.getState().setCurrentSession(sid)}
          />
        </Col>
      </Row>

      <PublishModal
        visible={publishModalVisible}
        agentId={id || ''}
        onClose={() => setPublishModalVisible(false)}
      />
    </div>
  )
}
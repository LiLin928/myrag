import { useState, useEffect } from 'react'
import { Drawer, Form, Input, Select, Switch, InputNumber, Button, message, Divider, Spin } from 'antd'
import { conversationApi } from '../../api/conversations'
import { systemPromptsApi } from '../../api/systemPrompts'
import { knowledgeApi } from '../../api/knowledge'
import { toolApi } from '../../api/tools'
import { skillApi } from '../../api/skills'
import type { ConversationConfig, SystemPromptTemplate, KnowledgeBase, Tool, Skill } from '../../types/models'

interface ConfigPanelProps {
  conversationId: string
  open: boolean
  onClose: () => void
  onUpdate?: () => void
}

interface ConfigResponse {
  id: string
  mode: string
  model: string
  config: ConversationConfig | null
  workflow_id: string | null
  system_prompt_template_id: string | null
  system_prompt_template_content: string | null
  custom_system_prompt: string | null
  greeting_enabled: boolean
  greeting_content: string | null
  greeting_sent: boolean
}

interface FormValues {
  model: string
  knowledge_base_ids: string[]
  kb_config_enabled: boolean
  top_k: number
  threshold: number
  search_type: 'vector' | 'keyword' | 'hybrid'
  tools_enabled: boolean
  tool_ids: string[]
  skills_enabled: boolean
  skill_ids: string[]
  temperature: number
  max_tokens: number
  system_prompt_template_id: string | null
  custom_system_prompt: string
  greeting_enabled: boolean
  greeting_content: string
}

export function ConfigPanel({ conversationId, open, onClose, onUpdate }: ConfigPanelProps) {
  const [form] = Form.useForm<FormValues>()
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)

  // Options data
  const [templates, setTemplates] = useState<SystemPromptTemplate[]>([])
  const [knowledgeBases, setKnowledgeBases] = useState<KnowledgeBase[]>([])
  const [tools, setTools] = useState<Tool[]>([])
  const [skills, setSkills] = useState<Skill[]>([])

  // Track conversation mode
  const [mode, setMode] = useState<'model' | 'workflow'>('model')

  // Watch switches
  const kbConfigEnabled = Form.useWatch('kb_config_enabled', form)
  const toolsEnabled = Form.useWatch('tools_enabled', form)
  const skillsEnabled = Form.useWatch('skills_enabled', form)
  const greetingEnabled = Form.useWatch('greeting_enabled', form)

  // Load data when drawer opens
  useEffect(() => {
    if (open) {
      loadConfig()
      loadOptions()
    }
  }, [open, conversationId])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const response = await conversationApi.getConfig(conversationId)
      const data: ConfigResponse = response.data

      setMode(data.mode as 'model' | 'workflow')

      // Set form values
      form.setFieldsValue({
        model: data.model || 'gpt-4o-mini',
        knowledge_base_ids: data.config?.knowledge_base_ids || [],
        kb_config_enabled: !!data.config?.knowledge_base_config,
        top_k: data.config?.knowledge_base_config?.top_k || 5,
        threshold: data.config?.knowledge_base_config?.threshold || 0.7,
        search_type: data.config?.knowledge_base_config?.search_type || 'vector',
        tools_enabled: data.config?.tools_enabled || false,
        tool_ids: data.config?.tool_ids || [],
        skills_enabled: data.config?.skills_enabled || false,
        skill_ids: data.config?.skill_ids || [],
        temperature: data.config?.temperature ?? 0.7,
        max_tokens: data.config?.max_tokens || 4096,
        system_prompt_template_id: data.system_prompt_template_id,
        custom_system_prompt: data.custom_system_prompt || '',
        greeting_enabled: data.greeting_enabled,
        greeting_content: data.greeting_content || '',
      })
    } catch {
      message.error('Failed to load configuration')
    } finally {
      setLoading(false)
    }
  }

  const loadOptions = async () => {
    try {
      const [templatesRes, kbRes, toolsRes, skillsRes] = await Promise.all([
        systemPromptsApi.list(),
        knowledgeApi.list(),
        toolApi.available(),
        skillApi.list(),
      ])

      setTemplates(templatesRes.data)
      setKnowledgeBases(kbRes.data.items || [])
      setTools(toolsRes.data)
      setSkills(skillsRes.data)
    } catch {
      // Ignore errors for options loading
    }
  }

  const handleSave = async () => {
    try {
      await form.validateFields()
      setSaving(true)

      const values = form.getFieldsValue()

      // Build config
      const config: ConversationConfig = {
        knowledge_base_ids: values.knowledge_base_ids || [],
        knowledge_base_config: values.kb_config_enabled
          ? {
              top_k: values.top_k || 5,
              threshold: values.threshold || 0.7,
              search_type: values.search_type || 'vector',
            }
          : null,
        tools_enabled: values.tools_enabled || false,
        tool_ids: values.tools_enabled ? (values.tool_ids || []) : [],
        skills_enabled: values.skills_enabled || false,
        skill_ids: values.skills_enabled ? (values.skill_ids || []) : [],
        temperature: values.temperature ?? 0.7,
        max_tokens: values.max_tokens || 4096,
      }

      await conversationApi.updateConfig(conversationId, {
        config,
        system_prompt_template_id: values.system_prompt_template_id || undefined,
        custom_system_prompt: values.custom_system_prompt || undefined,
        greeting_enabled: values.greeting_enabled,
        greeting_content: values.greeting_enabled ? values.greeting_content : undefined,
      })

      message.success('Configuration updated')
      onUpdate?.()
      onClose()
    } catch {
      message.error('Failed to save configuration')
    } finally {
      setSaving(false)
    }
  }

  const handleClose = () => {
    form.resetFields()
    onClose()
  }

  return (
    <Drawer
      title="Conversation Configuration"
      placement="right"
      width={520}
      open={open}
      onClose={handleClose}
      destroyOnClose
      footer={
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
          <Button onClick={handleClose}>Cancel</Button>
          <Button type="primary" loading={saving} onClick={handleSave}>
            Save
          </Button>
        </div>
      }
    >
      {loading ? (
        <div style={{ display: 'flex', justifyContent: 'center', padding: 40 }}>
          <Spin />
        </div>
      ) : (
        <Form
          form={form}
          layout="vertical"
          initialValues={{
            model: 'gpt-4o-mini',
            knowledge_base_ids: [],
            kb_config_enabled: false,
            top_k: 5,
            threshold: 0.7,
            search_type: 'vector',
            tools_enabled: false,
            tool_ids: [],
            skills_enabled: false,
            skill_ids: [],
            temperature: 0.7,
            max_tokens: 4096,
            system_prompt_template_id: null,
            custom_system_prompt: '',
            greeting_enabled: false,
            greeting_content: '',
          }}
        >
          {/* Model Section */}
          <Divider orientation="left">Model Settings</Divider>

          <Form.Item name="model" label="Model" rules={[{ required: mode === 'model', message: 'Please select a model' }]}>
            <Select
              options={[
                { value: 'gpt-4o-mini', label: 'GPT-4o Mini' },
                { value: 'gpt-4o', label: 'GPT-4o' },
                { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
                { value: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo' },
                { value: 'claude-3-opus', label: 'Claude 3 Opus' },
                { value: 'claude-3-sonnet', label: 'Claude 3 Sonnet' },
                { value: 'claude-3-haiku', label: 'Claude 3 Haiku' },
                { value: 'claude-sonnet-4-6', label: 'Claude Sonnet 4.6' },
              ]}
            />
          </Form.Item>

          <Form.Item name="temperature" label="Temperature">
            <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="max_tokens" label="Max Tokens">
            <InputNumber min={256} max={32768} step={256} style={{ width: '100%' }} />
          </Form.Item>

          {/* Knowledge Base Section */}
          <Divider orientation="left">Knowledge Base</Divider>

          <Form.Item name="knowledge_base_ids" label="Knowledge Bases">
            <Select
              mode="multiple"
              placeholder="Select knowledge bases"
              options={knowledgeBases.map((kb) => ({
                value: kb.id,
                label: kb.name,
              }))}
              allowClear
            />
          </Form.Item>

          <Form.Item name="kb_config_enabled" label="Custom KB Retrieval Config" valuePropName="checked">
            <Switch checkedChildren="On" unCheckedChildren="Off" />
          </Form.Item>

          {kbConfigEnabled && (
            <>
              <Form.Item name="search_type" label="Search Type">
                <Select
                  options={[
                    { value: 'vector', label: 'Vector Search' },
                    { value: 'keyword', label: 'Keyword Search' },
                    { value: 'hybrid', label: 'Hybrid Search' },
                  ]}
                />
              </Form.Item>
              <Form.Item name="top_k" label="Top K">
                <InputNumber min={1} max={20} style={{ width: '100%' }} />
              </Form.Item>
              <Form.Item name="threshold" label="Similarity Threshold">
                <InputNumber min={0} max={1} step={0.1} style={{ width: '100%' }} />
              </Form.Item>
            </>
          )}

          {/* Tools Section */}
          <Divider orientation="left">Tools & Skills</Divider>

          <Form.Item name="tools_enabled" label="Enable Tools" valuePropName="checked">
            <Switch checkedChildren="On" unCheckedChildren="Off" />
          </Form.Item>

          {toolsEnabled && (
            <Form.Item name="tool_ids" label="Available Tools">
              <Select
                mode="multiple"
                placeholder="Select tools"
                options={tools
                  .filter((t) => t.is_enabled)
                  .map((t) => ({
                    value: t.id,
                    label: t.name,
                  }))}
                allowClear
              />
            </Form.Item>
          )}

          <Form.Item name="skills_enabled" label="Enable Skills" valuePropName="checked">
            <Switch checkedChildren="On" unCheckedChildren="Off" />
          </Form.Item>

          {skillsEnabled && (
            <Form.Item name="skill_ids" label="Available Skills">
              <Select
                mode="multiple"
                placeholder="Select skills"
                options={skills
                  .filter((s) => s.status === 'published')
                  .map((s) => ({
                    value: s.id,
                    label: s.display_name || s.internal_name,
                  }))}
                allowClear
              />
            </Form.Item>
          )}

          {/* System Prompt Section */}
          <Divider orientation="left">System Prompt</Divider>

          <Form.Item name="system_prompt_template_id" label="System Prompt Template">
            <Select
              placeholder="Select a template"
              options={templates.map((t) => ({
                value: t.id,
                label: t.name,
              }))}
              allowClear
            />
          </Form.Item>

          <Form.Item name="custom_system_prompt" label="Custom System Prompt">
            <Input.TextArea
              rows={4}
              placeholder="Enter custom system prompt that overrides the template"
            />
          </Form.Item>

          {/* Greeting Section */}
          <Divider orientation="left">Greeting</Divider>

          <Form.Item name="greeting_enabled" label="Enable Greeting" valuePropName="checked">
            <Switch checkedChildren="On" unCheckedChildren="Off" />
          </Form.Item>

          {greetingEnabled && (
            <Form.Item name="greeting_content" label="Greeting Content">
              <Input.TextArea
                rows={3}
                placeholder="Enter greeting message to send automatically when conversation starts"
              />
            </Form.Item>
          )}
        </Form>
      )}
    </Drawer>
  )
}
import { useState } from 'react'
import { Card, Form, Input, Button, Space, message, Spin } from 'antd'
import { RobotOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import Editor from '@monaco-editor/react'
import { useSkillStore } from '../../stores/skillStore'

export function SkillGenerate() {
  const navigate = useNavigate()
  const { generate, create, generatedCode, generatedName, generatedDescription, generating, clearGenerated } = useSkillStore()
  const [form] = Form.useForm()
  const [editedCode, setEditedCode] = useState('')
  const [saving, setSaving] = useState(false)

  const handleGenerate = async () => {
    try {
      const values = await form.validateFields()
      const result = await generate({
        requirement: values.requirement,
        skill_name: values.skill_name,
      })
      setEditedCode(result.code)
      message.success('生成成功')
    } catch (error: any) {
      message.error(error.message || '生成失败')
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      const values = form.getFieldsValue()
      await create({
        internal_name: generatedName || values.skill_name || 'generated_skill',
        display_name: generatedName || values.skill_name || 'Generated Skill',
        description: generatedDescription || values.requirement,
      })
      message.success('保存成功')
      clearGenerated()
      navigate('/skills')
    } catch {
      message.error('保存失败')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card title="AI 生成技能">
      <Form form={form} layout="vertical">
        <Form.Item name="skill_name" label="技能名称（可选）">
          <Input placeholder="留空则自动生成" />
        </Form.Item>
        <Form.Item name="requirement" label="需求描述" rules={[{ required: true, message: '请输入需求描述' }]}>
          <Input.TextArea rows={4} placeholder="描述你想要这个技能做什么..." />
        </Form.Item>
        <Form.Item>
          <Button type="primary" icon={<RobotOutlined />} onClick={handleGenerate} loading={generating}>
            生成代码
          </Button>
        </Form.Item>
      </Form>
      {generating && <Spin tip="正在生成..." style={{ display: 'block', margin: '50px auto' }} />}
      {generatedCode && (
        <Card title="生成的代码" style={{ marginTop: 16 }}>
          <div style={{ marginBottom: 8, color: '#666' }}>
            名称: <b>{generatedName}</b>
          </div>
          <Editor
            height="300px"
            language="python"
            value={editedCode || generatedCode}
            onChange={(value) => setEditedCode(value || '')}
            options={{ minimap: { enabled: false }, fontSize: 14 }}
          />
          <Space style={{ marginTop: 16 }}>
            <Button onClick={() => { clearGenerated(); setEditedCode('') }}>重新生成</Button>
            <Button onClick={() => navigate('/skills')}>取消</Button>
            <Button type="primary" onClick={handleSave} loading={saving}>
              保存技能
            </Button>
          </Space>
        </Card>
      )}
    </Card>
  )
}
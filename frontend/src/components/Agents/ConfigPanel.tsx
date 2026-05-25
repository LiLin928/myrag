import { Form, Input, Select, Switch, Collapse, InputNumber } from 'antd'
import { KnowledgeConfig } from './KnowledgeConfig'
import { ToolConfig } from './ToolConfig'
import { SkillConfig } from './SkillConfig'

interface ConfigPanelProps {
  config: any
  onChange: (config: any) => void
}

export function ConfigPanel({ config, onChange }: ConfigPanelProps) {
  const handleChange = (field: string, value: any) => {
    onChange({ ...config, [field]: value })
  }

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: 16, background: '#fff', borderRadius: 8 }}>
      <Form layout="vertical">
        {/* 基本信息 */}
        <Form.Item label="名称" required>
          <Input
            value={config.name}
            onChange={(e) => handleChange('name', e.target.value)}
            placeholder="智能体名称"
          />
        </Form.Item>

        <Form.Item label="描述">
          <Input.TextArea
            value={config.description}
            onChange={(e) => handleChange('description', e.target.value)}
            placeholder="智能体描述"
            rows={2}
          />
        </Form.Item>

        <Form.Item label="模型" required>
          <Select
            value={config.model_id}
            onChange={(value) => handleChange('model_id', value)}
            placeholder="选择模型"
            options={[
              { value: 'model-1', label: 'GPT-4' },
              { value: 'model-2', label: 'GPT-3.5' },
              // TODO: 从 API 加载模型列表
            ]}
          />
        </Form.Item>

        <Form.Item label="系统提示词">
          <Input.TextArea
            value={config.system_prompt}
            onChange={(e) => handleChange('system_prompt', e.target.value)}
            placeholder="智能体的系统提示词"
            rows={4}
          />
        </Form.Item>

        {/* 能力开关 */}
        <Form.Item label="使用知识库">
          <Switch
            checked={config.use_knowledge}
            onChange={(checked) => handleChange('use_knowledge', checked)}
          />
          {config.use_knowledge && (
            <KnowledgeConfig
              bindings={config.knowledge_bindings}
              onChange={(bindings) => handleChange('knowledge_bindings', bindings)}
            />
          )}
        </Form.Item>

        <Form.Item label="使用工具">
          <Switch
            checked={config.use_tools}
            onChange={(checked) => handleChange('use_tools', checked)}
          />
          {config.use_tools && (
            <ToolConfig
              bindings={config.tool_bindings}
              onChange={(bindings) => handleChange('tool_bindings', bindings)}
            />
          )}
        </Form.Item>

        <Form.Item label="使用 Skills">
          <Switch
            checked={config.use_skills}
            onChange={(checked) => handleChange('use_skills', checked)}
          />
          {config.use_skills && (
            <SkillConfig
              bindings={config.skill_bindings}
              onChange={(bindings) => handleChange('skill_bindings', bindings)}
            />
          )}
        </Form.Item>

        {/* 高级设置 */}
        <Collapse>
          <Collapse.Panel header="高级设置" key="advanced">
            <Form.Item label="检索策略">
              <Select
                value={config.search_type || 'hybrid'}
                onChange={(value) => handleChange('search_type', value)}
                options={[
                  { value: 'hybrid', label: '混合检索' },
                  { value: 'semantic', label: '语义检索' },
                  { value: 'keyword', label: '关键词检索' },
                ]}
              />
            </Form.Item>

            <Form.Item label="Top K">
              <InputNumber
                value={config.top_k || 5}
                onChange={(value) => handleChange('top_k', value)}
                min={1}
                max={20}
              />
            </Form.Item>

            <Form.Item label="分数阈值">
              <InputNumber
                value={config.score_threshold || 0.5}
                onChange={(value) => handleChange('score_threshold', value)}
                min={0}
                max={1}
                step={0.1}
              />
            </Form.Item>
          </Collapse.Panel>
        </Collapse>
      </Form>
    </div>
  )
}
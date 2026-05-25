import { Select } from 'antd'

interface SkillConfigProps {
  bindings: string[]
  onChange: (bindings: string[]) => void
}

export function SkillConfig({ bindings, onChange }: SkillConfigProps) {
  const handleChange = (value: string[]) => {
    onChange(value)
  }

  return (
    <div style={{ marginTop: 8 }}>
      <Select
        mode="multiple"
        value={bindings}
        onChange={handleChange}
        placeholder="选择 Skills"
        style={{ width: '100%' }}
        options={[
          { value: 'skill-1', label: 'Skill 1' },
          { value: 'skill-2', label: 'Skill 2' },
          // TODO: 从 API 加载 Skills 列表
        ]}
      />
    </div>
  )
}
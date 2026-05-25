import { Select } from 'antd'

interface ToolConfigProps {
  bindings: string[]
  onChange: (bindings: string[]) => void
}

export function ToolConfig({ bindings, onChange }: ToolConfigProps) {
  const handleChange = (value: string[]) => {
    onChange(value)
  }

  return (
    <div style={{ marginTop: 8 }}>
      <Select
        mode="multiple"
        value={bindings}
        onChange={handleChange}
        placeholder="选择工具"
        style={{ width: '100%' }}
        options={[
          { value: 'search', label: '搜索' },
          { value: 'calculator', label: '计算器' },
          { value: 'weather', label: '天气查询' },
          // TODO: 从 API 加载工具列表
        ]}
      />
    </div>
  )
}
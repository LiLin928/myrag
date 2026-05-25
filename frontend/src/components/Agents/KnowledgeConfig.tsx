import { Select, InputNumber } from 'antd'

interface KnowledgeConfigProps {
  bindings: any[]
  onChange: (bindings: any[]) => void
}

export function KnowledgeConfig({ bindings, onChange }: KnowledgeConfigProps) {
  const handleAdd = () => {
    onChange([
      ...bindings,
      {
        knowledge_base_id: '',
        search_type: 'hybrid',
        top_k: 5,
        score_threshold: 0.5,
        priority: bindings.length + 1,
      },
    ])
  }

  const handleRemove = (index: number) => {
    const newBindings = bindings.filter((_, i) => i !== index)
    onChange(newBindings)
  }

  const handleChange = (index: number, field: string, value: any) => {
    const newBindings = [...bindings]
    newBindings[index] = { ...newBindings[index], [field]: value }
    onChange(newBindings)
  }

  return (
    <div style={{ marginTop: 8 }}>
      {bindings.map((binding, index) => (
        <div key={index} style={{ marginBottom: 12, padding: 8, border: '1px solid #d9d9d9', borderRadius: 4 }}>
          <div style={{ marginBottom: 8 }}>
            <Select
              value={binding.knowledge_base_id}
              onChange={(value) => handleChange(index, 'knowledge_base_id', value)}
              placeholder="选择知识库"
              style={{ width: '100%' }}
              options={[
                { value: 'kb-1', label: '知识库 1' },
                { value: 'kb-2', label: '知识库 2' },
                // TODO: 从 API 加载知识库列表
              ]}
            />
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <Select
              value={binding.search_type}
              onChange={(value) => handleChange(index, 'search_type', value)}
              placeholder="检索策略"
              style={{ width: 120 }}
              options={[
                { value: 'hybrid', label: '混合' },
                { value: 'semantic', label: '语义' },
                { value: 'keyword', label: '关键词' },
              ]}
            />

            <InputNumber
              value={binding.top_k}
              onChange={(value) => handleChange(index, 'top_k', value)}
              placeholder="Top K"
              min={1}
              max={20}
              style={{ width: 80 }}
            />

            <InputNumber
              value={binding.score_threshold}
              onChange={(value) => handleChange(index, 'score_threshold', value)}
              placeholder="阈值"
              min={0}
              max={1}
              step={0.1}
              style={{ width: 80 }}
            />
          </div>

          <button onClick={() => handleRemove(index)} style={{ marginTop: 8 }}>
            删除
          </button>
        </div>
      ))}

      <button onClick={handleAdd}>添加知识库</button>
    </div>
  )
}
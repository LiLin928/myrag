export interface User {
  id: string
  email: string
  username: string
  role: string
  created_at: string
}

export interface KnowledgeBase {
  id: string
  name: string
  description: string

  // 分块配置
  chunk_strategy: 'auto' | 'structured' | 'semantic' | 'fixed'
  chunk_size: number
  chunk_overlap: number

  // 向量配置
  embedding_model: string
  vector_dimension: number

  // Rerank 配置
  rerank_model: string | null
  rerank_enabled: boolean
  rerank_top_n: number

  // 检索配置
  retrieval_method: 'vector' | 'keyword' | 'hybrid'
  retrieval_top_k: number
  similarity_threshold: number
  vector_weight: number
  keyword_weight: number

  // 统计
  document_count: number
  created_at: string
}

export interface Document {
  id: string
  filename: string
  file_type: string
  file_size: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  knowledge_base_id: string
  created_at: string
  job?: { job_id: string; status?: string }
}

export interface DocumentChunk {
  id: string
  content: string
  chunk_index: number
  metadata: Record<string, any>
}

export interface Skill {
  id: string
  internal_name: string
  display_name: string
  description: string
  is_public: boolean
  entry_command: string
  working_directory?: string
  version: string
  status: 'draft' | 'published' | 'archived'
  generated_by_llm: boolean
  execution_count: number
  created_at: string
  files?: SkillFile[]
  // 向后兼容
  name?: string
  code?: string
}

export interface SkillFile {
  id: string
  skill_id: string
  file_path: string
  file_type: string
  file_size: number
  content_hash: string
  is_entry: boolean
  created_at: string
  updated_at: string
}

export interface SkillVersion {
  id: string
  skill_id: string
  version_number: number
  files_manifest: Array<{ path: string; hash: string; size: number }>
  change_summary: string
  created_at: string
  created_by: string
}

export interface Workflow {
  id: string
  name: string
  description: string
  definition: WorkflowDefinition
  status: 'draft' | 'published' | 'archived'
  created_at: string
}

export interface WorkflowDefinition {
  nodes: WorkflowNode[]
  edges: WorkflowEdge[]
}

export interface WorkflowNode {
  id: string
  type: string
  position: { x: number; y: number }
  data: Record<string, any>
}

export interface WorkflowEdge {
  id: string
  source: string
  target: string
  condition?: string
}

export interface SystemPromptTemplate {
  id: string
  user_id: string
  name: string
  description: string | null
  content: string
  category: string | null
  is_public: boolean
  is_default: boolean
  created_at: string
  updated_at: string
}

export interface KnowledgeBaseConfig {
  top_k: number
  threshold: number
  search_type: 'vector' | 'keyword' | 'hybrid'
}

export interface ConversationConfig {
  knowledge_base_ids: string[]
  knowledge_base_config: KnowledgeBaseConfig | null
  tools_enabled: boolean
  tool_ids: string[]
  skills_enabled: boolean
  skill_ids: string[]
  temperature: number
  max_tokens: number
}

export interface Conversation {
  id: string
  thread_id: string
  title: string
  model: string
  mode: 'model' | 'workflow'
  config: ConversationConfig | null
  workflow_id: string | null
  system_prompt_template_id: string | null
  custom_system_prompt: string | null
  greeting_enabled: boolean
  greeting_content: string | null
  greeting_sent: boolean
  message_count: number
  total_tokens: number
  created_at: string
  updated_at: string
}

export interface CreateConversationRequest {
  title?: string
  mode: 'model' | 'workflow'
  model?: string
  config?: ConversationConfig
  workflow_id?: string
  system_prompt_template_id?: string
  custom_system_prompt?: string
  greeting_enabled?: boolean
  greeting_content?: string
}

export interface ConfigUpdateRequest {
  config?: ConversationConfig
  system_prompt_template_id?: string
  custom_system_prompt?: string
  greeting_enabled?: boolean
  greeting_content?: string
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'tool' | 'system'
  content: string
  tool_calls?: any[]
  tokens: number
  created_at: string
}

export interface Tool {
  id: string
  name: string
  description: string
  tool_type: 'http' | 'mcp'
  config: Record<string, any>
  input_schema: Record<string, any>
  output_schema: Record<string, any>
  is_public: boolean
  is_enabled: boolean
  owner_id: string | null
  created_at: string
  updated_at: string
}

export interface HttpToolConfig {
  url: string
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  headers?: Record<string, string>
  body_template?: Record<string, any>
  auth?: {
    type: 'none' | 'api_key' | 'bearer'
    key?: string
    header?: string
    prefix?: string
    token?: string
  }
  timeout?: number
  retry?: {
    max_retries: number
    delay: number
    backoff: 'constant' | 'linear' | 'exponential'
  }
  output_mapping?: Record<string, string>
}

export interface CreateToolRequest {
  name: string
  description?: string
  config: HttpToolConfig
  input_schema?: Record<string, any>
  is_public?: boolean
}

export interface CreateKnowledgeBaseRequest {
  name: string
  description?: string

  // 分块配置
  chunk_strategy?: 'auto' | 'structured' | 'semantic' | 'fixed'
  chunk_size?: number
  chunk_overlap?: number

  // 向量配置
  embedding_model?: string

  // Rerank 配置
  rerank_model?: string
  rerank_enabled?: boolean
  rerank_top_n?: number

  // 检索配置
  retrieval_method?: 'vector' | 'keyword' | 'hybrid'
  retrieval_top_k?: number
  similarity_threshold?: number
  vector_weight?: number
  keyword_weight?: number
}

// ========== 文档管理 ==========

export interface KnowledgeDocument {
  id: string
  filename: string
  file_type: string
  file_size: number
  status: 'pending' | 'parsing' | 'parsed' | 'indexing' | 'indexed' | 'vectorizing' | 'vectorized' | 'completed' | 'compiled' | 'failed'
  processing_progress: number
  processing_message: string | null
  chunk_count: number
  vectorized_count: number
  doc_metadata?: Record<string, string>
  created_at: string
}

export interface ParseResponse {
  job_id: string
  document_id: string
  status: string
  websocket_channel: string
}

// ========== 元数据相关类型 ==========

export interface MetadataResponse {
  inherited: Record<string, string>
  own: Record<string, string>
  merged: Record<string, string>
}

export interface MetadataFieldDefinition {
  name: string
  display_name: string
  readonly: boolean
}

export interface MetadataFieldsResponse {
  fields: MetadataFieldDefinition[]
}

export interface MetadataUpdateRequest {
  metadata: Record<string, string>
}

export interface MetadataPatchRequest {
  name: string
  value: string
}

// 新增分块详情类型（含元数据）
export interface ChunkDetail {
  id: string
  document_id: string
  clause_id: string
  clause_type: string | null
  clause_title: string | null
  content: string
  page_number: number
  content_length: number
  metadata: MetadataResponse
  has_embedding: boolean
  created_at: string
}

export interface ChunkListResponse {
  total: number
  page: number
  page_size: number
  chunks: ChunkDetail[]
}
/**
 * Workflow Node Configuration Types
 * Defines configuration interfaces for all workflow node types
 */

// ============================================================================
// Common Types
// ============================================================================

/**
 * Base configuration shared by all node types
 */
export interface CommonNodeConfig {
  /** Node display name */
  name: string
  /** Node description */
  description?: string
  /** Execution timeout in seconds */
  timeout?: number
  /** Number of retry attempts on failure */
  retry_count?: number
  /** Delay between retries in seconds */
  retry_delay?: number
  /** Error handling strategy */
  error_handling?: 'fail' | 'continue' | 'fallback'
}

/**
 * Output variable mapping configuration
 */
export interface OutputVariableMapping {
  /** Variable name */
  name: string
  /** JSON path to extract value from output */
  path?: string
}

/**
 * Input variable reference
 */
export interface InputVariableMapping {
  /** Variable name */
  name: string
  /** Source variable path (e.g., "nodes.start.output.query") */
  source?: string
  /** Default value if not found */
  default?: any
}

// ============================================================================
// Node-Specific Configurations
// ============================================================================

/**
 * LLM Node Configuration
 * Invokes a language model with prompts
 */
export interface LLMNodeConfig extends CommonNodeConfig {
  /** Model identifier (e.g., "gpt-4", "claude-3-sonnet") */
  model: string
  /** Prompt template with variable interpolation */
  prompt_template: string
  /** System prompt for the model */
  system_prompt?: string
  /** Temperature for response randomness (0-1) */
  temperature?: number
  /** Maximum tokens in response */
  max_tokens?: number
  /** Output variable mappings */
  output_variables?: OutputVariableMapping[]
}

/**
 * RAG Node Configuration
 * Retrieves context from knowledge base
 */
export interface RAGNodeConfig extends CommonNodeConfig {
  /** Knowledge base ID to query */
  knowledge_base_id: string
  /** Variable containing the query text */
  query_variable: string
  /** Number of top results to return */
  top_k?: number
  /** Minimum similarity score threshold */
  score_threshold?: number
  /** Search type: similarity, hybrid, or keyword */
  search_type?: 'similarity' | 'hybrid' | 'keyword'
  /** Rerank results for better relevance */
  rerank?: boolean
  /** Output variable mappings */
  output_variables?: OutputVariableMapping[]
}

/**
 * Code Node Configuration
 * Executes custom code in a sandbox
 */
export interface CodeNodeConfig extends CommonNodeConfig {
  /** Programming language */
  language: 'python' | 'javascript' | 'typescript'
  /** Code to execute */
  code: string
  /** Input variable references */
  input_variables?: InputVariableMapping[]
  /** Output variable mappings */
  output_variables?: OutputVariableMapping[]
  /** Sandbox execution configuration */
  sandbox_config?: SandboxConfig
}

/**
 * Sandbox configuration for code execution
 */
export interface SandboxConfig {
  /** Maximum execution time in seconds */
  timeout?: number
  /** Maximum memory in MB */
  memory_limit?: number
  /** Allow network access */
  network_access?: boolean
  /** Allowed file system paths */
  allowed_paths?: string[]
  /** Environment variables */
  env_vars?: Record<string, string>
}

/**
 * HTTP Node Configuration
 * Makes HTTP requests to external APIs
 */
export interface HTTPNodeConfig extends CommonNodeConfig {
  /** Request URL (can include variable interpolation) */
  url: string
  /** HTTP method */
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  /** Request headers */
  headers?: Record<string, string>
  /** Request body (for POST/PUT/PATCH) */
  body?: string | Record<string, any>
  /** Authentication configuration */
  auth?: HTTPAuthConfig
  /** Request timeout in seconds */
  timeout_seconds?: number
  /** Output variable mappings */
  output_variables?: OutputVariableMapping[]
}

/**
 * HTTP Authentication Configuration
 */
export interface HTTPAuthConfig {
  /** Authentication type */
  type: 'none' | 'basic' | 'bearer' | 'api_key' | 'oauth2'
  /** Credentials for basic auth */
  basic?: {
    username: string
    password: string
  }
  /** Token for bearer auth */
  bearer_token?: string
  /** API key configuration */
  api_key?: {
    key: string
    value: string
    location: 'header' | 'query'
  }
  /** OAuth2 configuration */
  oauth2?: {
    client_id: string
    client_secret: string
    token_url: string
    scopes?: string[]
  }
}

/**
 * Condition Node Configuration
 * Branches workflow based on conditions
 */
export interface ConditionNodeConfig extends CommonNodeConfig {
  /** Array of condition branches */
  conditions: ConditionBranch[]
  /** Default branch if no conditions match */
  default_branch?: string
}

/**
 * Condition branch definition
 */
export interface ConditionBranch {
  /** Branch identifier */
  id: string
  /** Branch label */
  label?: string
  /** Condition expression */
  condition: ConditionExpression
  /** Target node ID for this branch */
  target_node_id?: string
}

/**
 * Condition expression
 */
export interface ConditionExpression {
  /** Expression type */
  type: 'comparison' | 'logical' | 'variable'
  /** Comparison operator (for comparison type) */
  operator?: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'contains' | 'starts_with' | 'ends_with' | 'exists' | 'not_exists'
  /** Left operand (variable path or value) */
  left?: string | number | boolean
  /** Right operand (variable path or value) */
  right?: string | number | boolean
  /** Logical operator (for logical type) */
  logical_operator?: 'and' | 'or' | 'not'
  /** Nested conditions (for logical type) */
  conditions?: ConditionExpression[]
  /** Variable path (for variable type) */
  variable?: string
}

/**
 * Loop Node Configuration
 * Iterates over array or executes condition-based loops
 */
export interface LoopNodeConfig extends CommonNodeConfig {
  /** Type of loop */
  loop_type: 'for_each' | 'while' | 'for'
  /** Input array variable (for for_each) */
  input_array?: string
  /** Variable name for current item */
  loop_variable?: string
  /** Index variable name */
  index_variable?: string
  /** While condition (for while loops) */
  while_condition?: ConditionExpression
  /** Start value (for for loops) */
  start?: number
  /** End value (for for loops) */
  end?: number
  /** Step value (for for loops) */
  step?: number
  /** Maximum iterations to prevent infinite loops */
  max_iterations?: number
  /** Sub-node IDs executed in each iteration */
  sub_nodes?: string[]
  /** How to collect outputs */
  output_type?: 'array' | 'last' | 'concat'
  /** Output variable mappings */
  output_variables?: OutputVariableMapping[]
}

/**
 * Human Node Configuration
 * Pauses execution for human interaction
 */
export interface HumanNodeConfig extends CommonNodeConfig {
  /** Title shown to the human reviewer */
  title: string
  /** Description of what action is needed */
  description?: string
  /** Display configuration for inputs */
  input_display?: InputDisplayConfig[]
  /** Available action options */
  action_options?: ActionOption[]
  /** Input fields to collect */
  input_fields?: InputFieldConfig[]
  /** Timeout in hours before auto-action */
  timeout_hours?: number
  /** Action to take on timeout */
  timeout_action?: 'approve' | 'reject' | 'notify'
  /** Users or groups to notify */
  assignees?: string[]
  /** Output variable mappings */
  output_variables?: OutputVariableMapping[]
}

/**
 * Input display configuration
 */
export interface InputDisplayConfig {
  /** Variable name to display */
  variable: string
  /** Display label */
  label?: string
  /** Display format */
  format?: 'text' | 'markdown' | 'json' | 'code'
  /** Whether to show in summary */
  show_in_summary?: boolean
}

/**
 * Action option for human node
 */
export interface ActionOption {
  /** Action identifier */
  id: string
  /** Display label */
  label: string
  /** Action description */
  description?: string
  /** Style variant */
  variant?: 'primary' | 'secondary' | 'danger' | 'success'
  /** Whether this is the default action */
  default?: boolean
}

/**
 * Input field configuration for human node
 */
export interface InputFieldConfig {
  /** Field identifier */
  id: string
  /** Field label */
  label: string
  /** Input type */
  type: 'text' | 'textarea' | 'number' | 'select' | 'checkbox' | 'radio' | 'file'
  /** Whether the field is required */
  required?: boolean
  /** Default value */
  default?: any
  /** Placeholder text */
  placeholder?: string
  /** Options for select/radio types */
  options?: { label: string; value: any }[]
  /** Validation rules */
  validation?: ValidationRule[]
}

/**
 * Validation rule for input fields
 */
export interface ValidationRule {
  /** Rule type */
  type: 'required' | 'min_length' | 'max_length' | 'pattern' | 'min' | 'max' | 'email' | 'url'
  /** Rule value (e.g., pattern regex, min/max number) */
  value?: any
  /** Custom error message */
  message?: string
}

/**
 * Tool Node Configuration
 * Executes a registered tool
 */
export interface ToolNodeConfig extends CommonNodeConfig {
  /** Tool ID to execute */
  tool_id: string
  /** Tool name for display */
  tool_name?: string
  /** Input variable references */
  input_variables?: InputVariableMapping[]
  /** Output variable mappings */
  output_variables?: OutputVariableMapping[]
}

/**
 * Start Node Configuration
 * Entry point for workflow
 */
export interface StartNodeConfig extends CommonNodeConfig {
  /** Input variables expected by the workflow */
  input_variables: InputVariableDefinition[]
  /** Whether to validate inputs on start */
  validate_inputs?: boolean
}

/**
 * Input variable definition
 */
export interface InputVariableDefinition {
  /** Variable name */
  name: string
  /** Display label */
  label?: string
  /** Data type */
  type: 'string' | 'number' | 'boolean' | 'object' | 'array' | 'file'
  /** Whether this input is required */
  required?: boolean
  /** Default value */
  default?: any
  /** Description */
  description?: string
  /** Validation rules */
  validation?: ValidationRule[]
}

/**
 * End Node Configuration
 * Exit point for workflow
 */
export interface EndNodeConfig extends CommonNodeConfig {
  /** Output variables from the workflow */
  output_variables: OutputVariableDefinition[]
  /** Whether to save execution history */
  save_history?: boolean
  /** Whether to notify on completion */
  notify_on_complete?: boolean
}

/**
 * Output variable definition
 */
export interface OutputVariableDefinition {
  /** Variable name */
  name: string
  /** Display label */
  label?: string
  /** Source variable path */
  source: string
  /** Description */
  description?: string
}

// ============================================================================
// Node Type Mapping
// ============================================================================

/**
 * Map of node types to their configuration types
 */
export interface NodeConfigMap {
  start: StartNodeConfig
  end: EndNodeConfig
  llm: LLMNodeConfig
  rag: RAGNodeConfig
  code: CodeNodeConfig
  http: HTTPNodeConfig
  condition: ConditionNodeConfig
  loop: LoopNodeConfig
  human: HumanNodeConfig
  tool: ToolNodeConfig
}

/**
 * All possible node configuration types
 */
export type NodeConfig =
  | StartNodeConfig
  | EndNodeConfig
  | LLMNodeConfig
  | RAGNodeConfig
  | CodeNodeConfig
  | HTTPNodeConfig
  | ConditionNodeConfig
  | LoopNodeConfig
  | HumanNodeConfig
  | ToolNodeConfig

/**
 * Get the configuration type for a specific node type
 */
export type GetNodeConfig<T extends keyof NodeConfigMap> = NodeConfigMap[T]

// ============================================================================
// Helper Types
// ============================================================================

/**
 * Node position on the canvas
 */
export interface NodePosition {
  x: number
  y: number
}

/**
 * Full node definition with configuration
 */
export interface WorkflowNodeWithConfig<T extends keyof NodeConfigMap = keyof NodeConfigMap> {
  id: string
  type: T
  position: NodePosition
  config: NodeConfigMap[T]
}

/**
 * Node connection definition
 */
export interface NodeConnection {
  /** Source node ID */
  source: string
  /** Target node ID */
  target: string
  /** Source output handle */
  source_handle?: string
  /** Target input handle */
  target_handle?: string
  /** Condition for conditional connections */
  condition?: ConditionExpression
  /** Connection label */
  label?: string
}

/**
 * Variable reference in workflow
 */
export interface WorkflowVariable {
  /** Variable ID */
  id: string
  /** Variable name */
  name: string
  /** Source node ID */
  source_node: string
  /** Data type */
  type: string
  /** Variable path (for nested access) */
  path?: string
}

/**
 * Execution status for a node
 */
export type NodeExecutionStatus =
  | 'pending'
  | 'running'
  | 'completed'
  | 'failed'
  | 'skipped'
  | 'waiting'

/**
 * Node execution result
 */
export interface NodeExecutionResult {
  /** Node ID */
  node_id: string
  /** Execution status */
  status: NodeExecutionStatus
  /** Output variables */
  output?: Record<string, any>
  /** Error message if failed */
  error?: string
  /** Execution start time */
  started_at?: string
  /** Execution end time */
  ended_at?: string
  /** Duration in milliseconds */
  duration_ms?: number
  /** Retry count */
  retry_count?: number
}
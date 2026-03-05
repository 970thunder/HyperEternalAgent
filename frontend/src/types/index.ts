// Project types
export interface Project {
  id: string
  name: string
  description: string
  status: ProjectStatus
  created_at: string
  updated_at: string
  messages: Message[]
  files: ProjectFile[]
  tasks: Task[]
}

export type ProjectStatus = 'idle' | 'running' | 'paused' | 'completed' | 'error'

// Message types
export interface Message {
  id: string
  project_id: string
  role: MessageRole
  content: string
  type: MessageType
  metadata?: MessageMetadata
  created_at: string
}

export type MessageRole = 'user' | 'assistant' | 'system' | 'agent'
export type MessageType = 'text' | 'code' | 'error' | 'status' | 'action' | 'file' | 'command'

export interface MessageMetadata {
  agent_name?: string
  agent_type?: string
  task_id?: string
  file_path?: string
  command?: string
  exit_code?: number
  duration?: number
  tokens_used?: number
  progress?: number
}

// File types
export interface ProjectFile {
  id: string
  project_id: string
  path: string
  name: string
  type: FileType
  content?: string
  size: number
  created_at: string
  modified_at: string
}

export type FileType = 'file' | 'directory'

// Task types
export interface Task {
  id: string
  project_id: string
  name: string
  description: string
  status: TaskStatus
  priority: number
  dependencies: string[]
  result?: TaskResult
  created_at: string
  started_at?: string
  completed_at?: string
}

export type TaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface TaskResult {
  success: boolean
  output?: string
  error?: string
  artifacts?: string[]
}

// Log types
export interface LogEntry {
  id: string
  project_id: string
  level: LogLevel
  source: string
  message: string
  timestamp: string
  details?: Record<string, unknown>
}

export type LogLevel = 'debug' | 'info' | 'warning' | 'error' | 'critical'

// Command types
export interface CommandExecution {
  id: string
  project_id: string
  command: string
  status: CommandStatus
  output: CommandOutputLine[]
  exit_code?: number
  started_at: string
  completed_at?: string
}

export type CommandStatus = 'running' | 'completed' | 'failed' | 'killed'

export interface CommandOutputLine {
  content: string
  type: 'stdout' | 'stderr'
  timestamp: string
}

// Agent types
export interface AgentInfo {
  id: string
  name: string
  type: AgentType
  status: AgentStatus
  current_task?: string
  capabilities: string[]
}

export type AgentType = 'coder' | 'reviewer' | 'tester' | 'planner' | 'executor' | 'custom'
export type AgentStatus = 'idle' | 'working' | 'waiting' | 'error'

// WebSocket event types
export type WSEventType =
  | 'project_created'
  | 'project_updated'
  | 'message_created'
  | 'message_stream'
  | 'task_updated'
  | 'file_created'
  | 'file_updated'
  | 'file_deleted'
  | 'log_created'
  | 'command_started'
  | 'command_output'
  | 'command_completed'
  | 'agent_status'

export interface WSEvent<T = unknown> {
  type: WSEventType
  project_id: string
  data: T
  timestamp: string
}

// API Response types
export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// Settings types
export interface AppSettings {
  theme: 'light' | 'dark' | 'system'
  auto_scroll: boolean
  show_timestamps: boolean
  max_log_lines: number
  llm_provider: string
  llm_model: string
}

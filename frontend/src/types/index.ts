/**
 * 型定義
 * バックエンドのスキーマに対応する型を定義
 */

// サーバ関連の型
export type AuthMethod = 'password' | 'key'

export interface Server {
  id: number
  name: string
  description: string | null
  host: string
  port: number
  username: string
  auth_method: AuthMethod
  created_at: string
  updated_at: string | null
}

export interface ServerCreate {
  name: string
  description?: string
  host: string
  port: number
  username: string
  auth_method: AuthMethod
  password?: string
  private_key?: string
}

export interface ServerUpdate {
  name?: string
  description?: string
  host?: string
  port?: number
  username?: string
  auth_method?: AuthMethod
  password?: string
  private_key?: string
}

// ジョブ関連の型
export type JobTriggerType = 'manual' | 'github_poll'

export interface Job {
  id: number
  name: string
  description: string | null
  script: string
  server_id: number
  trigger_type: JobTriggerType
  github_repository: string | null
  github_branch: string | null
  github_token_configured: boolean
  github_last_commit_sha: string | null
  github_last_checked_at: string | null
  github_last_error: string | null
  created_at: string
  updated_at: string | null
}

export interface JobWithServer extends Job {
  server: Server
}

export interface JobCreate {
  name: string
  description?: string
  script: string
  server_id: number
  trigger_type?: JobTriggerType
  github_repository?: string
  github_branch?: string
  github_token?: string
}

export interface JobUpdate {
  name?: string
  description?: string
  script?: string
  server_id?: number
  trigger_type?: JobTriggerType
  github_repository?: string | null
  github_branch?: string | null
  github_token?: string | null
}

// 実行履歴関連の型
export type ExecutionStatus = 'pending' | 'running' | 'success' | 'failed' | 'timeout' | 'cancelled'
export type ExecutionTriggerSource = 'manual' | 'github_poll'

export interface Execution {
  id: number
  job_id: number
  status: ExecutionStatus
  trigger_source: ExecutionTriggerSource
  trigger_commit_sha: string | null
  exit_code: number | null
  stdout: string | null
  stderr: string | null
  error_message: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  duration_seconds: number | null
}

export interface ExecutionWithJob extends Execution {
  job: Job
}

// WebSocketメッセージ型
export interface ExecutionLogMessage {
  type: 'log' | 'status' | 'error'
  data: string
  timestamp: string
}

export interface ExecutionStatusMessage {
  type: 'status'
  execution_id: number
  status: ExecutionStatus
  exit_code: number | null
  timestamp: string
}

// API レスポンス型
export interface ApiError {
  detail: string
}

// SSH接続テスト
export interface ServerTestRequest {
  host: string
  port: number
  username: string
  auth_method: AuthMethod
  password?: string
  private_key?: string
}

export interface ServerTestResponse {
  success: boolean
  message: string
  details?: string
}

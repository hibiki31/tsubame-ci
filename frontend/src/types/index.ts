/**
 * 型定義
 * バックエンドのスキーマに対応する型を定義
 */

// サーバ関連の型
export type AuthMethod = 'password' | 'key'
export type ServerConnectionStatus = 'unknown' | 'online' | 'offline'

export interface ServerHardwareInfo {
  hostname: string | null
  architecture: string | null
  cpu_model: string | null
  cpu_cores: number | null
  memory_total_bytes: number | null
  disk_total_bytes: number | null
}

export interface ServerSoftwareInfo {
  os_name: string | null
  os_version: string | null
  kernel: string | null
  package_manager: string | null
  python_version: string | null
  docker_version: string | null
  git_version: string | null
}

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
  connection_status: ServerConnectionStatus
  last_checked_at: string | null
  last_check_latency_ms: number | null
  last_check_error: string | null
  hardware_info: ServerHardwareInfo | null
  software_info: ServerSoftwareInfo | null
  inventory_collected_at: string | null
}

export interface ServerMonitoring {
  enabled: boolean
  check_interval_seconds: number
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
export type GitHubTokenSource = 'none' | 'shared' | 'job'

export interface Job {
  id: number
  name: string
  description: string | null
  script: string
  server_id: number
  trigger_type: JobTriggerType
  github_repository: string | null
  github_branch: string | null
  github_token_source: GitHubTokenSource
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

export interface JobLatestExecution {
  id: number
  status: ExecutionStatus
  created_at: string
}

export interface JobListItem extends JobWithServer {
  latest_execution: JobLatestExecution | null
}

export interface JobCreate {
  name: string
  description?: string
  script: string
  server_id: number
  trigger_type?: JobTriggerType
  github_repository?: string
  github_branch?: string
  github_token_source?: GitHubTokenSource
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
  github_token_source?: GitHubTokenSource
  github_token?: string | null
}

export interface GitHubTokenStatus {
  configured: boolean
  updated_at: string | null
}

// 実行履歴関連の型
export type ExecutionStatus = 'pending' | 'running' | 'success' | 'failed' | 'timeout' | 'cancelled'
export type ExecutionTriggerSource = 'manual' | 'github_poll'
export type ExecutionKind = 'job' | 'ad_hoc'

export interface Execution {
  id: number
  job_id: number | null
  execution_kind: ExecutionKind
  name_snapshot: string
  server_id_snapshot: number
  server_name_snapshot: string
  script_snapshot: string
  status: ExecutionStatus
  trigger_source: ExecutionTriggerSource
  trigger_commit_sha: string | null
  remote_execution_id: string | null
  remote_process_id: number | null
  exit_code: number | null
  stdout: string | null
  stderr: string | null
  error_message: string | null
  tracking_error: string | null
  created_at: string
  started_at: string | null
  finished_at: string | null
  last_synced_at: string | null
  cancel_requested_at: string | null
  duration_seconds: number | null
}

export interface ExecutionJobSummary {
  id: number
  name: string
  server_id: number
}

export interface ExecutionWithJob extends Execution {
  job: ExecutionJobSummary | null
}

export interface AdHocExecutionCreate {
  name: string
  server_id: number
  script: string
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

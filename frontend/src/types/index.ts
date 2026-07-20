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
export interface Job {
  id: number
  name: string
  description: string | null
  script: string
  server_id: number
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
}

export interface JobUpdate {
  name?: string
  description?: string
  script?: string
  server_id?: number
}

// 実行履歴関連の型
export type ExecutionStatus = 'pending' | 'running' | 'success' | 'failed' | 'cancelled'

export interface Execution {
  id: number
  job_id: number
  status: ExecutionStatus
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

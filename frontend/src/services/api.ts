/**
 * APIクライアント
 * axiosを使用したバックエンドとの通信
 */
import axios from 'axios'
import type { 
  Server, ServerCreate, ServerUpdate, ServerTestRequest, ServerTestResponse,
  Job, JobCreate, JobUpdate, JobWithServer,
  Execution, ExecutionWithJob
} from '@/types'

// axiosインスタンスの作成
const apiClient = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// レスポンスインターセプター（エラーハンドリング）
apiClient.interceptors.response.use(
  response => response,
  error => {
    // エラーメッセージの整形
    const message = error.response?.data?.detail || error.message || 'エラーが発生しました'
    return Promise.reject(new Error(message))
  }
)

// サーバAPI
export const serverApi = {
  // サーバ一覧取得
  async getAll(): Promise<Server[]> {
    const response = await apiClient.get<Server[]>('/servers')
    return response.data
  },

  // サーバ詳細取得
  async get(id: number): Promise<Server> {
    const response = await apiClient.get<Server>(`/servers/${id}`)
    return response.data
  },

  // サーバ作成
  async create(data: ServerCreate): Promise<Server> {
    const response = await apiClient.post<Server>('/servers', data)
    return response.data
  },

  // サーバ更新
  async update(id: number, data: ServerUpdate): Promise<Server> {
    const response = await apiClient.put<Server>(`/servers/${id}`, data)
    return response.data
  },

  // サーバ削除
  async delete(id: number): Promise<void> {
    await apiClient.delete(`/servers/${id}`)
  },

  // SSH接続テスト
  async testConnection(data: ServerTestRequest): Promise<ServerTestResponse> {
    const response = await apiClient.post<ServerTestResponse>('/servers/test', data)
    return response.data
  }
}

// ジョブAPI
export const jobApi = {
  // ジョブ一覧取得
  async getAll(): Promise<JobWithServer[]> {
    const response = await apiClient.get<JobWithServer[]>('/jobs')
    return response.data
  },

  // ジョブ詳細取得
  async get(id: number): Promise<JobWithServer> {
    const response = await apiClient.get<JobWithServer>(`/jobs/${id}`)
    return response.data
  },

  // ジョブ作成
  async create(data: JobCreate): Promise<Job> {
    const response = await apiClient.post<Job>('/jobs', data)
    return response.data
  },

  // ジョブ更新
  async update(id: number, data: JobUpdate): Promise<Job> {
    const response = await apiClient.put<Job>(`/jobs/${id}`, data)
    return response.data
  },

  // ジョブ削除
  async delete(id: number): Promise<void> {
    await apiClient.delete(`/jobs/${id}`)
  },

  // ジョブ実行
  async execute(jobId: number): Promise<Execution> {
    const response = await apiClient.post<Execution>(`/jobs/${jobId}/execute`)
    return response.data
  }
}

// 実行履歴API
export const executionApi = {
  // 実行履歴一覧取得
  async getAll(limit?: number, offset?: number): Promise<ExecutionWithJob[]> {
    const params = new URLSearchParams()
    if (limit !== undefined) params.append('limit', limit.toString())
    if (offset !== undefined) params.append('offset', offset.toString())
    
    const response = await apiClient.get<ExecutionWithJob[]>('/executions', { params })
    return response.data
  },

  // 実行履歴詳細取得
  async get(id: number): Promise<ExecutionWithJob> {
    const response = await apiClient.get<ExecutionWithJob>(`/executions/${id}`)
    return response.data
  },

  // ジョブの実行履歴取得
  async getByJob(jobId: number, limit?: number): Promise<Execution[]> {
    const params = new URLSearchParams()
    if (limit !== undefined) params.append('limit', limit.toString())
    
    const response = await apiClient.get<Execution[]>(`/jobs/${jobId}/executions`, { params })
    return response.data
  }
}

// WebSocket接続用
export const createExecutionWebSocket = (executionId: number): WebSocket => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/v1/executions/${executionId}/logs`
  return new WebSocket(wsUrl)
}

export default apiClient

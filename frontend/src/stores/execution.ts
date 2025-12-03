/**
 * 実行履歴ストア
 * ジョブ実行履歴の状態管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { executionApi, createExecutionWebSocket } from '@/services/api'
import type { ExecutionWithJob, ExecutionLogMessage, ExecutionStatusMessage } from '@/types'

export const useExecutionStore = defineStore('execution', () => {
  // State
  const executions = ref<ExecutionWithJob[]>([])
  const currentExecution = ref<ExecutionWithJob | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const realtimeLogs = ref<string[]>([])
  const wsConnection = ref<WebSocket | null>(null)

  // Getters
  const getExecutionById = computed(() => {
    return (id: number) => executions.value.find(e => e.id === id)
  })

  const getExecutionsByJob = computed(() => {
    return (jobId: number) => executions.value.filter(e => e.job_id === jobId)
  })

  const latestExecutions = computed(() => {
    return executions.value.slice(0, 10)
  })

  // Actions
  async function fetchExecutions(limit?: number, offset?: number) {
    loading.value = true
    error.value = null
    try {
      executions.value = await executionApi.getAll(limit, offset)
    } catch (err) {
      error.value = err instanceof Error ? err.message : '実行履歴の取得に失敗しました'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchExecution(id: number) {
    loading.value = true
    error.value = null
    try {
      currentExecution.value = await executionApi.get(id)
      return currentExecution.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : '実行履歴の取得に失敗しました'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchJobExecutions(jobId: number, limit?: number) {
    loading.value = true
    error.value = null
    try {
      const jobExecutions = await executionApi.getByJob(jobId, limit)
      // 既存の実行履歴とマージ
      jobExecutions.forEach(exec => {
        const index = executions.value.findIndex(e => e.id === exec.id)
        if (index === -1) {
          // 実行履歴をExecutionWithJobに変換（job情報は後で追加）
          executions.value.push(exec as any)
        }
      })
      return jobExecutions
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'ジョブの実行履歴取得に失敗しました'
      throw err
    } finally {
      loading.value = false
    }
  }

  // WebSocket接続の確立
  function connectToExecution(executionId: number) {
    // 既存の接続があれば閉じる
    disconnectExecution()
    
    realtimeLogs.value = []
    
    try {
      wsConnection.value = createExecutionWebSocket(executionId)
      
      wsConnection.value.onopen = () => {
        console.log('WebSocket接続確立:', executionId)
      }
      
      wsConnection.value.onmessage = (event) => {
        const message = JSON.parse(event.data) as ExecutionLogMessage | ExecutionStatusMessage
        
        if (message.type === 'log') {
          const logMessage = message as ExecutionLogMessage
          realtimeLogs.value.push(logMessage.data)
        } else if (message.type === 'status') {
          const statusMessage = message as ExecutionStatusMessage
          // 実行ステータスの更新
          if (currentExecution.value?.id === statusMessage.execution_id) {
            currentExecution.value.status = statusMessage.status
            if (statusMessage.exit_code !== null) {
              currentExecution.value.exit_code = statusMessage.exit_code
            }
          }
        } else if (message.type === 'error') {
          const errorMessage = message as ExecutionLogMessage
          error.value = errorMessage.data
        }
      }
      
      wsConnection.value.onerror = (event) => {
        console.error('WebSocketエラー:', event)
        error.value = 'リアルタイム接続でエラーが発生しました'
      }
      
      wsConnection.value.onclose = () => {
        console.log('WebSocket接続終了:', executionId)
        wsConnection.value = null
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'WebSocket接続に失敗しました'
      throw err
    }
  }

  // WebSocket接続の切断
  function disconnectExecution() {
    if (wsConnection.value) {
      wsConnection.value.close()
      wsConnection.value = null
    }
  }

  // リアルタイムログのクリア
  function clearRealtimeLogs() {
    realtimeLogs.value = []
  }

  function clearError() {
    error.value = null
  }

  return {
    // State
    executions,
    currentExecution,
    loading,
    error,
    realtimeLogs,
    wsConnection,
    
    // Getters
    getExecutionById,
    getExecutionsByJob,
    latestExecutions,
    
    // Actions
    fetchExecutions,
    fetchExecution,
    fetchJobExecutions,
    connectToExecution,
    disconnectExecution,
    clearRealtimeLogs,
    clearError
  }
})

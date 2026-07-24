/**
 * 実行履歴ストア
 * ジョブ実行履歴の状態管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { executionApi } from '@/services/api'
import type { ExecutionWithJob } from '@/types'

export const useExecutionStore = defineStore('execution', () => {
  // State
  const executions = ref<ExecutionWithJob[]>([])
  const currentExecution = ref<ExecutionWithJob | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

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

  async function fetchExecution(id: number, silent = false) {
    if (!silent) {
      loading.value = true
      error.value = null
    }
    try {
      currentExecution.value = await executionApi.get(id)
      error.value = null
      return currentExecution.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : '実行履歴の取得に失敗しました'
      throw err
    } finally {
      if (!silent) {
        loading.value = false
      }
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

  function clearError() {
    error.value = null
  }

  return {
    // State
    executions,
    currentExecution,
    loading,
    error,
    
    // Getters
    getExecutionById,
    getExecutionsByJob,
    latestExecutions,
    
    // Actions
    fetchExecutions,
    fetchExecution,
    fetchJobExecutions,
    clearError
  }
})

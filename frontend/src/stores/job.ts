/**
 * ジョブストア
 * ジョブ管理の状態管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { jobApi } from '@/services/api'
import type { JobWithServer, JobCreate, JobUpdate } from '@/types'

export const useJobStore = defineStore('job', () => {
  // State
  const jobs = ref<JobWithServer[]>([])
  const currentJob = ref<JobWithServer | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const getJobById = computed(() => {
    return (id: number) => jobs.value.find(j => j.id === id)
  })

  const getJobsByServer = computed(() => {
    return (serverId: number) => jobs.value.filter(j => j.server_id === serverId)
  })

  // Actions
  async function fetchJobs() {
    loading.value = true
    error.value = null
    try {
      jobs.value = await jobApi.getAll()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'ジョブ一覧の取得に失敗しました'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchJob(id: number) {
    loading.value = true
    error.value = null
    try {
      currentJob.value = await jobApi.get(id)
      return currentJob.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'ジョブの取得に失敗しました'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createJob(data: JobCreate) {
    loading.value = true
    error.value = null
    try {
      const newJob = await jobApi.create(data)
      // 一覧を再取得（サーバ情報を含むため）
      await fetchJobs()
      return newJob
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'ジョブの作成に失敗しました'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateJob(id: number, data: JobUpdate) {
    loading.value = true
    error.value = null
    try {
      const updated = await jobApi.update(id, data)
      // 一覧を再取得（サーバ情報を含むため）
      await fetchJobs()
      if (currentJob.value?.id === id) {
        await fetchJob(id)
      }
      return updated
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'ジョブの更新に失敗しました'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteJob(id: number) {
    loading.value = true
    error.value = null
    try {
      await jobApi.delete(id)
      jobs.value = jobs.value.filter(j => j.id !== id)
      if (currentJob.value?.id === id) {
        currentJob.value = null
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'ジョブの削除に失敗しました'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function executeJob(jobId: number) {
    loading.value = true
    error.value = null
    try {
      const execution = await jobApi.execute(jobId)
      return execution
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'ジョブの実行に失敗しました'
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
    jobs,
    currentJob,
    loading,
    error,
    
    // Getters
    getJobById,
    getJobsByServer,
    
    // Actions
    fetchJobs,
    fetchJob,
    createJob,
    updateJob,
    deleteJob,
    executeJob,
    clearError
  }
})

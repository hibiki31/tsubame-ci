/**
 * サーバストア
 * サーバ管理の状態管理
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { serverApi } from '@/services/api'
import type { Server, ServerCreate, ServerUpdate } from '@/types'

export const useServerStore = defineStore('server', () => {
  // State
  const servers = ref<Server[]>([])
  const currentServer = ref<Server | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  // Getters
  const getServerById = computed(() => {
    return (id: number) => servers.value.find(s => s.id === id)
  })

  // Actions
  async function fetchServers() {
    loading.value = true
    error.value = null
    try {
      servers.value = await serverApi.getAll()
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'サーバ一覧の取得に失敗しました'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchServer(id: number) {
    loading.value = true
    error.value = null
    try {
      currentServer.value = await serverApi.get(id)
      return currentServer.value
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'サーバの取得に失敗しました'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createServer(data: ServerCreate) {
    loading.value = true
    error.value = null
    try {
      const newServer = await serverApi.create(data)
      servers.value.push(newServer)
      return newServer
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'サーバの作成に失敗しました'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateServer(id: number, data: ServerUpdate) {
    loading.value = true
    error.value = null
    try {
      const updated = await serverApi.update(id, data)
      const index = servers.value.findIndex(s => s.id === id)
      if (index !== -1) {
        servers.value[index] = updated
      }
      if (currentServer.value?.id === id) {
        currentServer.value = updated
      }
      return updated
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'サーバの更新に失敗しました'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteServer(id: number) {
    loading.value = true
    error.value = null
    try {
      await serverApi.delete(id)
      servers.value = servers.value.filter(s => s.id !== id)
      if (currentServer.value?.id === id) {
        currentServer.value = null
      }
    } catch (err) {
      error.value = err instanceof Error ? err.message : 'サーバの削除に失敗しました'
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
    servers,
    currentServer,
    loading,
    error,
    
    // Getters
    getServerById,
    
    // Actions
    fetchServers,
    fetchServer,
    createServer,
    updateServer,
    deleteServer,
    clearError
  }
})

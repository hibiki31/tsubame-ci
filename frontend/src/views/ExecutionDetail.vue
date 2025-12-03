<template>
  <div v-if="execution">
    <v-btn
      prepend-icon="mdi-arrow-left"
      variant="text"
      :to="`/jobs/${execution.job_id}`"
      class="mb-4"
    >
      戻る
    </v-btn>

    <!-- 実行情報 -->
    <v-card class="mb-6">
      <v-card-title class="d-flex justify-space-between align-center">
        <span>{{ execution.job?.name }}</span>
        <v-chip
          :color="getStatusColor(execution.status)"
          size="large"
        >
          {{ getStatusText(execution.status) }}
        </v-chip>
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" md="6">
            <div class="mb-2">
              <strong>実行ID:</strong> {{ execution.id }}
            </div>
            <div class="mb-2">
              <strong>開始時刻:</strong> {{ execution.started_at ? formatDate(execution.started_at) : '未開始' }}
            </div>
            <div class="mb-2">
              <strong>終了時刻:</strong> {{ execution.finished_at ? formatDate(execution.finished_at) : '未完了' }}
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div class="mb-2">
              <strong>実行時間:</strong> {{ formatDuration(execution.duration_seconds) }}
            </div>
            <div class="mb-2">
              <strong>終了コード:</strong> 
              <v-chip
                v-if="execution.exit_code !== null"
                :color="execution.exit_code === 0 ? 'success' : 'error'"
                size="small"
              >
                {{ execution.exit_code }}
              </v-chip>
              <span v-else>-</span>
            </div>
          </v-col>
        </v-row>
      </v-card-text>
    </v-card>

    <!-- 標準出力 -->
    <v-card class="mb-6">
      <v-card-title>
        標準出力 (stdout)
        <v-spacer></v-spacer>
        <v-chip
          v-if="execution.status === 'running'"
          color="info"
          size="small"
        >
          <v-icon start>mdi-circle</v-icon>
          リアルタイム
        </v-chip>
      </v-card-title>
      <v-card-text>
        <pre class="log-output">{{ displayStdout }}</pre>
      </v-card-text>
    </v-card>

    <!-- 標準エラー出力 -->
    <v-card v-if="execution.stderr || execution.error_message" class="mb-6">
      <v-card-title class="text-error">標準エラー出力 (stderr)</v-card-title>
      <v-card-text>
        <pre class="log-output error">{{ execution.stderr || execution.error_message }}</pre>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useExecutionStore } from '@/stores/execution'
import type { ExecutionStatus } from '@/types'

const route = useRoute()
const executionStore = useExecutionStore()

const executionId = computed(() => parseInt(route.params.id as string))
const execution = computed(() => executionStore.currentExecution)
const realtimeLogs = computed(() => executionStore.realtimeLogs)

// リアルタイムログと保存済みログを統合して表示
const displayStdout = computed(() => {
  if (execution.value?.status === 'running' && realtimeLogs.value.length > 0) {
    return realtimeLogs.value.join('\n')
  }
  return execution.value?.stdout || 'ログなし'
})

function getStatusColor(status: ExecutionStatus): string {
  switch (status) {
    case 'success': return 'success'
    case 'failed': return 'error'
    case 'running': return 'info'
    case 'pending': return 'warning'
    default: return 'grey'
  }
}

function getStatusText(status: ExecutionStatus): string {
  switch (status) {
    case 'success': return '成功'
    case 'failed': return '失敗'
    case 'running': return '実行中'
    case 'pending': return '待機中'
    case 'cancelled': return 'キャンセル'
    default: return status
  }
}

function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString('ja-JP')
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return '-'
  if (seconds < 60) return `${seconds.toFixed(1)}秒`
  const minutes = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${minutes}分${secs}秒`
}

onMounted(async () => {
  try {
    await executionStore.fetchExecution(executionId.value)
    
    // 実行中の場合はWebSocket接続
    if (execution.value?.status === 'running' || execution.value?.status === 'pending') {
      executionStore.connectToExecution(executionId.value)
      
      // 定期的にステータスを更新（WebSocketが切断された場合のフォールバック）
      const intervalId = setInterval(async () => {
        if (execution.value?.status === 'running' || execution.value?.status === 'pending') {
          await executionStore.fetchExecution(executionId.value)
        } else {
          clearInterval(intervalId)
        }
      }, 5000)
      
      // コンポーネント破棄時にクリーンアップ
      onUnmounted(() => {
        clearInterval(intervalId)
      })
    }
  } catch (error) {
    console.error('実行履歴の取得に失敗しました:', error)
  }
})

onUnmounted(() => {
  // WebSocket接続を切断
  executionStore.disconnectExecution()
  executionStore.clearRealtimeLogs()
})
</script>

<style scoped>
.log-output {
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.5;
  max-height: 600px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-wrap: break-word;
}

.log-output.error {
  background-color: #2d1e1e;
  color: #ff6b6b;
}
</style>

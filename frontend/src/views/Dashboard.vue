<template>
  <div>
    <h1 class="text-h4 mb-6">ダッシュボード</h1>

    <!-- 統計カード -->
    <v-row>
      <v-col cols="12" md="3">
        <v-card>
          <v-card-text>
            <div class="text-h6">サーバ数</div>
            <div class="text-h3 mt-2">{{ servers.length }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="3">
        <v-card>
          <v-card-text>
            <div class="text-h6">ジョブ数</div>
            <div class="text-h3 mt-2">{{ jobs.length }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="3">
        <v-card color="success">
          <v-card-text class="text-white">
            <div class="text-h6">成功</div>
            <div class="text-h3 mt-2">{{ successCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>

      <v-col cols="12" md="3">
        <v-card color="error">
          <v-card-text class="text-white">
            <div class="text-h6">失敗</div>
            <div class="text-h3 mt-2">{{ failedCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <!-- 最近の実行履歴 -->
    <v-card class="mt-6">
      <v-card-title>最近の実行履歴</v-card-title>
      <v-card-text>
        <v-data-table
          :headers="headers"
          :items="latestExecutions"
          :loading="loading"
          :items-per-page="10"
          density="compact"
        >
          <template v-slot:item.status="{ item }">
            <v-chip
              :color="getStatusColor(item.status)"
              size="small"
            >
              {{ getStatusText(item.status) }}
            </v-chip>
          </template>

          <template v-slot:item.created_at="{ item }">
            {{ formatDate(item.created_at) }}
          </template>

          <template v-slot:item.actions="{ item }">
            <v-btn
              icon="mdi-eye"
              size="small"
              variant="text"
              :to="`/executions/${item.id}`"
            ></v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useServerStore } from '@/stores/server'
import { useJobStore } from '@/stores/job'
import { useExecutionStore } from '@/stores/execution'
import type { ExecutionStatus } from '@/types'

const serverStore = useServerStore()
const jobStore = useJobStore()
const executionStore = useExecutionStore()

const servers = computed(() => serverStore.servers)
const jobs = computed(() => jobStore.jobs)
const latestExecutions = computed(() => executionStore.latestExecutions)
const loading = computed(() => executionStore.loading)

// 成功・失敗の集計
const successCount = computed(() => 
  latestExecutions.value.filter(e => e.status === 'success').length
)
const failedCount = computed(() => 
  latestExecutions.value.filter(e => e.status === 'failed').length
)

// テーブルヘッダー
const headers = [
  { title: 'ジョブ名', key: 'job.name' },
  { title: 'ステータス', key: 'status' },
  { title: '実行日時', key: 'created_at' },
  { title: '操作', key: 'actions', sortable: false }
]

// ステータスの色
function getStatusColor(status: ExecutionStatus): string {
  switch (status) {
    case 'success': return 'success'
    case 'failed': return 'error'
    case 'running': return 'info'
    case 'pending': return 'warning'
    default: return 'grey'
  }
}

// ステータスのテキスト
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

// 日付フォーマット
function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString('ja-JP')
}

// 初期データの取得
onMounted(async () => {
  try {
    await Promise.all([
      serverStore.fetchServers(),
      jobStore.fetchJobs(),
      executionStore.fetchExecutions(10)
    ])
  } catch (error) {
    console.error('データの取得に失敗しました:', error)
  }
})
</script>

<style scoped>
/* スタイルはVuetifyのクラスで対応 */
</style>

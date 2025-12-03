<template>
  <div>
    <h1 class="text-h4 mb-6">実行履歴</h1>

    <v-card>
      <v-card-text>
        <v-data-table
          :headers="headers"
          :items="executions"
          :loading="loading"
          :items-per-page="20"
        >
          <template v-slot:item.job="{ item }">
            <router-link :to="`/jobs/${item.job_id}`">
              {{ item.job?.name }}
            </router-link>
          </template>

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

          <template v-slot:item.duration="{ item }">
            {{ formatDuration(item.duration_seconds) }}
          </template>

          <template v-slot:item.exit_code="{ item }">
            <v-chip
              v-if="item.exit_code !== null"
              :color="item.exit_code === 0 ? 'success' : 'error'"
              size="small"
            >
              {{ item.exit_code }}
            </v-chip>
            <span v-else>-</span>
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
import { useExecutionStore } from '@/stores/execution'
import type { ExecutionStatus } from '@/types'

const executionStore = useExecutionStore()

const executions = computed(() => executionStore.executions)
const loading = computed(() => executionStore.loading)

const headers = [
  { title: 'ジョブ名', key: 'job' },
  { title: 'ステータス', key: 'status' },
  { title: '実行日時', key: 'created_at' },
  { title: '実行時間', key: 'duration' },
  { title: '終了コード', key: 'exit_code' },
  { title: '操作', key: 'actions', sortable: false }
]

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
    await executionStore.fetchExecutions(50)
  } catch (error) {
    console.error('実行履歴の取得に失敗しました:', error)
  }
})
</script>

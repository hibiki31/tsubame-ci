<template>
  <div v-if="job">
    <v-btn
      prepend-icon="mdi-arrow-left"
      variant="text"
      to="/jobs"
      class="mb-4"
    >
      戻る
    </v-btn>

    <v-card class="mb-6">
      <v-card-title class="d-flex justify-space-between align-center">
        <span>{{ job.name }}</span>
        <v-btn
          color="success"
          prepend-icon="mdi-play"
          @click="executeJob"
          :loading="executing"
        >
          実行
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-row>
          <v-col cols="12" md="6">
            <div class="mb-2">
              <strong>サーバ:</strong> {{ job.server?.name }}
            </div>
            <div class="mb-2">
              <strong>ホスト:</strong> {{ job.server?.host }}:{{ job.server?.port }}
            </div>
            <div class="mb-2">
              <strong>説明:</strong> {{ job.description || 'なし' }}
            </div>
          </v-col>
          <v-col cols="12" md="6">
            <div class="mb-2">
              <strong>作成日:</strong> {{ formatDate(job.created_at) }}
            </div>
            <div v-if="job.updated_at" class="mb-2">
              <strong>更新日:</strong> {{ formatDate(job.updated_at) }}
            </div>
            <div class="mb-2">
              <strong>実行トリガー:</strong>
              {{ job.trigger_type === 'github_poll' ? 'GitHub ブランチ変更' : '手動のみ' }}
            </div>
          </v-col>
        </v-row>

        <v-alert
          v-if="job.trigger_type === 'github_poll'"
          :type="job.github_last_error ? 'error' : 'info'"
          variant="tonal"
          class="mt-3"
        >
          <div class="font-weight-medium">
            <v-icon icon="mdi-source-branch" size="small" class="mr-1" />
            {{ job.github_repository }} · {{ job.github_branch }}
          </div>
          <div v-if="job.github_last_error" class="text-body-2 mt-1">
            {{ job.github_last_error }}
          </div>
          <div v-else class="text-body-2 mt-1">
            {{ getPollingStatus() }}
          </div>
        </v-alert>

        <v-divider class="my-4"></v-divider>

        <div>
          <strong>スクリプト:</strong>
          <pre class="script-code mt-2">{{ job.script }}</pre>
        </div>
      </v-card-text>
    </v-card>

    <v-card>
      <v-card-title>実行履歴</v-card-title>
      <v-card-text>
        <v-data-table
          :headers="headers"
          :items="executions"
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

          <template v-slot:item.trigger_source="{ item }">
            <v-chip
              :color="item.trigger_source === 'github_poll' ? 'info' : 'default'"
              size="small"
              variant="tonal"
            >
              {{ item.trigger_source === 'github_poll' ? 'GitHub' : '手動' }}
            </v-chip>
          </template>

          <template v-slot:item.duration="{ item }">
            {{ formatDuration(item.duration_seconds) }}
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
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useJobStore } from '@/stores/job'
import { useExecutionStore } from '@/stores/execution'
import type { ExecutionStatus, Execution } from '@/types'

const route = useRoute()
const router = useRouter()
const jobStore = useJobStore()
const executionStore = useExecutionStore()

const jobId = computed(() => parseInt(route.params.id as string))
const job = computed(() => jobStore.currentJob)
const executions = ref<Execution[]>([])
const loading = computed(() => executionStore.loading)
const executing = ref(false)

const headers = [
  { title: 'ステータス', key: 'status' },
  { title: '実行元', key: 'trigger_source' },
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
    case 'timeout': return 'error'
    default: return 'grey'
  }
}

function getStatusText(status: ExecutionStatus): string {
  switch (status) {
    case 'success': return '成功'
    case 'failed': return '失敗'
    case 'running': return '実行中'
    case 'pending': return '待機中'
    case 'timeout': return 'タイムアウト'
    case 'cancelled': return 'キャンセル'
    default: return status
  }
}

function getPollingStatus(): string {
  if (!job.value?.github_last_checked_at) return '初回確認待ちです'
  const checkedAt = formatDate(job.value.github_last_checked_at)
  const sha = job.value.github_last_commit_sha?.slice(0, 7)
  return sha ? `最終確認: ${checkedAt}（${sha}）` : `最終確認: ${checkedAt}`
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

async function executeJob() {
  executing.value = true
  try {
    const execution = await jobStore.executeJob(jobId.value)
    router.push(`/executions/${execution.id}`)
  } catch (error) {
    console.error('ジョブの実行に失敗しました:', error)
  } finally {
    executing.value = false
  }
}

onMounted(async () => {
  try {
    await jobStore.fetchJob(jobId.value)
    executions.value = await executionStore.fetchJobExecutions(jobId.value, 20)
  } catch (error) {
    console.error('データの取得に失敗しました:', error)
  }
})
</script>

<style scoped>
.script-code {
  background-color: #f5f5f5;
  padding: 16px;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 14px;
}
</style>

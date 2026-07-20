<template>
  <div>
    <v-btn class="back-link" prepend-icon="mdi-arrow-left" to="/jobs" variant="text">ジョブ一覧</v-btn>

    <template v-if="job">
      <AppPageHeader
        eyebrow="Job detail"
        icon="mdi-script-text-outline"
        :title="job.name"
        :description="job.description || 'このジョブには説明がありません。'"
      >
        <template #actions>
          <v-btn color="success" prepend-icon="mdi-play" :loading="executing" @click="executeDialog = true">
            ジョブを実行
          </v-btn>
        </template>
      </AppPageHeader>

      <v-alert
        v-if="loadError"
        class="mb-6"
        closable
        color="error"
        icon="mdi-alert-circle-outline"
        variant="tonal"
        @click:close="clearErrors"
      >
        {{ loadError }}
      </v-alert>

      <v-row>
        <v-col cols="12" lg="4">
          <v-card class="panel-card detail-card" height="100%">
            <v-card-title class="panel-card__header">
              <div>
                <div class="panel-card__title">実行コンテキスト</div>
                <div class="panel-card__subtitle">ジョブID {{ job.id }}</div>
              </div>
            </v-card-title>
            <v-card-text class="detail-list">
              <div class="detail-list__item">
                <div class="detail-list__icon"><v-icon icon="mdi-server-outline" size="18" /></div>
                <div>
                  <span>実行サーバ</span>
                  <strong>{{ job.server?.name || `サーバ #${job.server_id}` }}</strong>
                  <small v-if="job.server">{{ job.server.username }}@{{ job.server.host }}:{{ job.server.port }}</small>
                </div>
              </div>

              <div class="detail-list__item">
                <div class="detail-list__icon"><v-icon icon="mdi-calendar-plus" size="18" /></div>
                <div>
                  <span>登録日時</span>
                  <strong>{{ formatDate(job.created_at) }}</strong>
                </div>
              </div>

              <div v-if="job.updated_at" class="detail-list__item">
                <div class="detail-list__icon"><v-icon icon="mdi-calendar-edit" size="18" /></div>
                <div>
                  <span>最終更新</span>
                  <strong>{{ formatDate(job.updated_at) }}</strong>
                </div>
              </div>
            </v-card-text>
          </v-card>
        </v-col>

        <v-col cols="12" lg="8">
          <v-card class="panel-card script-card" height="100%">
            <v-card-title class="panel-card__header">
              <div>
                <div class="panel-card__title">シェルスクリプト</div>
                <div class="panel-card__subtitle">実行前に対象と内容を確認してください</div>
              </div>
              <v-chip prepend-icon="mdi-console" size="small" variant="tonal">Shell</v-chip>
            </v-card-title>
            <v-card-text class="script-card__body">
              <pre class="code-panel script-code"><code>{{ job.script }}</code></pre>
            </v-card-text>
          </v-card>
        </v-col>
      </v-row>

      <v-card class="panel-card table-card mt-6">
        <v-card-title class="panel-card__header">
          <div>
            <div class="panel-card__title">実行履歴</div>
            <div class="panel-card__subtitle">このジョブの最近の実行</div>
          </div>
          <v-chip size="small" variant="tonal">{{ executions.length }}件</v-chip>
        </v-card-title>

        <v-data-table
          :headers="headers"
          :items="executions"
          :loading="loading"
          :items-per-page="10"
          density="comfortable"
          hover
        >
          <template #item.status="{ item }">
            <ExecutionStatusChip :status="item.status" />
          </template>

          <template #item.created_at="{ item }">
            <span class="date-cell">{{ formatDate(item.created_at) }}</span>
          </template>

          <template #item.duration="{ item }">
            <span class="numeric-cell">{{ formatDuration(item.duration_seconds) }}</span>
          </template>

          <template #item.exit_code="{ item }">
            <v-chip
              v-if="item.exit_code !== null"
              :color="item.exit_code === 0 ? 'success' : 'error'"
              label
              size="small"
              variant="tonal"
            >
              {{ item.exit_code }}
            </v-chip>
            <span v-else class="muted-cell">—</span>
          </template>

          <template #item.actions="{ item }">
            <v-btn
              :aria-label="`実行 ${item.id} の詳細を見る`"
              class="icon-action"
              icon="mdi-arrow-top-right"
              size="small"
              variant="text"
              :to="`/executions/${item.id}`"
            />
          </template>

          <template #no-data>
            <v-empty-state
              class="empty-state"
              icon="mdi-play-circle-outline"
              title="実行履歴はまだありません"
              text="このジョブを実行すると結果が表示されます。"
            />
          </template>
        </v-data-table>
      </v-card>
    </template>

    <v-card v-else-if="loading" class="panel-card">
      <v-skeleton-loader type="article, paragraph, actions" />
    </v-card>

    <v-card v-else class="panel-card">
      <v-empty-state
        class="empty-state"
        icon="mdi-file-question-outline"
        title="ジョブを表示できません"
        :text="jobStore.error || '指定されたジョブが見つかりませんでした。'"
      >
        <template #actions>
          <v-btn color="primary" prepend-icon="mdi-arrow-left" to="/jobs">ジョブ一覧へ</v-btn>
        </template>
      </v-empty-state>
    </v-card>

    <v-dialog v-model="executeDialog" max-width="500">
      <v-card class="dialog-card">
        <v-card-title>ジョブを実行しますか？</v-card-title>
        <v-card-subtitle>実行先を確認して開始してください。</v-card-subtitle>
        <v-card-text>
          <div class="execute-summary">
            <div>
              <span>ジョブ</span>
              <strong>{{ job?.name }}</strong>
            </div>
            <v-divider />
            <div>
              <span>実行サーバ</span>
              <strong>{{ job?.server?.name || `サーバ #${job?.server_id}` }}</strong>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="executeDialog = false">キャンセル</v-btn>
          <v-btn color="success" prepend-icon="mdi-play" :loading="executing" @click="executeJob">実行</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppPageHeader from '@/components/AppPageHeader.vue'
import ExecutionStatusChip from '@/components/ExecutionStatusChip.vue'
import { useJobStore } from '@/stores/job'
import { useExecutionStore } from '@/stores/execution'
import type { Execution } from '@/types'

const route = useRoute()
const router = useRouter()
const jobStore = useJobStore()
const executionStore = useExecutionStore()

const jobId = computed(() => parseInt(route.params.id as string))
const job = computed(() => jobStore.currentJob)
const executions = ref<Execution[]>([])
const loading = computed(() => jobStore.loading || executionStore.loading)
const loadError = computed(() => jobStore.error || executionStore.error)
const executing = ref(false)
const executeDialog = ref(false)

const headers = [
  { title: 'ステータス', key: 'status', width: 150 },
  { title: '実行日時', key: 'created_at', width: 210 },
  { title: '所要時間', key: 'duration', width: 140 },
  { title: '終了コード', key: 'exit_code', width: 120 },
  { title: '', key: 'actions', sortable: false, align: 'end' as const, width: 72 },
]

function clearErrors() {
  jobStore.clearError()
  executionStore.clearError()
}

function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat('ja-JP', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(dateString))
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return '—'
  if (seconds < 60) return `${seconds.toFixed(1)}秒`
  const minutes = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${minutes}分 ${secs}秒`
}

async function executeJob() {
  executing.value = true
  try {
    const execution = await jobStore.executeJob(jobId.value)
    executeDialog.value = false
    await router.push(`/executions/${execution.id}`)
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
.back-link {
  margin: -8px 0 18px -12px;
  color: rgb(var(--v-theme-on-surface-variant));
}

.detail-list {
  display: grid;
  gap: 6px;
  padding: 8px 24px 24px !important;
}

.detail-list__item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 13px 0;
  border-bottom: 1px solid rgba(var(--v-border-color), 0.08);
}

.detail-list__item:last-child {
  border-bottom: 0;
}

.detail-list__icon {
  display: grid;
  flex: 0 0 34px;
  width: 34px;
  height: 34px;
  place-items: center;
  color: rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-primary-soft));
  border-radius: 9px;
}

.detail-list span,
.detail-list strong,
.detail-list small {
  display: block;
}

.detail-list span {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.69rem;
  font-weight: 650;
}

.detail-list strong {
  margin-top: 2px;
  font-size: 0.85rem;
}

.detail-list small {
  margin-top: 3px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-family: var(--font-mono);
  font-size: 0.67rem;
}

.script-card__body {
  padding: 8px 24px 24px !important;
}

.script-code {
  max-height: 380px;
  min-height: 220px;
  white-space: pre-wrap;
}

.date-cell,
.muted-cell {
  color: rgb(var(--v-theme-on-surface-variant));
}

.date-cell,
.numeric-cell {
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.execute-summary {
  display: grid;
  gap: 14px;
  padding: 18px;
  background: rgb(var(--v-theme-surface-light));
  border-radius: 14px;
}

.execute-summary span,
.execute-summary strong {
  display: block;
}

.execute-summary span {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.69rem;
  font-weight: 650;
}

.execute-summary strong {
  margin-top: 3px;
}
</style>

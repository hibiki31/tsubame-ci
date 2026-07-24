<template>
  <div>
    <v-btn class="back-link" prepend-icon="mdi-arrow-left" to="/executions" variant="text">実行履歴</v-btn>

    <template v-if="execution">
      <AppPageHeader
        eyebrow="Execution detail"
        icon="mdi-console-line"
        :title="execution.job?.name || `実行 #${execution.id}`"
        :description="`実行ID ${execution.id} の結果とログを表示しています。`"
      >
        <template #actions>
          <div v-if="isActive" class="refresh-state" aria-live="polite">
            <v-progress-circular
              v-if="refreshing"
              color="info"
              indeterminate
              size="16"
              width="2"
            />
            <v-icon v-else color="info" icon="mdi-sync" size="16" />
            <span>{{ refreshing ? '更新中' : '2秒ごとに更新' }}</span>
          </div>
          <ExecutionStatusChip :status="execution.status" />
          <ExecutionTriggerChip :source="execution.trigger_source" />
          <v-btn
            aria-label="実行状態とログを更新"
            icon="mdi-refresh"
            :loading="refreshing"
            size="small"
            variant="text"
            @click="refreshExecution(false)"
          />
          <v-btn
            v-if="execution.job_id"
            prepend-icon="mdi-script-text-outline"
            :to="`/jobs/${execution.job_id}`"
            variant="outlined"
          >
            ジョブ詳細
          </v-btn>
        </template>
      </AppPageHeader>

      <v-alert
        v-if="executionStore.error"
        class="mb-6"
        closable
        color="error"
        icon="mdi-alert-circle-outline"
        variant="tonal"
        @click:close="executionStore.clearError()"
      >
        {{ executionStore.error }}
      </v-alert>

      <v-alert
        v-if="execution.tracking_error"
        class="mb-6"
        color="warning"
        icon="mdi-lan-disconnect"
        title="SSH 接続を再試行しています"
        variant="tonal"
      >
        リモートジョブは停止せず、接続復旧後に状態とログを再同期します。
        <span class="tracking-alert__detail">{{ execution.tracking_error }}</span>
      </v-alert>

      <v-card class="panel-card execution-meta">
        <div v-for="item in metadata" :key="item.label" class="execution-meta__item">
          <div class="execution-meta__icon" aria-hidden="true"><v-icon :icon="item.icon" size="18" /></div>
          <div>
            <span>{{ item.label }}</span>
            <strong :title="item.value">{{ item.value }}</strong>
          </div>
        </div>
      </v-card>

      <v-card class="panel-card log-card mt-6">
        <v-card-title class="panel-card__header">
          <div>
            <div class="panel-card__title">標準出力</div>
            <div class="panel-card__subtitle">stdout</div>
          </div>
          <div class="log-card__actions">
            <v-chip
              v-if="isActive"
              class="live-chip"
              color="info"
              prepend-icon="mdi-access-point"
              size="small"
              variant="tonal"
            >
              {{ execution.status === 'pending' ? '開始待ち' : '追従中' }}
            </v-chip>
            <v-btn
              :aria-label="copiedLog === 'stdout' ? '標準出力をコピーしました' : '標準出力をコピー'"
              :color="copiedLog === 'stdout' ? 'success' : undefined"
              :prepend-icon="copiedLog === 'stdout' ? 'mdi-check' : 'mdi-content-copy'"
              size="small"
              variant="text"
              @click="copyLog(displayStdout, 'stdout')"
            >
              {{ copiedLog === 'stdout' ? 'コピー済み' : 'コピー' }}
            </v-btn>
          </div>
        </v-card-title>
        <v-card-text class="log-card__body">
          <pre class="code-panel log-output"><code>{{ displayStdout }}</code></pre>
        </v-card-text>
      </v-card>

      <v-card v-if="displayStderr" class="panel-card log-card log-card--error mt-6">
        <v-card-title class="panel-card__header">
          <div>
            <div class="panel-card__title text-error">標準エラー出力</div>
            <div class="panel-card__subtitle">stderr / error message</div>
          </div>
          <v-btn
            :aria-label="copiedLog === 'stderr' ? '標準エラー出力をコピーしました' : '標準エラー出力をコピー'"
            :color="copiedLog === 'stderr' ? 'success' : undefined"
            :prepend-icon="copiedLog === 'stderr' ? 'mdi-check' : 'mdi-content-copy'"
            size="small"
            variant="text"
            @click="copyLog(displayStderr, 'stderr')"
          >
            {{ copiedLog === 'stderr' ? 'コピー済み' : 'コピー' }}
          </v-btn>
        </v-card-title>
        <v-card-text class="log-card__body">
          <pre class="code-panel log-output log-output--error"><code>{{ displayStderr }}</code></pre>
        </v-card-text>
      </v-card>
    </template>

    <v-card v-else-if="loading" class="panel-card">
      <v-skeleton-loader type="article, paragraph, paragraph" />
    </v-card>

    <v-card v-else class="panel-card">
      <v-empty-state
        class="empty-state"
        icon="mdi-file-question-outline"
        title="実行結果を表示できません"
        :text="executionStore.error || '指定された実行履歴が見つかりませんでした。'"
      >
        <template #actions>
          <v-btn color="primary" prepend-icon="mdi-arrow-left" to="/executions">実行履歴へ</v-btn>
        </template>
      </v-empty-state>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import AppPageHeader from '@/components/AppPageHeader.vue'
import ExecutionStatusChip from '@/components/ExecutionStatusChip.vue'
import ExecutionTriggerChip from '@/components/ExecutionTriggerChip.vue'
import { useExecutionStore } from '@/stores/execution'

const route = useRoute()
const executionStore = useExecutionStore()

const executionId = computed(() => parseInt(route.params.id as string))
const execution = computed(() => executionStore.currentExecution)
const loading = computed(() => executionStore.loading)
const copiedLog = ref<'stdout' | 'stderr' | null>(null)
const refreshing = ref(false)
const now = ref(Date.now())
let intervalId: ReturnType<typeof setInterval> | null = null
let copyResetId: ReturnType<typeof setTimeout> | null = null

const isActive = computed(() =>
  execution.value?.status === 'running' || execution.value?.status === 'pending'
)

const displayStdout = computed(() => {
  if (execution.value?.stdout) return execution.value.stdout
  if (execution.value?.status === 'pending') return '実行開始を待っています…'
  if (execution.value?.status === 'running') return '標準出力を待っています…'
  return '標準出力はありません。'
})

const displayStderr = computed(() => execution.value?.stderr || execution.value?.error_message || '')

const displayDuration = computed(() => {
  if (
    execution.value?.duration_seconds !== null &&
    execution.value?.duration_seconds !== undefined
  ) {
    return execution.value.duration_seconds
  }
  if (execution.value?.started_at && isActive.value) {
    return Math.max(0, (now.value - new Date(execution.value.started_at).getTime()) / 1000)
  }
  return null
})

const metadata = computed(() => {
  if (!execution.value) return []
  return [
    {
      label: '開始時刻',
      value: execution.value.started_at ? formatDate(execution.value.started_at) : '未開始',
      icon: 'mdi-clock-start',
    },
    {
      label: '終了時刻',
      value: execution.value.finished_at ? formatDate(execution.value.finished_at) : '未完了',
      icon: 'mdi-clock-check-outline',
    },
    {
      label: '所要時間',
      value: formatDuration(displayDuration.value),
      icon: 'mdi-timer-outline',
    },
    {
      label: '終了コード',
      value: execution.value.exit_code === null ? '—' : String(execution.value.exit_code),
      icon: 'mdi-code-tags-check',
    },
    {
      label: '最終同期',
      value: execution.value.last_synced_at ? formatDate(execution.value.last_synced_at) : '同期待ち',
      icon: 'mdi-cloud-sync-outline',
    },
    {
      label: 'リモート PID',
      value: execution.value.remote_process_id === null
        ? '起動待ち'
        : String(execution.value.remote_process_id),
      icon: 'mdi-identifier',
    },
  ]
})

function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat('ja-JP', {
    dateStyle: 'medium',
    timeStyle: 'medium',
  }).format(new Date(dateString))
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return '—'
  if (seconds < 60) return `${seconds.toFixed(1)}秒`
  const minutes = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${minutes}分 ${secs}秒`
}

async function copyLog(value: string, target: 'stdout' | 'stderr') {
  try {
    await navigator.clipboard.writeText(value)
    copiedLog.value = target
    if (copyResetId) clearTimeout(copyResetId)
    copyResetId = setTimeout(() => {
      copiedLog.value = null
    }, 1800)
  } catch (error) {
    console.error('ログのコピーに失敗しました:', error)
  }
}

async function refreshExecution(silent = true) {
  if (refreshing.value) return
  refreshing.value = true
  now.value = Date.now()
  try {
    await executionStore.fetchExecution(executionId.value, silent)
  } catch (error) {
    console.error('実行履歴の更新に失敗しました:', error)
  } finally {
    refreshing.value = false
  }
}

function handleVisibilityChange() {
  if (!document.hidden && isActive.value) {
    void refreshExecution()
  }
}

onMounted(async () => {
  try {
    await executionStore.fetchExecution(executionId.value)

    if (isActive.value) {
      intervalId = setInterval(() => {
        now.value = Date.now()
        if (isActive.value) {
          if (!document.hidden) void refreshExecution()
        } else if (intervalId) {
          clearInterval(intervalId)
          intervalId = null
        }
      }, 2000)
      document.addEventListener('visibilitychange', handleVisibilityChange)
    }
  } catch (error) {
    console.error('実行履歴の取得に失敗しました:', error)
  }
})

onUnmounted(() => {
  if (intervalId) clearInterval(intervalId)
  if (copyResetId) clearTimeout(copyResetId)
  document.removeEventListener('visibilitychange', handleVisibilityChange)
})
</script>

<style scoped>
.back-link {
  margin: -8px 0 18px -12px;
  color: rgb(var(--v-theme-on-surface-variant));
}

.execution-meta {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  padding: 8px;
}

.execution-meta__item {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  padding: 16px;
  border-right: 1px solid rgba(var(--v-border-color), 0.09);
}

.execution-meta__item:nth-child(3n) {
  border-right: 0;
}

.execution-meta__item:nth-child(-n + 3) {
  border-bottom: 1px solid rgba(var(--v-border-color), 0.09);
}

.execution-meta__icon {
  display: grid;
  flex: 0 0 36px;
  width: 36px;
  height: 36px;
  place-items: center;
  color: rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-primary-soft));
  border-radius: 10px;
}

.execution-meta span,
.execution-meta strong {
  display: block;
}

.execution-meta span {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.68rem;
  font-weight: 650;
}

.execution-meta strong {
  margin-top: 3px;
  overflow: hidden;
  font-size: 0.82rem;
  font-variant-numeric: tabular-nums;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tracking-alert__detail {
  display: block;
  margin-top: 4px;
  font-size: 0.78rem;
  opacity: 0.82;
}

.log-card__actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.refresh-state {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  min-height: 32px;
  padding: 0 11px;
  color: rgb(var(--v-theme-info));
  background: rgba(var(--v-theme-info), 0.08);
  border: 1px solid rgba(var(--v-theme-info), 0.16);
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 750;
  white-space: nowrap;
}

.log-card__body {
  padding: 4px 24px 24px !important;
}

.log-output {
  max-height: 620px;
  min-height: 260px;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.log-output--error {
  min-height: 120px;
  color: #ffd4cd;
  background: #2b1d1b;
  border-color: rgba(var(--v-theme-error), 0.28);
}

.log-card--error {
  border-color: rgba(var(--v-theme-error), 0.2) !important;
}

.live-chip :deep(.v-icon) {
  animation: live-pulse 1.6s ease-in-out infinite;
}

@keyframes live-pulse {
  50% {
    opacity: 0.3;
  }
}

@media (max-width: 1100px) {
  .execution-meta {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .execution-meta__item {
    border-right: 1px solid rgba(var(--v-border-color), 0.09);
    border-bottom: 1px solid rgba(var(--v-border-color), 0.09);
  }

  .execution-meta__item:nth-child(2n) {
    border-right: 0;
  }

  .execution-meta__item:nth-last-child(-n + 2) {
    border-bottom: 0;
  }
}

@media (max-width: 599px) {
  .execution-meta {
    grid-template-columns: 1fr;
  }

  .execution-meta__item {
    border-right: 0;
    border-bottom: 1px solid rgba(var(--v-border-color), 0.09);
  }

  .execution-meta__item:last-child {
    border-bottom: 0;
  }

  .log-card__actions {
    justify-content: space-between;
    width: 100%;
  }

  .log-card__body {
    padding: 2px 16px 16px !important;
  }
}

@media (prefers-reduced-motion: reduce) {
  .live-chip :deep(.v-icon) {
    animation: none;
  }
}
</style>

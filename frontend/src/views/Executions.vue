<template>
  <div>
    <AppPageHeader
      eyebrow="Activity"
      icon="mdi-history"
      title="実行履歴"
      description="ジョブの結果、所要時間、終了コードを時系列で追跡します。"
    />

    <v-alert
      v-if="executionStore.error"
      class="mb-6"
      closable
      color="error"
      icon="mdi-alert-circle-outline"
      title="実行履歴を取得できませんでした"
      variant="tonal"
      @click:close="executionStore.clearError()"
    >
      {{ executionStore.error }}
    </v-alert>

    <div class="summary-strip" aria-label="実行履歴の集計">
      <div v-for="summary in summaries" :key="summary.label" class="summary-strip__item">
        <span :class="['summary-strip__signal', `summary-strip__signal--${summary.tone}`]" aria-hidden="true" />
        <span>{{ summary.label }}</span>
        <strong>{{ summary.value }}</strong>
      </div>
    </div>

    <v-card class="panel-card table-card mt-5">
      <v-card-title class="panel-card__header execution-table-header">
        <div>
          <div class="panel-card__title">すべての実行</div>
          <div class="panel-card__subtitle">取得済みの最新{{ executions.length }}件</div>
        </div>
        <v-text-field
          v-model="search"
          aria-label="実行履歴を検索"
          class="execution-search"
          clearable
          density="compact"
          hide-details
          placeholder="ジョブ名で検索"
          prepend-inner-icon="mdi-magnify"
          single-line
        />
      </v-card-title>

      <v-data-table
        :headers="headers"
        :items="executions"
        :loading="loading"
        :search="search"
        :items-per-page="20"
        density="comfortable"
        hover
      >
        <template #item.job="{ item }">
          <router-link class="job-link" :to="`/jobs/${item.job_id}`">
            <span class="job-link__icon" aria-hidden="true"><v-icon icon="mdi-script-text-outline" size="16" /></span>
            {{ item.job?.name || `ジョブ #${item.job_id}` }}
          </router-link>
        </template>

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
            icon="mdi-history"
            :title="search ? '一致する実行がありません' : '実行履歴はまだありません'"
            :text="search ? '検索語を変えてもう一度お試しください。' : 'ジョブを実行すると、ここに結果が表示されます。'"
          />
        </template>
      </v-data-table>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import AppPageHeader from '@/components/AppPageHeader.vue'
import ExecutionStatusChip from '@/components/ExecutionStatusChip.vue'
import { useExecutionStore } from '@/stores/execution'

const executionStore = useExecutionStore()
const search = ref('')

const executions = computed(() => executionStore.executions)
const loading = computed(() => executionStore.loading)
const summaries = computed(() => [
  { label: '総実行', value: executions.value.length, tone: 'primary' },
  { label: '実行中', value: executions.value.filter((item) => item.status === 'running').length, tone: 'info' },
  { label: '成功', value: executions.value.filter((item) => item.status === 'success').length, tone: 'success' },
  { label: '失敗', value: executions.value.filter((item) => item.status === 'failed').length, tone: 'error' },
])

const headers = [
  { title: 'ジョブ', key: 'job', minWidth: 210 },
  { title: 'ステータス', key: 'status', width: 150 },
  { title: '実行日時', key: 'created_at', width: 200 },
  { title: '所要時間', key: 'duration', width: 130 },
  { title: '終了コード', key: 'exit_code', width: 120 },
  { title: '', key: 'actions', sortable: false, align: 'end' as const, width: 72 },
]

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

onMounted(async () => {
  try {
    await executionStore.fetchExecutions(50)
  } catch (error) {
    console.error('実行履歴の取得に失敗しました:', error)
  }
})
</script>

<style scoped>
.summary-strip {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.summary-strip__item {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 40px;
  padding: 8px 13px;
  color: rgb(var(--v-theme-on-surface-variant));
  background: rgb(var(--v-theme-surface));
  border: 1px solid rgba(var(--v-border-color), 0.09);
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 650;
}

.summary-strip__item strong {
  color: rgb(var(--v-theme-on-surface));
  font-family: var(--font-display);
  font-size: 1rem;
}

.summary-strip__signal {
  width: 7px;
  height: 7px;
  background: rgb(var(--v-theme-primary));
  border-radius: 50%;
}

.summary-strip__signal--info {
  background: rgb(var(--v-theme-info));
}

.summary-strip__signal--success {
  background: rgb(var(--v-theme-success));
}

.summary-strip__signal--error {
  background: rgb(var(--v-theme-error));
}

.execution-search {
  flex: 0 1 280px;
}

.job-link {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  text-decoration: none;
}

.job-link:hover {
  text-decoration: underline;
}

.job-link__icon {
  display: grid;
  width: 30px;
  height: 30px;
  place-items: center;
  background: rgb(var(--v-theme-primary-soft));
  border-radius: 8px;
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

@media (max-width: 599px) {
  .execution-table-header,
  .execution-search {
    width: 100%;
  }
}
</style>

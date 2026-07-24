<template>
  <div>
    <AppPageHeader
      eyebrow="Overview"
      icon="mdi-view-dashboard-outline"
      title="ダッシュボード"
      description="登録リソースと直近の実行状況を、ひと目で確認できます。"
    >
      <template #actions>
        <v-btn color="primary" prepend-icon="mdi-play-outline" to="/jobs">ジョブを実行</v-btn>
      </template>
    </AppPageHeader>

    <v-alert
      v-if="loadError"
      class="mb-6"
      closable
      color="error"
      icon="mdi-alert-circle-outline"
      title="データを取得できませんでした"
      variant="tonal"
    >
      {{ loadError }}
    </v-alert>

    <v-row class="metric-grid">
      <v-col v-for="metric in metrics" :key="metric.label" cols="12" sm="6" lg="3">
        <v-card class="metric-card panel-card" height="100%">
          <v-card-text class="metric-card__body">
            <div :class="['metric-card__icon', `metric-card__icon--${metric.tone}`]">
              <v-icon :icon="metric.icon" size="22" />
            </div>
            <div>
              <div class="metric-card__label">{{ metric.label }}</div>
              <div class="metric-card__value">{{ metric.value }}</div>
              <div class="metric-card__hint">{{ metric.hint }}</div>
            </div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-card class="panel-card table-card mt-6">
      <v-card-title class="panel-card__header">
        <div>
          <div class="panel-card__title">最近の実行</div>
          <div class="panel-card__subtitle">新しいものから最大10件を表示</div>
        </div>
        <v-btn color="primary" size="small" to="/executions" variant="text" append-icon="mdi-arrow-right">
          すべて見る
        </v-btn>
      </v-card-title>

      <v-data-table
        :headers="headers"
        :items="latestExecutions"
        :loading="loading"
        :items-per-page="10"
        density="comfortable"
        hover
      >
        <template #item.job_name="{ item }">
          <div class="job-cell">
            <div class="job-cell__mark" aria-hidden="true"><v-icon icon="mdi-script-text-outline" size="17" /></div>
            <span>{{ item.job?.name || `ジョブ #${item.job_id}` }}</span>
          </div>
        </template>

        <template #item.status="{ item }">
          <ExecutionStatusChip :status="item.status" />
        </template>

        <template #item.trigger_source="{ item }">
          <ExecutionTriggerChip :source="item.trigger_source" />
        </template>

        <template #item.created_at="{ item }">
          <span class="date-cell">{{ formatDate(item.created_at) }}</span>
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
            title="実行履歴はまだありません"
            text="ジョブを実行すると、ここに結果が表示されます。"
          />
        </template>
      </v-data-table>
    </v-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import AppPageHeader from '@/components/AppPageHeader.vue'
import ExecutionStatusChip from '@/components/ExecutionStatusChip.vue'
import ExecutionTriggerChip from '@/components/ExecutionTriggerChip.vue'
import { useServerStore } from '@/stores/server'
import { useJobStore } from '@/stores/job'
import { useExecutionStore } from '@/stores/execution'

const serverStore = useServerStore()
const jobStore = useJobStore()
const executionStore = useExecutionStore()

const servers = computed(() => serverStore.servers)
const jobs = computed(() => jobStore.jobs)
const latestExecutions = computed(() => executionStore.latestExecutions)
const loading = computed(() => executionStore.loading)
const loadError = computed(() => serverStore.error || jobStore.error || executionStore.error)

const successCount = computed(() => latestExecutions.value.filter((item) => item.status === 'success').length)
const failedCount = computed(() => latestExecutions.value.filter((item) => item.status === 'failed').length)

const metrics = computed(() => [
  { label: '登録サーバ', value: servers.value.length, hint: '接続先', icon: 'mdi-server-outline', tone: 'primary' },
  { label: '登録ジョブ', value: jobs.value.length, hint: '実行可能', icon: 'mdi-script-text-outline', tone: 'info' },
  { label: '成功', value: successCount.value, hint: '直近10件', icon: 'mdi-check-circle-outline', tone: 'success' },
  { label: '失敗', value: failedCount.value, hint: '要確認', icon: 'mdi-alert-circle-outline', tone: 'error' },
])

const headers = [
  { title: 'ジョブ', key: 'job_name' },
  { title: '実行方法', key: 'trigger_source', width: 120 },
  { title: 'ステータス', key: 'status', width: 150 },
  { title: '実行日時', key: 'created_at', width: 210 },
  { title: '', key: 'actions', sortable: false, align: 'end' as const, width: 72 },
]

function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat('ja-JP', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(dateString))
}

onMounted(async () => {
  try {
    await Promise.all([
      serverStore.fetchServers(),
      jobStore.fetchJobs(),
      executionStore.fetchExecutions(10),
    ])
  } catch (error) {
    console.error('データの取得に失敗しました:', error)
  }
})
</script>

<style scoped>
.metric-grid {
  margin-top: -12px;
}

.metric-card {
  position: relative;
}

.metric-card::after {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 3px;
  background: rgb(var(--v-theme-primary));
  content: "";
  opacity: 0.16;
}

.metric-card__body {
  display: flex;
  align-items: flex-start;
  gap: 18px;
  padding: 24px !important;
}

.metric-card__icon {
  display: grid;
  flex: 0 0 44px;
  width: 44px;
  height: 44px;
  place-items: center;
  color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.09);
  border-radius: 13px;
}

.metric-card__icon--info {
  color: rgb(var(--v-theme-info));
  background: rgba(var(--v-theme-info), 0.09);
}

.metric-card__icon--success {
  color: rgb(var(--v-theme-success));
  background: rgba(var(--v-theme-success), 0.09);
}

.metric-card__icon--error {
  color: rgb(var(--v-theme-error));
  background: rgba(var(--v-theme-error), 0.09);
}

.metric-card__label {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.75rem;
  font-weight: 700;
}

.metric-card__value {
  margin-top: 2px;
  font-family: var(--font-display);
  font-size: 2rem;
  font-weight: 750;
  letter-spacing: -0.04em;
  line-height: 1.15;
}

.metric-card__hint {
  margin-top: 3px;
  color: rgba(var(--v-theme-on-surface), 0.48);
  font-size: 0.7rem;
  font-weight: 600;
}

.job-cell {
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 180px;
  font-weight: 700;
}

.job-cell__mark {
  display: grid;
  width: 32px;
  height: 32px;
  place-items: center;
  color: rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-primary-soft));
  border-radius: 9px;
}

.date-cell {
  color: rgb(var(--v-theme-on-surface-variant));
  font-variant-numeric: tabular-nums;
}
</style>

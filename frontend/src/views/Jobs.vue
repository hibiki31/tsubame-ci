<template>
  <div>
    <AppPageHeader
      eyebrow="Automation"
      icon="mdi-script-text-outline"
      title="ジョブ管理"
      description="繰り返し実行するシェルスクリプトを、接続先ごとに整理します。"
    >
      <template #actions>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">ジョブを追加</v-btn>
      </template>
    </AppPageHeader>

    <v-alert
      v-if="loadError"
      class="mb-6"
      closable
      color="error"
      icon="mdi-alert-circle-outline"
      title="ジョブ情報を取得できませんでした"
      variant="tonal"
      @click:close="clearErrors"
    >
      {{ loadError }}
    </v-alert>

    <v-row v-if="loading && jobs.length === 0" class="job-grid">
      <v-col v-for="index in 3" :key="index" cols="12" md="6" xl="4">
        <v-skeleton-loader class="panel-card" type="heading, paragraph, actions" />
      </v-col>
    </v-row>

    <v-row v-else-if="jobs.length > 0" class="job-grid">
      <v-col v-for="job in jobs" :key="job.id" cols="12" md="6" xl="4">
        <v-card class="job-card panel-card" height="100%">
          <v-card-text class="job-card__body">
            <div class="job-card__heading">
              <div class="job-card__mark" aria-hidden="true">
                <v-icon icon="mdi-console-line" size="21" />
              </div>
              <v-chip size="x-small" variant="tonal">ID {{ job.id }}</v-chip>
            </div>

            <h2 class="job-card__title">{{ job.name }}</h2>
            <p class="job-card__description">{{ job.description || 'このジョブには説明がありません。' }}</p>

            <div class="job-card__meta">
              <div class="job-card__meta-item">
                <v-icon icon="mdi-server-outline" size="17" />
                <div>
                  <span>実行サーバ</span>
                  <strong>{{ job.server?.name || `サーバ #${job.server_id}` }}</strong>
                </div>
              </div>
              <div class="job-card__meta-item">
                <v-icon icon="mdi-calendar-blank-outline" size="17" />
                <div>
                  <span>登録日</span>
                  <strong>{{ formatDate(job.created_at) }}</strong>
                </div>
              </div>
            </div>
          </v-card-text>

          <v-divider />
          <v-card-actions class="job-card__actions">
            <v-btn color="success" prepend-icon="mdi-play" size="small" variant="tonal" @click="executeJob(job)">
              実行
            </v-btn>
            <v-spacer />
            <v-btn
              :aria-label="`${job.name}の詳細を見る`"
              class="icon-action"
              icon="mdi-arrow-top-right"
              size="small"
              variant="text"
              :to="`/jobs/${job.id}`"
            />
            <v-btn
              :aria-label="`${job.name}を編集`"
              class="icon-action"
              icon="mdi-pencil-outline"
              size="small"
              variant="text"
              @click="openEditDialog(job)"
            />
            <v-btn
              :aria-label="`${job.name}を削除`"
              color="error"
              icon="mdi-trash-can-outline"
              size="small"
              variant="text"
              @click="confirmDelete(job)"
            />
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <v-card v-else class="panel-card">
      <v-empty-state
        class="empty-state"
        icon="mdi-script-text-key-outline"
        title="ジョブがまだありません"
        text="サーバを選び、最初のシェルスクリプトを登録しましょう。"
      >
        <template #actions>
          <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">ジョブを追加</v-btn>
        </template>
      </v-empty-state>
    </v-card>

    <v-dialog v-model="dialog" max-width="820">
      <v-card class="dialog-card">
        <v-card-title>{{ editMode ? 'ジョブを編集' : 'ジョブを追加' }}</v-card-title>
        <v-card-subtitle>実行先とシェルスクリプトを設定してください。</v-card-subtitle>
        <v-divider />
        <v-card-text>
          <v-alert
            v-if="servers.length === 0"
            class="mb-5"
            color="warning"
            icon="mdi-server-off"
            variant="tonal"
          >
            先に実行先サーバを登録してください。
            <template #append>
              <v-btn size="small" to="/servers" variant="text" @click="dialog = false">サーバ管理へ</v-btn>
            </template>
          </v-alert>

          <v-form ref="formRef" @submit.prevent="saveJob">
            <div class="form-grid">
              <v-text-field
                v-model="form.name"
                label="ジョブ名"
                placeholder="Deploy frontend"
                :rules="[rules.required]"
                required
              />

              <v-select
                v-model="form.server_id"
                label="実行サーバ"
                :items="serverOptions"
                :rules="[rules.required]"
                required
              />

              <v-textarea
                v-model="form.description"
                class="form-grid__wide"
                label="説明（任意）"
                placeholder="ジョブの目的や実行時の注意事項"
                rows="2"
              />

              <v-textarea
                v-model="form.script"
                auto-grow
                class="form-grid__wide script-field"
                hint="実行前に内容と対象サーバを確認してください"
                label="シェルスクリプト"
                persistent-hint
                placeholder="#!/bin/bash&#10;set -euo pipefail&#10;echo 'Hello, World!'"
                rows="11"
                :rules="[rules.required]"
                required
              />
            </div>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">キャンセル</v-btn>
          <v-btn
            color="primary"
            :disabled="servers.length === 0"
            prepend-icon="mdi-content-save-outline"
            :loading="saving"
            @click="saveJob"
          >
            保存
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="deleteDialog" max-width="460">
      <v-card class="dialog-card">
        <v-card-title>ジョブを削除しますか？</v-card-title>
        <v-card-subtitle>登録したスクリプトが削除されます。</v-card-subtitle>
        <v-card-text>
          <v-alert color="error" icon="mdi-alert-outline" variant="tonal">
            「{{ deleteTarget?.name }}」を削除します。この操作は取り消せません。
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">キャンセル</v-btn>
          <v-btn color="error" prepend-icon="mdi-trash-can-outline" :loading="deleting" @click="deleteJob">
            削除
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="executeDialog" max-width="500">
      <v-card class="dialog-card">
        <v-card-title>ジョブを実行しますか？</v-card-title>
        <v-card-subtitle>対象サーバとジョブ名を確認してください。</v-card-subtitle>
        <v-card-text>
          <div class="execute-summary">
            <div>
              <span>ジョブ</span>
              <strong>{{ executeTarget?.name }}</strong>
            </div>
            <v-icon icon="mdi-arrow-right" color="secondary" />
            <div>
              <span>実行サーバ</span>
              <strong>{{ executeTarget?.server?.name || `サーバ #${executeTarget?.server_id}` }}</strong>
            </div>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="executeDialog = false">キャンセル</v-btn>
          <v-btn color="success" prepend-icon="mdi-play" :loading="executing" @click="confirmExecute">実行</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppPageHeader from '@/components/AppPageHeader.vue'
import { useJobStore } from '@/stores/job'
import { useServerStore } from '@/stores/server'
import type { JobWithServer, JobCreate, JobUpdate } from '@/types'

const router = useRouter()
const jobStore = useJobStore()
const serverStore = useServerStore()

const jobs = computed(() => jobStore.jobs)
const servers = computed(() => serverStore.servers)
const loading = computed(() => jobStore.loading || serverStore.loading)
const loadError = computed(() => jobStore.error || serverStore.error)

const dialog = ref(false)
const deleteDialog = ref(false)
const executeDialog = ref(false)
const editMode = ref(false)
const saving = ref(false)
const deleting = ref(false)
const executing = ref(false)
const deleteTarget = ref<JobWithServer | null>(null)
const executeTarget = ref<JobWithServer | null>(null)
const formRef = ref()
const currentJobId = ref<number | null>(null)

const form = ref({
  name: '',
  description: '',
  script: '',
  server_id: 0,
})

const serverOptions = computed(() => servers.value.map((server) => ({ title: server.name, value: server.id })))

const rules = {
  required: (value: unknown) => !!value || '必須項目です',
}

function clearErrors() {
  jobStore.clearError()
  serverStore.clearError()
}

function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat('ja-JP', { dateStyle: 'medium' }).format(new Date(dateString))
}

function openCreateDialog() {
  editMode.value = false
  currentJobId.value = null
  resetForm()
  dialog.value = true
}

function openEditDialog(job: JobWithServer) {
  editMode.value = true
  currentJobId.value = job.id
  form.value = {
    name: job.name,
    description: job.description || '',
    script: job.script,
    server_id: job.server_id,
  }
  dialog.value = true
}

function resetForm() {
  form.value = {
    name: '',
    description: '',
    script: '',
    server_id: 0,
  }
}

async function saveJob() {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  saving.value = true
  try {
    if (editMode.value && currentJobId.value) {
      const updateData: JobUpdate = {
        name: form.value.name,
        description: form.value.description || undefined,
        script: form.value.script,
        server_id: form.value.server_id,
      }
      await jobStore.updateJob(currentJobId.value, updateData)
    } else {
      const createData: JobCreate = {
        name: form.value.name,
        description: form.value.description || undefined,
        script: form.value.script,
        server_id: form.value.server_id,
      }
      await jobStore.createJob(createData)
    }
    dialog.value = false
    resetForm()
  } catch (error) {
    console.error('ジョブの保存に失敗しました:', error)
  } finally {
    saving.value = false
  }
}

function confirmDelete(job: JobWithServer) {
  deleteTarget.value = job
  deleteDialog.value = true
}

async function deleteJob() {
  if (!deleteTarget.value) return

  deleting.value = true
  try {
    await jobStore.deleteJob(deleteTarget.value.id)
    deleteDialog.value = false
    deleteTarget.value = null
  } catch (error) {
    console.error('ジョブの削除に失敗しました:', error)
  } finally {
    deleting.value = false
  }
}

function executeJob(job: JobWithServer) {
  executeTarget.value = job
  executeDialog.value = true
}

async function confirmExecute() {
  if (!executeTarget.value) return

  executing.value = true
  try {
    const execution = await jobStore.executeJob(executeTarget.value.id)
    executeDialog.value = false
    executeTarget.value = null
    await router.push(`/executions/${execution.id}`)
  } catch (error) {
    console.error('ジョブの実行に失敗しました:', error)
  } finally {
    executing.value = false
  }
}

onMounted(async () => {
  try {
    await Promise.all([serverStore.fetchServers(), jobStore.fetchJobs()])
  } catch (error) {
    console.error('データの取得に失敗しました:', error)
  }
})
</script>

<style scoped>
.job-grid {
  margin-top: -12px;
}

.job-card {
  display: flex;
  flex-direction: column;
}

.job-card__body {
  flex: 1 1 auto;
  padding: 24px !important;
}

.job-card__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}

.job-card__mark {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  color: rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-primary-soft));
  border-radius: 12px;
}

.job-card__title {
  margin: 0;
  font-family: var(--font-display);
  font-size: 1.32rem;
  font-weight: 750;
  letter-spacing: -0.025em;
}

.job-card__description {
  min-height: 3.2em;
  margin: 8px 0 22px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.85rem;
  line-height: 1.6;
}

.job-card__meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.job-card__meta-item {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  min-width: 0;
  padding: 11px 12px;
  background: rgb(var(--v-theme-surface-light));
  border-radius: 10px;
}

.job-card__meta-item .v-icon {
  margin-top: 2px;
  color: rgb(var(--v-theme-secondary));
}

.job-card__meta-item span,
.job-card__meta-item strong {
  display: block;
}

.job-card__meta-item span {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.65rem;
  font-weight: 650;
}

.job-card__meta-item strong {
  margin-top: 2px;
  overflow: hidden;
  font-size: 0.76rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.job-card__actions {
  min-height: 62px;
  padding: 10px 16px !important;
}

.script-field :deep(textarea) {
  font-family: var(--font-mono);
  font-size: 0.79rem;
  line-height: 1.65;
}

.execute-summary {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr);
  align-items: center;
  gap: 14px;
  padding: 18px;
  background: rgb(var(--v-theme-surface-light));
  border: 1px solid rgba(var(--v-border-color), 0.09);
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
  margin-top: 4px;
  font-size: 0.86rem;
}

@media (max-width: 480px) {
  .job-card__meta {
    grid-template-columns: 1fr;
  }

  .execute-summary {
    grid-template-columns: 1fr;
  }

  .execute-summary > .v-icon {
    transform: rotate(90deg);
  }
}
</style>

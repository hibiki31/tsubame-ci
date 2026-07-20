<template>
  <div>
    <div class="d-flex flex-wrap ga-3 justify-space-between align-center mb-6">
      <div>
        <h1 class="text-h4">ジョブ管理</h1>
        <p class="text-body-2 text-medium-emphasis mt-1 mb-0">
          手動実行と GitHub ブランチ変更による自動実行を管理します。
        </p>
      </div>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
        ジョブ追加
      </v-btn>
    </div>

    <v-alert
      v-if="jobStore.error"
      type="error"
      variant="tonal"
      closable
      class="mb-4"
      @click:close="jobStore.clearError()"
    >
      {{ jobStore.error }}
    </v-alert>

    <v-progress-linear
      v-if="loading"
      color="primary"
      indeterminate
      class="mb-4"
      aria-label="ジョブを読み込み中"
    />

    <v-card v-if="!loading && jobs.length === 0" variant="outlined" class="empty-state">
      <v-card-text class="text-center pa-8">
        <v-icon icon="mdi-script-text-outline" size="48" color="medium-emphasis" />
        <h2 class="text-h6 mt-3">ジョブはまだありません</h2>
        <p class="text-body-2 text-medium-emphasis mt-2 mb-4">
          実行先とスクリプト、必要に応じて GitHub トリガーを登録してください。
        </p>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
          最初のジョブを追加
        </v-btn>
      </v-card-text>
    </v-card>

    <v-row v-else>
      <v-col v-for="job in jobs" :key="job.id" cols="12" md="6" lg="4">
        <v-card class="job-card" height="100%">
          <v-card-title>{{ job.name }}</v-card-title>
          <v-card-subtitle>
            <v-icon size="small" class="mr-1">mdi-server</v-icon>
            {{ job.server?.name }}
          </v-card-subtitle>
          <v-card-text class="d-flex flex-column ga-3">
            <p v-if="job.description" class="text-body-2 mb-0">
              {{ job.description }}
            </p>

            <div v-if="job.trigger_type === 'github_poll'" class="trigger-summary">
              <v-chip
                color="info"
                variant="tonal"
                size="small"
                prepend-icon="mdi-source-branch"
                class="trigger-chip"
              >
                {{ job.github_repository }} · {{ job.github_branch }}
              </v-chip>
              <div v-if="job.github_last_error" class="text-caption text-error mt-2">
                <v-icon icon="mdi-alert-circle-outline" size="small" class="mr-1" />
                {{ job.github_last_error }}
              </div>
              <div v-else class="text-caption text-medium-emphasis mt-2">
                {{ formatPollingStatus(job) }}
              </div>
            </div>

            <div class="text-caption text-medium-emphasis">
              作成日: {{ formatDate(job.created_at) }}
            </div>
          </v-card-text>
          <v-card-actions>
            <v-btn
              color="success"
              prepend-icon="mdi-play"
              size="small"
              @click="executeJob(job)"
            >
              実行
            </v-btn>
            <v-spacer />
            <v-btn
              icon="mdi-eye"
              size="small"
              variant="text"
              :to="`/jobs/${job.id}`"
              :aria-label="`${job.name}の詳細`"
            />
            <v-btn
              icon="mdi-pencil"
              size="small"
              variant="text"
              :aria-label="`${job.name}を編集`"
              @click="openEditDialog(job)"
            />
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              :aria-label="`${job.name}を削除`"
              @click="confirmDelete(job)"
            />
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <v-dialog v-model="dialog" max-width="900px">
      <v-card>
        <v-card-title class="d-flex align-center ga-2 pa-5">
          <v-icon :icon="editMode ? 'mdi-pencil' : 'mdi-plus-circle-outline'" />
          {{ editMode ? 'ジョブ編集' : 'ジョブ追加' }}
        </v-card-title>
        <v-divider />
        <v-form ref="formRef" @submit.prevent="saveJob">
          <v-card-text class="pa-5">
            <v-alert v-if="saveError" type="error" variant="tonal" class="mb-5">
              {{ saveError }}
            </v-alert>

            <v-text-field
              v-model="form.name"
              label="ジョブ名"
              :rules="[rules.required]"
              :disabled="saving"
              required
            />

            <v-textarea
              v-model="form.description"
              label="説明"
              rows="2"
              :disabled="saving"
            />

            <v-select
              v-model="form.server_id"
              label="実行サーバ"
              :items="serverOptions"
              :rules="[rules.required]"
              :disabled="saving"
              required
            />

            <v-textarea
              v-model="form.script"
              label="スクリプト"
              rows="9"
              :rules="[rules.required]"
              :disabled="saving"
              required
              placeholder="#!/bin/bash&#10;echo 'Hello, World!'"
            />

            <v-divider class="my-5" />

            <section aria-labelledby="github-trigger-heading">
              <div class="d-flex flex-wrap align-center justify-space-between ga-3">
                <div>
                  <h2 id="github-trigger-heading" class="text-subtitle-1 font-weight-bold">
                    GitHub ブランチ監視
                  </h2>
                  <p class="text-body-2 text-medium-emphasis mb-0">
                    Webhook を公開せず、Backend から GitHub を定期確認します。
                  </p>
                </div>
                <v-switch
                  v-model="form.github_trigger_enabled"
                  color="primary"
                  inset
                  hide-details
                  :disabled="saving"
                  label="自動実行"
                />
              </div>

              <v-expand-transition>
                <div v-if="form.github_trigger_enabled" class="trigger-fields mt-4 pa-4">
                  <v-alert
                    type="info"
                    variant="tonal"
                    density="compact"
                    class="mb-4"
                  >
                    初回確認は現在の commit を基準として記録し、次の変更から実行します。
                  </v-alert>

                  <v-row>
                    <v-col cols="12" md="7">
                      <v-text-field
                        v-model="form.github_repository"
                        label="GitHub リポジトリ"
                        placeholder="owner/repository"
                        prepend-inner-icon="mdi-github"
                        :rules="[rules.required, rules.repository]"
                        :disabled="saving"
                        hint="owner/repository 形式"
                        persistent-hint
                        required
                      />
                    </v-col>
                    <v-col cols="12" md="5">
                      <v-text-field
                        v-model="form.github_branch"
                        label="監視ブランチ"
                        placeholder="main"
                        prepend-inner-icon="mdi-source-branch"
                        :rules="[rules.required, rules.branch]"
                        :disabled="saving"
                        required
                      />
                    </v-col>
                  </v-row>

                  <v-text-field
                    v-model="form.github_token"
                    label="GitHub Personal Access Token（任意）"
                    type="password"
                    autocomplete="new-password"
                    prepend-inner-icon="mdi-key-outline"
                    :disabled="saving"
                    :hint="tokenHint"
                    persistent-hint
                  />
                  <p class="text-caption text-medium-emphasis mt-2 mb-0">
                    private repository では、対象 repository の Contents 読み取り権限を持つ
                    fine-grained token を指定してください。Token は暗号化して保存され、画面や API には返りません。
                  </p>
                </div>
              </v-expand-transition>
            </section>
          </v-card-text>
          <v-divider />
          <v-card-actions class="pa-4">
            <v-spacer />
            <v-btn :disabled="saving" @click="dialog = false">キャンセル</v-btn>
            <v-btn color="primary" type="submit" :loading="saving">保存</v-btn>
          </v-card-actions>
        </v-form>
      </v-card>
    </v-dialog>

    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card>
        <v-card-title>ジョブの削除</v-card-title>
        <v-card-text>
          本当に「{{ deleteTarget?.name }}」を削除しますか？
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn :disabled="deleting" @click="deleteDialog = false">キャンセル</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteJob">削除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="executeDialog" max-width="400px">
      <v-card>
        <v-card-title>ジョブの実行</v-card-title>
        <v-card-text>「{{ executeTarget?.name }}」を実行しますか？</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn :disabled="executing" @click="executeDialog = false">キャンセル</v-btn>
          <v-btn color="success" :loading="executing" @click="confirmExecute">実行</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useJobStore } from '@/stores/job'
import { useServerStore } from '@/stores/server'
import type { Job, JobCreate, JobUpdate, JobWithServer } from '@/types'

interface JobForm {
  name: string
  description: string
  script: string
  server_id: number
  github_trigger_enabled: boolean
  github_repository: string
  github_branch: string
  github_token: string
}

const router = useRouter()
const jobStore = useJobStore()
const serverStore = useServerStore()

const jobs = computed(() => jobStore.jobs)
const servers = computed(() => serverStore.servers)
const loading = computed(() => jobStore.loading)
const serverOptions = computed(() =>
  servers.value.map(server => ({ title: server.name, value: server.id }))
)

const dialog = ref(false)
const deleteDialog = ref(false)
const executeDialog = ref(false)
const editMode = ref(false)
const saving = ref(false)
const deleting = ref(false)
const executing = ref(false)
const saveError = ref<string | null>(null)
const deleteTarget = ref<JobWithServer | null>(null)
const executeTarget = ref<JobWithServer | null>(null)
const currentJobId = ref<number | null>(null)
const currentJobTokenConfigured = ref(false)
const formRef = ref()

const blankForm = (): JobForm => ({
  name: '',
  description: '',
  script: '',
  server_id: 0,
  github_trigger_enabled: false,
  github_repository: '',
  github_branch: 'main',
  github_token: '',
})
const form = ref<JobForm>(blankForm())

const tokenHint = computed(() =>
  editMode.value && currentJobTokenConfigured.value
    ? '設定済みです。変更する場合だけ新しい token を入力してください。'
    : 'public repository では空欄でも利用できます。'
)

const rules = {
  required: (value: unknown) => !!value || '必須項目です',
  repository: (value: string) =>
    /^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})\/[A-Za-z0-9._-]{1,100}$/.test(value)
    || 'owner/repository 形式で入力してください',
  branch: (value: string) => !/\s/.test(value) || 'ブランチ名に空白は使用できません',
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('ja-JP')
}

function formatPollingStatus(job: Job): string {
  if (!job.github_last_checked_at) return '初回確認待ち'
  const checkedAt = new Date(job.github_last_checked_at).toLocaleString('ja-JP')
  const shortSha = job.github_last_commit_sha?.slice(0, 7)
  return shortSha ? `最終確認 ${checkedAt} · ${shortSha}` : `最終確認 ${checkedAt}`
}

function openCreateDialog() {
  editMode.value = false
  currentJobId.value = null
  currentJobTokenConfigured.value = false
  form.value = blankForm()
  saveError.value = null
  dialog.value = true
}

function openEditDialog(job: JobWithServer) {
  editMode.value = true
  currentJobId.value = job.id
  currentJobTokenConfigured.value = job.github_token_configured
  form.value = {
    name: job.name,
    description: job.description || '',
    script: job.script,
    server_id: job.server_id,
    github_trigger_enabled: job.trigger_type === 'github_poll',
    github_repository: job.github_repository || '',
    github_branch: job.github_branch || 'main',
    github_token: '',
  }
  saveError.value = null
  dialog.value = true
}

async function saveJob() {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  saving.value = true
  saveError.value = null
  const triggerFields = form.value.github_trigger_enabled
    ? {
        trigger_type: 'github_poll' as const,
        github_repository: form.value.github_repository,
        github_branch: form.value.github_branch,
        ...(form.value.github_token ? { github_token: form.value.github_token } : {}),
      }
    : { trigger_type: 'manual' as const }

  try {
    if (editMode.value && currentJobId.value) {
      const updateData: JobUpdate = {
        name: form.value.name,
        description: form.value.description || undefined,
        script: form.value.script,
        server_id: form.value.server_id,
        ...triggerFields,
      }
      await jobStore.updateJob(currentJobId.value, updateData)
    } else {
      const createData: JobCreate = {
        name: form.value.name,
        description: form.value.description || undefined,
        script: form.value.script,
        server_id: form.value.server_id,
        ...triggerFields,
      }
      await jobStore.createJob(createData)
    }
    dialog.value = false
    form.value = blankForm()
  } catch (error) {
    saveError.value = error instanceof Error ? error.message : 'ジョブの保存に失敗しました'
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
  } finally {
    executing.value = false
  }
}

onMounted(async () => {
  await Promise.all([
    serverStore.fetchServers(),
    jobStore.fetchJobs(),
  ])
})
</script>

<style scoped>
.job-card {
  display: flex;
  flex-direction: column;
}

.job-card .v-card-text {
  flex: 1;
}

.trigger-summary,
.trigger-fields {
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background: rgba(var(--v-theme-info), 0.04);
}

.trigger-summary {
  padding: 12px;
}

.trigger-chip {
  max-width: 100%;
}

.empty-state {
  border-style: dashed;
}
</style>

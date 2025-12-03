<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-6">
      <h1 class="text-h4">ジョブ管理</h1>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
        ジョブ追加
      </v-btn>
    </div>

    <!-- ジョブ一覧 -->
    <v-row>
      <v-col v-for="job in jobs" :key="job.id" cols="12" md="6" lg="4">
        <v-card>
          <v-card-title>{{ job.name }}</v-card-title>
          <v-card-subtitle>
            <v-icon size="small" class="mr-1">mdi-server</v-icon>
            {{ job.server?.name }}
          </v-card-subtitle>
          <v-card-text>
            <p v-if="job.description" class="text-body-2 mb-2">
              {{ job.description }}
            </p>
            <div class="text-caption text-grey">
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
            <v-spacer></v-spacer>
            <v-btn
              icon="mdi-eye"
              size="small"
              variant="text"
              :to="`/jobs/${job.id}`"
            ></v-btn>
            <v-btn
              icon="mdi-pencil"
              size="small"
              variant="text"
              @click="openEditDialog(job)"
            ></v-btn>
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              @click="confirmDelete(job)"
            ></v-btn>
          </v-card-actions>
        </v-card>
      </v-col>
    </v-row>

    <!-- ジョブ作成/編集ダイアログ -->
    <v-dialog v-model="dialog" max-width="800px">
      <v-card>
        <v-card-title>
          {{ editMode ? 'ジョブ編集' : 'ジョブ追加' }}
        </v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-text-field
              v-model="form.name"
              label="ジョブ名"
              :rules="[rules.required]"
              required
            ></v-text-field>

            <v-textarea
              v-model="form.description"
              label="説明"
              rows="2"
            ></v-textarea>

            <v-select
              v-model="form.server_id"
              label="実行サーバ"
              :items="serverOptions"
              :rules="[rules.required]"
              required
            ></v-select>

            <v-textarea
              v-model="form.script"
              label="スクリプト"
              rows="10"
              :rules="[rules.required]"
              required
              placeholder="#!/bin/bash&#10;echo 'Hello, World!'"
            ></v-textarea>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="dialog = false">キャンセル</v-btn>
          <v-btn color="primary" @click="saveJob" :loading="saving">
            保存
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 削除確認ダイアログ -->
    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card>
        <v-card-title>ジョブの削除</v-card-title>
        <v-card-text>
          本当に「{{ deleteTarget?.name }}」を削除しますか？
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="deleteDialog = false">キャンセル</v-btn>
          <v-btn color="error" @click="deleteJob" :loading="deleting">
            削除
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 実行確認ダイアログ -->
    <v-dialog v-model="executeDialog" max-width="400px">
      <v-card>
        <v-card-title>ジョブの実行</v-card-title>
        <v-card-text>
          「{{ executeTarget?.name }}」を実行しますか？
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="executeDialog = false">キャンセル</v-btn>
          <v-btn color="success" @click="confirmExecute" :loading="executing">
            実行
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useJobStore } from '@/stores/job'
import { useServerStore } from '@/stores/server'
import type { JobWithServer, JobCreate, JobUpdate } from '@/types'

const router = useRouter()
const jobStore = useJobStore()
const serverStore = useServerStore()

const jobs = computed(() => jobStore.jobs)
const servers = computed(() => serverStore.servers)

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

// フォームデータ
const form = ref({
  name: '',
  description: '',
  script: '',
  server_id: 0
})

const currentJobId = ref<number | null>(null)

// サーバ選択肢
const serverOptions = computed(() => 
  servers.value.map(s => ({ title: s.name, value: s.id }))
)

// バリデーションルール
const rules = {
  required: (v: any) => !!v || '必須項目です'
}

// 日付フォーマット
function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleDateString('ja-JP')
}

// ダイアログを開く（新規作成）
function openCreateDialog() {
  editMode.value = false
  currentJobId.value = null
  resetForm()
  dialog.value = true
}

// ダイアログを開く（編集）
function openEditDialog(job: JobWithServer) {
  editMode.value = true
  currentJobId.value = job.id
  form.value = {
    name: job.name,
    description: job.description || '',
    script: job.script,
    server_id: job.server_id
  }
  dialog.value = true
}

// フォームリセット
function resetForm() {
  form.value = {
    name: '',
    description: '',
    script: '',
    server_id: 0
  }
}

// ジョブ保存
async function saveJob() {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  saving.value = true
  try {
    if (editMode.value && currentJobId.value) {
      // 更新
      const updateData: JobUpdate = {
        name: form.value.name,
        description: form.value.description || undefined,
        script: form.value.script,
        server_id: form.value.server_id
      }
      await jobStore.updateJob(currentJobId.value, updateData)
    } else {
      // 新規作成
      const createData: JobCreate = {
        name: form.value.name,
        description: form.value.description || undefined,
        script: form.value.script,
        server_id: form.value.server_id
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

// 削除確認
function confirmDelete(job: JobWithServer) {
  deleteTarget.value = job
  deleteDialog.value = true
}

// ジョブ削除
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

// ジョブ実行確認
function executeJob(job: JobWithServer) {
  executeTarget.value = job
  executeDialog.value = true
}

// ジョブ実行
async function confirmExecute() {
  if (!executeTarget.value) return

  executing.value = true
  try {
    const execution = await jobStore.executeJob(executeTarget.value.id)
    executeDialog.value = false
    executeTarget.value = null
    // 実行詳細画面に遷移
    router.push(`/executions/${execution.id}`)
  } catch (error) {
    console.error('ジョブの実行に失敗しました:', error)
  } finally {
    executing.value = false
  }
}

// 初期データ取得
onMounted(async () => {
  try {
    await Promise.all([
      serverStore.fetchServers(),
      jobStore.fetchJobs()
    ])
  } catch (error) {
    console.error('データの取得に失敗しました:', error)
  }
})
</script>

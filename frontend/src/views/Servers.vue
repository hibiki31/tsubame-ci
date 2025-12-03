<template>
  <div>
    <div class="d-flex justify-space-between align-center mb-6">
      <h1 class="text-h4">サーバ管理</h1>
      <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
        サーバ追加
      </v-btn>
    </div>

    <!-- サーバ一覧テーブル -->
    <v-card>
      <v-card-text>
        <v-data-table
          :headers="headers"
          :items="servers"
          :loading="loading"
          :items-per-page="15"
        >
          <template v-slot:item.auth_method="{ item }">
            <v-chip size="small">
              {{ item.auth_method === 'password' ? 'パスワード' : '秘密鍵' }}
            </v-chip>
          </template>

          <template v-slot:item.created_at="{ item }">
            {{ formatDate(item.created_at) }}
          </template>

          <template v-slot:item.actions="{ item }">
            <v-btn
              icon="mdi-pencil"
              size="small"
              variant="text"
              @click="openEditDialog(item)"
            ></v-btn>
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              @click="confirmDelete(item)"
            ></v-btn>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>

    <!-- サーバ作成/編集ダイアログ -->
    <v-dialog v-model="dialog" max-width="600px">
      <v-card>
        <v-card-title>
          {{ editMode ? 'サーバ編集' : 'サーバ追加' }}
        </v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-text-field
              v-model="form.name"
              label="サーバ名"
              :rules="[rules.required]"
              required
            ></v-text-field>

            <v-textarea
              v-model="form.description"
              label="説明"
              rows="2"
            ></v-textarea>

            <v-text-field
              v-model="form.host"
              label="ホスト"
              :rules="[rules.required]"
              required
            ></v-text-field>

            <v-text-field
              v-model.number="form.port"
              label="ポート"
              type="number"
              :rules="[rules.required]"
              required
            ></v-text-field>

            <v-text-field
              v-model="form.username"
              label="ユーザー名"
              :rules="[rules.required]"
              required
            ></v-text-field>

            <v-select
              v-model="form.auth_method"
              label="認証方式"
              :items="authMethods"
              :rules="[rules.required]"
              required
            ></v-select>

            <v-text-field
              v-if="form.auth_method === 'password'"
              v-model="form.password"
              label="パスワード"
              type="password"
              :rules="editMode ? [] : [rules.required]"
            ></v-text-field>

            <v-textarea
              v-if="form.auth_method === 'key'"
              v-model="form.private_key"
              label="秘密鍵"
              rows="4"
              :rules="editMode ? [] : [rules.required]"
            ></v-textarea>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="dialog = false">キャンセル</v-btn>
          <v-btn color="primary" @click="saveServer" :loading="saving">
            保存
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <!-- 削除確認ダイアログ -->
    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card>
        <v-card-title>サーバの削除</v-card-title>
        <v-card-text>
          本当に「{{ deleteTarget?.name }}」を削除しますか？
        </v-card-text>
        <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn @click="deleteDialog = false">キャンセル</v-btn>
          <v-btn color="error" @click="deleteServer" :loading="deleting">
            削除
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useServerStore } from '@/stores/server'
import type { Server, ServerCreate, ServerUpdate, AuthMethod } from '@/types'

const serverStore = useServerStore()

const servers = computed(() => serverStore.servers)
const loading = computed(() => serverStore.loading)

const dialog = ref(false)
const deleteDialog = ref(false)
const editMode = ref(false)
const saving = ref(false)
const deleting = ref(false)
const deleteTarget = ref<Server | null>(null)
const formRef = ref()

// フォームデータ
const form = ref({
  name: '',
  description: '',
  host: '',
  port: 22,
  username: '',
  auth_method: 'password' as AuthMethod,
  password: '',
  private_key: ''
})

const currentServerId = ref<number | null>(null)

// テーブルヘッダー
const headers = [
  { title: 'サーバ名', key: 'name' },
  { title: 'ホスト', key: 'host' },
  { title: 'ポート', key: 'port' },
  { title: 'ユーザー名', key: 'username' },
  { title: '認証方式', key: 'auth_method' },
  { title: '作成日時', key: 'created_at' },
  { title: '操作', key: 'actions', sortable: false }
]

// 認証方式の選択肢
const authMethods = [
  { title: 'パスワード', value: 'password' },
  { title: '秘密鍵', value: 'key' }
]

// バリデーションルール
const rules = {
  required: (v: any) => !!v || '必須項目です'
}

// 日付フォーマット
function formatDate(dateString: string): string {
  const date = new Date(dateString)
  return date.toLocaleString('ja-JP')
}

// ダイアログを開く（新規作成）
function openCreateDialog() {
  editMode.value = false
  currentServerId.value = null
  resetForm()
  dialog.value = true
}

// ダイアログを開く（編集）
function openEditDialog(server: Server) {
  editMode.value = true
  currentServerId.value = server.id
  form.value = {
    name: server.name,
    description: server.description || '',
    host: server.host,
    port: server.port,
    username: server.username,
    auth_method: server.auth_method,
    password: '',
    private_key: ''
  }
  dialog.value = true
}

// フォームリセット
function resetForm() {
  form.value = {
    name: '',
    description: '',
    host: '',
    port: 22,
    username: '',
    auth_method: 'password',
    password: '',
    private_key: ''
  }
}

// サーバ保存
async function saveServer() {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  saving.value = true
  try {
    if (editMode.value && currentServerId.value) {
      // 更新
      const updateData: ServerUpdate = {
        name: form.value.name,
        description: form.value.description || undefined,
        host: form.value.host,
        port: form.value.port,
        username: form.value.username,
        auth_method: form.value.auth_method
      }
      if (form.value.password) updateData.password = form.value.password
      if (form.value.private_key) updateData.private_key = form.value.private_key

      await serverStore.updateServer(currentServerId.value, updateData)
    } else {
      // 新規作成
      const createData: ServerCreate = {
        name: form.value.name,
        description: form.value.description || undefined,
        host: form.value.host,
        port: form.value.port,
        username: form.value.username,
        auth_method: form.value.auth_method,
        password: form.value.password || undefined,
        private_key: form.value.private_key || undefined
      }
      await serverStore.createServer(createData)
    }
    dialog.value = false
    resetForm()
  } catch (error) {
    console.error('サーバの保存に失敗しました:', error)
  } finally {
    saving.value = false
  }
}

// 削除確認
function confirmDelete(server: Server) {
  deleteTarget.value = server
  deleteDialog.value = true
}

// サーバ削除
async function deleteServer() {
  if (!deleteTarget.value) return

  deleting.value = true
  try {
    await serverStore.deleteServer(deleteTarget.value.id)
    deleteDialog.value = false
    deleteTarget.value = null
  } catch (error) {
    console.error('サーバの削除に失敗しました:', error)
  } finally {
    deleting.value = false
  }
}

// 初期データ取得
onMounted(async () => {
  try {
    await serverStore.fetchServers()
  } catch (error) {
    console.error('サーバ一覧の取得に失敗しました:', error)
  }
})
</script>

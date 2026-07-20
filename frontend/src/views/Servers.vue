<template>
  <div>
    <AppPageHeader
      eyebrow="Infrastructure"
      icon="mdi-server-outline"
      title="サーバ管理"
      description="SSH接続先と認証方式を一元管理します。認証情報は編集画面には再表示されません。"
    >
      <template #actions>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">サーバを追加</v-btn>
      </template>
    </AppPageHeader>

    <v-alert
      v-if="serverStore.error"
      class="mb-6"
      closable
      color="error"
      icon="mdi-server-off"
      title="サーバ情報を取得できませんでした"
      variant="tonal"
      @click:close="serverStore.clearError()"
    >
      {{ serverStore.error }}
    </v-alert>

    <v-card class="panel-card table-card">
      <v-card-title class="panel-card__header">
        <div>
          <div class="panel-card__title">接続先</div>
          <div class="panel-card__subtitle">{{ servers.length }}台のサーバを登録済み</div>
        </div>
        <v-chip color="primary" prepend-icon="mdi-shield-key-outline" size="small" variant="tonal">
          暗号化して保存
        </v-chip>
      </v-card-title>

      <v-data-table
        :headers="headers"
        :items="servers"
        :loading="loading"
        :items-per-page="15"
        density="comfortable"
        hover
      >
        <template #item.name="{ item }">
          <div class="server-cell">
            <div class="server-cell__icon" aria-hidden="true"><v-icon icon="mdi-server" size="18" /></div>
            <div>
              <div class="server-cell__name">{{ item.name }}</div>
              <div class="server-cell__description">{{ item.description || '説明なし' }}</div>
            </div>
          </div>
        </template>

        <template #item.endpoint="{ item }">
          <code class="endpoint-cell">{{ item.username }}@{{ item.host }}:{{ item.port }}</code>
        </template>

        <template #item.auth_method="{ item }">
          <v-chip
            :prepend-icon="item.auth_method === 'password' ? 'mdi-form-textbox-password' : 'mdi-key-chain-variant'"
            size="small"
            variant="tonal"
          >
            {{ item.auth_method === 'password' ? 'パスワード' : '秘密鍵' }}
          </v-chip>
        </template>

        <template #item.created_at="{ item }">
          <span class="date-cell">{{ formatDate(item.created_at) }}</span>
        </template>

        <template #item.actions="{ item }">
          <div class="action-group">
            <v-btn
              :aria-label="`${item.name}を編集`"
              class="icon-action"
              icon="mdi-pencil-outline"
              size="small"
              variant="text"
              @click="openEditDialog(item)"
            />
            <v-btn
              :aria-label="`${item.name}を削除`"
              color="error"
              icon="mdi-trash-can-outline"
              size="small"
              variant="text"
              @click="confirmDelete(item)"
            />
          </div>
        </template>

        <template #no-data>
          <v-empty-state
            class="empty-state"
            icon="mdi-server-plus"
            title="サーバが登録されていません"
            text="最初のSSH接続先を登録して、ジョブの実行準備を始めましょう。"
          >
            <template #actions>
              <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">サーバを追加</v-btn>
            </template>
          </v-empty-state>
        </template>
      </v-data-table>
    </v-card>

    <v-dialog v-model="dialog" max-width="760">
      <v-card class="dialog-card">
        <v-card-title>{{ editMode ? 'サーバを編集' : 'サーバを追加' }}</v-card-title>
        <v-card-subtitle>
          {{ editMode ? '接続情報を更新します。認証情報は変更する場合のみ入力してください。' : 'SSH接続に必要な情報を入力してください。' }}
        </v-card-subtitle>
        <v-divider />
        <v-card-text>
          <v-form ref="formRef" @submit.prevent="saveServer">
            <div class="form-grid">
              <v-text-field
                v-model="form.name"
                class="form-grid__wide"
                label="サーバ名"
                placeholder="Production Web 01"
                :rules="[rules.required]"
                required
              />

              <v-textarea
                v-model="form.description"
                class="form-grid__wide"
                label="説明（任意）"
                placeholder="用途や管理担当など"
                rows="2"
              />

              <v-text-field
                v-model="form.host"
                label="ホスト"
                placeholder="192.0.2.10"
                :rules="[rules.required]"
                required
              />

              <v-text-field
                v-model.number="form.port"
                label="ポート"
                min="1"
                max="65535"
                type="number"
                :rules="[rules.required]"
                required
              />

              <v-text-field
                v-model="form.username"
                autocomplete="username"
                label="ユーザー名"
                :rules="[rules.required]"
                required
              />

              <v-select
                v-model="form.auth_method"
                label="認証方式"
                :items="authMethods"
                :rules="[rules.required]"
                required
              />

              <v-text-field
                v-if="form.auth_method === 'password'"
                v-model="form.password"
                autocomplete="new-password"
                class="form-grid__wide"
                :hint="editMode ? '変更しない場合は空欄のままにしてください' : undefined"
                label="パスワード"
                :persistent-hint="editMode"
                :rules="editMode ? [] : [rules.required]"
                :type="passwordVisible ? 'text' : 'password'"
              >
                <template #append-inner>
                  <v-btn
                    :aria-label="passwordVisible ? 'パスワードを隠す' : 'パスワードを表示'"
                    :icon="passwordVisible ? 'mdi-eye-off-outline' : 'mdi-eye-outline'"
                    size="x-small"
                    variant="text"
                    @click="passwordVisible = !passwordVisible"
                  />
                </template>
              </v-text-field>

              <v-textarea
                v-if="form.auth_method === 'key'"
                v-model="form.private_key"
                class="form-grid__wide private-key-field"
                :hint="editMode ? '変更しない場合は空欄のままにしてください' : 'PEM形式の秘密鍵を貼り付けてください'"
                label="秘密鍵"
                persistent-hint
                rows="7"
                :rules="editMode ? [] : [rules.required]"
              />
            </div>
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="dialog = false">キャンセル</v-btn>
          <v-btn color="primary" prepend-icon="mdi-content-save-outline" :loading="saving" @click="saveServer">
            保存
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="deleteDialog" max-width="460">
      <v-card class="dialog-card">
        <v-card-title>サーバを削除しますか？</v-card-title>
        <v-card-subtitle>この操作は取り消せません。</v-card-subtitle>
        <v-card-text>
          <v-alert color="error" icon="mdi-alert-outline" variant="tonal">
            「{{ deleteTarget?.name }}」を登録済み接続先から削除します。
          </v-alert>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" @click="deleteDialog = false">キャンセル</v-btn>
          <v-btn color="error" prepend-icon="mdi-trash-can-outline" :loading="deleting" @click="deleteServer">
            削除
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import AppPageHeader from '@/components/AppPageHeader.vue'
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
const passwordVisible = ref(false)
const deleteTarget = ref<Server | null>(null)
const formRef = ref()
const currentServerId = ref<number | null>(null)

const form = ref({
  name: '',
  description: '',
  host: '',
  port: 22,
  username: '',
  auth_method: 'password' as AuthMethod,
  password: '',
  private_key: '',
})

const headers = [
  { title: 'サーバ', key: 'name', minWidth: 220 },
  { title: '接続先', key: 'endpoint', minWidth: 220 },
  { title: '認証方式', key: 'auth_method', width: 160 },
  { title: '登録日', key: 'created_at', width: 150 },
  { title: '', key: 'actions', sortable: false, align: 'end' as const, width: 110 },
]

const authMethods = [
  { title: 'パスワード', value: 'password' },
  { title: '秘密鍵', value: 'key' },
]

const rules = {
  required: (value: unknown) => !!value || '必須項目です',
}

function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat('ja-JP', { dateStyle: 'medium' }).format(new Date(dateString))
}

function openCreateDialog() {
  editMode.value = false
  currentServerId.value = null
  passwordVisible.value = false
  resetForm()
  dialog.value = true
}

function openEditDialog(server: Server) {
  editMode.value = true
  currentServerId.value = server.id
  passwordVisible.value = false
  form.value = {
    name: server.name,
    description: server.description || '',
    host: server.host,
    port: server.port,
    username: server.username,
    auth_method: server.auth_method,
    password: '',
    private_key: '',
  }
  dialog.value = true
}

function resetForm() {
  form.value = {
    name: '',
    description: '',
    host: '',
    port: 22,
    username: '',
    auth_method: 'password',
    password: '',
    private_key: '',
  }
}

async function saveServer() {
  const { valid } = await formRef.value.validate()
  if (!valid) return

  saving.value = true
  try {
    if (editMode.value && currentServerId.value) {
      const updateData: ServerUpdate = {
        name: form.value.name,
        description: form.value.description || undefined,
        host: form.value.host,
        port: form.value.port,
        username: form.value.username,
        auth_method: form.value.auth_method,
      }
      if (form.value.password) updateData.password = form.value.password
      if (form.value.private_key) updateData.private_key = form.value.private_key
      await serverStore.updateServer(currentServerId.value, updateData)
    } else {
      const createData: ServerCreate = {
        name: form.value.name,
        description: form.value.description || undefined,
        host: form.value.host,
        port: form.value.port,
        username: form.value.username,
        auth_method: form.value.auth_method,
        password: form.value.password || undefined,
        private_key: form.value.private_key || undefined,
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

function confirmDelete(server: Server) {
  deleteTarget.value = server
  deleteDialog.value = true
}

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

onMounted(async () => {
  try {
    await serverStore.fetchServers()
  } catch (error) {
    console.error('サーバ一覧の取得に失敗しました:', error)
  }
})
</script>

<style scoped>
.server-cell {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 220px;
  padding-block: 5px;
}

.server-cell__icon {
  display: grid;
  flex: 0 0 36px;
  width: 36px;
  height: 36px;
  place-items: center;
  color: rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-primary-soft));
  border-radius: 10px;
}

.server-cell__name {
  font-weight: 750;
}

.server-cell__description {
  max-width: 240px;
  margin-top: 2px;
  overflow: hidden;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.74rem;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.endpoint-cell {
  padding: 5px 8px;
  color: rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-primary-soft));
  border-radius: 7px;
  font-family: var(--font-mono);
  font-size: 0.76rem;
  white-space: nowrap;
}

.date-cell {
  color: rgb(var(--v-theme-on-surface-variant));
  font-variant-numeric: tabular-nums;
}

.action-group {
  display: flex;
  justify-content: flex-end;
  gap: 2px;
}

.private-key-field :deep(textarea) {
  font-family: var(--font-mono);
  font-size: 0.78rem;
}
</style>

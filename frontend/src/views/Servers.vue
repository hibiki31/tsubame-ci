<template>
  <div class="server-page">
    <header class="d-flex flex-wrap justify-space-between align-start ga-4 mb-6">
      <div>
        <div class="text-overline text-medium-emphasis">INFRASTRUCTURE</div>
        <h1 class="text-h4 font-weight-bold">サーバ管理</h1>
        <p class="text-body-2 text-medium-emphasis mt-1 mb-0">
          接続状態とマシン構成をひとつの画面で監視します。
        </p>
      </div>
      <div class="d-flex align-center ga-3">
        <v-chip
          :color="monitoring?.enabled ? 'success' : 'default'"
          :prepend-icon="monitoring?.enabled ? 'mdi-radar' : 'mdi-radar-off'"
          variant="tonal"
        >
          {{ monitoringLabel }}
        </v-chip>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">
          サーバ追加
        </v-btn>
      </div>
    </header>

    <v-row class="mb-3" dense>
      <v-col cols="6" sm="3">
        <v-card class="summary-card" variant="outlined">
          <v-card-text>
            <div class="summary-label">登録</div>
            <div class="summary-value">{{ servers.length }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card class="summary-card summary-card--online" variant="outlined">
          <v-card-text>
            <div class="summary-label">ONLINE</div>
            <div class="summary-value">{{ onlineCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card class="summary-card summary-card--offline" variant="outlined">
          <v-card-text>
            <div class="summary-label">OFFLINE</div>
            <div class="summary-value">{{ offlineCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card class="summary-card summary-card--unknown" variant="outlined">
          <v-card-text>
            <div class="summary-label">未確認</div>
            <div class="summary-value">{{ unknownCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

    <v-alert
      v-if="error"
      class="mb-4"
      type="error"
      variant="tonal"
      closable
      @click:close="serverStore.clearError"
    >
      {{ error }}
    </v-alert>

    <v-card class="server-table" variant="outlined">
      <v-data-table
        :headers="headers"
        :items="servers"
        :loading="loading"
        :items-per-page="15"
        item-value="id"
        show-expand
        hover
      >
        <template #item.connection_status="{ item }">
          <v-chip
            :color="statusMeta(item.connection_status).color"
            :prepend-icon="statusMeta(item.connection_status).icon"
            size="small"
            variant="tonal"
          >
            {{ statusMeta(item.connection_status).label }}
          </v-chip>
        </template>

        <template #item.name="{ item }">
          <div class="py-2">
            <div class="font-weight-bold">{{ item.name }}</div>
            <div class="text-caption text-medium-emphasis server-description">
              {{ item.description || '説明なし' }}
            </div>
          </div>
        </template>

        <template #item.host="{ item }">
          <code class="connection-address">{{ item.username }}@{{ item.host }}:{{ item.port }}</code>
        </template>

        <template #item.environment="{ item }">
          <div v-if="item.software_info || item.hardware_info" class="py-1">
            <div>{{ item.software_info?.os_name || 'Linux' }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ item.hardware_info?.architecture || 'architecture 未取得' }}
            </div>
          </div>
          <span v-else class="text-medium-emphasis">—</span>
        </template>

        <template #item.last_checked_at="{ item }">
          <div v-if="item.last_checked_at" class="py-1">
            <div>{{ formatRelativeDate(item.last_checked_at) }}</div>
            <div class="text-caption text-medium-emphasis">
              {{ item.last_check_latency_ms !== null ? `${item.last_check_latency_ms} ms` : '応答なし' }}
            </div>
          </div>
          <span v-else class="text-medium-emphasis">確認待ち</span>
        </template>

        <template #item.actions="{ item }">
          <div class="d-flex flex-nowrap justify-end">
            <v-btn
              icon="mdi-refresh"
              size="small"
              variant="text"
              :loading="checkingServerIds.includes(item.id)"
              :aria-label="`${item.name}を接続確認`"
              title="今すぐ接続確認"
              @click="checkServer(item)"
            />
            <v-btn
              icon="mdi-pencil"
              size="small"
              variant="text"
              :aria-label="`${item.name}を編集`"
              title="編集"
              @click="openEditDialog(item)"
            />
            <v-btn
              icon="mdi-delete"
              size="small"
              variant="text"
              color="error"
              :aria-label="`${item.name}を削除`"
              title="削除"
              @click="confirmDelete(item)"
            />
          </div>
        </template>

        <template #expanded-row="{ columns, item }">
          <tr class="inventory-row">
            <td :colspan="columns.length">
              <div class="inventory-panel pa-4 pa-md-6">
                <div class="d-flex flex-wrap justify-space-between align-center ga-2 mb-4">
                  <div>
                    <div class="text-subtitle-1 font-weight-bold">{{ item.name }} のシステム情報</div>
                    <div class="text-caption text-medium-emphasis">
                      構成取得: {{ item.inventory_collected_at ? formatDate(item.inventory_collected_at) : '未取得' }}
                    </div>
                  </div>
                  <v-chip size="small" variant="outlined" prepend-icon="mdi-shield-key-outline">
                    {{ item.auth_method === 'password' ? 'パスワード認証' : '秘密鍵認証' }}
                  </v-chip>
                </div>

                <v-alert
                  v-if="item.last_check_error"
                  class="mb-4"
                  type="warning"
                  variant="tonal"
                  density="compact"
                >
                  {{ item.last_check_error }}
                </v-alert>

                <v-row>
                  <v-col cols="12" md="6">
                    <section class="inventory-section" :aria-labelledby="`hardware-title-${item.id}`">
                      <h2 :id="`hardware-title-${item.id}`" class="inventory-title">
                        <v-icon icon="mdi-memory" size="18" />
                        ハードウェア
                      </h2>
                      <dl class="detail-list">
                        <dt>ホスト名</dt><dd>{{ valueOrDash(item.hardware_info?.hostname) }}</dd>
                        <dt>CPU</dt><dd>{{ valueOrDash(item.hardware_info?.cpu_model) }}</dd>
                        <dt>論理コア</dt><dd>{{ item.hardware_info?.cpu_cores ?? '—' }}</dd>
                        <dt>メモリ</dt><dd>{{ formatBytes(item.hardware_info?.memory_total_bytes) }}</dd>
                        <dt>ルートディスク</dt><dd>{{ formatBytes(item.hardware_info?.disk_total_bytes) }}</dd>
                        <dt>アーキテクチャ</dt><dd>{{ valueOrDash(item.hardware_info?.architecture) }}</dd>
                      </dl>
                    </section>
                  </v-col>
                  <v-col cols="12" md="6">
                    <section class="inventory-section" :aria-labelledby="`software-title-${item.id}`">
                      <h2 :id="`software-title-${item.id}`" class="inventory-title">
                        <v-icon icon="mdi-console-line" size="18" />
                        ソフトウェア
                      </h2>
                      <dl class="detail-list">
                        <dt>OS</dt><dd>{{ osLabel(item) }}</dd>
                        <dt>カーネル</dt><dd>{{ valueOrDash(item.software_info?.kernel) }}</dd>
                        <dt>パッケージ管理</dt><dd>{{ valueOrDash(item.software_info?.package_manager) }}</dd>
                        <dt>Python</dt><dd>{{ valueOrDash(item.software_info?.python_version) }}</dd>
                        <dt>Docker</dt><dd>{{ valueOrDash(item.software_info?.docker_version) }}</dd>
                        <dt>Git</dt><dd>{{ valueOrDash(item.software_info?.git_version) }}</dd>
                      </dl>
                    </section>
                  </v-col>
                </v-row>
              </div>
            </td>
          </tr>
        </template>

        <template #no-data>
          <div class="py-10 text-center">
            <v-icon icon="mdi-server-off" size="36" class="mb-3 text-medium-emphasis" />
            <div class="font-weight-medium">登録されたサーバはありません</div>
            <div class="text-body-2 text-medium-emphasis mt-1">サーバを追加すると自動監視が始まります。</div>
          </div>
        </template>
      </v-data-table>
    </v-card>

    <v-dialog v-model="dialog" max-width="600px">
      <v-card>
        <v-card-title>{{ editMode ? 'サーバ編集' : 'サーバ追加' }}</v-card-title>
        <v-card-text>
          <v-form ref="formRef">
            <v-text-field v-model="form.name" label="サーバ名" :rules="[rules.required]" required />
            <v-textarea v-model="form.description" label="説明" rows="2" />
            <v-text-field v-model="form.host" label="ホスト" :rules="[rules.required]" required />
            <v-text-field
              v-model.number="form.port"
              label="ポート"
              type="number"
              :rules="[rules.required, rules.port]"
              required
            />
            <v-text-field v-model="form.username" label="ユーザー名" :rules="[rules.required]" required />
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
              label="パスワード"
              type="password"
              :hint="editMode ? '変更する場合だけ入力してください' : undefined"
              persistent-hint
              :rules="editMode ? [] : [rules.required]"
            />
            <v-textarea
              v-if="form.auth_method === 'key'"
              v-model="form.private_key"
              label="秘密鍵"
              rows="4"
              :hint="editMode ? '変更する場合だけ入力してください' : undefined"
              persistent-hint
              :rules="editMode ? [] : [rules.required]"
            />
          </v-form>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="dialog = false">キャンセル</v-btn>
          <v-btn color="primary" :loading="saving" @click="saveServer">保存</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>

    <v-dialog v-model="deleteDialog" max-width="400px">
      <v-card>
        <v-card-title>サーバの削除</v-card-title>
        <v-card-text>本当に「{{ deleteTarget?.name }}」を削除しますか？</v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn @click="deleteDialog = false">キャンセル</v-btn>
          <v-btn color="error" :loading="deleting" @click="deleteServer">削除</v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useServerStore } from '@/stores/server'
import type {
  AuthMethod,
  Server,
  ServerConnectionStatus,
  ServerCreate,
  ServerUpdate
} from '@/types'

const serverStore = useServerStore()
const servers = computed(() => serverStore.servers)
const loading = computed(() => serverStore.loading)
const error = computed(() => serverStore.error)
const monitoring = computed(() => serverStore.monitoring)
const onlineCount = computed(() => servers.value.filter(server => server.connection_status === 'online').length)
const offlineCount = computed(() => servers.value.filter(server => server.connection_status === 'offline').length)
const unknownCount = computed(() => servers.value.filter(server => server.connection_status === 'unknown').length)
const monitoringLabel = computed(() => {
  if (!monitoring.value) return '監視設定を確認中'
  if (!monitoring.value.enabled) return '自動監視は停止中'
  return `${formatDuration(monitoring.value.check_interval_seconds)}ごとに自動確認`
})

const dialog = ref(false)
const deleteDialog = ref(false)
const editMode = ref(false)
const saving = ref(false)
const deleting = ref(false)
const deleteTarget = ref<Server | null>(null)
const formRef = ref()
const checkingServerIds = ref<number[]>([])
let refreshTimer: ReturnType<typeof setInterval> | undefined

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

const headers = [
  { title: '状態', key: 'connection_status', width: 128 },
  { title: 'サーバ', key: 'name', minWidth: 180 },
  { title: '接続先', key: 'host', minWidth: 220 },
  { title: '環境', key: 'environment', minWidth: 150, sortable: false },
  { title: '最終確認', key: 'last_checked_at', minWidth: 150 },
  { title: '', key: 'actions', align: 'end' as const, sortable: false, width: 136 }
]

const authMethods = [
  { title: 'パスワード', value: 'password' },
  { title: '秘密鍵', value: 'key' }
]

const rules = {
  required: (value: unknown) => !!value || '必須項目です',
  port: (value: number) => (value >= 1 && value <= 65535) || '1〜65535で入力してください'
}

function statusMeta(status: ServerConnectionStatus) {
  const metadata = {
    online: { label: 'ONLINE', color: 'success', icon: 'mdi-check-circle' },
    offline: { label: 'OFFLINE', color: 'error', icon: 'mdi-alert-circle' },
    unknown: { label: '未確認', color: 'default', icon: 'mdi-help-circle' }
  }
  return metadata[status]
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleString('ja-JP')
}

function formatRelativeDate(dateString: string): string {
  const elapsedSeconds = Math.max(0, Math.floor((Date.now() - new Date(dateString).getTime()) / 1000))
  if (elapsedSeconds < 60) return `${elapsedSeconds}秒前`
  if (elapsedSeconds < 3600) return `${Math.floor(elapsedSeconds / 60)}分前`
  if (elapsedSeconds < 86400) return `${Math.floor(elapsedSeconds / 3600)}時間前`
  return formatDate(dateString)
}

function formatDuration(seconds: number): string {
  if (seconds % 3600 === 0) return `${seconds / 3600}時間`
  if (seconds % 60 === 0) return `${seconds / 60}分`
  return `${seconds}秒`
}

function formatBytes(value?: number | null): string {
  if (value === undefined || value === null) return '—'
  const units = ['B', 'KB', 'GB', 'TB']
  let size = value
  let unitIndex = 0
  while (size >= 1000 && unitIndex < units.length - 1) {
    size /= 1000
    unitIndex += 1
  }
  return `${size.toLocaleString('ja-JP', { maximumFractionDigits: 1 })} ${units[unitIndex]}`
}

function valueOrDash(value?: string | null): string {
  return value || '—'
}

function osLabel(server: Server): string {
  const os = server.software_info
  if (!os) return '—'
  return [os.os_name, os.os_version].filter(Boolean).join(' ') || '—'
}

function openCreateDialog() {
  editMode.value = false
  currentServerId.value = null
  resetForm()
  dialog.value = true
}

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
        auth_method: form.value.auth_method
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
        private_key: form.value.private_key || undefined
      }
      await serverStore.createServer(createData)
    }
    dialog.value = false
    resetForm()
  } catch (saveError) {
    console.error('サーバの保存に失敗しました:', saveError)
  } finally {
    saving.value = false
  }
}

async function checkServer(server: Server) {
  if (checkingServerIds.value.includes(server.id)) return
  checkingServerIds.value = [...checkingServerIds.value, server.id]
  try {
    await serverStore.checkServer(server.id)
  } catch (checkError) {
    console.error('サーバの接続確認に失敗しました:', checkError)
  } finally {
    checkingServerIds.value = checkingServerIds.value.filter(id => id !== server.id)
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
  } catch (deleteError) {
    console.error('サーバの削除に失敗しました:', deleteError)
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  try {
    await Promise.all([serverStore.fetchServers(), serverStore.fetchMonitoring()])
  } catch (fetchError) {
    console.error('サーバ監視情報の取得に失敗しました:', fetchError)
  }

  refreshTimer = setInterval(() => {
    serverStore.fetchServers(true).catch(refreshError => {
      console.error('サーバ監視情報の更新に失敗しました:', refreshError)
    })
  }, 30000)
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.server-page {
  --monitor-online: #15805d;
  --monitor-offline: #c33d45;
  --monitor-unknown: #707782;
  max-width: 1600px;
  margin: 0 auto;
}

.summary-card {
  border-top: 3px solid rgb(var(--v-theme-primary));
}

.summary-card--online {
  border-top-color: var(--monitor-online);
}

.summary-card--offline {
  border-top-color: var(--monitor-offline);
}

.summary-card--unknown {
  border-top-color: var(--monitor-unknown);
}

.summary-label {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.09em;
}

.summary-value {
  margin-top: 0.2rem;
  font-size: clamp(1.65rem, 4vw, 2.2rem);
  font-variant-numeric: tabular-nums;
  font-weight: 700;
  line-height: 1.1;
}

.server-table {
  overflow: hidden;
}

.server-description {
  max-width: 28ch;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.connection-address {
  padding: 0.25rem 0.45rem;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 4px;
  background: rgba(var(--v-theme-on-surface), 0.035);
  font-size: 0.78rem;
}

.inventory-row {
  background: rgba(var(--v-theme-primary), 0.035);
}

.inventory-panel {
  border-top: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
}

.inventory-section {
  height: 100%;
  padding: 1rem;
  border: 1px solid rgba(var(--v-border-color), var(--v-border-opacity));
  border-radius: 8px;
  background: rgb(var(--v-theme-surface));
}

.inventory-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.9rem;
  font-size: 0.82rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.detail-list {
  display: grid;
  grid-template-columns: minmax(7rem, 0.7fr) minmax(0, 1.6fr);
  gap: 0.55rem 1rem;
  margin: 0;
  font-size: 0.86rem;
}

.detail-list dt {
  color: rgb(var(--v-theme-on-surface-variant));
}

.detail-list dd {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
  font-weight: 500;
}

@media (max-width: 600px) {
  .detail-list {
    grid-template-columns: 1fr;
    gap: 0.15rem;
  }

  .detail-list dd {
    margin-bottom: 0.65rem;
  }
}
</style>

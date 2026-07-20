<template>
  <div>
    <AppPageHeader
      eyebrow="Infrastructure"
      icon="mdi-server-outline"
      title="サーバ管理"
      description="SSH接続先の稼働状態とマシン構成を一元管理します。認証情報は編集画面には再表示されません。"
    >
      <template #actions>
        <v-chip
          :color="monitoring?.enabled ? 'success' : 'default'"
          :prepend-icon="monitoring?.enabled ? 'mdi-radar' : 'mdi-radar-off'"
          variant="tonal"
        >
          {{ monitoringLabel }}
        </v-chip>
        <v-btn color="primary" prepend-icon="mdi-plus" @click="openCreateDialog">サーバを追加</v-btn>
      </template>
    </AppPageHeader>

    <v-row class="monitor-summary mb-6" dense>
      <v-col cols="6" sm="3">
        <v-card class="monitor-metric monitor-metric--registered">
          <v-card-text>
            <div class="monitor-metric__label">登録サーバ</div>
            <div class="monitor-metric__value">{{ servers.length }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card class="monitor-metric monitor-metric--online">
          <v-card-text>
            <div class="monitor-metric__label">ONLINE</div>
            <div class="monitor-metric__value">{{ onlineCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card class="monitor-metric monitor-metric--offline">
          <v-card-text>
            <div class="monitor-metric__label">OFFLINE</div>
            <div class="monitor-metric__value">{{ offlineCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>
      <v-col cols="6" sm="3">
        <v-card class="monitor-metric monitor-metric--unknown">
          <v-card-text>
            <div class="monitor-metric__label">未確認</div>
            <div class="monitor-metric__value">{{ unknownCount }}</div>
          </v-card-text>
        </v-card>
      </v-col>
    </v-row>

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
          <div class="panel-card__title">接続先と稼働状態</div>
          <div class="panel-card__subtitle">行を展開するとハードウェアとソフトウェアの詳細を確認できます</div>
        </div>
        <v-chip color="primary" prepend-icon="mdi-shield-key-outline" size="small" variant="tonal">
          認証情報は暗号化して保存
        </v-chip>
      </v-card-title>

      <v-data-table
        :headers="headers"
        :items="servers"
        :loading="loading"
        :items-per-page="15"
        density="comfortable"
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

        <template #item.environment="{ item }">
          <div v-if="item.software_info || item.hardware_info" class="environment-cell">
            <div>{{ item.software_info?.os_name || 'Linux' }}</div>
            <div>{{ item.hardware_info?.architecture || 'architecture 未取得' }}</div>
          </div>
          <span v-else class="date-cell">—</span>
        </template>

        <template #item.last_checked_at="{ item }">
          <div v-if="item.last_checked_at" class="check-time-cell">
            <div>{{ formatRelativeDate(item.last_checked_at) }}</div>
            <div>{{ item.last_check_latency_ms !== null ? `${item.last_check_latency_ms} ms` : '応答なし' }}</div>
          </div>
          <span v-else class="date-cell">確認待ち</span>
        </template>

        <template #item.actions="{ item }">
          <div class="action-group">
            <v-btn
              :aria-label="`${item.name}を接続確認`"
              class="icon-action"
              icon="mdi-refresh"
              size="small"
              title="今すぐ接続確認"
              variant="text"
              :loading="checkingServerIds.includes(item.id)"
              @click="checkServer(item)"
            />
            <v-btn
              :aria-label="`${item.name}を編集`"
              class="icon-action"
              icon="mdi-pencil-outline"
              size="small"
              title="編集"
              variant="text"
              @click="openEditDialog(item)"
            />
            <v-btn
              :aria-label="`${item.name}を削除`"
              color="error"
              icon="mdi-trash-can-outline"
              size="small"
              title="削除"
              variant="text"
              @click="confirmDelete(item)"
            />
          </div>
        </template>

        <template #expanded-row="{ columns, item }">
          <tr class="inventory-row">
            <td :colspan="columns.length">
              <div class="inventory-panel">
                <div class="inventory-panel__header">
                  <div>
                    <div class="inventory-panel__title">{{ item.name }} のシステム情報</div>
                    <div class="inventory-panel__subtitle">
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
                  color="warning"
                  icon="mdi-alert-outline"
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
          <v-empty-state
            class="empty-state"
            icon="mdi-server-plus"
            title="サーバが登録されていません"
            text="最初のSSH接続先を登録すると、接続状態とシステム情報の自動確認が始まります。"
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
                :rules="[rules.required, rules.port]"
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import AppPageHeader from '@/components/AppPageHeader.vue'
import { useServerStore } from '@/stores/server'
import type {
  AuthMethod,
  Server,
  ServerConnectionStatus,
  ServerCreate,
  ServerUpdate,
} from '@/types'

const serverStore = useServerStore()
const servers = computed(() => serverStore.servers)
const loading = computed(() => serverStore.loading)
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
const passwordVisible = ref(false)
const deleteTarget = ref<Server | null>(null)
const formRef = ref()
const currentServerId = ref<number | null>(null)
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
  private_key: '',
})

const headers = [
  { title: '状態', key: 'connection_status', width: 128 },
  { title: 'サーバ', key: 'name', minWidth: 220 },
  { title: '接続先', key: 'endpoint', minWidth: 220 },
  { title: '環境', key: 'environment', minWidth: 150, sortable: false },
  { title: '最終確認', key: 'last_checked_at', minWidth: 150 },
  { title: '', key: 'actions', sortable: false, align: 'end' as const, width: 136 },
]

const authMethods = [
  { title: 'パスワード', value: 'password' },
  { title: '秘密鍵', value: 'key' },
]

const rules = {
  required: (value: unknown) => !!value || '必須項目です',
  port: (value: number) => (value >= 1 && value <= 65535) || '1〜65535で入力してください',
}

function statusMeta(status: ServerConnectionStatus) {
  const metadata = {
    online: { label: 'ONLINE', color: 'success', icon: 'mdi-check-circle' },
    offline: { label: 'OFFLINE', color: 'error', icon: 'mdi-alert-circle' },
    unknown: { label: '未確認', color: 'default', icon: 'mdi-help-circle' },
  }
  return metadata[status]
}

function formatDate(dateString: string): string {
  return new Intl.DateTimeFormat('ja-JP', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(dateString))
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

async function checkServer(server: Server) {
  if (checkingServerIds.value.includes(server.id)) return
  checkingServerIds.value = [...checkingServerIds.value, server.id]
  try {
    await serverStore.checkServer(server.id)
  } catch (error) {
    console.error('サーバの接続確認に失敗しました:', error)
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
  } catch (error) {
    console.error('サーバの削除に失敗しました:', error)
  } finally {
    deleting.value = false
  }
}

onMounted(async () => {
  try {
    await Promise.all([serverStore.fetchServers(), serverStore.fetchMonitoring()])
  } catch (error) {
    console.error('サーバ監視情報の取得に失敗しました:', error)
  }

  refreshTimer = setInterval(() => {
    serverStore.fetchServers(true).catch(error => {
      console.error('サーバ監視情報の更新に失敗しました:', error)
    })
  }, 30000)
})

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>

<style scoped>
.monitor-metric {
  position: relative;
  overflow: hidden;
  border: 1px solid rgba(var(--v-border-color), 0.1) !important;
  box-shadow: 0 10px 28px rgba(23, 61, 59, 0.035) !important;
}

.monitor-metric::before {
  position: absolute;
  inset: 0 auto 0 0;
  width: 4px;
  background: rgb(var(--v-theme-primary));
  content: '';
}

.monitor-metric--online::before {
  background: rgb(var(--v-theme-success));
}

.monitor-metric--offline::before {
  background: rgb(var(--v-theme-error));
}

.monitor-metric--unknown::before {
  background: rgb(var(--v-theme-on-surface-variant));
}

.monitor-metric__label {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.monitor-metric__value {
  margin-top: 3px;
  color: rgb(var(--v-theme-on-surface));
  font-family: var(--font-display);
  font-size: clamp(1.65rem, 4vw, 2.2rem);
  font-variant-numeric: tabular-nums;
  font-weight: 750;
  line-height: 1.1;
}

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

.environment-cell,
.check-time-cell {
  font-size: 0.8rem;
  font-weight: 650;
}

.environment-cell > :last-child,
.check-time-cell > :last-child {
  margin-top: 2px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.72rem;
  font-weight: 500;
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

.inventory-row {
  background: rgba(var(--v-theme-primary), 0.025);
}

.inventory-panel {
  padding: 24px;
  border-top: 1px solid rgba(var(--v-border-color), 0.08);
}

.inventory-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.inventory-panel__title {
  color: rgb(var(--v-theme-on-surface));
  font-family: var(--font-display);
  font-size: 1.05rem;
  font-weight: 750;
}

.inventory-panel__subtitle {
  margin-top: 3px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.74rem;
}

.inventory-section {
  height: 100%;
  padding: 18px;
  border: 1px solid rgba(var(--v-border-color), 0.1);
  border-radius: 14px;
  background: rgb(var(--v-theme-surface));
}

.inventory-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 14px;
  color: rgb(var(--v-theme-primary));
  font-size: 0.76rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.detail-list {
  display: grid;
  grid-template-columns: minmax(7rem, 0.7fr) minmax(0, 1.6fr);
  gap: 9px 16px;
  margin: 0;
  font-size: 0.82rem;
}

.detail-list dt {
  color: rgb(var(--v-theme-on-surface-variant));
}

.detail-list dd {
  min-width: 0;
  margin: 0;
  overflow-wrap: anywhere;
  font-weight: 650;
}

.private-key-field :deep(textarea) {
  font-family: var(--font-mono);
  font-size: 0.78rem;
}

@media (max-width: 599px) {
  .monitor-summary :deep(.v-card-text) {
    padding: 16px;
  }

  .inventory-panel {
    padding: 18px;
  }

  .inventory-panel__header {
    align-items: flex-start;
    flex-direction: column;
  }

  .detail-list {
    grid-template-columns: 1fr;
    gap: 2px;
  }

  .detail-list dd {
    margin-bottom: 10px;
  }
}
</style>

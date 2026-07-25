<template>
  <div>
    <v-btn class="back-link" prepend-icon="mdi-arrow-left" to="/executions" variant="text">
      実行履歴
    </v-btn>

    <AppPageHeader
      eyebrow="One-time run"
      icon="mdi-console"
      title="単発実行"
      description="保存済みジョブを作らず、長時間のスクリプトやバッチを既存の堅牢な実行基盤へ投入します。"
    />

    <v-alert
      v-if="loadError"
      class="mb-6"
      closable
      color="error"
      icon="mdi-alert-circle-outline"
      title="単発実行の準備ができませんでした"
      variant="tonal"
      @click:close="clearError"
    >
      {{ loadError }}
    </v-alert>

    <v-skeleton-loader
      v-if="serverStore.loading && servers.length === 0"
      class="panel-card"
      type="article, paragraph, paragraph"
    />

    <v-card v-else-if="servers.length === 0" class="panel-card">
      <v-empty-state
        class="empty-state"
        icon="mdi-server-off"
        title="実行先サーバがありません"
        text="単発スクリプトを投入する前に、SSH接続先を登録してください。"
      >
        <template #actions>
          <v-btn color="primary" prepend-icon="mdi-server-plus" to="/servers">
            サーバを登録
          </v-btn>
        </template>
      </v-empty-state>
    </v-card>

    <v-form
      v-else
      ref="formRef"
      validate-on="submit lazy"
      @submit.prevent="prepareExecution"
    >
      <div class="execution-workspace">
        <v-card class="panel-card script-panel">
          <v-card-title class="panel-card__header">
            <div>
              <div class="panel-card__title">実行スクリプト</div>
              <div class="panel-card__subtitle">対象サーバ上で POSIX sh として実行されます</div>
            </div>
            <v-chip color="info" prepend-icon="mdi-shield-sync-outline" size="small" variant="tonal">
              切断後も継続
            </v-chip>
          </v-card-title>
          <v-card-text class="script-panel__body">
            <v-textarea
              v-model="form.script"
              aria-label="実行するシェルスクリプト"
              class="script-input"
              hint="BackendやSSH接続が一時的に切れても、対象サーバ上で処理とログ保存が継続します。"
              no-resize
              persistent-hint
              placeholder="set -eu&#10;&#10;cd /opt/application&#10;./monthly_batch.sh"
              rows="20"
              :rules="[rules.required]"
            />
          </v-card-text>
        </v-card>

        <aside class="execution-sidebar">
          <v-card class="panel-card">
            <v-card-title class="panel-card__header">
              <div>
                <div class="panel-card__title">実行設定</div>
                <div class="panel-card__subtitle">履歴を識別する名前と接続先</div>
              </div>
            </v-card-title>
            <v-card-text class="execution-settings">
              <v-text-field
                v-model="form.name"
                autocomplete="off"
                label="実行名"
                maxlength="255"
                placeholder="月次データ再集計"
                prepend-inner-icon="mdi-label-outline"
                :rules="[rules.required]"
              />

              <v-select
                v-model="form.server_id"
                item-title="title"
                item-value="value"
                :items="serverOptions"
                label="実行サーバ"
                prepend-inner-icon="mdi-server-outline"
                :rules="[rules.server]"
              />

              <v-alert
                v-if="selectedServer && selectedServer.connection_status !== 'online'"
                class="mb-5"
                color="warning"
                icon="mdi-lan-pending"
                variant="tonal"
              >
                {{ selectedServer.name }} は現在
                {{ selectedServer.connection_status === 'offline' ? 'オフライン' : '状態未確認' }}です。
                投入後は接続できるまで再試行します。
              </v-alert>

              <div class="durability-note">
                <div class="durability-note__icon" aria-hidden="true">
                  <v-icon icon="mdi-timeline-clock-outline" size="21" />
                </div>
                <div>
                  <strong>長時間実行に対応</strong>
                  <span>設定された実行タイムアウトに従います（既定は無制限）。進捗とログは実行詳細から確認できます。</span>
                </div>
              </div>
            </v-card-text>
            <v-divider />
            <v-card-actions class="execution-actions">
              <v-btn variant="text" to="/executions">キャンセル</v-btn>
              <v-spacer />
              <v-btn
                color="success"
                prepend-icon="mdi-play"
                type="submit"
              >
                内容を確認
              </v-btn>
            </v-card-actions>
          </v-card>
        </aside>
      </div>
    </v-form>

    <v-dialog v-model="confirmDialog" max-width="620">
      <v-card class="dialog-card">
        <v-card-title>単発スクリプトを実行しますか？</v-card-title>
        <v-card-subtitle>投入後は実行履歴から状態とログを追跡できます。</v-card-subtitle>
        <v-divider />
        <v-card-text>
          <v-alert
            v-if="submitError"
            class="mb-5"
            color="error"
            icon="mdi-alert-circle-outline"
            variant="tonal"
          >
            {{ submitError }}
          </v-alert>

          <dl class="confirmation-grid">
            <div>
              <dt>実行名</dt>
              <dd>{{ form.name }}</dd>
            </div>
            <div>
              <dt>実行サーバ</dt>
              <dd>{{ selectedServer?.name || `サーバ #${form.server_id}` }}</dd>
            </div>
          </dl>

          <div class="script-preview">
            <div class="script-preview__label">実行内容</div>
            <pre class="code-panel"><code>{{ form.script }}</code></pre>
          </div>
        </v-card-text>
        <v-card-actions>
          <v-spacer />
          <v-btn variant="text" :disabled="submitting" @click="confirmDialog = false">
            戻る
          </v-btn>
          <v-btn
            color="success"
            prepend-icon="mdi-play"
            :loading="submitting"
            @click="execute"
          >
            実行する
          </v-btn>
        </v-card-actions>
      </v-card>
    </v-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import AppPageHeader from '@/components/AppPageHeader.vue'
import { useExecutionStore } from '@/stores/execution'
import { useServerStore } from '@/stores/server'

interface FormInstance {
  validate: () => Promise<{ valid: boolean }>
}

const router = useRouter()
const executionStore = useExecutionStore()
const serverStore = useServerStore()
const formRef = ref<FormInstance | null>(null)
const confirmDialog = ref(false)
const submitting = ref(false)
const submitError = ref<string | null>(null)
const form = ref({
  name: '',
  server_id: 0,
  script: '',
})

const servers = computed(() => serverStore.servers)
const loadError = computed(() => serverStore.error)
const selectedServer = computed(() =>
  servers.value.find((server) => server.id === form.value.server_id)
)
const serverOptions = computed(() => servers.value.map((server) => ({
  title: `${server.name} · ${formatServerStatus(server.connection_status)}`,
  value: server.id,
})))

const rules = {
  required: (value: string) => !!value?.trim() || '必須項目です',
  server: (value: number) =>
    servers.value.some((server) => server.id === value) || '実行サーバを選択してください',
}

function formatServerStatus(status: 'unknown' | 'online' | 'offline') {
  if (status === 'online') return 'オンライン'
  if (status === 'offline') return 'オフライン'
  return '状態未確認'
}

function clearError() {
  serverStore.clearError()
  executionStore.clearError()
  submitError.value = null
}

async function prepareExecution() {
  const validation = await formRef.value?.validate()
  if (!validation?.valid) return
  submitError.value = null
  confirmDialog.value = true
}

async function execute() {
  if (submitting.value) return
  submitting.value = true
  submitError.value = null
  try {
    const execution = await executionStore.createAdHoc({
      name: form.value.name.trim(),
      server_id: form.value.server_id,
      script: form.value.script,
    })
    confirmDialog.value = false
    await router.push(`/executions/${execution.id}`)
  } catch (error) {
    submitError.value = error instanceof Error
      ? error.message
      : '単発実行を開始できませんでした'
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  try {
    await serverStore.fetchServers()
    const [onlyServer] = servers.value
    if (onlyServer && servers.value.length === 1) {
      form.value.server_id = onlyServer.id
    }
  } catch (error) {
    console.error('サーバ一覧の取得に失敗しました:', error)
  }
})
</script>

<style scoped>
.back-link {
  margin: -8px 0 18px -12px;
  color: rgb(var(--v-theme-on-surface-variant));
}

.execution-workspace {
  display: grid;
  grid-template-columns: minmax(0, 1.65fr) minmax(320px, 0.75fr);
  gap: 22px;
  align-items: start;
}

.script-panel__body {
  padding: 4px 22px 22px !important;
}

.script-input :deep(textarea) {
  min-height: 440px;
  font-family: var(--font-mono);
  font-size: 0.86rem;
  line-height: 1.7;
  tab-size: 2;
}

.execution-sidebar {
  position: sticky;
  top: 88px;
}

.execution-settings {
  padding: 6px 22px 22px !important;
}

.execution-actions {
  padding: 16px 20px 20px;
}

.durability-note {
  display: flex;
  gap: 13px;
  padding: 15px;
  color: rgb(var(--v-theme-on-surface-variant));
  background: rgb(var(--v-theme-primary-soft));
  border: 1px solid rgba(var(--v-theme-primary), 0.12);
  border-radius: 14px;
}

.durability-note__icon {
  display: grid;
  flex: 0 0 38px;
  height: 38px;
  place-items: center;
  color: rgb(var(--v-theme-primary));
  background: rgba(var(--v-theme-primary), 0.09);
  border-radius: 11px;
}

.durability-note strong,
.durability-note span {
  display: block;
}

.durability-note strong {
  color: rgb(var(--v-theme-primary));
  font-size: 0.82rem;
}

.durability-note span {
  margin-top: 4px;
  font-size: 0.75rem;
  line-height: 1.6;
}

.confirmation-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
}

.confirmation-grid div {
  padding: 14px 16px;
  background: rgb(var(--v-theme-surface-light));
  border: 1px solid rgba(var(--v-border-color), 0.1);
  border-radius: 13px;
}

.confirmation-grid dt,
.script-preview__label {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.69rem;
  font-weight: 750;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.confirmation-grid dd {
  margin: 5px 0 0;
  color: rgb(var(--v-theme-on-surface));
  font-weight: 700;
}

.script-preview {
  margin-top: 18px;
}

.script-preview__label {
  margin-bottom: 8px;
}

.script-preview .code-panel {
  max-height: 280px;
  white-space: pre-wrap;
}

@media (max-width: 959px) {
  .execution-workspace {
    grid-template-columns: 1fr;
  }

  .execution-sidebar {
    position: static;
  }
}

@media (max-width: 599px) {
  .confirmation-grid {
    grid-template-columns: 1fr;
  }

  .script-panel__body,
  .execution-settings {
    padding-inline: 18px !important;
  }
}
</style>

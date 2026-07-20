<template>
  <v-chip
    :aria-label="`ステータス: ${config.label}`"
    :class="['status-chip', { 'status-chip--active': status === 'running' }]"
    :color="config.color"
    :prepend-icon="config.icon"
    label
    size="small"
    variant="tonal"
  >
    {{ config.label }}
  </v-chip>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ExecutionStatus } from '@/types'

const props = defineProps<{
  status: ExecutionStatus
}>()

const statusConfig: Record<string, { label: string; color: string; icon: string }> = {
  pending: { label: '待機中', color: 'warning', icon: 'mdi-clock-outline' },
  running: { label: '実行中', color: 'info', icon: 'mdi-progress-clock' },
  success: { label: '成功', color: 'success', icon: 'mdi-check-circle-outline' },
  failed: { label: '失敗', color: 'error', icon: 'mdi-alert-circle-outline' },
  cancelled: { label: 'キャンセル', color: 'secondary', icon: 'mdi-cancel' },
  timeout: { label: 'タイムアウト', color: 'warning', icon: 'mdi-timer-alert-outline' },
}

const config = computed(() => statusConfig[props.status] ?? {
  label: props.status,
  color: 'secondary',
  icon: 'mdi-help-circle-outline',
})
</script>

<style scoped>
.status-chip {
  min-width: 90px;
  justify-content: flex-start;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.status-chip--active :deep(.v-icon) {
  animation: status-pulse 1.8s ease-in-out infinite;
}

@keyframes status-pulse {
  50% {
    opacity: 0.35;
  }
}

@media (prefers-reduced-motion: reduce) {
  .status-chip--active :deep(.v-icon) {
    animation: none;
  }
}
</style>

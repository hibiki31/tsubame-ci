<template>
  <v-chip
    :color="appearance.color"
    :prepend-icon="appearance.icon"
    :title="appearance.description"
    label
    size="small"
    variant="tonal"
  >
    {{ appearance.label }}
  </v-chip>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ExecutionTriggerSource } from '@/types'

const props = defineProps<{
  source: ExecutionTriggerSource
}>()

const appearance = computed(() => {
  if (props.source === 'github_poll') {
    return {
      label: '自動',
      color: 'info',
      icon: 'mdi-source-branch-sync',
      description: 'GitHubブランチの更新を検知して自動実行',
    }
  }

  return {
    label: '手動',
    color: 'secondary',
    icon: 'mdi-account-outline',
    description: 'ユーザーによる手動実行',
  }
})
</script>

<template>
  <v-chip
    :color="appearance.color"
    :prepend-icon="appearance.icon"
    label
    size="small"
    variant="tonal"
  >
    {{ appearance.label }}
  </v-chip>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { ExecutionKind } from '@/types'

const props = defineProps<{
  kind: ExecutionKind
}>()

const appearance = computed(() => props.kind === 'ad_hoc'
  ? {
      label: '単発',
      color: 'accent',
      icon: 'mdi-console',
    }
  : {
      label: '登録ジョブ',
      color: 'primary',
      icon: 'mdi-script-text-outline',
    }
)
</script>

<template>
  <header class="page-header">
    <div class="page-header__copy">
      <div class="page-header__icon" aria-hidden="true">
        <v-icon :icon="icon" size="22" />
      </div>
      <div>
        <p v-if="eyebrow" class="page-header__eyebrow">{{ eyebrow }}</p>
        <h1 class="page-header__title">{{ title }}</h1>
        <p v-if="description" class="page-header__description">{{ description }}</p>
      </div>
    </div>

    <div v-if="$slots.actions" class="page-header__actions">
      <slot name="actions" />
    </div>
  </header>
</template>

<script setup lang="ts">
defineProps<{
  title: string
  description?: string
  eyebrow?: string
  icon: string
}>()
</script>

<style scoped>
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 24px;
  margin-bottom: 28px;
}

.page-header__copy {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  min-width: 0;
}

.page-header__icon {
  display: grid;
  flex: 0 0 48px;
  width: 48px;
  height: 48px;
  place-items: center;
  color: rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-primary-soft));
  border: 1px solid rgba(var(--v-theme-primary), 0.14);
  border-radius: 15px;
}

.page-header__eyebrow {
  margin: 0 0 4px;
  color: rgb(var(--v-theme-accent));
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.16em;
  line-height: 1.3;
  text-transform: uppercase;
}

.page-header__title {
  margin: 0;
  color: rgb(var(--v-theme-on-background));
  font-family: var(--font-display);
  font-size: clamp(1.75rem, 2vw, 2.25rem);
  font-stretch: condensed;
  font-weight: 700;
  letter-spacing: -0.035em;
  line-height: 1.15;
}

.page-header__description {
  max-width: 680px;
  margin: 8px 0 0;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.925rem;
  line-height: 1.65;
}

.page-header__actions {
  display: flex;
  flex-wrap: wrap;
  flex: 0 0 auto;
  justify-content: flex-end;
  gap: 10px;
}

@media (max-width: 599px) {
  .page-header {
    align-items: stretch;
    flex-direction: column;
    gap: 20px;
    margin-bottom: 24px;
  }

  .page-header__icon {
    flex-basis: 42px;
    width: 42px;
    height: 42px;
    border-radius: 13px;
  }

  .page-header__copy {
    gap: 13px;
  }

  .page-header__actions :deep(.v-btn) {
    flex: 1 1 auto;
  }
}
</style>

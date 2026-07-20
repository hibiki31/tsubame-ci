<template>
  <v-app>
    <v-navigation-drawer
      v-model="drawer"
      app
      class="app-drawer"
      :permanent="$vuetify.display.mdAndUp"
      width="272"
    >
      <div class="brand-block">
        <div class="brand-block__mark" aria-hidden="true">
          <v-icon icon="mdi-bird" size="25" />
        </div>
        <div>
          <div class="brand-block__name">tsubame-ci</div>
          <div class="brand-block__caption">Deployment control</div>
        </div>
      </div>

      <div class="nav-label">Workspace</div>
      <v-list class="app-nav" nav>
        <v-list-item prepend-icon="mdi-view-dashboard-outline" title="ダッシュボード" to="/" exact />
        <v-list-item prepend-icon="mdi-server-outline" title="サーバ管理" to="/servers" />
        <v-list-item prepend-icon="mdi-script-text-outline" title="ジョブ管理" to="/jobs" />
        <v-list-item prepend-icon="mdi-history" title="実行履歴" to="/executions" />
      </v-list>

      <template #append>
        <div class="environment-card">
          <div class="environment-card__signal" aria-hidden="true" />
          <div>
            <div class="environment-card__label">MVP environment</div>
            <div class="environment-card__value">Console ready</div>
          </div>
        </div>
      </template>
    </v-navigation-drawer>

    <v-app-bar app class="app-bar" color="surface" flat>
      <v-app-bar-nav-icon
        v-if="$vuetify.display.smAndDown"
        aria-label="ナビゲーションを開く"
        @click="drawer = !drawer"
      />

      <div class="app-bar__context">
        <span class="app-bar__product">Operations</span>
        <span class="app-bar__separator" aria-hidden="true">/</span>
        <span class="app-bar__page">{{ currentPageTitle }}</span>
      </div>

      <v-spacer />

      <div class="app-bar__status">
        <span class="app-bar__status-dot" aria-hidden="true" />
        UI online
      </div>
    </v-app-bar>

    <v-main class="app-main">
      <v-container class="app-container" fluid>
        <router-view v-slot="{ Component }">
          <transition name="page" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </v-container>
    </v-main>

    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="snackbar.timeout"
      rounded="lg"
      variant="tonal"
    >
      {{ snackbar.message }}
      <template #actions>
        <v-btn variant="text" @click="snackbar.show = false">閉じる</v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const currentPageTitle = computed(() => (route.meta.title as string | undefined) ?? 'Console')
const drawer = ref(true)

const snackbar = ref({
  show: false,
  message: '',
  color: 'success',
  timeout: 3000
})

window.addEventListener('unhandledrejection', (event) => {
  console.error('Unhandled promise rejection:', event.reason)
  snackbar.value = {
    show: true,
    message: 'エラーが発生しました',
    color: 'error',
    timeout: 5000
  }
})
</script>

<style scoped>
.app-drawer {
  border-right: 1px solid rgba(var(--v-border-color), 0.1);
}

.brand-block {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 22px 26px;
}

.brand-block__mark {
  display: grid;
  width: 44px;
  height: 44px;
  place-items: center;
  color: white;
  background: rgb(var(--v-theme-primary));
  border-radius: 14px 14px 14px 5px;
  box-shadow: 0 8px 20px rgba(var(--v-theme-primary), 0.2);
}

.brand-block__name {
  color: rgb(var(--v-theme-primary));
  font-family: var(--font-display);
  font-size: 1.06rem;
  font-weight: 800;
  letter-spacing: -0.02em;
}

.brand-block__caption {
  margin-top: 1px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.69rem;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
}

.nav-label {
  padding: 4px 26px 8px;
  color: rgba(var(--v-theme-on-surface), 0.45);
  font-size: 0.66rem;
  font-weight: 800;
  letter-spacing: 0.15em;
  text-transform: uppercase;
}

.app-nav {
  padding: 0 14px;
}

.app-nav :deep(.v-list-item) {
  min-height: 48px;
  margin-bottom: 6px;
  color: rgb(var(--v-theme-on-surface-variant));
  border-radius: 13px;
  font-weight: 650;
}

.app-nav :deep(.v-list-item__prepend > .v-icon) {
  margin-inline-end: 16px;
  opacity: 0.72;
}

.app-nav :deep(.v-list-item--active) {
  color: rgb(var(--v-theme-primary));
  background: rgb(var(--v-theme-primary-soft));
}

.app-nav :deep(.v-list-item--active .v-list-item__overlay) {
  opacity: 0;
}

.app-nav :deep(.v-list-item--active .v-icon) {
  opacity: 1;
}

.environment-card {
  display: flex;
  align-items: center;
  gap: 11px;
  margin: 16px;
  padding: 15px 16px;
  background: rgb(var(--v-theme-surface-light));
  border: 1px solid rgba(var(--v-border-color), 0.1);
  border-radius: 15px;
}

.environment-card__signal,
.app-bar__status-dot {
  width: 8px;
  height: 8px;
  background: rgb(var(--v-theme-success));
  border-radius: 50%;
  box-shadow: 0 0 0 4px rgba(var(--v-theme-success), 0.12);
}

.environment-card__label {
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.67rem;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.environment-card__value {
  margin-top: 2px;
  color: rgb(var(--v-theme-on-surface));
  font-size: 0.82rem;
  font-weight: 700;
}

.app-bar {
  border-bottom: 1px solid rgba(var(--v-border-color), 0.09) !important;
}

.app-bar__context {
  display: flex;
  align-items: center;
  gap: 9px;
  padding-left: 24px;
  font-size: 0.84rem;
}

.app-bar__product {
  color: rgb(var(--v-theme-on-surface-variant));
  font-weight: 600;
}

.app-bar__separator {
  color: rgba(var(--v-theme-on-surface), 0.25);
}

.app-bar__page {
  color: rgb(var(--v-theme-on-surface));
  font-weight: 750;
}

.app-bar__status {
  display: flex;
  align-items: center;
  gap: 9px;
  margin-right: 28px;
  color: rgb(var(--v-theme-on-surface-variant));
  font-size: 0.75rem;
  font-weight: 650;
}

.app-bar__status-dot {
  width: 7px;
  height: 7px;
}

@media (max-width: 599px) {
  .app-bar__context {
    padding-left: 4px;
  }

  .app-bar__product,
  .app-bar__separator,
  .app-bar__status {
    display: none;
  }
}
</style>

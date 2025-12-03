<template>
  <v-app>
    <v-navigation-drawer
      v-model="drawer"
      app
      :permanent="$vuetify.display.mdAndUp"
    >
      <v-list>
        <v-list-item
          prepend-icon="mdi-view-dashboard"
          title="tsubame-ci"
          subtitle="CI/CD Dashboard"
        ></v-list-item>
      </v-list>

      <v-divider></v-divider>

      <v-list density="compact" nav>
        <v-list-item
          prepend-icon="mdi-view-dashboard"
          title="ダッシュボード"
          to="/"
        ></v-list-item>
        
        <v-list-item
          prepend-icon="mdi-server"
          title="サーバ管理"
          to="/servers"
        ></v-list-item>
        
        <v-list-item
          prepend-icon="mdi-script-text"
          title="ジョブ管理"
          to="/jobs"
        ></v-list-item>
        
        <v-list-item
          prepend-icon="mdi-history"
          title="実行履歴"
          to="/executions"
        ></v-list-item>
      </v-list>
    </v-navigation-drawer>

    <v-app-bar app color="primary" dark>
      <v-app-bar-nav-icon
        v-if="$vuetify.display.smAndDown"
        @click="drawer = !drawer"
      ></v-app-bar-nav-icon>

      <v-toolbar-title>
        <v-icon icon="mdi-bird" class="mr-2"></v-icon>
        tsubame-ci
      </v-toolbar-title>

      <v-spacer></v-spacer>

      <v-btn icon="mdi-cog"></v-btn>
    </v-app-bar>

    <v-main>
      <v-container fluid>
        <router-view />
      </v-container>
    </v-main>

    <!-- グローバルスナックバー（エラー表示用） -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="snackbar.timeout"
    >
      {{ snackbar.message }}
      <template v-slot:actions>
        <v-btn
          variant="text"
          @click="snackbar.show = false"
        >
          閉じる
        </v-btn>
      </template>
    </v-snackbar>
  </v-app>
</template>

<script setup lang="ts">
import { ref } from 'vue'

// ドロワー（サイドバー）の表示状態
const drawer = ref(true)

// スナックバー（通知）の状態
const snackbar = ref({
  show: false,
  message: '',
  color: 'success',
  timeout: 3000
})

// グローバルエラーハンドラー（将来的に使用）
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
/* コンポーネント固有のスタイル */
</style>

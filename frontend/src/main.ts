/**
 * tsubame-ci フロントエンド
 * アプリケーションエントリーポイント
 */
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import vuetify from './plugins/vuetify'

// スタイル
import './style.css'

// Vueアプリケーションの作成
const app = createApp(App)

// プラグインの登録
app.use(createPinia())
app.use(router)
app.use(vuetify)

// アプリケーションのマウント
app.mount('#app')

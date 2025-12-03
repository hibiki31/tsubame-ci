/**
 * Vue Router設定
 */
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: () => import('@/views/Dashboard.vue'),
      meta: { title: 'ダッシュボード' }
    },
    {
      path: '/servers',
      name: 'servers',
      component: () => import('@/views/Servers.vue'),
      meta: { title: 'サーバ管理' }
    },
    {
      path: '/jobs',
      name: 'jobs',
      component: () => import('@/views/Jobs.vue'),
      meta: { title: 'ジョブ管理' }
    },
    {
      path: '/jobs/:id',
      name: 'job-detail',
      component: () => import('@/views/JobDetail.vue'),
      meta: { title: 'ジョブ詳細' }
    },
    {
      path: '/executions',
      name: 'executions',
      component: () => import('@/views/Executions.vue'),
      meta: { title: '実行履歴' }
    },
    {
      path: '/executions/:id',
      name: 'execution-detail',
      component: () => import('@/views/ExecutionDetail.vue'),
      meta: { title: '実行詳細' }
    }
  ]
})

// ページタイトルの設定
router.beforeEach((to, _from, next) => {
  const title = to.meta.title as string | undefined
  if (title) {
    document.title = `${title} | tsubame-ci`
  } else {
    document.title = 'tsubame-ci'
  }
  next()
})

export default router

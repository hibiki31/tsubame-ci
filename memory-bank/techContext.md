# Tech Context: tsubame-ci

## 技術スタック概要

tsubame-ciは、モダンなWeb技術とPython生態系を組み合わせた、フルスタックアプリケーションです。

## フロントエンド

### Vue3 (Composition API)
**バージョン**: Vue 3.x
**なぜVue3を選んだか**:
- Composition APIによる柔軟なコード組織化
- 優れたパフォーマンス
- 豊富なエコシステムとコミュニティ
- TypeScriptとの統合が優れている

**主な使用方法**:
```typescript
// Composition APIを使用した典型的なコンポーネント構造
<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useJobStore } from '@/stores/job'

const jobStore = useJobStore()
const jobs = computed(() => jobStore.jobs)
</script>
```

### TypeScript
**なぜTypeScriptを選んだか**:
- 型安全性によるバグの早期発見
- IDEサポートの向上
- 大規模開発での保守性
- Vue3との優れた統合

**設定方針**:
- strict モードを有効化
- 明示的な型定義を推奨
- anyの使用を最小限に

### Pinia (状態管理)
**なぜPiniaを選んだか**:
- Vue3の公式推奨状態管理ライブラリ
- シンプルなAPI
- TypeScript完全サポート
- 優れた開発者体験

**使用パターン**:
```typescript
// stores/job.ts
import { defineStore } from 'pinia'

export const useJobStore = defineStore('job', {
  state: () => ({
    jobs: [],
    currentJob: null
  }),
  actions: {
    async fetchJobs() {
      // API呼び出し
    }
  }
})
```

### Vue Router
**用途**: SPAのルーティング管理
**主な機能**:
- ページ間のナビゲーション
- 認証ガード
- 動的ルート

### Vuetify3
**なぜVuetify3を選んだか**:
- Material Designに基づく統一されたUI
- 豊富なコンポーネント
- レスポンシブデザインの容易な実装
- Vue3対応

**使用コンポーネント例**:
- `v-app`, `v-navigation-drawer`: レイアウト
- `v-data-table`: ジョブ一覧表示
- `v-card`, `v-btn`: UI要素
- `v-dialog`: モーダル

## バックエンド

### FastAPI
**バージョン**: FastAPI 0.100+
**なぜFastAPIを選んだか**:
- 高速なパフォーマンス
- 自動API ドキュメント生成 (Swagger/OpenAPI)
- Pythonの型ヒントを活用
- 非同期処理のネイティブサポート
- WebSocketサポート

**主な機能**:
```python
# 典型的なエンドポイント構造
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel

app = FastAPI()

class Job(BaseModel):
    name: str
    script: str
    server_id: int

@app.post("/api/jobs")
async def create_job(job: Job):
    # ジョブ作成ロジック
    return {"id": 1, "status": "created"}

@app.websocket("/ws/jobs/{job_id}")
async def job_execution_ws(websocket: WebSocket, job_id: int):
    # リアルタイム実行状況の配信
    pass
```

### Python依存ライブラリ

#### paramiko / asyncssh
**用途**: SSH接続とリモートコマンド実行
**選択理由**: Pythonで最も成熟したSSHライブラリ

#### SQLAlchemy
**用途**: ORM (Object-Relational Mapping)
**選択理由**: 
- Pythonの標準的なORM
- FastAPIとの統合が容易
- マイグレーション管理 (Alembic)

#### Pydantic
**用途**: データバリデーションとシリアライゼーション
**選択理由**: FastAPIとの統合、型安全性

### PostgreSQL
**バージョン**: PostgreSQL 14+
**なぜPostgreSQLを選んだか**:
- 信頼性の高いオープンソースRDBMS
- JSON型サポート（実行ログの柔軟な保存）
- 優れたパフォーマンス
- 豊富な拡張機能

**主なテーブル設計** (想定):
```sql
-- jobs: ジョブ定義
CREATE TABLE jobs (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    script TEXT NOT NULL,
    server_id INTEGER REFERENCES servers(id),
    created_at TIMESTAMP DEFAULT NOW()
);

-- job_executions: 実行履歴
CREATE TABLE job_executions (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id),
    status VARCHAR(50),
    output TEXT,
    started_at TIMESTAMP,
    finished_at TIMESTAMP
);

-- servers: 接続先サーバ情報
CREATE TABLE servers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    host VARCHAR(255) NOT NULL,
    port INTEGER DEFAULT 22,
    username VARCHAR(255) NOT NULL,
    auth_method VARCHAR(50) -- 'password' or 'key'
);
```

## デプロイ・インフラ

### Docker Compose
**なぜDocker Composeを選んだか**:
- 簡単なセットアップ
- 開発環境と本番環境の一貫性
- 依存関係の分離
- ポータビリティ

**構成** (想定):
```yaml
services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
      
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:pass@db:5432/tsubame
    depends_on:
      - db
      
  db:
    image: postgres:14
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: tsubame
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass

volumes:
  postgres_data:
```

## 開発環境

### 必要なツール
- **Node.js**: v18+ (フロントエンド開発)
- **Python**: 3.10+ (バックエンド開発)
- **Docker & Docker Compose**: コンテナ環境
- **Git**: バージョン管理

### 開発サーバー起動
```bash
# フロントエンド
cd frontend
npm install
npm run dev  # localhost:3000

# バックエンド
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload  # localhost:8000

# データベース
docker-compose up db
```

### ビルドツール

#### フロントエンド: Vite
**なぜViteを選んだか**:
- 高速な開発サーバー起動
- HMR (Hot Module Replacement)
- Vue3の公式推奨
- 効率的なビルド

#### バックエンド: Uvicorn
**なぜUvicornを選んだか**:
- ASGI対応
- 高速なパフォーマンス
- FastAPIの推奨サーバー

## 技術的制約

### セキュリティ考慮事項
1. **SSH認証情報の保存**
   - 暗号化して保存する必要がある
   - 環境変数や秘密管理ツールの使用を検討

2. **API認証**
   - JWT認証を実装予定
   - CORS設定の適切な管理

3. **実行ログのサニタイゼーション**
   - 機密情報のマスキング

### パフォーマンス考慮事項
1. **長時間実行ジョブ**
   - 非同期実行とWebSocketでの進捗通知
   - タイムアウト設定

2. **大量のログ出力**
   - ストリーミング処理
   - ログのページネーション

## 依存関係バージョン管理

### フロントエンド (package.json)
```json
{
  "dependencies": {
    "vue": "^3.3.0",
    "vue-router": "^4.2.0",
    "pinia": "^2.1.0",
    "vuetify": "^3.3.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.2.0",
    "typescript": "^5.0.0",
    "vite": "^4.3.0"
  }
}
```

### バックエンド (requirements.txt)
```txt
fastapi>=0.100.0
uvicorn[standard]>=0.22.0
sqlalchemy>=2.0.0
asyncpg>=0.27.0
pydantic>=2.0.0
asyncssh>=2.13.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
alembic>=1.11.0
```

## コーディング規約

### Python (バックエンド)
- PEP 8準拠
- 型ヒントの使用を必須化
- docstringは日本語で記述
- Black でコードフォーマット

### TypeScript (フロントエンド)
- ESLint + Prettier使用
- Composition APIを優先
- コメントは日本語で記述
- ファイル名: kebab-case

### Git
- コミットメッセージ: 日本語
- ブランチ戦略: Git Flow

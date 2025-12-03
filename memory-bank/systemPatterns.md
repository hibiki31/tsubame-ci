# System Patterns: tsubame-ci

## システムアーキテクチャ

tsubame-ciは、フロントエンド、バックエンド、データベースの3層アーキテクチャを採用しています。

```
┌─────────────────────────────────────────────────────────┐
│                     Web Browser                         │
│                  (Vue3 + Vuetify3)                      │
└────────────────────┬────────────────────────────────────┘
                     │
                     │ HTTP/REST API
                     │ WebSocket (リアルタイム通信)
                     │
┌────────────────────▼────────────────────────────────────┐
│                  FastAPI Backend                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │   API Layer  │  │  SSH Client  │  │  Job Engine  │ │
│  │  (Routing)   │  │   (asyncssh) │  │  (Executor)  │ │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘ │
│         │                 │                  │          │
│  ┌──────▼─────────────────▼──────────────────▼───────┐ │
│  │          Business Logic Layer                     │ │
│  │        (Services & Domain Models)                 │ │
│  └──────┬────────────────────────────────────────────┘ │
│         │                                               │
│  ┌──────▼────────────────┐                            │
│  │   Data Access Layer   │                            │
│  │   (SQLAlchemy ORM)    │                            │
│  └──────┬────────────────┘                            │
└─────────┼───────────────────────────────────────────────┘
          │
          │ SQL
          │
┌─────────▼───────────────────────────────────────────────┐
│                  PostgreSQL Database                    │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │   Jobs   │  │ Job Execution│  │    Servers       │ │
│  │  (定義)  │  │   (履歴)     │  │  (接続先情報)   │ │
│  └──────────┘  └──────────────┘  └──────────────────┘ │
└─────────────────────────────────────────────────────────┘
          │
          │ SSH
          │
┌─────────▼───────────────────────────────────────────────┐
│              Remote Linux Servers                       │
│           (スクリプト実行対象サーバ)                   │
└─────────────────────────────────────────────────────────┘
```

## レイヤー別設計パターン

### フロントエンド層 (Vue3)

#### コンポーネント構成
```
src/
├── components/
│   ├── common/          # 共通コンポーネント
│   │   ├── AppHeader.vue
│   │   ├── AppSidebar.vue
│   │   └── LoadingSpinner.vue
│   ├── jobs/            # ジョブ関連
│   │   ├── JobList.vue
│   │   ├── JobDetail.vue
│   │   ├── JobForm.vue
│   │   └── JobExecutionLog.vue
│   └── servers/         # サーバ管理関連
│       ├── ServerList.vue
│       └── ServerForm.vue
├── stores/              # Pinia ストア
│   ├── job.ts
│   ├── server.ts
│   └── execution.ts
├── views/               # ページコンポーネント
│   ├── Dashboard.vue
│   ├── Jobs.vue
│   ├── Servers.vue
│   └── ExecutionHistory.vue
├── router/
│   └── index.ts
└── services/            # API通信
    ├── api.ts
    ├── jobService.ts
    └── serverService.ts
```

#### 状態管理パターン (Pinia)
```typescript
// ストアの責務分離
// 1. job.ts: ジョブ定義の管理
// 2. execution.ts: 実行状態とログの管理
// 3. server.ts: サーバ情報の管理

// APIコールはストアのactionで集中管理
export const useJobStore = defineStore('job', {
  state: () => ({
    jobs: [] as Job[],
    loading: false,
    error: null as string | null
  }),
  actions: {
    async fetchJobs() {
      this.loading = true
      try {
        const response = await jobService.getJobs()
        this.jobs = response.data
      } catch (error) {
        this.error = error.message
      } finally {
        this.loading = false
      }
    }
  }
})
```

### バックエンド層 (FastAPI)

#### ディレクトリ構造
```
backend/
├── app/
│   ├── main.py              # アプリケーションエントリーポイント
│   ├── api/                 # APIエンドポイント
│   │   ├── v1/
│   │   │   ├── jobs.py
│   │   │   ├── servers.py
│   │   │   └── executions.py
│   │   └── deps.py          # 依存性注入
│   ├── core/                # コア設定
│   │   ├── config.py
│   │   ├── security.py
│   │   └── database.py
│   ├── models/              # SQLAlchemy モデル
│   │   ├── job.py
│   │   ├── server.py
│   │   └── execution.py
│   ├── schemas/             # Pydantic スキーマ
│   │   ├── job.py
│   │   ├── server.py
│   │   └── execution.py
│   ├── services/            # ビジネスロジック
│   │   ├── job_service.py
│   │   ├── ssh_service.py
│   │   └── execution_service.py
│   └── utils/               # ユーティリティ
│       ├── ssh_client.py
│       └── logger.py
├── alembic/                 # DBマイグレーション
├── tests/
└── requirements.txt
```

#### レイヤー別の責務

##### 1. API Layer (api/)
- HTTPリクエストの受付
- レスポンスの返却
- バリデーション (Pydantic)
- 認証・認可

```python
# api/v1/jobs.py
from fastapi import APIRouter, Depends
from app.services.job_service import JobService
from app.schemas.job import JobCreate, JobResponse

router = APIRouter()

@router.post("/jobs", response_model=JobResponse)
async def create_job(
    job: JobCreate,
    service: JobService = Depends()
):
    """ジョブを作成する"""
    return await service.create_job(job)
```

##### 2. Service Layer (services/)
- ビジネスロジックの実装
- 複数のモデルやリソースの調整
- トランザクション管理

```python
# services/job_service.py
from app.models.job import Job
from app.schemas.job import JobCreate

class JobService:
    def __init__(self, db: Session):
        self.db = db
    
    async def create_job(self, job_data: JobCreate) -> Job:
        """ジョブ作成ロジック"""
        # バリデーション
        await self._validate_server_exists(job_data.server_id)
        
        # ジョブ作成
        job = Job(**job_data.dict())
        self.db.add(job)
        self.db.commit()
        
        return job
```

##### 3. Data Access Layer (models/)
- データベースとのやり取り
- SQLAlchemy ORM

```python
# models/job.py
from sqlalchemy import Column, Integer, String, Text, ForeignKey
from sqlalchemy.orm import relationship

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    script = Column(Text, nullable=False)
    server_id = Column(Integer, ForeignKey("servers.id"))
    
    # リレーション
    server = relationship("Server", back_populates="jobs")
    executions = relationship("JobExecution", back_populates="job")
```

## 主要な技術的決定

### 1. SSH実行の非同期処理

**決定**: asyncsshを使用した非同期SSH実行
**理由**: 
- 複数ジョブの同時実行をサポート
- UIのブロッキングを防ぐ
- FastAPIの非同期処理と統合しやすい

```python
# services/ssh_service.py
import asyncssh

class SSHService:
    async def execute_script(
        self,
        host: str,
        username: str,
        script: str
    ) -> tuple[str, str]:
        """スクリプトを非同期で実行"""
        async with asyncssh.connect(
            host,
            username=username,
            known_hosts=None
        ) as conn:
            result = await conn.run(script)
            return result.stdout, result.stderr
```

### 2. リアルタイム実行状況の配信

**決定**: WebSocketを使用したリアルタイム通信
**理由**:
- 実行中のログをリアルタイムで配信
- ポーリングよりも効率的
- FastAPIのWebSocketサポート

```python
# api/v1/executions.py
@router.websocket("/ws/executions/{execution_id}")
async def execution_websocket(
    websocket: WebSocket,
    execution_id: int
):
    await websocket.accept()
    
    async for log_line in execution_service.stream_logs(execution_id):
        await websocket.send_json({
            "type": "log",
            "data": log_line
        })
```

### 3. 認証情報の安全な保存

**決定**: Fernet暗号化を使用
**理由**:
- SSH秘密鍵やパスワードを平文で保存しない
- Pythonの標準的な暗号化ライブラリ
- 鍵管理の簡素化

```python
# core/security.py
from cryptography.fernet import Fernet

class CredentialEncryptor:
    def __init__(self, key: bytes):
        self.fernet = Fernet(key)
    
    def encrypt(self, data: str) -> str:
        """認証情報を暗号化"""
        return self.fernet.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted: str) -> str:
        """認証情報を復号化"""
        return self.fernet.decrypt(encrypted.encode()).decode()
```

### 4. エラーハンドリング戦略

**パターン**: 3層のエラーハンドリング

1. **API層**: HTTPステータスコードの返却
2. **Service層**: カスタム例外の発生
3. **フロントエンド**: ユーザーフレンドリーなエラー表示

```python
# services/exceptions.py
class SSHConnectionError(Exception):
    """SSH接続エラー"""
    pass

class JobNotFoundError(Exception):
    """ジョブが見つからない"""
    pass

# api/v1/jobs.py
@router.post("/jobs/{job_id}/execute")
async def execute_job(job_id: int):
    try:
        result = await job_service.execute(job_id)
        return result
    except JobNotFoundError:
        raise HTTPException(status_code=404, detail="ジョブが見つかりません")
    except SSHConnectionError as e:
        raise HTTPException(status_code=500, detail=f"SSH接続エラー: {str(e)}")
```

## コンポーネント間の関係

### データフロー: ジョブ実行

```
1. ユーザーがUIで実行ボタンをクリック
   └→ JobDetail.vue

2. Piniaストアのactionを呼び出し
   └→ useExecutionStore().executeJob(jobId)

3. APIサービス経由でバックエンドにリクエスト
   └→ POST /api/v1/jobs/{jobId}/execute

4. FastAPI: ExecutionServiceを呼び出し
   └→ execution_service.create_and_execute()

5. JobExecutionレコードをDBに作成
   └→ models.JobExecution (status: "running")

6. SSHServiceで非同期実行を開始
   └→ ssh_service.execute_script()

7. WebSocket経由でログをストリーミング
   └→ ws://api/v1/executions/{execution_id}

8. フロントエンドでリアルタイム表示
   └→ JobExecutionLog.vue

9. 実行完了後、ステータスを更新
   └→ models.JobExecution (status: "success" or "failed")
```

## スケーラビリティ考慮事項

### 現在の設計（Phase 1-2）
- 単一バックエンドサーバ
- 同期的なSSH実行
- シンプルなアーキテクチャ

### 将来的な拡張（Phase 3-4）
- タスクキュー (Celery) の導入
- 複数ワーカーでの分散実行
- Redis for キャッシュとセッション管理
- 実行履歴のアーカイブ戦略

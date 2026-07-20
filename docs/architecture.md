# Architecture

## 全体像

```text
Browser → Nginx/Vue → FastAPI → PostgreSQL
                         └── SSH → Linux server
```

Frontend は `/api/v1` を同一 origin へ送り、開発時は Vite、本番 image では Nginx が Backend へ proxy する。Backend は SSH 認証情報を暗号化して DB に保存し、ジョブ実行時だけ復号する。

## 責務

```text
backend/app/
├── api/v1/       HTTP route と例外の HTTP 変換
├── services/     CRUD、SSH 接続、ジョブ実行
├── models/       SQLAlchemy model
├── schemas/      Pydantic の API 契約
├── core/         設定、DB session、暗号化
└── main.py       app、CORS、router 登録

frontend/src/
├── views/        route 単位の画面
├── stores/       Pinia の状態と action
├── services/     Axios と WebSocket client
├── types/        API 対応型
└── router/       画面 route
```

依存方向は Backend が `route → service → model`、Frontend が `view → store → API client`。共有契約を画面内へ再定義しない。

## データと実行

- `Server` は接続先と暗号化済み password/private key を持ち、削除時に Job を cascade 削除する。
- `Job` は script と `server_id` を持つ。
- `JobExecution` は status、stdout/stderr、exit code、開始・終了時刻を持つ。
- 現行の実行 API は SSH 完了まで request 内で待機する。非同期 queue、実処理の cancel、WebSocket 配信は未実装。

API の正確な route/schema は FastAPI の `/docs` と `/openapi.json` を正本とする。主要 prefix は `/api/v1/servers`、`/api/v1/jobs`、`/api/v1/executions`。

## 設定と永続化

- 必須環境変数は `DATABASE_URL`、`SECRET_KEY`、`ENCRYPTION_KEY`。全項目は `backend/.env.example` と `backend/app/core/config.py` を参照する。
- Debug 起動時は `Base.metadata.create_all()` で table を作る。Alembic は依存にあるが設定・migration は未作成で、本番 schema 更新手段は未整備。
- Compose の DB volume は `postgres_data`。実データを伴う破壊的操作は行わない。

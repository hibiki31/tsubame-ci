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

- `Server` は接続先と暗号化済み password/private key に加え、直近の接続状態、応答時間、確認エラー、hardware/software inventory を持つ。削除時に Job を cascade 削除する。
- `Job` は script と `server_id` を持つ。
- `JobExecution` は status、stdout/stderr、exit code、開始・終了時刻を持つ。
- 現行の実行 API は SSH 完了まで request 内で待機する。非同期 queue、実処理の cancel、WebSocket 配信は未実装。

## サーバ監視

Backend の lifespan で `ServerMonitor` を起動し、`SERVER_CHECK_INTERVAL_SECONDS` ごとに登録サーバを確認する。起動直後にも一度実行する。確認対象は設定した concurrency まで並列化し、サーバごとに独立した DB session を使う。

```text
ServerMonitor → ServerService → SSHService → Linux server
                     └── status / latency / inventory → PostgreSQL
```

- 保存済み認証情報を復号し、SSH 接続成功までの時間を計測する。
- 同じ SSH 接続で hostname、architecture、CPU、memory、root disk、OS、kernel、package manager、Python、Docker、Git を読み取る。
- 接続失敗時は `offline` とエラーを保存するが、最後に成功した inventory は障害調査用に残す。
- 構成取得だけが失敗した場合は接続を `online` とし、警告を保存する。
- API は `POST /api/v1/servers/{server_id}/check` で即時確認、`GET /api/v1/servers/monitoring` で自動監視設定を提供する。

定期処理は Backend process 内で動くため、複数 worker/process を起動すると worker 数だけ確認が重複する。現状は単一 worker を前提とし、複数 worker 化する場合は scheduler の leader election または外部 worker への分離が必要である。

API の正確な route/schema は FastAPI の `/docs` と `/openapi.json` を正本とする。主要 prefix は `/api/v1/servers`、`/api/v1/jobs`、`/api/v1/executions`。

## 設定と永続化

- 必須環境変数は `DATABASE_URL`、`SECRET_KEY`、`ENCRYPTION_KEY`。全項目は `backend/.env.example` と `backend/app/core/config.py` を参照する。
- Alembic の初期 schema とサーバ監視 migration がある。新規 DB は `alembic upgrade head`、従来の `create_all()` 由来 DB は初期 revision の stamp 後に upgrade する。
- Debug 起動時の `Base.metadata.create_all()` は新規 table の作成だけを行い、既存 table へ列を追加しない。既存 DB の更新には必ず Alembic を使う。
- Compose の DB volume は `postgres_data`。実データを伴う破壊的操作は行わない。

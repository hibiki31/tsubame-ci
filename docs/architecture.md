# Architecture

## 全体像

```text
Browser → Nginx/Vue → FastAPI → PostgreSQL
                         └── SSH → Linux server
                         └── polling → GitHub REST API
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
- `Job` は script と `server_id` に加え、任意で GitHub repository・branch・暗号化済み PAT・最後に確認した commit SHA を持つ。
- `JobExecution` は status、stdout/stderr、exit code、開始・終了時刻、実行元（手動/GitHub）とトリガー元 commit SHA を持つ。
- 現行の実行 API は SSH 完了まで request 内で待機する。非同期 queue、実処理の cancel、WebSocket 配信は未実装。

## GitHub branch ポーリング

- `GITHUB_POLL_INTERVAL_SECONDS` ごとに、`github_poll` を設定した Job の branch HEAD を GitHub REST API で確認する。受信用 port や webhook の外部公開は不要。
- 初回確認は現在の HEAD SHA を基準として保存するだけで実行しない。以後 SHA が変化したときだけ `pending` の履歴を作成し、SSH 実行をアプリ内 task へ投入する。
- SHA 更新と実行履歴作成は Job row の lock 下で同一 transaction にする。複数 Backend が同時確認しても、同一 SHA の実行履歴は重複作成しない。
- SHA 保存後から task 開始前にプロセスが停止しても、次回起動時に `pending` の GitHub 実行履歴を再投入する。
- PAT は SSH password/private key と同じ Fernet で暗号化し、API には設定有無だけを返す。public repository は PAT なしでも確認でき、private repository は対象 repository の Contents 読み取り権限を持つ fine-grained PAT を使用する。
- GitHub API の ETag を保持し、変更がない確認では response body を再取得しない。確認失敗時はジョブを実行せず、最終確認日時と安全なエラー文を Job に記録する。
- 複数 Backend の API 呼び出し自体を一台へ限定したい場合は、一台だけ `GITHUB_POLLING_ENABLED=True` とし、他を `False` にする。

API の正確な route/schema は FastAPI の `/docs` と `/openapi.json` を正本とする。主要 prefix は `/api/v1/servers`、`/api/v1/jobs`、`/api/v1/executions`。

## 設定と永続化

- 必須環境変数は `DATABASE_URL`、`SECRET_KEY`、`ENCRYPTION_KEY`。全項目は `backend/.env.example` と `backend/app/core/config.py` を参照する。
- Alembic は `backend/alembic/` にあり、Docker 起動時は `backend/scripts/migrate.py` が自動適用する。既存 MVP database は旧 schema を baseline として stamp してから GitHub trigger migration を適用し、空 database は全 revision を適用する。
- Debug 起動時の `Base.metadata.create_all()` は新規開発 database の補助として残しているが、既存 schema の column 追加は行わない。起動前に migration を適用する。
- Compose の DB volume は `postgres_data`。実データを伴う破壊的操作は行わない。

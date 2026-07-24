# Development

## Docker Compose

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f backend frontend
```

- UI: `http://localhost:30682`
- API / OpenAPI UI: `http://localhost:8000` / `http://localhost:8000/docs`
- Backend container は起動前に `python scripts/migrate.py` を実行する。
- `compose.yml` の値は開発用である。本番では secret、DB credential、CORS、Debug を必ず差し替える。
- service に固定 `container_name` があるため、既存環境や別 worktree と併用する前に衝突を確認する。

## ローカル起動

Backend は PostgreSQL と `backend/.env` を用意してから起動する。

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python scripts/migrate.py
uvicorn app.main:app --reload
```

## DB migration

revision chain は次のとおり。

```text
0001_initial_schema → 0002_server_monitoring → 0003_add_github_job_triggers
                    → 0004_resumable_remote_executions → 0005_shared_github_token
```

`scripts/migrate.py` は次を判定して `head` へ移行する。

- 空 DB: 全 revision を適用する。
- Alembic 管理済み DB: 現在 revision から upgrade する。
- 従来の `Base.metadata.create_all()` DB: 存在する監視/trigger column に応じて baseline を登録し、不足 migration を適用する。
- 開発中の旧 GitHub trigger revision 適用済み DB: server monitoring だけを適用し、新しい単一 chain の head へ登録し直す。
- 必須 table や機能 column が一部だけ存在する DB: 自動適用せず停止する。

本番 DB では事前に backup を取得し、schema と migration 手順を rehearsal してから適用する。

## 定期処理設定

GitHub trigger:

- `GITHUB_POLLING_ENABLED`: アプリ内ポーラーの有効/無効。既定 `True`。
- `GITHUB_POLL_INTERVAL_SECONDS`: 確認間隔。既定 60 秒、最小 10 秒。
- `GITHUB_API_TIMEOUT_SECONDS`: GitHub API timeout。既定 10 秒。
- Jobs 画面の「共通トークン」から、複数ジョブで使用する PAT を登録・更新する。値は保存後に再表示されず、共通 PAT を参照するジョブがある間は削除できない。
- GitHub ジョブごとに `認証なし`、`共通トークン`、`ジョブ固有トークン` を選択する。既存の固有 PAT は migration 後もジョブ固有として引き継ぐ。
- private repository は Contents: Read の fine-grained PAT を使用する。public repository は `認証なし` を選択できる。
- 監視対象を変更すると基準 SHA と ETag をリセットし、次回確認は自動実行しない。

サーバ監視:

- `SERVER_MONITOR_ENABLED`: 定期監視の有効/無効。
- `SERVER_CHECK_INTERVAL_SECONDS`: 接続確認間隔。
- `SERVER_CHECK_CONCURRENCY`: 同時確認数。
- `SERVER_INVENTORY_TIMEOUT`: 構成取得 timeout。

ジョブ実行:

- `EXECUTION_TIMEOUT_SECONDS`: detached ジョブ全体の timeout 秒。既定 `0` は無制限。0より大きい場合、期限後にリモート process group を停止できてから `timeout` へ遷移する。
- `SSH_TIMEOUT`: 旧 foreground 実行 API の互換設定。detached ジョブの期限には使用しない。
- `SSH_CONNECT_TIMEOUT`: 1回の SSH 接続 timeout。
- `SSH_KEEPALIVE_INTERVAL_SECONDS` / `SSH_KEEPALIVE_COUNT_MAX`: 一時通信断・half-open 接続の検出設定。
- `EXECUTION_SSH_OPERATION_TIMEOUT_SECONDS`: 1回の SFTP/状態確認操作の timeout。
- `EXECUTION_POLL_INTERVAL_SECONDS`: リモート状態とログの通常確認間隔。
- `EXECUTION_RECONNECT_MAX_INTERVAL_SECONDS`: SSH エラー時の指数 backoff 上限。
- `EXECUTION_LOG_CHUNK_BYTES`: 1 stream・1回あたりに同期する最大ログ量。

実行先は Linux、POSIX shell、SFTP subsystem、`mkdir`、`nohup`、`setsid`、`awk`、`date`、`/proc` を必要とする。実行用 SSH user の home に `~/.local/state/tsubame-ci/executions/` を作成できる必要がある。script とログは認証した user だけが読める permission で保存され、自動削除しないため、容量と保存期間は運用側で監視する。

Frontend は Backend を `localhost:8000` で起動して使用する。

```bash
cd frontend
npm ci
npm run dev
```

## 変更時の確認

- Backend: route → schema → service → model の責務を守り、例外、transaction、認証情報の非露出を確認する。
- Frontend: API URL、request/response 型、loading/error、画面遷移を確認する。
- API 契約: `/openapi.json` と `frontend/src/services/api.ts`・`frontend/src/types/index.ts` を照合する。
- DB: model、migration、既存データの互換性を一体で扱う。
- SSH/実行: timeout、connection close、status 遷移、stdout/stderr、cancel の実効性を確認する。

## 検証コマンド

```bash
docker compose config --quiet
python3 -m compileall -q backend/app
cd backend && python -m unittest discover -s tests -v
cd frontend && npm ci && npm run build
git diff --check
```

Backend には SSH、サーバ監視、GitHub client/poller の `unittest` がある。coverage、Backend lint/type-check、Frontend component/E2E test は未整備である。検証できない項目は成功扱いにせず、理由と影響を報告する。

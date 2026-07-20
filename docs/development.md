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
- private repository は Job 編集画面で Contents: Read の fine-grained PAT を登録する。PAT は保存後に再表示されない。
- 監視対象を変更すると基準 SHA と ETag をリセットし、次回確認は自動実行しない。

サーバ監視:

- `SERVER_MONITOR_ENABLED`: 定期監視の有効/無効。
- `SERVER_CHECK_INTERVAL_SECONDS`: 接続確認間隔。
- `SERVER_CHECK_CONCURRENCY`: 同時確認数。
- `SERVER_INVENTORY_TIMEOUT`: 構成取得 timeout。

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

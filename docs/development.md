# Development

## Docker Compose

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f backend frontend
```

- UI: `http://localhost:30682`
- API / OpenAPI UI: `http://localhost:8000` / `http://localhost:8000/docs`
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

`scripts/migrate.py` は database の状態を判定する。空 database では `alembic upgrade head`、Alembic 導入前の既存 MVP database では `0001_existing_schema_baseline` を stamp してから差分を適用する。GitHub trigger column がすでに `create_all()` で作成済みなら head を stamp する。一部の column だけが存在する不整合状態では自動処理せず停止する。

## GitHubトリガー設定

- `GITHUB_POLLING_ENABLED`: アプリ内ポーラーの有効/無効。既定 `True`。
- `GITHUB_POLL_INTERVAL_SECONDS`: 確認間隔。既定 60 秒、最小 10 秒。
- `GITHUB_API_TIMEOUT_SECONDS`: GitHub API timeout。既定 10 秒。
- private repository は Job 編集画面で fine-grained PAT を登録する。必要権限は対象 repository の Contents: Read。PAT は保存後に再表示されない。
- 監視対象を変更すると基準 SHA と ETag をリセットする。次回の初回確認では自動実行しない。

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
cd frontend && npm ci && npm run build
git diff --check
```

Backend は標準 `unittest` の小規模な service test がある。coverage、Backend lint/type-check、Frontend test は未整備である。検証できない項目は成功扱いにせず、理由と影響を報告する。

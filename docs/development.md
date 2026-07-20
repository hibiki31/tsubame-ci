# Development

## Docker Compose

```bash
docker compose up --build -d
docker compose ps
docker compose logs -f backend frontend
```

- UI: `http://localhost:8888`
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
uvicorn app.main:app --reload
```

## DB migration

新規 DB は Backend 起動前に次を実行する。

```bash
cd backend
alembic upgrade head
```

このプロジェクトで従来使われていた `Base.metadata.create_all()` により作成済みの DB は、先にバックアップを取得し、既存 schema が `0001_initial_schema` と一致することを確認してから baseline を登録する。

```bash
cd backend
alembic stamp 0001_initial_schema
alembic upgrade head
```

Compose の既存 DB を更新する場合は同じコマンドを `docker compose exec backend ...` で実行する。`stamp` は schema を変更せず migration 適用済み位置だけを記録するため、別 schema や一部だけ作成された DB には使わない。

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

Backend には SSH 接続終了処理とサーバ監視の `unittest` がある。coverage、Backend lint/type-check、Frontend component/E2E test はまだない。検証できない項目は成功扱いにせず、理由と影響を報告する。

# AGENTS.md

tsubame-ci は、登録した Linux サーバへ SSH 接続し、シェルスクリプトの実行と履歴確認を Web UI から行う CI/CD アプリケーションである。現状は MVP の骨格まで実装済みだが、Frontend と API の統合は未完了である。

## 作業開始

- 最初に `git status --short --branch` と [`docs/README.md`](docs/README.md) を確認し、実装作業では [`docs/status.md`](docs/status.md) の既知課題も読む。
- 資料と挙動が異なる場合は、コード、設定、実行結果を優先する。`memory-bank/` と `.clinerules` は過去資料であり、現状の正本ではない。
- 未コミット変更は利用者の作業として保護し、依頼外の変更、stash、reset、無関係な整形を行わない。
- 変更は依頼範囲に限定する。秘密情報、実サーバ情報、秘密鍵、実行ログをコミットしない。

## 実装規約

- Backend は `api/v1`（HTTP）→ `services`（業務処理）→ `models`（DB）の依存方向を保ち、入出力は `schemas`、共通設定は `core` に置く。DB と SSH は既存どおり async で扱う。
- Frontend は Vue 3 の `<script setup lang="ts">`、TypeScript strict、Pinia を維持する。画面は `views`、状態は `stores`、通信は `services/api.ts`、共有型は `types` に置く。
- API 変更では Backend の route/schema と Frontend の client/type を同時に照合する。Python schema を契約の基準とし、可能なら OpenAPI で確認する。
- 実行処理を変える場合は、`pending → running → success/failed/timeout/cancelled`、DB commit、ログ保存、timeout、切断時の扱いを一体で検討する。
- SSH 認証情報は Fernet 暗号化を維持する。`known_hosts=None` の適用範囲を広げず、本番向け変更ではホスト鍵検証を必須要件として扱う。
- DB schema 変更では model だけを先行させない。現在 Alembic 環境が未構築なので、migration 方針と導入を変更範囲に含める。

## 検証

変更範囲に応じて最小セットから実行する。

```bash
docker compose config --quiet
python3 -m compileall -q backend/app
cd frontend && npm ci && npm run build
```

- 自動テストと Backend lint の設定はまだない。追加・修正時は可能なら再現テストと設定を同時に整備する。
- Compose の本格起動は稼働中コンテナを確認してから行う。固定 `container_name` があるため、別 worktree の Compose と衝突し得る。
- 完了時は `git diff --check`、`git diff --stat`、`git status --short` を確認し、実行した検証と未実行理由を報告する。

## Git と文書

- 実装作業は既存の依頼専用 branch、または `codex/<type>-<short-name>` を使い、利用者の `main` を直接変更しない。
- commit は依頼された場合に `<prefix>: <日本語の説明>` とする。push、PR、稼働環境の変更は明示依頼がある場合だけ行う。
- API、DB、環境変数、運用手順、重要な設計判断、既知課題を変えた場合だけ関連する `docs/` を更新し、重複説明を増やさない。

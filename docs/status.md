# Project Status

調査時点: 2026-07-24。静的確認、Backend unit test、Frontend production build、Alembic migration、Compose 起動と主要 HTTP endpoint を確認した。

## 現在地

MVP の主要部品は存在する。

- Server の CRUD、SSH 接続テスト、認証情報の Fernet 暗号化
- Server の定期 SSH 接続確認、online/offline 状態・応答時間・hardware/software inventory の保存と表示
- Job の CRUD、SSH script 実行、実行結果の DB 保存
- 手動/GitHub 実行を request から分離するアプリ内 runner、stdout/stderr の逐次保存、実行詳細画面の約2秒間隔の自動更新
- GitHub branch の定期確認、SHA 変更時のジョブ実行、private repository 用 PAT の暗号化保存
- 実行履歴 API と status・stdout/stderr・所要時間の model
- Vue/Vuetify の dashboard、Server、Job、Execution 画面
- PostgreSQL、FastAPI、Vue/Nginx の Compose 構成
- Alembic の初期 schema、サーバ監視、GitHub trigger migration

Python compile、Backend unit test、Frontend production build は成功した。空 DB と Alembic 未導入の旧 MVP DB の migration、Compose 上の Backend health・Jobs API・Frontend・Nginx proxy も確認した。逐次ログ保存は SSH stream の unit test で確認したが、実 SSH server から画面までの End-to-End test は、外部接続先を使用していないため未実施である。

## 既知課題

優先度順。

1. **実行制御が未完成**: 実行 task は Backend process 内で所有するため外部 queue の永続性はなく、強制終了後に `running` の履歴を自動回復できない。cancel は DB status を変えるだけで SSH process の停止を保証しない。
2. **定期処理と実行 runner は単一 worker 前提**: 複数 worker ではサーバ確認と GitHub API request が重複する。実行履歴は row lock で二重実行を抑えるが、scheduler の leader election は未実装である。
3. **migration 運用の実地確認が限定的**: 開発用の空/旧 DB migration は確認したが、production data の backup/restore を含む rehearsal は未実施である。
4. **セキュリティ未完了**: 認証・認可がなく、SSH host key 検証を無効化している。Compose には開発用 secret/DB credential が直書きされている。
5. **品質ゲート不足**: Backend unit test はあるが、DB integration/Frontend/E2E test、Backend lint/type-check、coverage、CI workflow がない。README と旧 `memory-bank/` には古い記述が残る。

## 次の優先事項

1. 主要 CRUD と実行フローの DB integration/E2E test を追加し、OpenAPI と Frontend 型の整合を継続検証する。
2. 外部 queue、再起動時の `running` 整合性、実 cancel を設計し、必要な更新頻度と負荷を確認してから WebSocket/SSE を検討する。
3. Alembic migration の production rehearsal と CI 品質ゲートを整備する。
4. 認証・認可、SSH host key 検証、secret 管理を整えてから本番利用を検討する。

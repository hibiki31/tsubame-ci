# Project Status

調査時点: 2026-07-20。コードと設定の静的確認に加え、Compose 構文、Python 構文、Backend unit test、Alembic offline SQL、Frontend production build を確認した。

## 現在地

MVP の主要部品は存在する。

- Server の CRUD、SSH 接続テスト、認証情報の Fernet 暗号化
- Server の定期 SSH 接続確認、online/offline 状態・応答時間・hardware/software inventory の保存と表示
- Job の CRUD、SSH script 実行、実行結果の DB 保存
- 実行履歴 API と status・stdout/stderr・所要時間の model
- Vue/Vuetify の dashboard、Server（監視・構成情報を含む）、Job、Execution 画面
- PostgreSQL、FastAPI、Vue/Nginx の Compose 構成
- Alembic の初期 schema とサーバ監視 migration

ただし実 SSH サーバを使った End-to-End 動作確認済みとはいえない。Backend unit test 9件、Frontend build、使い捨て PostgreSQL 15 への Alembic migration 実適用は成功した。Compose は廃止済みの `version` 属性を警告する。

## 既知課題

優先度順。

1. **Frontend/API 契約不一致**: 実行開始と Job 別履歴の URL が Backend route と異なる。Frontend は Job/Execution に入れ子情報を期待するが、API は平坦な response を返す。`timeout` status も Frontend 型にない。
2. **実行制御が未完成**: 実行 API は SSH 完了まで応答せず、WebSocket endpoint はない。cancel は DB status を変えるだけで SSH process を停止しない。
3. **監視処理は単一 worker 前提**: Backend process 内 scheduler のため、複数 worker では接続確認が重複する。外部 worker や leader election は未実装である。
4. **既存 DB の baseline 操作が必要**: `create_all()` で作られた既存 DB は、schema 確認と backup 後に `0001_initial_schema` を stamp してから upgrade する必要がある。migration の自動実行はしない。
5. **セキュリティ未完了**: 認証・認可がなく、SSH host key 検証を無効化している。Compose には開発用 secret/DB credential が直書きされている。
6. **品質ゲート不足**: サーバ監視を含む Backend unit test はあるが、Frontend component/E2E test、Backend lint/type-check、coverage、CI workflow がない。README と旧 `memory-bank/` には実装済み画面、公開 port、API に関する古い記述がある。

## 次の優先事項

1. OpenAPI を基準に Frontend/API 契約を揃え、主要 CRUD と実行フローの統合テストを追加する。
2. ジョブを request から分離し、task の所有・再起動時整合性・実 cancel を設計してから WebSocket を追加する。
3. Alembic 適用を deployment 手順へ組み込み、CI 品質ゲートを導入する。
4. 認証・認可、SSH host key 検証、secret 管理を整えてから本番利用を検討する。

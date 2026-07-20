# Project Status

調査時点: 2026-07-20。コードと設定の静的確認に加え、Compose 構文と Python 構文を確認した。

## 現在地

MVP の主要部品は存在する。

- Server の CRUD、SSH 接続テスト、認証情報の Fernet 暗号化
- Job の CRUD、SSH script 実行、実行結果の DB 保存
- 実行履歴 API と status・stdout/stderr・所要時間の model
- Vue/Vuetify の dashboard、Server、Job、Execution 画面
- PostgreSQL、FastAPI、Vue/Nginx の Compose 構成

ただし End-to-End で動作確認済みとはいえない。`docker compose config --quiet` と `python3 -m compileall -q backend/app` は成功したが、Frontend は `npm ci` が完了せず build 未実行、実サービスも未起動である。Compose は廃止済みの `version` 属性を警告する。

## 既知課題

優先度順。

1. **Frontend/API 契約不一致**: 実行開始と Job 別履歴の URL が Backend route と異なる。Frontend は Job/Execution に入れ子情報を期待するが、API は平坦な response を返す。`timeout` status も Frontend 型にない。
2. **実行制御が未完成**: 実行 API は SSH 完了まで応答せず、WebSocket endpoint はない。cancel は DB status を変えるだけで SSH process を停止しない。
3. **接続テスト route の競合**: `/servers/{server_id}` が `/servers/test` より先に登録され、`test` が ID として処理される可能性がある。
4. **本番 DB 更新手段がない**: Alembic は requirements にあるが、設定と migration がない。table 自動作成は Debug 時だけである。
5. **セキュリティ未完了**: 認証・認可がなく、SSH host key 検証を無効化している。Compose には開発用 secret/DB credential が直書きされている。
6. **品質ゲート不足**: Backend/Frontend/E2E test、Backend lint/type-check、CI workflow がない。README と旧 `memory-bank/` には実装済み画面、公開 port、API に関する古い記述がある。

## 次の優先事項

1. OpenAPI を基準に Frontend/API 契約を揃え、主要 CRUD と実行フローの統合テストを追加する。
2. ジョブを request から分離し、task の所有・再起動時整合性・実 cancel を設計してから WebSocket を追加する。
3. Alembic と CI 品質ゲートを導入する。
4. 認証・認可、SSH host key 検証、secret 管理を整えてから本番利用を検討する。
